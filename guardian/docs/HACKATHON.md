# Hackathon scope and contribution disclosure

UNISON Guardian is an Indie Developer Track project for the **Push the Frontier** theme of the Meta Global AI Developer Hackathon. The new contribution is the `guardian/` component of the UNISON-StateBench repository: a bounded software demonstration of authority reachability, delegated revocation and evidence inspection.

The implementation was created in this task on **October 29, 2026**. Preserve the actual Git history and dated build/test evidence when preparing the submission. Do not backdate commits or describe earlier research as newly built hackathon functionality.

## What was built for this entry

| Contribution | Implemented scope |
| --- | --- |
| Authority graph | New registered synthetic principals, delegated grants, queued worker and tool-gateway routes, including an independent alternative path. |
| Action-time verification | New deterministic checks of the current grant ancestry when a queued operation commits. Enqueue-time permission cannot substitute for current authority. |
| Three-result demonstration | New `queued`, `alternate` and `unknown` scenarios showing bounded PASS, surviving-path FAIL and incomplete-coverage UNKNOWN. |
| Evidence and identity views | New per-run event receipts, hash-chain consistency checks, evidence filters and downloadable JSON. Run, task, configured model, principal, deployment and owner are separate fields. |
| Meta adapter | New server-side Muse Wonder integration that requests structured advisory analysis. A model proposal cannot modify grants, policies or verifier results. |
| Product surface and tests | New React interface, Node service and reproducible tests for these implemented boundaries. Report only checks actually run against the submitted commit. |
| Public deployment entry point | New Cloudflare Worker with a SQLite-backed Durable Object per anonymous browser session, validated internal checkpoints, idle expiry and event bounds. Public model requests remain disabled. |

## Existing ideas and separate work

Authority graphs, least-privilege delegation, action-time authorization, revocation, provenance and hash-linked audit records are established engineering ideas. Earlier research informed the problem framing. This entry does not claim to invent these concepts or establish scientific novelty.

[UNISON-StateBench](https://github.com/DeontewattsV1/UNISON-StateBench) is existing work hosted in the same repository. Its Python benchmark, fixtures, experiments, plugins and results outside `guardian/` predate this Guardian integration and are not new hackathon contributions. Guardian is a separate component; it is not a rename or a validation result of StateBench. [PR #24](https://github.com/DeontewattsV1/UNISON-StateBench/pull/24) added Guardian to main on October 29, 2026, with merge commit `ae06eab73316c94a4bd8c2e3a81c99a77bd208da`. The pre-integration StateBench baseline is `c5fd57605d7cdf538a7be254adbfbfede2390af7`.

Private research packages and their source, fixtures and documents are not redistributed with Guardian. The `guardian/` component uses newly created demonstration source and synthetic scenario data. Its [Apache-2.0 license](../LICENSE) and [NOTICE](../NOTICE) apply to this component. Existing StateBench code remains under the repository root's [MIT license](../../LICENSE); neither license relicenses the other component or supplied private inputs. Third-party libraries retain their own licenses and attribution.

## What the demonstration establishes

The verifier can compute reachability over its registered synthetic graph, check delegated ancestry at a local commit boundary and report the result of the implemented scenario. The alternative-path scenario deliberately produces FAIL when a registered route survives. The incomplete-inventory scenario deliberately returns UNKNOWN when graph coverage is insufficient.

The protected action changes a synthetic demonstration counter. It does not move money, revoke an external credential, cancel a third-party job or enforce permissions in another system. State is isolated per demonstration session. Node sessions are held in memory and disappear on server restart. The Worker entry point stores validated checkpoints in SQLite so sessions survive runtime restart, subject to reset and one-hour idle expiry; it is not an immutable evidence archive.

The ledger recomputes local SHA-256 digests and sequence links. It does not verify signatures, establish legal or vendor identity, provide an external witness or prevent a privileged operator from reconstructing an exported chain. No production authorization, independent evaluation or certification is claimed.

## Meta usage disclosure

The local Node adapter targets `muse-wonder-1.0` through Meta's Responses API. Credentials remain on the server. Model analysis is advisory; the deterministic verification layer makes the authority decision. The public Worker unconditionally disables model requests and requires no model credential.

An implemented adapter, configured key, mocked test response or model name is not evidence of a successful real Meta call. Before submission, record a successful authorized request against the submitted build, retain a non-secret response identifier when supplied, and show the corresponding structured proposal. If no real request has completed, mark live model usage **PENDING**. Do not present an offline response as Meta-generated output.

## Submission boundary

The participant guide supplied for this task requires a public repository, an accessible live product and a three-minute demonstration video that identifies work created during the event. [Guardian source is public on main](https://github.com/DeontewattsV1/UNISON-StateBench/tree/main/guardian), and the [public Guardian sandbox](https://unison-guardian.info-ccehospitalitygroup.workers.dev) runs the reviewed merged build. The existing StateBench benchmark must be disclosed as prior work. [Release checks](RELEASE_CHECKS.md) record the reviewed source, CI and deployment evidence. Live Meta usage, the video and organizer submission remain pending; no acceptance or certification is claimed.
