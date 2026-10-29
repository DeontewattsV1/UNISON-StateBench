# Changelog

## 0.2.0 — October 29, 2026

- License newly written Guardian source under Apache-2.0, with explicit exclusions for private research and separate prior work.
- Add a Cloudflare Worker entry point with per-session SQLite Durable Objects, validated server checkpoints, restart persistence, one-hour idle expiry and a transactional 200-event limit.
- Keep public model requests disabled; the local Node service retains the optional server-side Muse Wonder integration.
- Distinguish hosted and local storage in the interface and evidence documentation.
- Add hosted runtime tests, a reproducible Worker bundle and a GitHub verification workflow.
- Keep the local frontend on loopback and renew local browser session cookies with their sliding idle deadline.

Guardian is public under [UNISON-StateBench's `guardian/` directory](https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian), merged through [PR #24](https://github.com/DeontewattsV1/UNISON-StateBench/pull/24) as commit `ae06eab73316c94a4bd8c2e3a81c99a77bd208da`. The [public sandbox](https://unison-guardian.info-ccehospitalitygroup.workers.dev) was deployed from that merged source with its SQLite namespace retained. A queued run survived the deployment; revocation and replay then blocked the stale action without increasing the synthetic counter. Guardian and StateBench CI passed for the merged source, and desktop/mobile workflows passed at the redeployed HTTPS origin; see [release checks](docs/RELEASE_CHECKS.md) for exact run references. StateBench remains MIT and Guardian remains Apache-2.0. Live Meta inference and the demo recording remain pending.

## 0.1.0 — October 29, 2026

- Implement the synthetic authority graph, queued-action revocation checks, surviving-path and incomplete-inventory scenarios, evidence export, identity views and local Meta adapter.
