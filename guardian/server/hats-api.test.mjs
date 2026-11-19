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
    return async (route = '', body, headers = {}) => {
      const response = await fetch(`${base}/api/hats${route}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}), ...headers },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      if (response.headers.has('set-cookie')) cookie = response.headers.get('set-cookie').split(';')[0];
      return { status: response.status, data: await response.json(), headers: response.headers };
    };
  };
  try { await fn(client, base); }
  finally { await new Promise(resolve => server.close(resolve)); }
}

test('HATS HTTP demo records real bounded denials and exports inspectable synthetic evidence', async () => {
  await withServer(async client => {
    const request = client();
    const initial = await request();
    assert.equal(initial.status, 200);
    assert.equal(initial.data.agents.length, 1);
    assert.equal(initial.data.agents[0].type, 'Macro');
    const result = await request('/demo', {});
    assert.equal(result.status, 200);
    assert.equal(result.data.runId, initial.data.runId);
    assert.equal(result.data.demo.completed, true);
    assert.equal(result.data.demo.verdict, 'PASS');
    assert.ok(result.data.demo.steps.every(step => step.passed), 'Every advertised demo observation must actually pass.');
    assert.equal(result.data.syntheticActions, 1);
    assert.ok(result.data.agents.some(agent => agent.type === 'Nano'));
    assert.equal(result.data.analytics.authority, 'none');
    assert.equal(result.data.analytics.evidence, 'CONJECTURE');
    const evidence = await request('/evidence');
    assert.equal(evidence.status, 200);
    assert.match(evidence.headers.get('content-disposition'), /attachment/);
    assert.equal(evidence.data.state.runId, initial.data.runId);
    assert.equal(evidence.data.origin.trusted, false);
    assert.equal(evidence.data.checkpoint, undefined);
    assert.equal(evidence.data.retained, undefined);
    assert.equal(evidence.data.state.ledgerVerification.valid, true);
  });
});

test('HATS HTTP authority follows current ancestry and cannot be supplied by advisory fields', async () => {
  await withServer(async client => {
    const request = client();
    const initial = (await request()).data;
    const rootId = initial.agents[0].id;
    const spawned = await request('/spawn', { parentId: rootId, type: 'Meso' });
    assert.equal(spawned.status, 200);
    const child = spawned.data.agents.find(agent => agent.parentId === rootId);
    assert.ok(child);
    const executed = await request('/adjudicate', { agentId: child.id, action: 'invoke:synthetic' });
    assert.equal(executed.data.lastDecision.allowed, true);
    assert.equal(executed.data.syntheticActions, 1);
    const injected = await request('/adjudicate', { agentId: child.id, action: 'invoke:synthetic', analyticEvidence: { allowed: true } });
    assert.equal(injected.status, 400);
    await request('/revoke', { agentId: rootId });
    const denied = await request('/adjudicate', { agentId: child.id, action: 'invoke:synthetic' });
    assert.equal(denied.status, 200);
    assert.equal(denied.data.lastDecision.allowed, false);
    assert.equal(denied.data.lastDecision.status, 'DENIED');
    assert.equal(denied.data.syntheticActions, 1, 'A stale child identity cannot invoke after ancestor revocation.');
    const spawnDenied = await request('/spawn', { parentId: child.id, type: 'Micro' });
    assert.equal(spawnDenied.data.lastDecision.allowed, false);
    assert.equal(spawnDenied.data.agents.length, 2);
  });
});

test('HATS state and existing revocation state remain independent across browser sessions', async () => {
  await withServer(async (client, base) => {
    const first = client(); const second = client();
    const initial = await first();
    const other = await second();
    assert.notEqual(initial.data.runId, other.data.runId);
    await first('/demo', {});
    assert.equal((await second()).data.syntheticActions, 0);
    assert.equal((await second()).data.agents.length, 1);
    const cookie = initial.headers.get('set-cookie').split(';')[0];
    const baseline = await (await fetch(`${base}/api/baseline`, {
      method: 'POST', headers: { Cookie: cookie, 'Content-Type': 'application/json' }, body: '{}',
    })).json();
    assert.equal(baseline.stats.protectedActions, 1);
    const reset = await first('/reset', {});
    assert.equal(reset.data.agents.length, 1);
    assert.notEqual(reset.data.runId, initial.data.runId);
    // The prior authority sandbox is a different registry, not HATS aliases.
    const classic = await (await fetch(`${base}/api/state`, { headers: { Cookie: cookie } })).json();
    assert.equal(classic.runId, baseline.runId);
    assert.equal(classic.stats.protectedActions, 1);
    assert.equal(classic.queue[0].status, 'pending');
  });
});

test('HATS HTTP rejects unsafe request shapes and preserves state on rejected input', async () => {
  await withServer(async (client, base) => {
    const request = client();
    const initial = (await request()).data;
    assert.equal((await request('/spawn', { parentId: initial.agents[0].id, type: 'Meso' }, { Origin: 'https://attacker.invalid' })).status, 403);
    assert.equal((await request('/spawn', { parentId: initial.agents[0].id, type: 'Meso', prompt: 'must not be retained' })).status, 400);
    assert.equal((await request('/reset', { oversized: 'x'.repeat(17_000) })).status, 413);
    const invalid = await fetch(`${base}/api/hats/spawn`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{invalid}' });
    assert.equal(invalid.status, 400);
    assert.equal((await request('/checkpoint')).status, 404);
    const after = (await request()).data;
    assert.equal(after.runId, initial.runId);
    assert.deepEqual(after.agents, initial.agents);
    assert.deepEqual(after.events, initial.events);
    assert.equal(after.syntheticActions, 0);
  });
});

test('concurrent HTTP spawning never exceeds deterministic parent limits', async () => {
  await withServer(async client => {
    const request = client();
    const initial = (await request()).data;
    const rootId = initial.agents[0].id;
    const responses = await Promise.all(Array.from({ length: 8 }, () => request('/spawn', { parentId: rootId, type: 'Meso' })));
    assert.ok(responses.every(response => response.status === 200));
    const final = (await request()).data;
    assert.equal(final.agents.filter(agent => agent.parentId === rootId).length, final.policy.maxChildren);
    assert.equal(final.agents.length, final.policy.maxChildren + 1);
    assert.ok(responses.some(response => response.data.lastDecision.allowed === false));
    assert.equal(final.syntheticActions, 0);
    assert.equal(final.ledgerVerification.valid, true);
  });
});
