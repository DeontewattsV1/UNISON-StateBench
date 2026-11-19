import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  createSandbox, snapshot, runBaseline, revokeAuthority,
  replayQueued, verifySandbox, exportEvidence,
} from './engine.mjs';
import { metaStatus, analyzeWithMeta } from './meta.mjs';
import { createHatsStore } from './hats-sqlite.mjs';
import { HATS_COMMANDS } from './hats-service.mjs';

const DIST = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const SCENARIOS = new Set(['queued', 'alternate', 'unknown']);
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json' };
const SESSION_TTL = 60 * 60 * 1000;

class ApiError extends Error {
  constructor(code, message, status = 400) { super(message); this.code = code; this.status = status; }
}

export function createApp({ analyze = analyzeWithMeta, status = metaStatus, now = Date.now } = {}) {
  // Sessions isolate demo data. They are not a substitute for deployment authentication.
  const sessions = new Map();
  const hatsStore = createHatsStore();
  let analysisInFlight = false;
  let lastGlobalAnalysis = null;

  function session(req, res) {
    for (const [key, value] of sessions) if (now() - value.touched > SESSION_TTL) {
      sessions.delete(key);
      hatsStore.delete(key);
    }
    const cookie = req.headers.cookie?.split(';').map(v => v.trim()).find(v => v.startsWith('guardian_session='))?.slice(17);
    let id = cookie && /^[a-f0-9]{48}$/.test(cookie) ? cookie : null;
    let value = id ? sessions.get(id) : null;
    if (!value) {
      if (sessions.size >= 256) {
        const expiredId = sessions.keys().next().value;
        sessions.delete(expiredId);
        hatsStore.delete(expiredId);
      }
      id = randomBytes(24).toString('hex');
      value = { id, sandbox: createSandbox(), touched: now(), lastAnalysis: null };
      sessions.set(id, value);
    }
    value.touched = now();
    // Keep the browser cookie aligned with the server's sliding idle deadline.
    res.setHeader('Set-Cookie', `guardian_session=${id}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600`);
    return value;
  }

  function send(res, code, value, headers = {}) {
    res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers });
    res.end(JSON.stringify(value));
  }

  async function body(req) {
    if (!req.headers['content-type']?.startsWith('application/json')) throw new ApiError('JSON_REQUIRED', 'Send application/json.', 415);
    let size = 0;
    const chunks = [];
    for await (const chunk of req) {
      size += chunk.length;
      if (size > 16_384) throw new ApiError('BODY_TOO_LARGE', 'Request exceeds 16 KiB.', 413);
      chunks.push(chunk);
    }
    if (!size) return {};
    try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
    catch { throw new ApiError('INVALID_JSON', 'The request body is not valid JSON.'); }
  }

  const server = createServer(async (req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    try {
      const url = new URL(req.url, 'http://localhost');
      if (req.method === 'GET' && ['/health/live', '/health/ready'].includes(url.pathname)) return send(res, 200, {
        status: url.pathname.endsWith('ready') ? 'ready' : 'ok', service: 'unison-guardian', version: '0.3.0',
        authorityLane: 'deterministic synthetic sandbox', analyticsAuthority: 'none',
      });
      if (!url.pathname.startsWith('/api/')) {
        if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, { error: { code: 'METHOD_NOT_ALLOWED', message: 'Method not allowed.' } });
        const requested = decodeURIComponent(url.pathname);
        const candidate = path.resolve(DIST, `.${requested}`);
        if (!candidate.startsWith(DIST + path.sep) && candidate !== DIST) throw new ApiError('NOT_FOUND', 'Not found.', 404);
        let asset;
        let filename = candidate;
        try { asset = await readFile(filename); }
        catch {
          if (path.extname(requested)) throw new ApiError('NOT_FOUND', 'Asset not found.', 404);
          filename = path.join(DIST, 'index.html');
          try { asset = await readFile(filename); }
          catch { throw new ApiError('BUILD_REQUIRED', 'Run npm run build, or use npm run dev.', 503); }
        }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(filename)] || 'application/octet-stream', 'Cache-Control': 'no-cache', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'" });
        return res.end(req.method === 'HEAD' ? undefined : asset);
      }

      if (req.method === 'GET' && url.pathname === '/api/health') return send(res, 200, { status: 'ok', version: '0.3.0', mode: 'local-sandbox', meta: status(), persistence: 'in-memory', hatsPersistence: 'in-memory-sqlite', authorityScope: 'registered synthetic paths only' });

      if (req.method === 'POST' && req.headers.origin) {
        let origin;
        try { origin = new URL(req.headers.origin); } catch { throw new ApiError('ORIGIN_DENIED', 'Origin not allowed.', 403); }
        if (origin.host !== req.headers.host) throw new ApiError('ORIGIN_DENIED', 'Cross-origin changes are not allowed.', 403);
      }

      const state = session(req, res);
      if (url.pathname === '/api/hats' || url.pathname.startsWith('/api/hats/')) {
        const name = url.pathname === '/api/hats' ? 'state' : url.pathname.slice('/api/hats/'.length);
        const read = ['state', 'evidence'].includes(name);
        if (!HATS_COMMANDS.has(name) || req.method !== (read ? 'GET' : 'POST')) throw new ApiError('NOT_FOUND', 'HATS route not found.', 404);
        const input = read ? {} : await body(req);
        const result = hatsStore.command(state.id, name, input);
        return send(res, 200, result, name === 'evidence' ? { 'Content-Disposition': 'attachment; filename="unison-guardian-hats-evidence.json"' } : {});
      }
      if (req.method === 'GET' && url.pathname === '/api/state') return send(res, 200, snapshot(state.sandbox));
      if (req.method === 'GET' && url.pathname === '/api/evidence') return send(res, 200, exportEvidence(state.sandbox), { 'Content-Disposition': 'attachment; filename="unison-guardian-evidence.json"' });
      if (req.method !== 'POST') throw new ApiError('NOT_FOUND', 'API route not found.', 404);
      const input = await body(req);
      if (!input || typeof input !== 'object' || Array.isArray(input)) throw new ApiError('INVALID_BODY', 'The request body must be an object.');
      switch (url.pathname) {
        case '/api/reset': {
          const scenario = input.scenario ?? 'queued';
          if (!SCENARIOS.has(scenario)) throw new ApiError('UNKNOWN_SCENARIO', 'Choose queued, alternate, or unknown.');
          state.sandbox = createSandbox(scenario);
          return send(res, 200, snapshot(state.sandbox));
        }
        case '/api/baseline': return send(res, 200, runBaseline(state.sandbox));
        case '/api/revoke': return send(res, 200, revokeAuthority(state.sandbox));
        case '/api/replay': return send(res, 200, replayQueued(state.sandbox));
        case '/api/verify': return send(res, 200, verifySandbox(state.sandbox));
        case '/api/analyze': {
          if (!status().configured) throw new ApiError('META_NOT_CONFIGURED', 'Add META_API_KEY to the server environment to use Muse Wonder. Deterministic checks remain available.', 503);
          if (analysisInFlight || (lastGlobalAnalysis !== null && now() - lastGlobalAnalysis < 30_000) || (state.lastAnalysis !== null && now() - state.lastAnalysis < 30_000)) throw new ApiError('ANALYSIS_RATE_LIMIT', 'Wait 30 seconds before another model analysis.', 429);
          analysisInFlight = true;
          state.lastAnalysis = now();
          lastGlobalAnalysis = now();
          const captured = snapshot(state.sandbox);
          try {
            const result = await analyze(captured);
            return send(res, 200, { ...result, evidence: 'CONJECTURE', authority: 'none', analyzedRunId: captured.runId, analyzedRevision: captured.revision });
          } finally { analysisInFlight = false; }
        }
        default: throw new ApiError('NOT_FOUND', 'API route not found.', 404);
      }
    } catch (error) {
      // Never expose upstream bodies, stack traces, credentials, or prompts.
      const known = typeof error?.code === 'string' && Number.isInteger(error?.status);
      send(res, known ? error.status : 500, { error: { code: known ? error.code : 'INTERNAL_ERROR', message: known ? error.message : 'The sandbox could not complete this request.' } });
    }
  });
  server.once('close', () => hatsStore.close());
  return server;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const host = process.env.HOST || '127.0.0.1';
  const port = Number(process.env.PORT || 3001);
  createApp().listen(port, host, () => console.log(`UNISON Guardian: http://${host}:${port} (synthetic sandbox)`));
}
