# UNISON Guardian

**Verifiable authority and identity for AI agents.** A runnable verification sandbox built for the Meta Global AI Developer Hackathon, Indie Dev / Push the Frontier.

An action can be authorized when it is queued and unauthorized when it executes. Guardian checks the current delegation lineage at the execution boundary, inspects every registered route to the protected action, and preserves incomplete coverage as `UNKNOWN`. A Muse Wonder proposal is advisory; it cannot grant authority or override the verifier.

The **HATS lab** adds a second falsifiable workflow: create a Macro → Meso → Micro → Nano hierarchy, inspect recomputed lineage hashes, exercise spawning limits, revoke an ancestor and attempt a descendant action. Timestamp and topology analytics explain the recorded run without granting authority.

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

Open http://127.0.0.1:3001. Keep the default loopback binding for a local demo. The Node service stores revocation sessions in memory and HATS checkpoints/events in in-memory SQLite, so restarting it discards runs. Its session cookie provides browser isolation, not user authentication.

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

Guardian source is public on [UNISON-StateBench's main branch](https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian). [Pull request #24](https://github.com/DeontewattsV1/UNISON-StateBench/pull/24) merged the reviewed integration as commit `ae06eab73316c94a4bd8c2e3a81c99a77bd208da`, which supplies the deployed runtime. All commands below run from `guardian/`. The repository's existing Python benchmark remains a separate component and has its own checks.

The public entry point unconditionally disables `/api/analyze` and needs no model secret. Its anonymous session cookie is not authentication. Enabling paid model requests requires a separate authenticated service and shared rate limiter; adding a key to the public Worker does not enable the endpoint.

The deployment record above describes the released v0.2.0 runtime. The HATS expansion must be checked against its own source revision and deployment record before being described as live.

## The decisive demonstration

1. Select **Queued delegation** and **Run baseline**. One synthetic operation executes while authorized; another is queued.
2. **Revoke authority**. The planner's primary grant is removed; inherited child authority becomes invalid.
3. **Replay queued action**. The gateway checks current authority again and denies the stale queued operation. The synthetic action counter does not increase.
4. Inspect the bounded verification and export the evidence JSON.
5. Repeat with **Alternate authority path**: a separate service grant survives, so revocation closure fails and a witness path remains.
6. Repeat with **Incomplete inventory**: known paths can be disconnected, but the overall result remains `UNKNOWN`.

All principals, capabilities, and protected operations are synthetic. The `release:funds` action increments a demonstration counter; it moves no money and invokes no external tool.

## HATS: bounded spawning and current authority

1. Open **HATS lab** and select **Run HATS demo** in a fresh lab. The lab starts with one synthetic Macro agent and creates the three descendant levels.
2. Inspect the allowed synthetic action and the denied attempts to exceed depth, widen scope or exceed a spawning quota. The configured limits are depth 3, three children per parent, twelve agents per run and six successful spawns per rolling 60-second window.
3. Inspect the ancestor revocation and the descendant's denied action. Its earlier lineage does not grant current permission; the synthetic action counter remains one.
4. Recompute verification, inspect the event chain and export the HATS evidence. Reset the lab to repeat it, or use the individual spawn, invoke and revoke controls for a different bounded experiment.

Each lineage digest binds the run, agent identity, type, parent reference and digest, nonce, depth, inherited context and capability scope. The verifier recomputes ancestry rather than treating a nonempty hash as proof. Every spawn and invocation rechecks active ancestry and policy. Missing evidence produces `UNKNOWN` and does not authorize execution. Hashes and transition receipts establish internal consistency only; they are not signatures or independently authenticated identities.

The analytic lane computes features from recorded metadata. Its risk and coordination indicators are uncalibrated heuristics, not a probability that an actor is AI, proof of a swarm or evidence of a consensus protocol. Deterministic resource limits still apply when an analytic indicator is low or unavailable. The lab does not launch operating-system processes or collect live cluster traffic.

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

The backend suite covers inherited scope, missing/cyclic ancestry, stale queued authorization, alternate routes, incomplete inventories, state tampering, event-hash recomputation, checkpoint validation, HTTP session isolation, and a mocked Meta transport. HATS tests exercise its identity binding, bounded spawning, current ancestor checks, checkpoint restoration and advisory analytics. Worker tests exercise the Cloudflare runtime, persistence through runtime restart, session isolation and the disabled model boundary. The browser test checks the primary workflow, scenario results, navigation, and mobile overflow. Use `BROWSER_TEST_URL` for a different origin and `CHROMIUM_EXECUTABLE` for a local Chromium binary. For remote origins, the browser harness uses inherited `HTTPS_PROXY`/`HTTP_PROXY` and `NO_PROXY` settings when present.

## Evidence and identity boundaries

- `SIMULATED`: seeded actors, grants, and synthetic actions.
- `OBSERVED`: a check actually performed by the running harness, including hash recomputation.
- `UNKNOWN`: missing evidence or incomplete coverage.
- `CONJECTURE`: a model interpretation or uncalibrated analytic forecast, never an authorization.
- Run, task, model configuration, principal, deployment, and legal owner are separate identity fields. No legal-owner attestation is supplied.
- A SHA-256 chain detects edits relative to retained data. It is not a signature, an independently trusted origin, an immutable external ledger, or proof that a complete rewritten export is authentic.
- Node sessions, including the in-memory HATS SQLite ledger, are lost on server restart. Worker sessions use server-side SQLite checkpoints and survive runtime restarts until idle expiry or reset. Neither mode is an immutable archive; download evidence you need to keep.

See [architecture](docs/ARCHITECTURE.md), [metadata-only telemetry design](docs/TELEMETRY.md), [new-work disclosure](docs/HACKATHON.md), [three-minute demo](docs/DEMO_SCRIPT.md), and [submission draft](docs/SUBMISSION.md). The optional [SwiftUI evidence observer](examples/ios/AIDTASViewer.swift) is source-only: it imports a HATS JSON export and has not been compiled in this Linux environment.

The newly written source in `guardian/` is licensed under [Apache-2.0](LICENSE); see [NOTICE](NOTICE) for scope and attribution. The existing StateBench component outside this directory is prior work under the repository's [MIT license](../LICENSE), and is not presented as newly built for this demo. Neither component's license relicenses the other. No confidential research code, supplied private fixtures, outreach records, or source archives are included or relicensed. Bundled dependencies retain their [third-party licenses](public/third-party-notices.txt).
