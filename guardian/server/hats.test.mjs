import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import {
  createHats, hatsSnapshot, spawnAgent, revokeAgent, adjudicateAgent, verifyHats,
  runHatsDemo, exportHatsEvidence, checkpointHats, restoreHats,
  inspectHatsLineage, verifyHatsLineage,
} from './hats.mjs';
import { verifyLedger } from './engine.mjs';

const root = state => state.agents[0];
const child = (state, parent = root(state), extra = {}) => {
  const result = spawnAgent(state, { parentId: parent.id, ...extra });
  assert.equal(result.lastDecision.allowed, true, result.lastDecision.reason);
  return state.agents.at(-1);
};
const tree = state => {
  const meso = child(state);
  const micro = child(state, meso);
  const nano = child(state, micro);
  return { meso, micro, nano };
};
const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const hash = value => createHash('sha256').update(canonical(value)).digest('hex');
const reseal = checkpoint => {
  checkpoint.retained.seal = hash(checkpoint.state);
  checkpoint.checksum = hash({ version: checkpoint.version, state: checkpoint.state, retained: checkpoint.retained });
  return checkpoint;
};

test('HATS roots bind different identities and runs instead of sharing a fixed genesis digest', () => {
  const first = createHats();
  const second = createHats();
  assert.notEqual(first.runId, second.runId);
  assert.notEqual(root(first).id, root(second).id);
  assert.notEqual(root(first).lineageHash, root(second).lineageHash);
  assert.equal(verifyHatsLineage(hatsSnapshot(first)).status, 'PASS');
  assert.equal(verifyHatsLineage({ runId: second.runId, agents: first.agents }).status, 'FAIL');
});

test('Macro, Meso, Micro, and Nano inherit bounded scope with recomputable lineage', () => {
  const state = createHats();
  const { meso, micro, nano } = tree(state);
  assert.deepEqual(state.agents.map(agent => agent.type), ['Macro', 'Meso', 'Micro', 'Nano']);
  assert.deepEqual(state.agents.map(agent => agent.depth), [0, 1, 2, 3]);
  assert.equal(meso.parentId, root(state).id);
  assert.equal(micro.parentId, meso.id);
  assert.equal(nano.parentId, micro.id);
  assert.match(nano.genome.parentStateHash, /^[a-f0-9]{64}$/);
  assert.deepEqual(nano.genome.inheritanceMask, nano.capabilities);
  assert.equal(inspectHatsLineage(state.agents, state.runId).status, 'PASS');
  assert.equal(adjudicateAgent(state, { agentId: nano.id }).syntheticActions, 1);
  assert.match(state.lastDecision.receipt, /^[a-f0-9]{64}$/);
  assert.equal(state.lastDecision.status, 'AUTHORIZED');
  assert.equal(verifyLedger(state.events).valid, true);
});

test('narrowed inheritance prevents further delegation without removing allowed synthetic execution', () => {
  const state = createHats();
  const meso = child(state, root(state), { capabilities: ['invoke:synthetic'] });
  assert.equal(spawnAgent(state, { parentId: meso.id }).lastDecision.code, 'CAPABILITY_DENIED');
  assert.equal(state.agents.length, 2);
  assert.equal(adjudicateAgent(state, { agentId: meso.id }).syntheticActions, 1);
});

test('child scope widening and skipped generation are denied without creating an agent', () => {
  const state = createHats();
  const widened = spawnAgent(state, { parentId: root(state).id, capabilities: ['invoke:external'] });
  assert.equal(widened.lastDecision.code, 'SCOPE_WIDENING');
  assert.equal(widened.lastDecision.receipt, null);
  assert.equal(state.agents.length, 1);
  assert.equal(spawnAgent(state, { type: 'Nano' }).lastDecision.code, 'GENERATION_MISMATCH');
  assert.equal(state.agents.length, 1);
});

test('revocation is rechecked across every current ancestor before execution or spawning', () => {
  const state = createHats();
  const { meso, micro, nano } = tree(state);
  adjudicateAgent(state, { agentId: nano.id });
  revokeAgent(state, { agentId: meso.id });
  const denied = adjudicateAgent(state, { agentId: nano.id });
  assert.equal(denied.lastDecision.allowed, false);
  assert.equal(denied.lastDecision.code, 'ANCESTOR_REVOKED');
  assert.equal(denied.lastDecision.receipt, null);
  assert.equal(denied.syntheticActions, 1);
  assert.equal(spawnAgent(state, { parentId: micro.id }).lastDecision.code, 'ANCESTOR_REVOKED');
  assert.equal(verifyHats(state).verification.verdict, 'PASS');
});

test('missing registered identity preserves UNKNOWN and cannot increment the protected counter', () => {
  const state = createHats();
  for (const operation of [adjudicateAgent, spawnAgent, revokeAgent]) {
    const args = operation === spawnAgent ? { parentId: randomUUID() } : { agentId: randomUUID() };
    const result = operation(state, args);
    assert.equal(result.lastDecision.status, 'UNKNOWN');
    assert.equal(result.lastDecision.allowed, false);
    assert.equal(result.syntheticActions, 0);
  }
  assert.equal(state.agents.length, 1);
});

test('hard generation and child budgets bound fanout without consulting analytics', () => {
  const state = createHats();
  const { nano } = tree(state);
  const denied = spawnAgent(state, { parentId: nano.id });
  assert.equal(denied.lastDecision.code, 'DEPTH_LIMIT');
  child(state);
  child(state);
  assert.equal(spawnAgent(state).lastDecision.code, 'CHILD_LIMIT');
  assert.equal(state.agents.length, 6);
});

test('actual spawn time window independently denies the seventh spawn and releases budget after 60 seconds', () => {
  let now = 1_000;
  const state = createHats({ now: () => now });
  tree(state);
  const secondMeso = child(state);
  const secondMicro = child(state, secondMeso);
  child(state, secondMicro);
  assert.equal(state.agents.length, 7);
  assert.equal(spawnAgent(state).lastDecision.code, 'SPAWN_RATE_LIMIT');
  assert.equal(state.agents.length, 7);
  now += 60_000;
  assert.equal(spawnAgent(state).lastDecision.code, 'SPAWN_AUTHORIZED');
  assert.equal(state.agents.length, 8);
  assert.doesNotThrow(() => restoreHats(checkpointHats(state)));
});

test('the total agent budget persists across time windows and cannot be reset by waiting', () => {
  let now = 1_000;
  const state = createHats({ now: () => now });
  const mesos = [child(state), child(state), child(state)];
  for (let index = 0; index < 8; index += 1) {
    now += 60_001;
    child(state, mesos[Math.floor(index / 3)]);
  }
  assert.equal(state.agents.length, 12);
  now += 60_001;
  assert.equal(spawnAgent(state, { parentId: mesos[2].id }).lastDecision.code, 'AGENT_LIMIT');
  assert.equal(state.agents.length, 12);
});

test('model proposals and unexpected body fields cannot enter authority decisions', () => {
  const state = createHats();
  for (const input of [
    { parentId: root(state).id, analyticEvidence: { authorized: true } },
    { parentId: root(state).id, modelDecision: 'ALLOW' },
    { parentId: root(state).id, now: Date.now() + 60_000 },
    { parentId: root(state).id, specialization: 'raw user prompt or credential' },
  ]) assert.throws(() => spawnAgent(state, input), { code: 'INVALID_HATS_INPUT', status: 400 });
  assert.throws(() => adjudicateAgent(state, { agentId: root(state).id, authority: true }), { code: 'INVALID_HATS_INPUT' });
  assert.equal(state.events.length, 1);
  assert.equal(state.syntheticActions, 0);
});

test('malformed identifiers, types, duplicate capabilities, and unbounded actions are rejected before recording', () => {
  const state = createHats();
  for (const input of [null, [], { parentId: 'not-a-uuid' }, { type: 'Omega' }, { capabilities: ['spawn:agent', 'spawn:agent'] }, { capabilities: ['raw secret value'] }]) {
    assert.throws(() => spawnAgent(state, input), { code: 'INVALID_HATS_INPUT' });
  }
  assert.throws(() => adjudicateAgent(state, { action: 'x'.repeat(500) }), { code: 'INVALID_HATS_INPUT' });
  assert.equal(state.events.length, 1);
});

test('a spawn capability cannot invoke the execution boundary through a different action name', () => {
  const state = createHats();
  const result = adjudicateAgent(state, { action: 'spawn:agent' });
  assert.equal(result.lastDecision.code, 'ACTION_NOT_EXECUTABLE');
  assert.equal(result.syntheticActions, 0);
});

test('public lineage inspection distinguishes missing ancestry from corrupted lineage', () => {
  const state = createHats();
  const { meso } = tree(state);
  const missing = hatsSnapshot(state);
  missing.agents = missing.agents.filter(agent => agent.id !== meso.id);
  assert.equal(verifyHatsLineage(missing).status, 'UNKNOWN');
  for (const change of [
    snapshot => { snapshot.agents[1].nonce = randomUUID(); },
    snapshot => { snapshot.agents[2].parentId = snapshot.agents[0].id; },
    snapshot => { snapshot.agents[1].depth = 2; },
    snapshot => { snapshot.agents[0].parentId = snapshot.agents[3].id; },
    snapshot => { snapshot.agents[1].genome.parentStateHash = '0'.repeat(64); },
    snapshot => { delete snapshot.agents[0].capabilities; },
  ]) {
    const tampered = hatsSnapshot(state);
    change(tampered);
    assert.equal(verifyHatsLineage(tampered).status, 'FAIL');
  }
  assert.equal(verifyHatsLineage({ agents: [], runId: state.runId }).status, 'UNKNOWN');
});

test('engine-retained state seal prevents policy, identity, decision, counter, and ledger edits from creating authority', () => {
  for (const mutate of [
    state => { state.agents[0].capabilities.push('invoke:external'); },
    state => { state.agents[0].revoked = true; },
    state => { state.policy.maxDepth = 99; },
    state => { state.syntheticActions = 100; },
    state => { state.events[0].message = 'forged genesis'; },
    state => { state.lastDecision = { allowed: true }; },
    state => { state.agents = null; },
    state => { state.events = null; },
    state => { state.demo = { verdict: 'PASS', steps: null }; },
  ]) {
    const state = createHats();
    mutate(state);
    assert.throws(() => adjudicateAgent(state), { code: 'HATS_STATE_INTEGRITY' });
    assert.throws(() => checkpointHats(state), { code: 'INVALID_HATS_CHECKPOINT' });
    assert.equal(verifyHats(state).verification.verdict, 'FAIL');
  }
});

test('the guided demo records eleven falsifiable assertions and no post-revocation counter increment', () => {
  const state = createHats();
  const result = runHatsDemo(state);
  assert.equal(result.demo.completed, true);
  assert.equal(result.demo.steps.length, 11);
  assert.equal(result.demo.steps.every(step => step.passed), true);
  assert.equal(result.demo.verdict, 'PASS');
  assert.equal(result.verification.verdict, 'PASS');
  assert.equal(result.syntheticActions, 1);
  assert.equal(result.lastDecision.code, 'ANCESTOR_REVOKED');
  assert.deepEqual(runHatsDemo(state), result, 'a completed demo is idempotent');
  assert.equal(result.ledgerVerification.valid, true);
  assert.deepEqual(hatsSnapshot(restoreHats(JSON.parse(JSON.stringify(checkpointHats(state))))), result);
});

test('a nonfresh lab refuses a guided demo instead of silently replacing user evidence', () => {
  const state = createHats();
  child(state);
  const runId = state.runId;
  const result = runHatsDemo(state);
  assert.equal(result.lastDecision.code, 'DEMO_REQUIRES_RESET');
  assert.equal(result.demo, null);
  assert.equal(result.runId, runId);
  assert.equal(result.agents.length, 2);
});

test('evidence and snapshots are detached and make no signature or origin claim', () => {
  const state = createHats();
  runHatsDemo(state);
  const bundle = exportHatsEvidence(state);
  assert.equal(bundle.component, 'HATS');
  assert.equal(bundle.origin.trusted, false);
  assert.equal(bundle.origin.signaturesVerified, false);
  assert.equal(bundle.state.verification.originTrusted, false);
  assert.equal(bundle.state.lastDecision.receipt, null);
  assert.equal('retained' in bundle, false);
  assert.equal('checkpoint' in bundle, false);
  bundle.state.agents[0].revoked = false;
  bundle.state.events[0].message = 'mutated copy';
  assert.equal(hatsSnapshot(state).agents[0].revoked, true);
  assert.equal(verifyLedger(hatsSnapshot(state).events).valid, true);
});

test('fresh checkpoint restoration does not depend on a clock returning the same millisecond twice', () => {
  let clock = 1_000;
  const state = createHats({ now: () => clock++ });
  assert.equal(state.createdAt, root(state).createdAt);
  const restored = restoreHats(JSON.parse(JSON.stringify(checkpointHats(state))), { now: () => clock++ });
  assert.deepEqual(hatsSnapshot(restored), hatsSnapshot(state));
  child(restored);
  assert.equal(hatsSnapshot(restoreHats(checkpointHats(restored))).agents.length, 2);
});

test('checkpoint restore rejects altered checksums, forged counters, changed policy, and inconsistent registrations', () => {
  const state = createHats();
  tree(state);
  adjudicateAgent(state);
  const original = checkpointHats(state);
  for (const mutate of [
    checkpoint => { checkpoint.checksum = 'f'.repeat(64); },
    checkpoint => { checkpoint.state.syntheticActions = 999; reseal(checkpoint); },
    checkpoint => { checkpoint.state.policy.maxDepth = 99; reseal(checkpoint); },
    checkpoint => { checkpoint.state.agents[1].revoked = true; reseal(checkpoint); },
    checkpoint => { checkpoint.state.lastDecision = null; reseal(checkpoint); },
    checkpoint => { checkpoint.extra = 'unsupported'; },
  ]) {
    const altered = structuredClone(original);
    mutate(altered);
    assert.throws(() => restoreHats(altered), { code: 'INVALID_HATS_CHECKPOINT' });
  }
});

test('checkpoint JSON boundary rejects cyclic, nonfinite, accessor, sparse, and oversized values', () => {
  const original = checkpointHats(createHats());
  for (const value of [undefined, NaN, Infinity, new Date(), { ...original, extra: 'x'.repeat(1_048_577) }]) {
    assert.throws(() => restoreHats(value), { code: 'INVALID_HATS_CHECKPOINT' });
  }
  const cyclic = { ...original }; cyclic.self = cyclic;
  assert.throws(() => restoreHats(cyclic), { code: 'INVALID_HATS_CHECKPOINT' });
  const getter = { ...original }; Object.defineProperty(getter, 'extra', { enumerable: true, get: () => { throw new Error('must not execute'); } });
  assert.throws(() => restoreHats(getter), { code: 'INVALID_HATS_CHECKPOINT' });
  assert.throws(() => restoreHats({ ...original, extra: new Array(3) }), { code: 'INVALID_HATS_CHECKPOINT' });
});

test('an unanchored rewrite can be internally consistent without gaining trusted origin', () => {
  const bundle = exportHatsEvidence(createHats());
  const agent = bundle.state.agents[0];
  agent.specialization = 'analysis';
  const { revoked, lineageHash: previous, ...identity } = agent;
  agent.lineageHash = hash({ domain: 'unison-hats-lineage-v1', runId: bundle.state.runId, ...identity, parentHash: 'GENESIS' });
  assert.equal(verifyHatsLineage(bundle.state).status, 'PASS');
  assert.equal(verifyHatsLineage(bundle.state).originTrusted, false);
  assert.notEqual(agent.lineageHash, previous);
});

test('run event limit denies further effects while retaining exportable evidence', () => {
  const state = createHats();
  for (let index = 1; index < 200; index += 1) adjudicateAgent(state);
  assert.equal(state.events.length, 200);
  assert.throws(() => adjudicateAgent(state), { code: 'EVENT_LIMIT', status: 429 });
  assert.equal(exportHatsEvidence(state).state.syntheticActions, 199);
});
