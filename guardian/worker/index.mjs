import { DurableObject } from 'cloudflare:workers';
import { createSandbox, snapshot, runBaseline, revokeAuthority, replayQueued, verifySandbox, exportEvidence, checkpointSandbox, restoreSandbox } from '../server/engine.mjs';
import assets from './generated-assets.mjs';

const HOUR = 3_600_000;
const MAX_EVENTS = 200;
const METHODS = new Set(['state', 'evidence', 'reset', 'baseline', 'revoke', 'replay', 'verify']);
const SCENARIOS = new Set(['queued', 'alternate', 'unknown']);
const SECURITY = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'",
};

function json(value, status = 200, headers = {}) {
  return Response.json(value, { status, headers: { ...SECURITY, 'Cache-Control': 'no-store', ...headers } });
}
function problem(code, message, status = 400) { return json({ error: { code, message } }, status); }
function fresh(scenario = 'queued') {
  return createSandbox(scenario, { deployment: 'Cloudflare Durable Object synthetic sandbox' });
}

/**
 * One SQLite-backed coordination object per anonymous browser session. The
 * checkpoint is trusted server storage, never a browser-provided receipt.
 */
export class GuardianSession extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS session_state (singleton INTEGER PRIMARY KEY CHECK(singleton = 1), checkpoint TEXT NOT NULL, expires_at INTEGER NOT NULL)');
  }

  async command(name, input = {}) {
    if (!METHODS.has(name)) return { status: 404, body: { error: { code: 'NOT_FOUND', message: 'API route not found.' } } };
    // All reads, validation, mutations, and the resulting write are synchronous
    // within one SQLite transaction. No external I/O or mutable global cache.
    const result = this.ctx.storage.transactionSync(() => {
      const row = this.ctx.storage.sql.exec('SELECT checkpoint, expires_at FROM session_state WHERE singleton = 1').toArray()[0];
      let sandbox;
      if (name === 'reset') {
        const scenario = input.scenario ?? 'queued';
        if (!SCENARIOS.has(scenario)) return { status: 400, body: { error: { code: 'UNKNOWN_SCENARIO', message: 'Choose queued, alternate, or unknown.' } } };
        sandbox = fresh(scenario);
      } else if (row && row.expires_at > Date.now()) {
        try { sandbox = restoreSandbox(JSON.parse(row.checkpoint)); }
        catch { return { status: 409, body: { error: { code: 'CHECKPOINT_INVALID', message: 'Stored evidence failed its integrity check. Reset the sandbox to start a new run.' } } }; }
      } else sandbox = fresh();

      if (!['state', 'evidence', 'reset'].includes(name) && sandbox.events.length >= MAX_EVENTS) {
        return { status: 429, body: { error: { code: 'EVENT_LIMIT', message: 'This run reached its event limit. Export its evidence and reset the sandbox.' } } };
      }
      const operations = { baseline: runBaseline, revoke: revokeAuthority, replay: replayQueued, verify: verifySandbox };
      const body = name === 'evidence' ? exportEvidence(sandbox) : operations[name] ? operations[name](sandbox) : snapshot(sandbox);
      if (sandbox.events.length > MAX_EVENTS) return { status: 429, body: { error: { code: 'EVENT_LIMIT', message: 'This operation would exceed the run event limit. Export its evidence and reset the sandbox.' } } };
      const expiresAt = Date.now() + HOUR;
      this.ctx.storage.sql.exec('INSERT INTO session_state (singleton, checkpoint, expires_at) VALUES (1, ?, ?) ON CONFLICT(singleton) DO UPDATE SET checkpoint = excluded.checkpoint, expires_at = excluded.expires_at', JSON.stringify(checkpointSandbox(sandbox)), expiresAt);
      return { status: 200, body, expiresAt };
    });
    if (result.expiresAt) await this.ctx.storage.setAlarm(result.expiresAt);
    return { status: result.status, body: result.body };
  }

  async alarm() {
    const row = this.ctx.storage.sql.exec('SELECT expires_at FROM session_state WHERE singleton = 1').toArray()[0];
    if (row?.expires_at > Date.now()) await this.ctx.storage.setAlarm(row.expires_at);
    else this.ctx.storage.sql.exec('DELETE FROM session_state');
  }
}

async function readBody(request) {
  if (!request.headers.get('content-type')?.startsWith('application/json')) return { response: problem('JSON_REQUIRED', 'Send application/json.', 415) };
  if (!request.body) return { input: {} };
  const reader = request.body.getReader();
  const chunks = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > 16_384) {
      await reader.cancel();
      return { response: problem('BODY_TOO_LARGE', 'Request exceeds 16 KiB.', 413) };
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const part of chunks) { bytes.set(part, offset); offset += part.byteLength; }
  try {
    const input = length ? JSON.parse(new TextDecoder().decode(bytes)) : {};
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error();
    return { input };
  } catch { return { response: problem('INVALID_JSON', 'Send a valid JSON object.') }; }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.protocol === 'http:' && !['localhost', '127.0.0.1'].includes(url.hostname)) {
      url.protocol = 'https:';
      return Response.redirect(url.toString(), 308);
    }
    if (!url.pathname.startsWith('/api/')) {
      if (!['GET', 'HEAD'].includes(request.method)) return problem('METHOD_NOT_ALLOWED', 'Method not allowed.', 405);
      const asset = assets[url.pathname === '/' ? '/index.html' : url.pathname];
      if (!asset) return problem('NOT_FOUND', 'Asset not found.', 404);
      return new Response(request.method === 'HEAD' ? null : asset.text, { headers: { ...SECURITY, 'Content-Type': asset.type, 'Cache-Control': url.pathname.startsWith('/assets/') ? 'public, max-age=31536000, immutable' : 'no-cache' } });
    }
    if (request.method === 'GET' && url.pathname === '/api/health') {
      return json({ status: 'ok', mode: 'public-sandbox', persistence: 'per-session-durable-object-sqlite', sessionIdleTimeoutSeconds: 3600, authorityScope: 'registered synthetic paths only', meta: { configured: false, enabled: false, model: 'muse-wonder-1.0', provider: 'meta', disabledReason: 'PUBLIC_MODEL_DISABLED' } });
    }
    if (request.method === 'POST' && request.headers.has('origin') && request.headers.get('origin') !== url.origin) return problem('ORIGIN_DENIED', 'Cross-origin changes are not allowed.', 403);
    if (url.pathname === '/api/analyze') return problem('PUBLIC_MODEL_DISABLED', 'Live model analysis is disabled on this public demo. META_API_KEY is used only by a separately authenticated or local service.', 503);
    const name = url.pathname.slice(5);
    if (!METHODS.has(name) || (['state', 'evidence'].includes(name) ? request.method !== 'GET' : request.method !== 'POST')) return problem('NOT_FOUND', 'API route not found.', 404);
    let input = {};
    if (request.method === 'POST') {
      const parsed = await readBody(request);
      if (parsed.response) return parsed.response;
      input = parsed.input;
    }
    let sessionId = request.headers.get('cookie')?.split(';').map(value => value.trim()).find(value => value.startsWith('guardian_session='))?.slice(17);
    if (!sessionId || !/^[a-f0-9]{48}$/.test(sessionId)) sessionId = [...crypto.getRandomValues(new Uint8Array(24))].map(byte => byte.toString(16).padStart(2, '0')).join('');
    try {
      const result = await env.GUARDIAN_SESSIONS.getByName(sessionId).command(name, input);
      return json(result.body, result.status, {
        'Set-Cookie': `guardian_session=${sessionId}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600${url.protocol === 'https:' ? '; Secure' : ''}`,
        ...(name === 'evidence' ? { 'Content-Disposition': 'attachment; filename="unison-guardian-evidence.json"' } : {}),
      });
    } catch { return problem('SESSION_UNAVAILABLE', 'The session could not complete this operation. Retry or reset the sandbox.', 503); }
  },
};
