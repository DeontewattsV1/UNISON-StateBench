# Release checks

Checks performed October 29, 2026 for Guardian version 0.2.0. [PR #24](https://github.com/DeontewattsV1/UNISON-StateBench/pull/24) merged the reviewed Guardian component as commit [`ae06eab73316c94a4bd8c2e3a81c99a77bd208da`](https://github.com/DeontewattsV1/UNISON-StateBench/commit/ae06eab73316c94a4bd8c2e3a81c99a77bd208da). Source is publicly accessible under [`main/guardian`](https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian). The runtime deployed from that merged source is recorded below. These checks do not establish a real Meta response, participant eligibility or organizer submission.

## Automated verification

| Check | Observed result |
| --- | --- |
| [Guardian CI on merged source](https://github.com/DeontewattsV1/UNISON-StateBench/actions/runs/40860198801) | SUCCESS: 42 backend tests, 6 Worker tests, production build and desktop/mobile browser workflow |
| [StateBench CI on merged source](https://github.com/DeontewattsV1/UNISON-StateBench/actions/runs/40860198761) | SUCCESS on Python 3.11 and 3.12: compile checks, frozen empirical matrix verification and 104 tests per interpreter |
| `npm test` | 42 tests passed: deterministic engine, checkpoint restoration, local HTTP isolation, active-session cookie renewal and mocked Meta transport |
| `npm run build:worker` | React production build and bundled Worker completed |
| `npm run test:worker` | 6 tests passed in Miniflare/workerd, including complete runtime restarts with retained SQLite storage, concurrent replay, session isolation and event-limit rollback |
| `npx wrangler deploy --dry-run --outdir .release/wrangler` | Deployment bundle validated; this dry-run command performed no upload |
| Local browser workflow | Desktop 1536×1024 and mobile 390×844 passed against the nested Guardian app |
| Post-deployment HTTPS browser workflow | Desktop 1536×1024 and mobile 390×844 passed against the live origin |
| `node scripts/verify-evidence.mjs <live-browser-export>` | Event digests and sequence links recomputed; internal consistency PASS, origin untrusted |
| Focused source review | No credentials or confidential archive contents found in reviewed Guardian source; intended public profile links retained |

Browser checks exercised queued-action denial with an unchanged synthetic counter, alternate-path FAIL, incomplete-coverage UNKNOWN, evidence download, identity and ledger navigation, explicit model unavailability, and mobile overflow. There were no browser runtime errors. Proposal display and isolation used intercepted, explicitly mocked output. No paid inference was requested.

## Observed deployment

- Live public sandbox: https://unison-guardian.info-ccehospitalitygroup.workers.dev.
- Deployed merged source: `ae06eab73316c94a4bd8c2e3a81c99a77bd208da`.
- Worker SHA-256: `4345eea98f2f0df94d002c1906f7d62a7abd09e3060209575b08870477d07812`.
- Cloudflare upload returned HTTP 200, deployment ID `9bc7c42e0cd54601bd97987bae3885c1`.
- SQLite Durable Object class `GuardianSession`, binding `GUARDIAN_SESSIONS`, migration tag `v1`; the existing namespace was retained.
- Workers.dev enabled; preview URLs disabled. No model secrets, custom domain or DNS changes were added.
- Live `/api/health` returned HTTP 200 and confirmed `public-sandbox`, `per-session-durable-object-sqlite` and `meta.enabled: false`.
- A cross-deployment test preserved the same run and queued operation. Revoking authority and replaying afterward blocked the stale action; the synthetic action counter remained one.
- Post-deployment HTTPS browser checks passed all three scenario verdicts, stale queued denial, identity/ledger navigation, evidence export and model-unavailable HTTP 503.

The browser harness routes remote browser and Node-side API requests through inherited `HTTPS_PROXY`/`HTTP_PROXY` and `NO_PROXY` settings when present. The proposal isolation check uses mocked output; the public deployment does not perform Meta inference.

## Source and license scope

The public source is [DeontewattsV1/UNISON-StateBench's `guardian/` component](https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian). Existing benchmark code and results outside `guardian/` remain prior work under MIT. Guardian is a separate Apache-2.0 component; neither license relicenses the other. Supplied confidential research archives, private fixtures and outreach records are excluded from Guardian publication.

## Pending artifacts

For packaged source, Worker bundles and checksums, see the repository's [release page](https://github.com/DeontewattsV1/UNISON-StateBench/releases). A successful real Meta request needs an authorized server-side key. The three-minute recording, participant eligibility/rules acceptance and final organizer submission remain pending. See [DEPLOYMENT.md](DEPLOYMENT.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and [SUBMISSION.md](SUBMISSION.md).
