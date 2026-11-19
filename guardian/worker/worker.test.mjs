import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';

function runtime(storage) {
  // Use the same workerd generation as the pinned Wrangler toolchain.
  return new Miniflare({ ...convertV4MiniflareOptions({
    modules: true, scriptPath: '.release/worker.mjs',
    compatibilityDate: '2026-10-29', compatibilityFlags: ['nodejs_compat'],
    durableObjects: { GUARDIAN_SESSIONS: { className: 'GuardianSession', useSQLite: true } },
  }), ...(storage ? { resourcePersistencePath: storage } : {}) });
}
function client(getRuntime) {
  let cookie = '';
  return async (name, input, extra = {}) => {
    const res = await getRuntime().dispatchFetch(`https://guardian.test/api/${name}`, {
      method: input === undefined ? 'GET' : 'POST',
      headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}), ...extra },
      ...(input === undefined ? {} : { body: JSON.stringify(input) }),
    });
    if (res.headers.get('set-cookie')) cookie = res.headers.get('set-cookie').split(';')[0];
    return { status: res.status, data: await res.json(), headers: res.headers };
  };
}
async function workflow(request, scenario) {
  await request('reset', { scenario });
  await request('baseline', {});
  await request('revoke', {});
  await request('replay', {});
  return request('verify', {});
}

test('worker serves only built assets and exposes no paid model path', async () => {
  const mf = runtime();
  try {
    const page = await mf.dispatchFetch('https://guardian.test/');
    assert.equal(page.status, 200);
    assert.match(await page.text(), /UNISON Guardian/);
    assert.match(page.headers.get('content-security-policy'), /default-src 'self'/);
    const notices = await mf.dispatchFetch('https://guardian.test/third-party-notices.txt');
    assert.equal(notices.status, 200);
    assert.match(notices.headers.get('content-type'), /text\/plain/);
    assert.match(await notices.text(), /Copyright \(c\) Meta Platforms/);
    assert.equal((await mf.dispatchFetch('https://guardian.test/.env')).status, 404);
    assert.equal((await mf.dispatchFetch('https://guardian.test/server/engine.mjs')).status, 404);
    const request = client(() => mf);
    const health = await request('health');
    assert.equal(health.data.meta.enabled, false);
    assert.equal(health.data.persistence, 'per-session-durable-object-sqlite');
    const denied = await request('analyze', {});
    assert.equal(denied.status, 503);
    assert.equal(denied.data.error.code, 'PUBLIC_MODEL_DISABLED');
    assert.equal((await request('checkpoint')).status, 404);
  } finally { await mf.dispose(); }
});

test('revocation and queued work survive complete Workers runtime restarts', async () => {
  const storage = await mkdtemp(path.join(os.tmpdir(), 'guardian-worker-'));
  let mf = runtime(storage);
  const request = client(() => mf);
  try {
    const created = await request('state');
    assert.match(created.headers.get('set-cookie'), /HttpOnly/);
    assert.match(created.headers.get('set-cookie'), /SameSite=Strict/);
    assert.match(created.headers.get('set-cookie'), /Secure/);
    assert.equal((await request('baseline', {})).data.stats.protectedActions, 1);
    const beforeRestart = (await request('state')).data;
    await mf.dispose(); mf = runtime(storage);
    assert.deepEqual((await request('state')).data, beforeRestart);
    await request('revoke', {});
    const revoked = (await request('state')).data;
    await mf.dispose(); mf = runtime(storage);
    assert.deepEqual((await request('state')).data, revoked);
    await request('replay', {});
    const result = await request('verify', {});
    assert.equal(result.status, 200);
    assert.equal(result.data.runId, created.data.runId);
    assert.equal(result.data.results.verdict, 'PASS');
    assert.equal(result.data.stats.protectedActions, 1);
    assert.equal(result.data.queue[0].status, 'blocked');
  } finally { await mf.dispose(); await rm(storage, { recursive: true, force: true }); }
});

test('separate sessions retain alternate-path FAIL and incomplete-coverage UNKNOWN', async () => {
  const mf = runtime();
  try {
    const first = client(() => mf); const second = client(() => mf);
    const alternate = await workflow(first, 'alternate');
    const unknown = await workflow(second, 'unknown');
    assert.equal(alternate.data.results.verdict, 'FAIL');
    assert.ok(alternate.data.results.residualPaths.some(route => route.includes('service')));
    assert.equal(unknown.data.results.verdict, 'UNKNOWN');
    assert.notEqual(alternate.data.runId, unknown.data.runId);
    assert.equal((await first('state')).data.results.verdict, 'FAIL');
    const evidence = await second('evidence');
    assert.equal(evidence.data.origin.trusted, false);
    assert.equal(evidence.data.retained, undefined);
    assert.equal(evidence.data.checkpoint, undefined);
    assert.match(evidence.headers.get('content-disposition'), /attachment/);
  } finally { await mf.dispose(); }
});

test('worker rejects cross-origin changes, malformed JSON and oversized bodies', async () => {
  const mf = runtime();
  try {
    const request = client(() => mf);
    assert.equal((await request('baseline', {}, { Origin: 'https://attacker.test' })).status, 403);
    assert.equal((await request('reset', { scenario: 'not-registered' })).status, 400);
    assert.equal((await request('reset', { scenario: 'queued', excess: 'a'.repeat(17_000) })).status, 413);
    const bad = await mf.dispatchFetch('https://guardian.test/api/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{broken}' });
    assert.equal(bad.status, 400);
    assert.equal((await request('state')).data.phase, 'ready');
  } finally { await mf.dispose(); }
});

test('client-provided state cannot revive a grant and concurrent replays execute no action', async () => {
  const mf = runtime();
  try {
    const request = client(() => mf);
    await request('baseline', {});
    await request('revoke', {});
    await Promise.all(Array.from({ length: 4 }, () => request('replay', { checkpoint: { grants: [{ id: 'grant-primary', revoked: false }] } })));
    const state = (await request('state')).data;
    assert.equal(state.grants.find(grant => grant.id === 'grant-primary').revoked, true);
    assert.equal(state.stats.protectedActions, 1);
    assert.equal(state.events.filter(event => event.type === 'queue.blocked').length, 1);
    assert.equal((await request('verify', {})).data.results.verdict, 'PASS');
  } finally { await mf.dispose(); }
});

test('an operation exceeding the event budget leaves persisted authority and counters unchanged', async () => {
  const mf = runtime();
  try {
    const request = client(() => mf);
    await request('state');
    // A baseline appends two events. At 199, neither its counter nor its
    // queued operation may be committed if that would cross the 200 limit.
    for (let index = 0; index < 198; index += 1) assert.equal((await request('verify', {})).status, 200);
    const before = (await request('state')).data;
    assert.equal(before.events.length, 199);
    const denied = await request('baseline', {});
    assert.equal(denied.status, 429);
    assert.equal(denied.data.error.code, 'EVENT_LIMIT');
    assert.deepEqual((await request('state')).data, before);
    assert.equal((await request('verify', {})).data.events.length, 200);
    assert.equal((await request('revoke', {})).status, 429);
    assert.equal((await request('evidence')).status, 200);
    assert.equal((await request('reset', {})).data.events.length, 1);
  } finally { await mf.dispose(); }
});
