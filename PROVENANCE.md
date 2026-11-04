# Provenance

Consolidation branch: `consolidation/unison-unified`, based on UNISON-StateBench `main` at `86ccd538769d97815d3a271380a609dc167ade0f`. Snapshot date: 2026-11-04. All source repositories were read-only during this work; none was modified.

## Imported repositories (git subtree, full history preserved)

Each was added with `git subtree add --prefix=sources/<repo> <repo> main` (no squash), so `git log -- sources/<repo>` shows the original commits and authorship.

| Repository | Visibility | Commit SHA imported | Commits | Files | License | Location |
|---|---|---|---|---|---|---|
| DeontewattsV1/AGI-CP | public | `585590abd126973bc498835ec8774a03bcb3cac4` | 147 | 81 | MIT (© 2026 Deonte Watts) | `sources/AGI-CP/` |
| DeontewattsV1/traceability-matrix | public | `8e1e8b63dec391836241780f493866a36cdec81a` | 149 | 125 | **none (no LICENSE file)** | `sources/traceability-matrix/` |
| DeontewattsV1/Linguistic-Encryption-System-Celestial- | public | `e4e63f2cc54ad0819ea025716d7a1dbff5f8640c` | 93 | 84 | MIT (© 2026 GoodShyt Group / Deonte Watts) + LICENSE_COMMERCIAL.md | `sources/Linguistic-Encryption-System-Celestial-/` |
| DeontewattsV1/SOVEREIGN-LATTICE-GOVCORE | public | `fdcbeba822ec43f2aac7c6ffbc2483783733ee2d` | 11 | 43 | MIT (© 2026 DeontewattsV1) | `sources/SOVEREIGN-LATTICE-GOVCORE/` |
| DeontewattsV1/AISoulFrameworkConcepts | public | `11de77816cfea641d836cf9e98d0a5ca2e0919e1` | 15 | 12 | MIT (© 2026 DeontewattsV1) + LICENSE_COMMERCIAL.md | `sources/AISoulFrameworkConcepts/` |

## Formerly private repositories (imported 2026-11-04 with explicit owner approval to publish)

| Repository | Visibility at import | Commit SHA imported | Commits | License | Method | Location |
|---|---|---|---|---|---|---|
| DeontewattsV1/Recognitive-field | private | `23e39c0c0508fc369af0c1a8b0d7d2e7cb717876` | 13 | MIT | git subtree, full history | `sources/Recognitive-field/` |
| DeontewattsV1/celestial_agent_desktop_upgrade | private | `c3f3a629b700fb6cb310a48451c514e12025f360` | 15 | MIT + LICENSE_COMMERCIAL.md | git subtree, full history | `sources/celestial_agent_desktop_upgrade/` |
| DeontewattsV1/phaseform_runtime_package_v6 | private | `3d4f63c863f20206859fa9d42337f9699462088a` | 12 (history **not** imported) | MIT | **file copy** of the tree at that SHA | `sources/phaseform_runtime_package_v6/` |

phaseform history was not imported because it contains `phaseform_runtime_package_v6/keys/creator_private_key.b64` (a committed private key, deleted from the tree but still in history), plus `vault/*.enc`, `manifests/*.sig` and `runtime_state/audit.log`. The copy has 28 of the 35 tracked files. It excludes `vault/policy_a.enc`, `vault/policy_b.enc`, `vault/verify_me.enc`, `manifests/policy_a.sig`, `manifests/policy_b.sig`, `manifests/verify_me.sig` and `runtime_state/audit.log`. The included `manifests/*.json` carry only public keys, hashes, nonces and salts. **The owner should treat that private key as compromised and rotate it.** It remains in the private repository's history.

The Recognitive-field and celestial_agent_desktop_upgrade histories were scanned in full: no `.env`, keys or token patterns, and nothing over 50 MB (largest objects 58 KB and 21 KB). celestial_agent_desktop_upgrade history contains a `__pycache__/*.pyc` (21 KB). It is harmless and kept because it is part of history.

## What came from where (derived work in this branch)

| New file | Derived from |
|---|---|
| `playground/src/stages.js` `collectEvidence`, `decideEvidence` | `sources/AGI-CP/capability-gateway/src/auth/evidence.ts` (direct port) |
| `playground/src/stages.js` `governanceGate` | `sources/SOVEREIGN-LATTICE-GOVCORE/SOVEREIGN-LATTICE-GOVCORE/govcore/governance/kernel.py` `GovernanceKernel.evaluate_operating_mode` and rules RULE-001..007 (port) |
| `playground/src/stages.js` `detectStateCollapses` | `benchmark/state_collapse.py` `detect_state_collapses` (simplified port; oracle derivation replaced by an explicit `satisfied` flag) |
| `playground/src/stages.js` `validatePhaseformPolicy`, `phaseformStep` | `sources/phaseform_runtime_package_v6/policy_schema.py`, `orchestrator.py` (`handle_event`) (identical copies also in Linguistic-Encryption-System-Celestial-) |
| `playground/src/stages.js` `rfFlow`, `rfTurbCenter`, `rfProbe` | `sources/Recognitive-field/recognitive-field-v3.html` `flow()`, `turbCenter()`, `injectProbe()` (port; seeded PRNG replaces `Math.random`) |
| `playground/src/stages.js` `desktopCodec`, `resolveSafe`, `desktopExecute` | `sources/celestial_agent_desktop_upgrade/celestial_core.py` `CelestialCodec`, `SafeWorkspace.resolve_safe`, `AgentRuntime._execute_line` (port; in-memory; codec checked against Python in `playground/tests/desktop_fixture.json`) |
| `playground/src/stages.js` `glyphMap`, `encodeMessage`, `xorPad` | `sources/Linguistic-Encryption-System-Celestial-/celestial_agent/celestial_language.py` (port; output checked byte-for-byte against the Python in `playground/tests/celestial_fixture.json`). `decodeMessage` is new. |
| `playground/src/stages.js` `linkRequirements` | New code. Concept from `sources/traceability-matrix/attached_assets/*Requirements-Traceability-Matrix*` (that repo has no linking code) |
| `docs/ADMISSIBILITY.md` | IETF individual drafts draft-watts-scientific-admissibility(-evidence), -research-evidence-envelope, -claim-promotion-receipts, -verification-promotion-boundaries, -gov-verification-promotion-boundaries, -unison-state-preservation, -unison-noncollapse (datatracker abstracts, rev -01) |

## Skipped material

| Item | Reason |
|---|---|
| phaseform_runtime_package_v6 git history | Contains a committed private key (`keys/creator_private_key.b64`) and encrypted/signature files |
| phaseform `vault/*.enc`, `manifests/*.sig`, `runtime_state/audit.log` (7 files) | Encrypted payloads, signatures, runtime log |
| Nothing from the public repos | Scans of HEAD and full history found no `.env`, private keys, PEM/P12 files, or token patterns (GitHub, AWS, Slack, OpenAI-style). No file in any history exceeds 50 MB (largest: 3.8 MB PNG in Linguistic-Encryption-System-Celestial-). |

Note: `guardian/.env.example` already existed in UNISON-StateBench; it is a template, untouched.

## Confidentiality markers

Case-sensitive search for `CONFIDENTIAL`, `PROPRIETARY`, `FOUO` across all nine repositories, including the full history of the three formerly private ones: **no matches**. Case-insensitive matches are only license text ("integration into proprietary software" in LICENSE_COMMERCIAL.md) and existing UNISON Guardian notices that *exclude* confidential material. Nothing was withheld on this basis.

## License review (flags)

1. **traceability-matrix has no LICENSE.** By default that means all rights reserved. The owner is the same person, so inclusion here is permitted by the owner, but downstream users of `sources/traceability-matrix/` have no grant. Recommendation: add an MIT LICENSE upstream.
2. **Dual MIT + LICENSE_COMMERCIAL.md** (Linguistic-Encryption-System-Celestial-, AISoulFrameworkConcepts, celestial_agent_desktop_upgrade). MIT already permits commercial use, so the commercial-license file cannot restrict MIT-licensed copies. This is an internal inconsistency to resolve upstream, not a conflict with this repository.
3. **guardian/** in UNISON-StateBench is Apache-2.0 within an MIT repository. Compatible (both permissive); keep `guardian/NOTICE`.
4. Copyright-holder names differ (Deonte Watts; DeontewattsV1; GoodShyt Group / Deonte Watts). Not a conflict; noted for attribution.
5. `celestial_language.py` asks to retain the credit "created by TDD". Retained in the source file; the JS port references it.
6. GitHub's license detector reports `none` for every repository (it does not recognise the LICENSE files' format); the table above reflects the actual LICENSE file contents.
