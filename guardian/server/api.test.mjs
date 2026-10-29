import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createApp } from './index.mjs';

async function withServer(fn, options = {}) {
  const server = createApp(options);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  const client = () => {
    let cookie = '';
    return async (route, body, extra = {}) => {
      const res = await fetch(base + route, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}), ...extra },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      if (res.headers.get('set-cookie')) cookie = res.headers.get('set-cookie').split(';')[0];
      return { status: res.status, data: await res.json(), headers: res.headers };
    };
  };
  try { await fn(client, base); }
  finally { await new Promise(resolve => server.close(resolve)); }
}

test('API runs delegated baseline, revocation, queued denial and bounded verification', async () => {
  await withServer(async client => {
    const request = client();
    assert.equal((await request('/api/health')).data.mode, 'local-sandbox');
    await request('/api/state');
    const baseline = await request('/api/baseline', {});
    assert.equal(baseline.status, 200);
    assert.ok(baseline.data.queue.some(action => action.status === 'pending'));
    await request('/api/revoke', {});
    const replay = await request('/api/replay', {});
    assert.ok(replay.data.queue.some(action => action.status === 'blocked'));
    const verified = await request('/api/verify', {});
    assert.equal(verified.data.results.verdict, 'PASS');
    const evidence = await request('/api/evidence');
    assert.equal(evidence.status, 200);
    assert.match(evidence.headers.get('content-disposition'), /attachment/);
  });
});

test('different browser sessions have isolated authority and queues', async () => {
  await withServer(async client => {
    const alice = client(); const bob = client();
    const first = await alice('/api/state');
    const second = await bob('/api/state');
    assert.notEqual(first.data.runId, second.data.runId);
    await alice('/api/baseline', {});
    await alice('/api/revoke', {});
    assert.equal((await bob('/api/state')).data.phase, 'ready');
  });
});

test('API rejects cross-origin mutations, unknown scenarios and malformed JSON', async () => {
  await withServer(async (client, base) => {
    const request = client();
    assert.equal((await request('/api/revoke', {}, { Origin: 'https://untrusted.example' })).status, 403);
    assert.equal((await request('/api/reset', { scenario: 'fabricated' })).status, 400);
    const invalid = await fetch(base + '/api/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{no}' });
    assert.equal(invalid.status, 400);
  });
});

test('missing Meta key does not fabricate model analysis or change authority', async () => {
  await withServer(async client => {
    const request = client();
    const before = (await request('/api/state')).data;
    const model = await request('/api/analyze', {});
    assert.equal(model.status, 503);
    assert.equal(model.data.error.code, 'META_NOT_CONFIGURED');
    assert.deepEqual((await request('/api/state')).data, before);
  }, { status: () => ({ configured: false, model: 'muse-wonder-1.0' }) });
});

test('model proposals remain non-authoritative, revision-bound and rate limited', async () => {
  await withServer(async client => {
    const request = client();
    const before = (await request('/api/state')).data;
    const analyzed = await request('/api/analyze', {});
    assert.equal(analyzed.status, 200);
    assert.equal(analyzed.data.authority, 'none');
    assert.equal(analyzed.data.evidence, 'CONJECTURE');
    assert.equal(analyzed.data.analyzedRunId, before.runId);
    assert.equal(analyzed.data.analyzedRevision, before.revision);
    assert.deepEqual((await request('/api/state')).data, before);
    assert.equal((await request('/api/analyze', {})).status, 429);
  }, {
    status: () => ({ configured: true, model: 'muse-wonder-1.0' }),
    analyze: async () => ({ status: 'completed', model: 'muse-wonder-1.0', proposal: { explanation: 'Mocked transport proposal', suggestedGrantIds: [], uncertainty: 'Mocked only' } }),
  });
});

test('rotating an anonymous session cannot bypass the global model cooldown', async () => {
  let calls = 0;
  await withServer(async client => {
    assert.equal((await client()('/api/analyze', {})).status, 200);
    assert.equal((await client()('/api/analyze', {})).status, 429);
    assert.equal(calls, 1);
  }, {
    status: () => ({ configured: true, model: 'muse-wonder-1.0' }),
    analyze: async () => { calls += 1; return { status: 'completed', model: 'muse-wonder-1.0', proposal: {} }; },
  });
});
