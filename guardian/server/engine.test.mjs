import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  createSandbox, snapshot, runBaseline, revokeAuthority, replayQueued,
  verifySandbox, exportEvidence, verifyLedger, evaluateAuthority,
  checkpointSandbox, restoreSandbox,
} from './engine.mjs';

const check = (state, id) => state.results.checks.find(item => item.id === id);

test('delegated and queued authority is invalidated by revoking its ancestor', () => {
  const sandbox = createSandbox();
  assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'delegate').allowed, true);
  runBaseline(sandbox);
  assert.equal(snapshot(sandbox).stats.protectedActions, 1);
  assert.equal(snapshot(sandbox).queue[0].authorizationAtEnqueue, true);
  revokeAuthority(sandbox);
  assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'delegate').allowed, false);
  assert.equal(evaluateAuthority(sandbox, 'grant-queued', 'queued-worker').allowed, false);
  const replay = replayQueued(sandbox);
  assert.equal(replay.queue[0].status, 'blocked');
  assert.equal(replay.queue[0].authorizationAtCommit, false);
  assert.equal(replay.stats.protectedActions, 1, 'a stale queued job must not produce a second action');
  const verified = verifySandbox(sandbox);
  assert.equal(verified.results.verdict, 'PASS');
  assert.deepEqual(verified.results.residualPaths, []);
  assert.equal(verifyLedger(verified.events).valid, true);
});

test('verification refuses to certify a revocation before queued enforcement is tested', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  revokeAuthority(sandbox);
  const verified = verifySandbox(sandbox);
  assert.equal(check(verified, 'queue').status, 'UNKNOWN');
  assert.equal(verified.results.verdict, 'UNKNOWN');
});

test('an independent service grant leaves a registered route after primary revocation', () => {
  const sandbox = createSandbox('alternate');
  runBaseline(sandbox);
  revokeAuthority(sandbox);
  replayQueued(sandbox);
  const verified = verifySandbox(sandbox);
  assert.equal(verified.results.verdict, 'FAIL');
  assert.equal(check(verified, 'paths').status, 'FAIL');
  assert.deepEqual(verified.results.residualPaths, [['operator', 'service', 'gateway', 'protected-action']]);
  assert.equal(evaluateAuthority(sandbox, 'grant-independent', 'service-account').allowed, true);
  assert.equal(check(verified, 'queue').status, 'PASS', 'queue denial alone cannot prove total revocation');
});

test('an incomplete registry remains UNKNOWN even when every known route is disconnected', () => {
  const sandbox = createSandbox('unknown');
  runBaseline(sandbox);
  revokeAuthority(sandbox);
  replayQueued(sandbox);
  const verified = verifySandbox(sandbox);
  assert.equal(check(verified, 'paths').status, 'PASS');
  assert.equal(check(verified, 'inventory').status, 'UNKNOWN');
  assert.equal(verified.results.verdict, 'UNKNOWN');
});

test('principals and action scopes cannot borrow another registered grant', () => {
  const sandbox = createSandbox();
  assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'attacker').allowed, false);
  assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'delegate', 'delete:everything').allowed, false);
  assert.equal(evaluateAuthority(sandbox, 'invented', 'delegate').allowed, false);
});

test('missing and cyclic delegation ancestry is denied rather than repaired by inference', () => {
  for (const ancestor of ['missing-root', 'grant-delegate']) {
    const sandbox = createSandbox();
    sandbox.grants.find(grant => grant.id === 'grant-delegate').parentId = ancestor;
    assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'delegate').allowed, false);
    assert.throws(() => runBaseline(sandbox), { code: 'STATE_INTEGRITY' });
    const verified = verifySandbox(sandbox);
    assert.equal(verified.results.verdict, 'FAIL');
  }
});

test('a newly invented path or widened grant cannot enter the sealed registry silently', () => {
  const sandbox = createSandbox();
  sandbox.edges.push({ id: 'fake', source: 'operator', target: 'protected-action', label: 'fake', grantId: null });
  const verified = verifySandbox(sandbox);
  assert.equal(check(verified, 'inventory').status, 'FAIL');
  assert.equal(verified.results.verdict, 'FAIL');
  assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'delegate').allowed, false);
});

test('restoring a revoked flag without an engine transition cannot resurrect authority', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  revokeAuthority(sandbox);
  sandbox.grants[0].revoked = false;
  assert.equal(evaluateAuthority(sandbox, 'grant-queued', 'queued-worker').allowed, false);
  assert.throws(() => replayQueued(sandbox), { code: 'STATE_INTEGRITY' });
});

test('baseline, revoke, and queued replay are idempotent for a completed operation', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  const baseline = snapshot(sandbox);
  runBaseline(sandbox);
  assert.deepEqual(snapshot(sandbox), baseline);
  revokeAuthority(sandbox);
  const revoked = snapshot(sandbox);
  revokeAuthority(sandbox);
  assert.deepEqual(snapshot(sandbox), revoked);
  replayQueued(sandbox);
  const replayed = snapshot(sandbox);
  replayQueued(sandbox);
  assert.deepEqual(snapshot(sandbox), replayed);
});

test('queue execution before revocation is permitted but is not a post-revocation test', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  assert.equal(replayQueued(sandbox).stats.protectedActions, 2);
  revokeAuthority(sandbox);
  const verified = verifySandbox(sandbox);
  assert.equal(check(verified, 'queue').status, 'UNKNOWN');
  assert.equal(verified.results.verdict, 'UNKNOWN');
});

test('revocation before baseline fails closed and creates no stale authorized work', () => {
  const sandbox = createSandbox();
  revokeAuthority(sandbox);
  const state = runBaseline(sandbox);
  assert.equal(state.stats.protectedActions, 0);
  assert.equal(state.queue.length, 0);
  assert.equal(state.events.at(-1).type, 'action.denied');
});

test('ledger verification recomputes body hashes and validates sequence, links, and run references', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  const original = snapshot(sandbox).events;
  assert.equal(verifyLedger(original).valid, true);
  for (const change of [
    events => { events[1].message = 'fabricated execution'; },
    events => { events[1].previousHash = 'f'.repeat(64); },
    events => { events[1].seq = 20; },
    events => { events[1].id = events[0].id; },
    events => { events[1].runId = 'unrelated-run'; },
  ]) {
    const tampered = structuredClone(original);
    change(tampered);
    assert.equal(verifyLedger(tampered).valid, false);
  }
  assert.equal(verifyLedger([]).status, 'UNKNOWN');
});

test('a recomputed exported chain has no cryptographic origin trust', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  const events = snapshot(sandbox).events;
  events[1].message = 'an attacker can rewrite an unanchored export';
  const canonical = value => {
    if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
    if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
    return JSON.stringify(value);
  };
  for (let index = 0; index < events.length; index += 1) {
    events[index].previousHash = index === 0 ? '0'.repeat(64) : events[index - 1].hash;
    const { hash, ...body } = events[index];
    events[index].hash = createHash('sha256').update(canonical(body)).digest('hex');
  }
  const exportedCheck = verifyLedger(events);
  assert.equal(exportedCheck.valid, true);
  assert.equal(exportedCheck.originTrusted, false);
  assert.equal(exportedCheck.signaturesVerified, false);
  sandbox.events = events;
  assert.equal(verifySandbox(sandbox).results.verdict, 'FAIL', 'the live process detects replacement of its retained tip');
});

test('evidence export is detached and identifies simulations and origin limits', () => {
  const sandbox = createSandbox();
  const bundle = exportEvidence(sandbox);
  assert.equal(bundle.evidenceClass, 'SIMULATED');
  assert.equal(bundle.origin.trusted, false);
  assert.equal(bundle.ledgerVerification.valid, true);
  bundle.state.grants[0].revoked = true;
  assert.equal(snapshot(sandbox).grants[0].revoked, false);
});

test('a forged reported verdict cannot replace the process-retained finding in an export', () => {
  const sandbox = createSandbox();
  sandbox.results = { verdict: 'PASS', checks: [], residualPaths: [] };
  const exported = exportEvidence(sandbox);
  assert.equal(exported.state.results.verdict, 'FAIL');
  assert.match(exported.state.integrityErrors.join(' '), /verification result changed/);
  assert.throws(() => runBaseline(sandbox), { code: 'STATE_INTEGRITY' });
});

test('malformed state collections produce bounded failure snapshots and deny mutations', () => {
  const corruptions = [
    sandbox => { sandbox.grants = null; },
    sandbox => { sandbox.grants = [null]; },
    sandbox => { sandbox.grants = [1, 'unregistered']; },
    sandbox => { sandbox.nodes = null; },
    sandbox => { sandbox.nodes = [null]; },
    sandbox => { sandbox.edges = null; },
    sandbox => { sandbox.edges = [null]; },
    sandbox => { sandbox.queue = null; },
    sandbox => { sandbox.queue = [null]; },
    sandbox => { sandbox.events = null; },
    sandbox => { sandbox.events = [null]; },
  ];
  for (const corrupt of corruptions) {
    const sandbox = createSandbox();
    runBaseline(sandbox);
    corrupt(sandbox);
    const projected = snapshot(sandbox);
    assert.equal(projected.results.verdict, 'FAIL');
    assert.ok(projected.integrityErrors.length > 0);
    assert.ok(projected.edges.every(edge => edge.active === false));
    assert.ok(projected.grants.every(grant => grant.active === false));
    assert.doesNotThrow(() => JSON.stringify(projected));
    assert.equal(evaluateAuthority(sandbox, 'grant-delegate', 'delegate').allowed, false);
    assert.throws(() => replayQueued(sandbox), { code: 'STATE_INTEGRITY' });
    assert.equal(verifySandbox(sandbox).results.verdict, 'FAIL');
    assert.equal(exportEvidence(sandbox).state.results.verdict, 'FAIL');
  }
});

test('damaged ledger projection preserves its failed check rather than certifying a sanitized empty array', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  revokeAuthority(sandbox);
  replayQueued(sandbox);
  assert.equal(verifySandbox(sandbox).results.verdict, 'PASS');
  sandbox.events = null;
  const exported = exportEvidence(sandbox);
  assert.equal(exported.state.results.verdict, 'FAIL', 'a prior valid finding cannot survive corrupted state');
  assert.deepEqual(exported.state.events, []);
  assert.equal(exported.ledgerVerification.valid, false);
  assert.equal(exported.ledgerVerification.status, 'FAIL');
  assert.match(exported.ledgerVerification.detail, /must be an array/);
});

test('unsupported scenarios are rejected explicitly', () => {
  assert.throws(() => createSandbox('silently-safe'), RangeError);
});

test('trusted checkpoints preserve execution identity and queued revocation across process rehydration', () => {
  let sandbox = createSandbox('queued', { deployment: 'Cloudflare Durable Object synthetic sandbox' });
  const initial = snapshot(sandbox);
  runBaseline(sandbox);
  const beforeRestart = snapshot(sandbox);
  sandbox = restoreSandbox(JSON.parse(JSON.stringify(checkpointSandbox(sandbox))));
  assert.deepEqual(snapshot(sandbox), beforeRestart);
  assert.equal(snapshot(sandbox).identity.deployment, 'Cloudflare Durable Object synthetic sandbox');
  revokeAuthority(sandbox);
  const revoked = snapshot(sandbox);
  sandbox = restoreSandbox(checkpointSandbox(sandbox));
  assert.deepEqual(snapshot(sandbox), revoked);
  assert.equal(replayQueued(sandbox).stats.protectedActions, 1);
  const verified = verifySandbox(sandbox);
  assert.equal(verified.results.verdict, 'PASS');
  assert.equal(verified.runId, initial.runId);
  assert.deepEqual(verified.identity, initial.identity);
  assert.deepEqual(verified.events.slice(0, beforeRestart.events.length), beforeRestart.events);
  assert.equal(verified.results.originTrusted, false);
  assert.equal(verified.ledgerVerification.signaturesVerified, false);
});

test('trusted rehydration preserves residual-path FAIL and incomplete-registry UNKNOWN findings', () => {
  for (const [scenario, verdict] of [['alternate', 'FAIL'], ['unknown', 'UNKNOWN']]) {
    let sandbox = createSandbox(scenario);
    runBaseline(sandbox);
    sandbox = restoreSandbox(checkpointSandbox(sandbox));
    revokeAuthority(sandbox);
    replayQueued(sandbox);
    const completed = verifySandbox(sandbox);
    assert.equal(completed.results.verdict, verdict);
    sandbox = restoreSandbox(checkpointSandbox(sandbox));
    assert.deepEqual(snapshot(sandbox), completed);
    assert.equal(snapshot(sandbox).results.verdict, verdict);
  }
});

test('restoring completed findings preserves idempotency and exact ledger hashes', () => {
  let sandbox = createSandbox();
  replayQueued(sandbox); // Exercise the retained empty-replay observation flag.
  runBaseline(sandbox);
  revokeAuthority(sandbox);
  replayQueued(sandbox);
  const original = verifySandbox(sandbox);
  sandbox = restoreSandbox(checkpointSandbox(sandbox));
  assert.deepEqual(runBaseline(sandbox), original);
  assert.deepEqual(revokeAuthority(sandbox), original);
  assert.deepEqual(replayQueued(sandbox), original);
  assert.equal(verifyLedger(snapshot(sandbox).events).valid, true);
});

test('checkpoint objects and restored sandboxes are detached from their sources', () => {
  const source = createSandbox();
  runBaseline(source);
  const saved = checkpointSandbox(source);
  const restored = restoreSandbox(saved);
  const before = snapshot(source);
  saved.state.grants[0].revoked = true;
  saved.retained.jobs[0][1].status = 'blocked';
  assert.deepEqual(snapshot(source), before);
  assert.deepEqual(snapshot(restored), before);
  revokeAuthority(restored);
  assert.equal(snapshot(source).grants[0].revoked, false);
  assert.equal(snapshot(restored).grants[0].revoked, true);
});

test('checkpointing a corrupt sandbox fails before it can become trusted server state', () => {
  const sandbox = createSandbox();
  sandbox.grants[0].revoked = true;
  assert.throws(() => checkpointSandbox(sandbox), { code: 'STATE_INTEGRITY' });
});

// Re-sealing here deliberately shows that the unkeyed checksum is not an
// authenticity boundary. Restore must still reject inconsistent retained data.
function resealCheckpoint(saved) {
  const canonical = value => {
    if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
    if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
    return JSON.stringify(value);
  };
  const { checksum, ...body } = saved;
  saved.checksum = createHash('sha256').update(canonical(body)).digest('hex');
  return saved;
}

test('restore rejects unsupported versions and malformed or missing retained state', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  const corruptions = [
    saved => { saved.version = 2; },
    saved => { delete saved.retained; },
    saved => { saved.retained = null; },
    saved => { delete saved.retained.inventoryHash; },
    saved => { saved.retained.registeredInventory = {}; },
    saved => { saved.retained.revocations = []; },
    saved => { saved.retained.revocations[1][0] = saved.retained.revocations[0][0]; },
    saved => { saved.retained.jobs = [[saved.state.queue[0].id, null]]; },
    saved => { saved.retained.baselineDone = null; },
    saved => { saved.retained.ledgerLength = -1; },
    saved => { saved.state.events = [null]; },
    saved => { saved.state.queue = null; },
    saved => { saved.state.grants = [null]; },
    saved => { saved.state.identity = null; },
  ];
  for (const corrupt of corruptions) {
    const saved = checkpointSandbox(sandbox);
    corrupt(saved);
    resealCheckpoint(saved);
    assert.throws(() => restoreSandbox(saved), { code: 'INVALID_CHECKPOINT' });
  }
});

test('restore rejects changed public state or transition receipts against retained checkpoint metadata', () => {
  const sandbox = createSandbox();
  runBaseline(sandbox);
  const corruptions = [
    saved => { saved.state.grants[0].revoked = true; },
    saved => { saved.state.queue[0].principal = 'different-principal'; },
    saved => { saved.state.events[1].message = 'fabricated action'; },
    saved => { saved.state.protectedActions = 99; },
    saved => { saved.retained.baselineDone = false; },
    saved => { saved.retained.emptyReplayRecorded = true; },
    saved => { saved.retained.ledgerTip = 'f'.repeat(64); },
    saved => { saved.retained.verificationResult = { verdict: 'PASS' }; },
  ];
  for (const corrupt of corruptions) {
    const saved = checkpointSandbox(sandbox);
    corrupt(saved);
    resealCheckpoint(saved);
    assert.throws(() => restoreSandbox(saved), { code: 'INVALID_CHECKPOINT' });
  }
});

test('restore rejects modified bytes, oversized data, cycles, and non-JSON values', () => {
  const saved = checkpointSandbox(createSandbox());
  const modified = structuredClone(saved);
  modified.state.identity.deployment = 'modified after persistence';
  assert.throws(() => restoreSandbox(modified), { code: 'INVALID_CHECKPOINT' });
  assert.throws(() => restoreSandbox({ ...saved, oversized: 'x'.repeat(4 * 1024 * 1024 + 1) }), { code: 'INVALID_CHECKPOINT' });
  const cyclic = structuredClone(saved);
  cyclic.state.self = cyclic;
  assert.throws(() => restoreSandbox(cyclic), { code: 'INVALID_CHECKPOINT' });
  assert.throws(() => restoreSandbox({ ...saved, discarded: undefined }), { code: 'INVALID_CHECKPOINT' });
});

test('server deployment labels are sealed metadata and do not upgrade identity trust', () => {
  const sandbox = createSandbox('queued', { deployment: 'Cloudflare Durable Object synthetic sandbox' });
  const restored = restoreSandbox(checkpointSandbox(sandbox));
  assert.equal(snapshot(restored).identity.deployment, 'Cloudflare Durable Object synthetic sandbox');
  assert.match(snapshot(restored).identity.owner, /^UNKNOWN/);
  assert.equal(exportEvidence(restored).origin.trusted, false);
  assert.throws(() => createSandbox('queued', { deployment: '' }), RangeError);
  sandbox.identity.deployment = 'unsealed replacement';
  assert.throws(() => checkpointSandbox(sandbox), { code: 'STATE_INTEGRITY' });
});
