import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeWithMeta, metaStatus } from './meta.mjs';

const KEY = 'unit-test-key-never-sent';
const snapshot = {
  grants: [{ id: 'grant-root', source: 'owner', target: 'planner' }, { id: 'grant-worker', source: 'planner', target: 'worker' }],
  nodes: [{ id: 'owner' }, { id: 'planner' }, { id: 'worker' }],
};
const proposal = {
  explanation: 'Inspect the delegated worker path before export.',
  suggestedGrantIds: ['grant-worker'],
  uncertainty: 'Only registered paths are represented.',
};
function responseFor(value = proposal, overrides = {}) {
  return {
    ok: true,
    status: 200,
    json: async () => ({
      id: 'resp_unit_test', model: 'muse-wonder-1.0', status: 'completed',
      output: [{ type: 'message', role: 'assistant', content: [{ type: 'output_text', text: JSON.stringify(value) }] }],
      ...overrides,
    }),
  };
}
const options = (response) => ({ apiKey: KEY, fetchImpl: async () => response });

test('posts the fixed Responses contract and returns a locally validated advisory proposal without mutation', async () => {
  const original = structuredClone(snapshot);
  let request;
  const result = await analyzeWithMeta(snapshot, {
    apiKey: KEY,
    fetchImpl: async (url, init) => {
      request = { url, init, body: JSON.parse(init.body) };
      return responseFor();
    },
  });
  assert.equal(request.url, 'https://api.meta.ai/v1/responses');
  assert.equal(request.init.method, 'POST');
  assert.equal(request.init.redirect, 'error');
  assert.equal(request.init.headers.Authorization, `Bearer ${KEY}`);
  assert.equal(request.init.signal.aborted, false);
  assert.equal(request.body.model, 'muse-wonder-1.0');
  assert.equal(request.body.store, false);
  assert.equal(request.body.max_output_tokens, 8192);
  assert.deepEqual(request.body.reasoning, { effort: 'high', summary: 'auto' });
  assert.equal(request.body.text.format.type, 'json_schema');
  assert.equal(request.body.text.format.strict, true);
  assert.equal(request.body.text.format.schema.additionalProperties, false);
  assert.equal(request.body.response_format, undefined);
  assert.match(request.body.input[0].content[0].text, /untrusted graph data/);
  assert.deepEqual(JSON.parse(request.body.input[1].content[0].text), snapshot);
  assert.deepEqual(snapshot, original);
  assert.deepEqual(result, { status: 'completed', model: 'muse-wonder-1.0', proposal, requestId: 'resp_unit_test' });
});

test('missing key fails before transport and exposes only the documented safe error', async () => {
  let called = false;
  await assert.rejects(analyzeWithMeta(snapshot, { apiKey: '', fetchImpl: async () => { called = true; } }), (error) => {
    assert.equal(error.code, 'META_NOT_CONFIGURED');
    assert.equal(error.status, 503);
    return true;
  });
  assert.equal(called, false);
});

test('rejects malformed JSON output', async () => {
  const response = responseFor(null, { output: [{ type: 'message', role: 'assistant', content: [{ type: 'output_text', text: 'not json' }] }] });
  await assert.rejects(analyzeWithMeta(snapshot, options(response)), { code: 'META_INVALID_RESPONSE' });
});

test('rejects unknown grant IDs, duplicate IDs, incorrect fields, and extra authority claims', async () => {
  for (const invalid of [
    { ...proposal, suggestedGrantIds: ['unregistered-grant'] },
    { ...proposal, suggestedGrantIds: ['grant-root', 'grant-root'] },
    { ...proposal, explanation: 42 },
    { ...proposal, uncertainty: '' },
    { ...proposal, authorized: true },
  ]) {
    await assert.rejects(analyzeWithMeta(snapshot, options(responseFor(invalid))), { code: 'META_INVALID_RESPONSE' });
  }
});

test('refuses incomplete responses and a different model', async () => {
  for (const overrides of [{ status: 'incomplete' }, { model: 'other-model' }, { output: [] }]) {
    await assert.rejects(analyzeWithMeta(snapshot, options(responseFor(proposal, overrides))), { code: 'META_INVALID_RESPONSE' });
  }
});

test('sanitizes authentication errors without reading provider diagnostics', async () => {
  let bodyRead = false;
  const response = { ok: false, status: 401, json: async () => { bodyRead = true; return { error: KEY }; } };
  await assert.rejects(analyzeWithMeta(snapshot, options(response)), (error) => {
    assert.equal(error.code, 'META_AUTH_FAILED');
    assert.equal(error.status, 502);
    assert.ok(!error.message.includes(KEY));
    return true;
  });
  assert.equal(bodyRead, false);
});

test('sanitizes network failures and distinguishes rate limits and timeouts', async () => {
  await assert.rejects(analyzeWithMeta(snapshot, { apiKey: KEY, fetchImpl: async () => { throw new Error(`network diagnostic ${KEY}`); } }), (error) => {
    assert.equal(error.code, 'META_UNAVAILABLE');
    assert.ok(!error.message.includes(KEY));
    return true;
  });
  await assert.rejects(analyzeWithMeta(snapshot, options({ ok: false, status: 429 })), { code: 'META_RATE_LIMITED', status: 429 });
  await assert.rejects(analyzeWithMeta(snapshot, { apiKey: KEY, fetchImpl: async () => { const e = new Error(KEY); e.name = 'TimeoutError'; throw e; } }), { code: 'META_TIMEOUT', status: 504 });
});

test('configuration status reveals presence but never credential content', (t) => {
  const priorPrimary = process.env.META_API_KEY;
  const priorFallback = process.env.MODEL_API_KEY;
  t.after(() => {
    if (priorPrimary === undefined) delete process.env.META_API_KEY;
    else process.env.META_API_KEY = priorPrimary;
    if (priorFallback === undefined) delete process.env.MODEL_API_KEY;
    else process.env.MODEL_API_KEY = priorFallback;
  });
  process.env.META_API_KEY = KEY;
  delete process.env.MODEL_API_KEY;
  assert.deepEqual(metaStatus(), { configured: true, model: 'muse-wonder-1.0', provider: 'meta' });
  delete process.env.META_API_KEY;
  process.env.MODEL_API_KEY = KEY;
  assert.equal(metaStatus().configured, true);
  delete process.env.MODEL_API_KEY;
  assert.equal(metaStatus().configured, false);
});
