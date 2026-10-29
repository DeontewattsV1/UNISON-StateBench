# Release candidate checks

Checks performed October 29, 2026 for Guardian version 0.2.0 are recorded below. Guardian integrates under `guardian/` in UNISON-StateBench on branch `feat/unison-guardian-hackathon`. Local integration verification passed: 104 StateBench tests on Python 3.12, 41 Guardian backend tests, 6 Worker tests, the production build, and desktop/mobile browser workflows against the nested app. Python 3.11 and remote GitHub Actions remain to be verified. No real Meta response is established by these checks.

| Check | Observed result |
| --- | --- |
| `npm test` | 41 tests passed: deterministic engine, checkpoint restoration, local HTTP isolation and mocked Meta transport |
| `npm run build:worker` | React production build and bundled Worker completed |
| `npm run test:worker` | 6 tests passed in Miniflare/workerd, including complete runtime restarts with retained SQLite storage, concurrent replay, session isolation, and event-limit rollback |
| `npx wrangler deploy --dry-run --outdir .release/wrangler` | Deployment bundle validated; this dry-run command performed no upload |
| `BROWSER_TEST_URL=http://127.0.0.1:8787 npm run test:browser` | Desktop 1536×1024 and mobile 390×844 workflows passed against local Wrangler runtime |
| `node scripts/verify-evidence.mjs <browser-export>` | Event digests and sequence links recomputed; internal consistency PASS, origin untrusted |
| Focused source review | No credentials or confidential archive contents found in reviewed source; intended public profile links retained |

Browser checks exercised queued-action denial with an unchanged synthetic counter, alternate-path FAIL, incomplete-coverage UNKNOWN, evidence download, identity and ledger navigation, explicit model unavailability and mobile overflow. The proposal display test used intercepted, explicitly mocked responses. No paid inference was requested.

## Observed deployment and publication status

- Live public sandbox: https://unison-guardian.info-ccehospitalitygroup.workers.dev.
- Initial standalone Guardian source ID: `fafd11fff463a6b75dea6cce5820ceec7730088f`, before integration into StateBench.
- Uploaded Worker SHA-256: `4345eea98f2f0df94d002c1906f7d62a7abd09e3060209575b08870477d07812`.
- Cloudflare upload returned HTTP 200, deployment ID `21cfa18f8b4843fa9d5e5de516c30a18`.
- SQLite Durable Object class `GuardianSession`, binding `GUARDIAN_SESSIONS`, migration tag `v1`.
- Workers.dev enabled; preview URLs disabled. No model secrets, custom domain or DNS changes were added.
- Live `/api/health` returned HTTP 200 and confirmed `public-sandbox`, `per-session-durable-object-sqlite` and `meta.enabled: false`.
- Live browser workflow verification: **PASS** at the HTTPS origin, desktop 1536×1024 and mobile 390×844. All three scenario verdicts, stale queued denial with an unchanged counter, identity/ledger navigation, evidence export and model-unavailable HTTP 503 were exercised.

The live browser run used the updated proxy-aware test harness. It routes remote browser and Node-side API requests through inherited `HTTPS_PROXY`/`HTTP_PROXY` and `NO_PROXY` settings when present. The proposal isolation check used intercepted, explicitly mocked output; the live deployment did not perform Meta inference.

The public source destination is [DeontewattsV1/UNISON-StateBench](https://github.com/DeontewattsV1/UNISON-StateBench), component `guardian/`. The integration branch `feat/unison-guardian-hackathon` starts from StateBench commit `c5fd57605d7cdf538a7be254adbfbfede2390af7`. Existing benchmark code and results outside `guardian/` remain prior work under MIT; Guardian is a separate Apache-2.0 component. Record the actual pull request, reviewed merge commit, CI results and deployment of that build before submission. This initial deployment record does not assert that the integration branch has merged.

## Pending artifacts

The repository integration needs its final reviewed commit, CI and deployment record. A successful real Meta request needs an authorized server-side key. The three-minute recording and final organizer submission remain pending. See [DEPLOYMENT.md](DEPLOYMENT.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and [SUBMISSION.md](SUBMISSION.md).
