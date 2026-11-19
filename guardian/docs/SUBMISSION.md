# Submission draft — UNISON Guardian

**Status: draft for the participant's review.** The v0.2.0 Guardian runtime is public and deployed. The HATS expansion described below requires its own reviewed source, CI and deployment record before the release claims are updated. Existing release evidence is in [RELEASE_CHECKS.md](RELEASE_CHECKS.md). Video, real Meta usage and final submission remain pending.

## Entry details

| Field | Draft answer |
| --- | --- |
| Project | UNISON Guardian: Verifiable Authority and Identity for AI Agents |
| Track | Indie Developer Track |
| Theme | Push the Frontier |
| Builder | Deonte Watts |
| GitHub profile | https://github.com/DeontewattsV1 |
| LinkedIn | https://www.linkedin.com/in/deonte-watts-73aa363a7 |
| Location | San Francisco, California, United States |
| Public project repository | https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian — merged through PR #24 |
| Reviewed runtime source | `ae06eab73316c94a4bd8c2e3a81c99a77bd208da` |
| Live product | https://unison-guardian.info-ccehospitalitygroup.workers.dev — health check and desktop/mobile browser workflows verified |
| Three-minute video | PENDING — add an accessible video URL |

## Short description

UNISON Guardian is an open, testable harness for delegated authority. It maps registered paths, rechecks queued actions and hierarchical agent ancestry at execution time, enforces bounded spawning, and preserves evidence without treating model assertions as authorization.

## What we built

Agent permissions often span a planner, delegated agents, queued work and a tool gateway. Removing one authorization may leave another path to a protected action. Developers need a way to inspect that distinction and reproduce the failure.

Guardian combines an interactive authority graph with a deterministic verifier and an inspectable event ledger. A baseline run executes a synthetic action and queues another. Revoking the ancestor grant then blocks that queued operation at commit. A second scenario exposes a surviving independent route and returns FAIL. A third returns UNKNOWN because inventory coverage is incomplete.

The HATS lab adds a four-level Macro/Meso/Micro/Nano hierarchy. Each digest binds the run, child identity, parent digest and inherited scope. Actual lineage recomputation and current ancestor checks govern synthetic invocations. Hard depth, scope and spawning quotas reject excessive transitions independently of analytics. The one-click demo exercises these denials, then revokes an ancestor and attempts the stale descendant action while the synthetic action counter stays at one.

An analytic lane computes timestamp and topology features from recorded metadata. Its uncalibrated forecasts are advisory. They are not a probability that an actor is AI, proof of consensus or independently authenticated attribution. Metadata minimization rejects unsupported fields; raw prompts, generated text, tokens, credentials, private headers, literal IPs and mouse trajectories are outside the default contract. Proposed cluster collector rules are documented, not deployed sensors.

The model integration asks Muse Wonder to produce structured suggestions about the registered graph. That advisory output cannot modify permissions or decide verification outcomes. The server-side adapter and deterministic verifier are separate paths through the implementation.

A Cloudflare deployment uses SQLite-backed Durable Objects to preserve each anonymous demonstration session through runtime restart. It serves the deterministic scenarios with paid model requests disabled. The live runtime was deployed from merged source commit `ae06eab73316c94a4bd8c2e3a81c99a77bd208da`. A retained run and queued operation survived deployment; subsequent revocation and replay blocked the stale action while the synthetic counter stayed at one. Guardian is hosted in `guardian/` alongside the existing StateBench benchmark. See [RELEASE_CHECKS.md](RELEASE_CHECKS.md) for exact CI and deployment evidence.

## Why it fits Push the Frontier

Guardian explores a concrete control problem in agent software: whether revocation reaches delegated and delayed operations. The demo makes the authority boundary visible and provides counterexamples developers can run rather than relying on an agent's own report. Its scope is deliberately explicit: registered synthetic routes and a local protected-action counter.

## Meta integration — update before final submission

The local Node implementation targets `muse-wonder-1.0` through Meta's Responses API with structured output. Model calls use a server-held credential. The proposal identifies grants to inspect and includes uncertainty; it does not grant authority. The public Worker explicitly disables model analysis. A deterministic public demonstration alone does not demonstrate live Meta model usage.

**Live usage evidence: PENDING until a real authorized request succeeds.** Replace this status with the actual submitted commit, request date, model identifier, non-secret response identifier when supplied and the recording segment showing the result. Tests with injected responses establish adapter behavior only. They do not establish that Meta was called.

## Original contribution and limitations

The Guardian graph, verifier, three scenarios, HATS lab, metadata analytics, event inspector, Meta adapter, interface, SQLite persistence layer and tests in `guardian/` were newly implemented for this hackathon task. A SwiftUI evidence importer is included as source-only and has not been compiled in the Linux environment. Earlier research informed the problem framing. Existing StateBench code, fixtures, experiments and results outside `guardian/` are prior work in the same repository and are excluded from the new contribution; see [HACKATHON.md](HACKATHON.md). Guardian source is Apache-2.0, while existing StateBench remains MIT. Neither component relicenses the other. Supplied private research is excluded and is not relicensed.

All principals, grants, protected actions and scenario events are synthetic. The app does not revoke real cloud credentials or control third-party execution. HATS creates records, not external processes; bounded API spawning is not a proof against arbitrary program recursion. Its hash chains and receipts support consistency inspection, not authenticated legal identity, independent certification or externally immutable history. Node sessions, including its in-memory HATS SQLite database, are lost on server restart. Worker sessions survive runtime restart through server-side SQLite checkpoints, with one-hour idle expiry, reset and event bounds. Anonymous cookies isolate sessions without authenticating users.

## Participant-owned submission checklist

Complete these checks against the final artifact; unchecked items are pending, not completed work.

- [x] Publish the reviewed `guardian/` integration and confirm it opens without account access.
- [x] Verify `guardian/` contains only intended new source, synthetic scenarios and documentation; exclude credentials and private research inputs, and disclose StateBench outside it as prior work.
- [x] Record the reviewed candidate runtime commit and preserve an accurate history of work created during the event.
- [x] Run the relevant tests and production build for the reviewed candidate; retain the commit-specific results.
- [ ] Complete a successful real Meta request and retain non-secret evidence of the response.
- [x] Deploy the candidate build and confirm its live health endpoint; deployed source commit is recorded above.
- [x] Confirm the core workflow works at the live URL and retain the desktop/mobile browser verification result.
- [ ] Record the reviewed HATS expansion revision, CI and live desktop/mobile checks before including it in the deployed-runtime claim.
- [ ] Record the three-minute video using [DEMO_SCRIPT.md](DEMO_SCRIPT.md); clearly identify new work and actual model-call status.
- [ ] Confirm that judges can access the repository, live product and video links.
- [ ] List every project contributor accurately and confirm the selected track.
- [ ] Review the current organizer rules and complete any required participant acceptance personally.
- [ ] Submit one project entry through the organizer's platform and retain the actual confirmation.

The participant guide supplied for this task gives the deadline as **November 4, 2026 at 6:00 PM Pacific Time** (**9:00 PM America/New_York**). Check the current organizer page for changes before submitting: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit.

The source publication, merged candidate and public deployment are recorded above. This draft has not submitted an application, claimed credits, accepted terms or uploaded a video.
