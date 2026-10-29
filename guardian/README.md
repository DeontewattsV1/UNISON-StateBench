# UNISON Guardian

**Verifiable authority and identity for AI agents.** A runnable verification sandbox built for the Meta Global AI Developer Hackathon, Indie Dev / Push the Frontier.

An action can be authorized when it is queued and unauthorized when it executes. Guardian checks the current delegation lineage at the execution boundary, inspects every registered route to the protected action, and preserves incomplete coverage as `UNKNOWN`. A Muse Wonder proposal is advisory; it cannot grant authority or override the verifier.

## Run

Requires Node.js 24 or newer. From the UNISON-StateBench repository root:

```bash
cd guardian
npm ci
npm run dev
```

Open http://127.0.0.1:5173. The frontend and API bind to loopback; the API listens on `127.0.0.1:3001`. Both processes run with the dev command. No model credential is needed for deterministic scenarios.

For a production build on the same local machine:

```bash
npm run build
npm start
```

Open http://127.0.0.1:3001. Keep the default loopback binding for a local demo. The Node service stores sessions in memory, so restarting it discards runs. Its session cookie provides browser isolation, not user authentication.

## Public sandbox deployment

A separate Cloudflare Workers entry point serves the same interface with one SQLite-backed Durable Object per browser session. It retains grants, queued work and evidence across Worker runtime restarts. Runs expire after one hour of inactivity, and each run is limited to 200 events. Download evidence before resetting or allowing a session to expire.

```bash
npm run build:worker
npm run test:worker
# Preview the public-sandbox entry point locally:
npm run dev:worker
# After selecting the intended Cloudflare account:
npm run deploy:worker
```

The [public sandbox is live](https://unison-guardian.info-ccehospitalitygroup.workers.dev). Its health endpoint returned HTTP 200 with SQLite session persistence and model requests disabled. Desktop and mobile browser workflows passed at the live HTTPS URL. See [deployment instructions](docs/DEPLOYMENT.md) for the deployed commit, bundle digest and verification record. Hosting can incur Cloudflare usage charges.

Guardian is the `guardian/` component of [UNISON-StateBench](https://github.com/DeontewattsV1/UNISON-StateBench). The integration branch is `feat/unison-guardian-hackathon`; record its reviewed merge commit before final submission. All commands below run from `guardian/`. The repository's existing Python benchmark remains a separate component and has its own checks.

The public entry point unconditionally disables `/api/analyze` and needs no model secret. Its anonymous session cookie is not authentication. Enabling paid model requests requires a separate authenticated service and shared rate limiter; adding a key to the public Worker does not enable the endpoint.

## The decisive demonstration

1. Select **Queued delegation** and **Run baseline**. One synthetic operation executes while authorized; another is queued.
2. **Revoke authority**. The planner's primary grant is removed; inherited child authority becomes invalid.
3. **Replay queued action**. The gateway checks current authority again and denies the stale queued operation. The synthetic action counter does not increase.
4. Inspect the bounded verification and export the evidence JSON.
5. Repeat with **Alternate authority path**: a separate service grant survives, so revocation closure fails and a witness path remains.
6. Repeat with **Incomplete inventory**: known paths can be disconnected, but the overall result remains `UNKNOWN`.

All principals, capabilities, and protected operations are synthetic. The `release:funds` action increments a demonstration counter; it moves no money and invokes no external tool.

## Use Meta's models

The local Node server integrates `muse-wonder-1.0` through Meta's Responses API. The **Ask Muse** panel requests a structured explanation, candidate grant IDs to inspect, and uncertainty. Responses are schema-checked locally, bound to the analyzed run/revision, and have no authority to modify policy. The public Worker displays an explicit disabled state instead of making a model request.

Configure `META_API_KEY` as a server environment secret. `MODEL_API_KEY` is also accepted for compatibility with Meta documentation. For a local session, you can copy `.env.example` to `.env` and set the key there. `.env` is ignored by Git. Never use a `VITE_` variable for credentials. Restart the server after changing secrets.

An absent key produces an explicit unavailable state. Mocked transport tests do **not** establish a successful Meta invocation, account authorization, billing readiness, or competition eligibility. A real successful request is still required for a live Meta demo.

Official references: [Responses](https://dev.meta.ai/docs/protocols/responses), [structured output](https://dev.meta.ai/docs/structured-output), [reasoning](https://dev.meta.ai/docs/reasoning).

## Verify

```bash
npm test
npm run build
npm run build:worker
npm run test:worker
# With the app running and Chromium available:
npm run test:browser
# After exporting evidence from the app:
node scripts/verify-evidence.mjs path/to/unison-guardian-evidence.json
```

The backend suite covers inherited scope, missing/cyclic ancestry, stale queued authorization, alternate routes, incomplete inventories, state tampering, event-hash recomputation, checkpoint validation, HTTP session isolation, and a mocked Meta transport. Worker tests exercise the Cloudflare runtime, persistence through runtime restart, session isolation and the disabled model boundary. The browser test checks the primary workflow, scenario results, navigation, and mobile overflow. Use `BROWSER_TEST_URL` for a different origin and `CHROMIUM_EXECUTABLE` for a local Chromium binary. For remote origins, the browser harness uses inherited `HTTPS_PROXY`/`HTTP_PROXY` and `NO_PROXY` settings when present.

## Evidence and identity boundaries

- `SIMULATED`: seeded actors, grants, and synthetic actions.
- `OBSERVED`: a check actually performed by the running harness, including hash recomputation.
- `UNKNOWN`: missing evidence or incomplete coverage.
- `CONJECTURE`: a live model's advisory interpretation, never an authorization.
- Run, task, model configuration, principal, deployment, and legal owner are separate identity fields. No legal-owner attestation is supplied.
- A SHA-256 chain detects edits relative to retained data. It is not a signature, an independently trusted origin, an immutable external ledger, or proof that a complete rewritten export is authentic.
- Node sessions are held in memory and lost on server restart. Worker sessions use server-side SQLite checkpoints and survive runtime restarts until idle expiry or reset. Neither mode is an immutable archive; download evidence you need to keep.

See [architecture](docs/ARCHITECTURE.md), [new-work disclosure](docs/HACKATHON.md), [three-minute demo](docs/DEMO_SCRIPT.md), and [submission draft](docs/SUBMISSION.md).

The newly written source in `guardian/` is licensed under [Apache-2.0](LICENSE); see [NOTICE](NOTICE) for scope and attribution. The existing StateBench component outside this directory is prior work under the repository's [MIT license](../LICENSE), and is not presented as newly built for this demo. Neither component's license relicenses the other. No confidential research code, supplied private fixtures, outreach records, or source archives are included or relicensed. Bundled dependencies retain their [third-party licenses](public/third-party-notices.txt).
