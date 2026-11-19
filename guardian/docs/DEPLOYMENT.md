# Deployment

The [public sandbox](https://unison-guardian.info-ccehospitalitygroup.workers.dev) runs on Cloudflare Workers with SQLite-backed Durable Objects. It serves the deterministic sandbox without a model credential. Source is public as the [`guardian/` component of UNISON-StateBench](https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian), merged through [PR #24](https://github.com/DeontewattsV1/UNISON-StateBench/pull/24).

## Observed deployment

| Field | Recorded value |
| --- | --- |
| Live URL | https://unison-guardian.info-ccehospitalitygroup.workers.dev |
| Deployed source commit | [`ae06eab73316c94a4bd8c2e3a81c99a77bd208da`](https://github.com/DeontewattsV1/UNISON-StateBench/commit/ae06eab73316c94a4bd8c2e3a81c99a77bd208da) |
| Reviewed merge | [PR #24](https://github.com/DeontewattsV1/UNISON-StateBench/pull/24), component `guardian/` |
| Worker bundle SHA-256 | `4345eea98f2f0df94d002c1906f7d62a7abd09e3060209575b08870477d07812` |
| Cloudflare upload result | HTTP 200; deployment ID `9bc7c42e0cd54601bd97987bae3885c1` |
| Durable Object migration | `v1`, SQLite class `GuardianSession`, binding `GUARDIAN_SESSIONS` |
| Public route | Workers.dev enabled; preview URLs disabled |
| Live health check | HTTP 200; `public-sandbox`, `per-session-durable-object-sqlite`, `meta.enabled: false` |
| Post-deployment browser workflow | PASS at the HTTPS origin: desktop 1536×1024 and mobile 390×844 |
| State continuity across deployment | Same run and queued operation retained; later revocation/replay blocked the stale action and left the counter at one |

The post-deployment browser check exercised queued-action denial with an unchanged synthetic counter, alternate-path FAIL, incomplete-coverage UNKNOWN, identity and ledger navigation, evidence export, and HTTP 503 model unavailability. The exported evidence passed standalone digest recomputation with origin still untrusted. Proposal display and isolation used intercepted, explicitly mocked responses; no real Meta inference was requested.

This deployment uses the reviewed merged source. The existing SQLite Durable Object namespace and migration tag `v1` were retained. A cross-deployment test queued an operation before deployment, observed the same run and job afterward, then revoked authority and replayed the operation. Replay was blocked and the synthetic counter remained one. [Guardian CI](https://github.com/DeontewattsV1/UNISON-StateBench/actions/runs/40860198801) and [StateBench CI](https://github.com/DeontewattsV1/UNISON-StateBench/actions/runs/40860198761) both passed for the deployed source commit.

## Build and inspect locally

Requires Node.js 24 or newer. Run from the repository root:

```bash
cd guardian
npm ci
npm test
npm run build:worker
npm run test:worker
npm run dev:worker
```

All subsequent commands in this guide run from `guardian/`. Wrangler prints the local preview URL. This preview uses the public-sandbox behavior, including the disabled model endpoint. For browser verification against that URL:

```bash
BROWSER_TEST_URL=http://127.0.0.1:8787 npm run test:browser
```

The build first creates the React production files in `guardian/dist`, then embeds only supported built assets into `guardian/.release/worker.mjs`. Generated bundles, Wrangler state, credentials and `.env` are ignored by Git. Neither the build script nor the Worker reads StateBench benchmark files outside `guardian/` or separately supplied research archives. Distribute the reviewed Guardian source, its [Apache-2.0 license](../LICENSE), [NOTICE](../NOTICE) and dependency notices. The benchmark outside `guardian/` retains the repository root's MIT license.

## Cloudflare configuration

Review [wrangler.jsonc](../wrangler.jsonc) before deploying:

| Setting | Deployed value and purpose |
| --- | --- |
| Worker name | `unison-guardian`; subsequent deployments update this existing Worker |
| Entry point | `.release/worker.mjs` |
| Compatibility | `2026-10-29` with `nodejs_compat` |
| Session binding | `GUARDIAN_SESSIONS` → `GuardianSession` |
| Initial migration | Tag `v1`, `new_sqlite_classes: ["GuardianSession"]` |
| Public route | Workers.dev enabled; preview URLs disabled |
| Model secrets | None; the public entry point does not use a key |

Use the intended account and inspect the existing Worker before updating it. The initial Durable Object migration created the SQLite-backed class. Preserve the migration history and add a new migration tag for later schema or class changes; do not reuse the initial tag to describe a different migration.

```bash
npx wrangler login
npx wrangler whoami
npm run deploy:worker
```

These commands publish code and provision Cloudflare resources. Hosting may incur Worker, Durable Object request and storage charges under the selected account's plan. The 200-event limit applies to one run and does not impose an account-wide spending or request limit. Review account usage after deployment. No custom domain or DNS change is required for Workers.dev.

## Runtime boundaries

The Worker creates one Durable Object per random browser session cookie. The cookie is `HttpOnly`, `SameSite=Strict` and `Secure` over HTTPS. It identifies an anonymous sandbox session, not an authenticated person. It grants no authority over real tools or systems.

Each operation restores and validates the internal checkpoint, applies the deterministic operation and writes the result in one synchronous SQLite transaction. Revocation state, pending jobs, idempotency flags and evidence survive Worker runtime restart. The browser cannot upload or replace that checkpoint. Exported evidence is a separate, untrusted-origin artifact whose internal hashes can be recomputed.

Successful session operations extend the one-hour idle deadline. Expiry removes the session's checkpoint; reset replaces the run. A mutation that would exceed 200 events returns `EVENT_LIMIT` without saving its changes. State and evidence remain readable at that limit. Download evidence before reset or expiry. Cloudflare storage and retained checkpoints remain under the account operator's control; this is not a signature service or an immutable external ledger.

`/api/analyze` always returns HTTP 503 with `PUBLIC_MODEL_DISABLED`. The Worker does not import the Meta transport or use `META_API_KEY`/`MODEL_API_KEY`. Adding either secret will not enable model calls. Public model access would require a separate authenticated service, shared rate limiting and appropriate quota controls before changing this boundary.

For live Meta analysis on the same local machine, run the Node service as described in [README.md](../README.md), keep its default loopback binding and provide a server-side key. The Node backend's in-memory sessions do not gain Worker persistence.

## Verify a published instance

The live `/api/health` check confirmed `mode: public-sandbox`, `persistence: per-session-durable-object-sqlite` and `meta.enabled: false`. To repeat the browser verification:

```bash
BROWSER_TEST_URL=https://unison-guardian.info-ccehospitalitygroup.workers.dev npm run test:browser
```

The current source includes proxy handling for remote browser and API requests through inherited `HTTPS_PROXY`/`HTTP_PROXY` and `NO_PROXY` settings. The test harness runs separately from the Worker bundle.

Run the browser check with `BROWSER_TEST_URL` set to that HTTPS origin. Confirm the queued scenario blocks the stale operation without increasing the counter, the alternate route yields FAIL and incomplete inventory yields UNKNOWN. Use a separate browser context to check session isolation, refresh to check retained state, and download evidence for standalone inspection:

```bash
node scripts/verify-evidence.mjs path/to/unison-guardian-evidence.json
```

The Worker test suite separately exercises a complete local runtime restart with retained SQLite storage. A browser refresh alone does not establish restart persistence. Record the actual deployed source commit, Worker version, URL and observed checks for the release. Keep a real Meta request and the three-minute video marked pending until those artifacts exist.
