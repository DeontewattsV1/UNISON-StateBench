# Changelog

## 0.2.0 — October 29, 2026

- License newly written Guardian source under Apache-2.0, with explicit exclusions for private research and separate prior work.
- Add a Cloudflare Worker entry point with per-session SQLite Durable Objects, validated server checkpoints, restart persistence, one-hour idle expiry and a transactional 200-event limit.
- Keep public model requests disabled; the local Node service retains the optional server-side Muse Wonder integration.
- Distinguish hosted and local storage in the interface and evidence documentation.
- Add hosted runtime tests, a reproducible Worker bundle and a GitHub verification workflow.
- Keep the local frontend on loopback and renew local browser session cookies with their sliding idle deadline.

The public sandbox is deployed at https://unison-guardian.info-ccehospitalitygroup.workers.dev. Its initial standalone build used source ID `fafd11fff463a6b75dea6cce5820ceec7730088f`; health and desktop/mobile browser checks confirm the running synthetic sandbox with model requests disabled. Guardian now integrates under `guardian/` in the existing UNISON-StateBench repository on branch `feat/unison-guardian-hackathon`, preserving the benchmark's MIT license and Guardian's Apache-2.0 scope. The source includes inherited proxy support for remote browser checks. Record the reviewed integration commit and its deployment checks before final submission. Live Meta inference and the demo recording remain pending.

## 0.1.0 — October 29, 2026

- Implement the synthetic authority graph, queued-action revocation checks, surviving-path and incomplete-inventory scenarios, evidence export, identity views and local Meta adapter.
