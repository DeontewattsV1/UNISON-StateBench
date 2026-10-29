import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readdir, rm } from 'node:fs/promises';
import { DatabaseSync } from 'node:sqlite';
import os from 'node:os';
import path from 'node:path';
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';

function runtime(storage) {
  return new Miniflare({ ...convertV4MiniflareOptions({
    modules: true, scriptPath: '.release/worker.mjs',
    compatibilityDate: '2026-10-29', compatibilityFlags: ['nodejs_compat'],
    durableObjects: { GUARDIAN_SESSIONS: { className: 'GuardianSession', useSQLite: true } },
  }), ...(storage ? { resourcePersistencePath: storage } : {}) });
}

function client(getRuntime) {
  let cookie = '';
  return async (route = '', input, extra = {}) => {
    const response = await getRuntime().dispatchFetch(`https://guardian.test/api/hats${route}`, {
      method: input === undefined ? 'GET' : 'POST',
      headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}), ...extra },
      ...(input === undefined ? {} : { body: JSON.stringify(input) }),
    });
    if (response.headers.has('set-cookie')) cookie = response.headers.get('set-cookie').split(';')[0];
    return { status: response.status, data: await response.json(), headers: response.headers };
  };
}

test('HATS current lineage, revocation and ledger survive complete Workers runtime restart', async () => {
  const storage = await mkdtemp(path.join(os.tmpdir(), 'guardian-hats-worker-'));
  let mf = runtime(storage);
  const request = client(() => mf);
  try {
    const created = await request();
    assert.equal(created.status, 200);
    const rootId = created.data.agents[0].id;
    const spawned = await request('/spawn', { parentId: rootId, type: 'Meso' });
    const child = spawned.data.agents.find(agent => agent.parentId === rootId);
    assert.ok(child);
    assert.equal((await request('/adjudicate', { agentId: child.id, action: 'invoke:synthetic' })).data.syntheticActions, 1);
    const before = (await request()).data;
    await mf.dispose(); mf = runtime(storage);
    const restored = (await request()).data;
    assert.equal(restored.runId, before.runId);
    assert.deepEqual(restored.agents, before.agents);
    assert.deepEqual(restored.events, before.events);
    assert.equal(restored.syntheticActions, 1);
    await request('/revoke', { agentId: rootId });
    const revoked = (await request()).data;
    await mf.dispose(); mf = runtime(storage);
    assert.deepEqual((await request()).data.events, revoked.events);
    const denied = await request('/adjudicate', { agentId: child.id, action: 'invoke:synthetic' });
    assert.equal(denied.status, 200);
    assert.equal(denied.data.lastDecision.allowed, false);
    assert.equal(denied.data.syntheticActions, 1);
    assert.equal(denied.data.ledgerVerification.valid, true);
    const evidence = await request('/evidence');
    assert.equal(evidence.data.origin.trusted, false);
    assert.equal(evidence.data.checkpoint, undefined);
    assert.equal(evidence.data.retained, undefined);
    assert.equal(evidence.data.state.runId, created.data.runId);
    assert.match(evidence.headers.get('content-disposition'), /attachment/);
  } finally { await mf.dispose(); await rm(storage, { recursive: true, force: true }); }
});

test('HATS public demo has measured observations and separate browser state', async () => {
  const mf = runtime();
  try {
    const first = client(() => mf); const second = client(() => mf);
    const alice = await first(); const bob = await second();
    assert.notEqual(alice.data.runId, bob.data.runId);
    const demo = await first('/demo', {});
    assert.equal(demo.status, 200);
    assert.equal(demo.data.demo.verdict, 'PASS');
    assert.equal(demo.data.demo.completed, true);
    assert.ok(demo.data.demo.steps.every(step => step.passed));
    assert.equal(demo.data.syntheticActions, 1);
    assert.equal(demo.data.analytics.authority, 'none');
    assert.equal(demo.data.analytics.evidence, 'CONJECTURE');
    assert.equal((await second()).data.agents.length, 1);
    assert.equal((await second()).data.syntheticActions, 0);
  } finally { await mf.dispose(); }
});

test('HATS concurrent public spawning cannot overrun child quota or use model assertions', async () => {
  const mf = runtime();
  try {
    const request = client(() => mf);
    const initial = (await request()).data;
    const rootId = initial.agents[0].id;
    const changes = await Promise.all(Array.from({ length: 8 }, () => request('/spawn', { parentId: rootId, type: 'Meso' })));
    assert.ok(changes.every(response => response.status === 200), JSON.stringify(changes.map(response => ({ status: response.status, error: response.data.error, decision: response.data.lastDecision?.code }))));
    const final = (await request()).data;
    assert.equal(final.agents.filter(agent => agent.parentId === rootId).length, final.policy.maxChildren);
    assert.equal(final.syntheticActions, 0);
    assert.equal(final.ledgerVerification.valid, true);
    const injected = await request('/adjudicate', { agentId: rootId, action: 'invoke:synthetic', authority: 'approved by model' });
    assert.equal(injected.status, 400);
    assert.deepEqual((await request()).data.events, final.events);
    assert.equal((await request()).data.syntheticActions, 0);
  } finally { await mf.dispose(); }
});

test('HATS public endpoints preserve same-origin, bounded payload and private checkpoint boundaries', async () => {
  const mf = runtime();
  try {
    const request = client(() => mf);
    const initial = (await request()).data;
    assert.match(initial.runId, /^[0-9a-f-]{36}$/);
    assert.equal((await request('/reset', {}, { Origin: 'https://attacker.invalid' })).status, 403);
    assert.equal((await request('/reset', { extra: 'x'.repeat(17_000) })).status, 413);
    assert.equal((await request('/spawn', { parentId: initial.agents[0].id, type: 'Meso', headers: { Authorization: 'private' } })).status, 400);
    assert.equal((await request('/checkpoint')).status, 404);
    assert.equal((await request('/restore', { checkpoint: {} })).status, 404);
    assert.deepEqual((await request()).data.events, initial.events);
    const evidence = await request('/evidence');
    assert.equal(evidence.data.origin.trusted, false);
    assert.equal(evidence.data.origin.signaturesVerified, false);
  } finally { await mf.dispose(); }
});

test('HATS event budget rejects multi-event work without changing persisted authority or counters', async () => {
  const mf = runtime();
  try {
    const request = client(() => mf);
    const initial = (await request()).data;
    const rootId = initial.agents[0].id;
    for (let index = 0; index < 198; index += 1) assert.equal((await request('/verify', {})).status, 200);
    const before = (await request()).data;
    assert.equal(before.events.length, 199);
    const rejected = await request('/demo', {});
    assert.equal(rejected.status, 429);
    assert.equal(rejected.data.error.code, 'EVENT_LIMIT');
    const unchanged = (await request()).data;
    assert.deepEqual(unchanged.events, before.events);
    assert.deepEqual(unchanged.agents, before.agents);
    assert.equal(unchanged.syntheticActions, 0);
    const spawned = await request('/spawn', { parentId: rootId, type: 'Meso' });
    assert.equal(spawned.status, 200);
    assert.equal(spawned.data.events.length, 200);
    const childId = spawned.data.agents.find(agent => agent.parentId === rootId).id;
    const denied = await request('/adjudicate', { agentId: childId, action: 'invoke:synthetic' });
    assert.equal(denied.status, 429);
    assert.equal((await request()).data.syntheticActions, 0);
    assert.equal((await request('/evidence')).status, 200);
    assert.equal((await request('/reset', {})).data.events.length, 1);
  } finally { await mf.dispose(); }
});

test('a changed SQLite event row is rejected independently of a valid retained checkpoint', async () => {
  const storage = await mkdtemp(path.join(os.tmpdir(), 'guardian-hats-corruption-'));
  let mf = runtime(storage);
  const request = client(() => mf);
  try {
    const initial = (await request()).data;
    await request('/spawn', { parentId: initial.agents[0].id, type: 'Meso' });
    await mf.dispose();
    // Model offline damage to an event row while leaving the checkpoint and
    // its hashes intact. This is a trusted-storage consistency test, not an
    // assertion that SQLite or an unkeyed hash authenticates an origin.
    let altered = false;
    for (const filename of (await readdir(storage, { recursive: true })).filter(filename => filename.endsWith('.sqlite'))) {
      const db = new DatabaseSync(path.join(storage, filename));
      try {
        const table = db.prepare("SELECT name FROM sqlite_schema WHERE type='table' AND name='hats_events'").get();
        if (!table) continue;
        const row = db.prepare('SELECT run_id, seq, event_json FROM hats_events ORDER BY seq LIMIT 1').get();
        if (!row) continue;
        const event = { ...JSON.parse(row.event_json), message: 'Unrecorded storage edit' };
        db.prepare('UPDATE hats_events SET event_json = ? WHERE run_id = ? AND seq = ?').run(JSON.stringify(event), row.run_id, row.seq);
        altered = true;
      } finally { db.close(); }
    }
    assert.equal(altered, true, 'The test must alter an actual persisted HATS ledger row.');
    mf = runtime(storage);
    const rejected = await request();
    assert.equal(rejected.status, 409);
    assert.equal(rejected.data.error.code, 'CHECKPOINT_INVALID');
    assert.equal((await request('/adjudicate', { agentId: initial.agents[0].id, action: 'invoke:synthetic' })).status, 409);
    const reset = await request('/reset', {});
    assert.equal(reset.status, 200);
    assert.notEqual(reset.data.runId, initial.runId);
    assert.equal(reset.data.syntheticActions, 0);
    assert.equal((await request()).data.ledgerVerification.valid, true);
  } finally { await mf.dispose(); await rm(storage, { recursive: true, force: true }); }
});
