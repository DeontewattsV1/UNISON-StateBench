import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createApp } from './index.mjs';

async function withServer(fn, options = {}) {
  const server = createApp(options);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  const client = ({ now: browserNow = Date.now } = {}) => {
    let cookie = '';
    let cookieExpiresAt = 0;
    return async (route, body, extra = {}) => {
      if (browserNow() >= cookieExpiresAt) cookie = '';
      const res = await fetch(base + route, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}), ...extra },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      const setCookie = res.headers.get('set-cookie');
      if (setCookie) {
        cookie = setCookie.split(';')[0];
        const maxAge = /(?:^|;\s*)Max-Age=(\d+)(?:;|$)/i.exec(setCookie);
        cookieExpiresAt = maxAge ? browserNow() + Number(maxAge[1]) * 1000 : Infinity;
      }
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

test('active browser sessions renew their cookie and retain queued work past the original expiry', async () => {
  const minute = 60_000;
  let clock = 0;
  await withServer(async client => {
    const request = client({ now: () => clock });
    const initial = await request('/api/state');
    const initialCookie = initial.headers.get('set-cookie')?.split(';')[0];
    const baseline = await request('/api/baseline', {});
    assert.equal(baseline.data.stats.protectedActions, 1);
    assert.equal(baseline.data.queue[0].status, 'pending');

    clock = 50 * minute;
    const active = await request('/api/state');
    assert.equal(active.data.runId, initial.data.runId);
    assert.deepEqual(active.data.queue, baseline.data.queue);

    // The client models Max-Age rather than retaining cookies indefinitely.
    // Without renewal at 50 minutes, it drops the original cookie at 70.
    clock = 70 * minute;
    const continued = await request('/api/state');
    assert.equal(continued.data.runId, initial.data.runId, 'Activity must preserve the browser session beyond its original cookie expiry.');
    assert.deepEqual(continued.data.queue, baseline.data.queue);
    assert.equal(continued.data.stats.protectedActions, 1);

    const renewed = active.headers.get('set-cookie') || '';
    assert.ok(Boolean(initialCookie) && renewed.split(';')[0] === initialCookie, 'Renewal must retain the existing random session ID.');
    for (const attribute of ['Max-Age=3600', 'HttpOnly', 'SameSite=Strict', 'Path=/']) {
      assert.ok(renewed.split(';').map(value => value.trim()).includes(attribute), `Renewal must preserve ${attribute}.`);
    }

    // More than one hour idle since the last session activity starts a new run.
    clock = 131 * minute;
    const expired = await request('/api/state');
    assert.notEqual(expired.data.runId, initial.data.runId);
    assert.equal(expired.data.phase, 'ready');
    assert.deepEqual(expired.data.queue, []);
    assert.equal(expired.data.stats.protectedActions, 0);
    const expiredCookie = expired.headers.get('set-cookie')?.split(';')[0];
    assert.ok(Boolean(expiredCookie) && expiredCookie !== initialCookie, 'An expired browser session must receive a fresh random ID.');
  }, { now: () => clock });
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
