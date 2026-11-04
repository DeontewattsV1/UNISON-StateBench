# Claims register

Every method or concept brought into this repository is classified as exactly one of:
**D** definition · **IT** implemented mechanism with tests · **IU** implemented mechanism without tests · **H** hypothesis or concept only · **R** fitted or empirical result (with data location).

Classification reflects what is in the repository at the commits in `PROVENANCE.md`. "With tests" means a test file exercising the mechanism exists in the repository; it does not mean the tests were run by this review unless noted. Novelty for every row: **not assessed against prior work**.

| # | Item | Repository / path | Class | Notes |
|---|---|---|---|---|
| 1 | Typed invariant `I_k = (value, epistemic_status, provenance, authority)` | UNISON-StateBench `docs/STATEBENCH.md`, `benchmark/models.py` | D | |
| 2 | Consistency / correctness / state preservation distinction | UNISON-StateBench | D | |
| 3 | Deterministic oracle | `benchmark/oracle.py` | IT | `tests/test_oracle.py` |
| 4 | State-collapse detection (unsupported transition, unknown→known) | `benchmark/state_collapse.py` | IT | `tests/test_noncollapse.py`; ported to playground with tests |
| 5 | Typed non-collapse relations and certificates (C_I, C_Q, C_R, C_V, C_A) | `benchmark/typed_noncollapse.py` | IT | `tests/test_typed_noncollapse_extension.py` |
| 6 | Mutations (paraphrase, reorder, contradiction, missing, authority conflict, adversarial) | `benchmark/mutations/` | IT | `tests/test_mutations.py` |
| 7 | Metrics (abstention, authorization, contradiction, correspondence, invariant, isolation, state collapse) | `benchmark/metrics/` | IT | `tests/test_scoring.py` |
| 8 | Renderers (JSON, YAML, prose, table, event log) | `benchmark/renderers/` | IT | `tests/test_renderers.py` |
| 9 | Frozen v0.1 trial matrix (162 calls per model) | `experiments/v0.1/`, `empirical/` | IT | Plan and manifest only. **No result data in repository**, so no R entry. |
| 10 | Bootstrap and failure-topology analysis | `analysis/` | IT | `tests/test_empirical_analysis.py` |
| 11 | Guardian authority/revocation sandbox | `guardian/` | IT | `guardian/server/*.test.mjs`, `worker/*.test.mjs`; Apache-2.0 |
| 12 | Fail-closed gate `ALLOW ⇔ I∧K∧S∧D∧A∧T∧R∧P` | AGI-CP `capability-gateway/` | IT | `test/security-boundary.node-test.ts` |
| 13 | Evidence window and decision | AGI-CP `src/auth/evidence.ts` | IT | `test/evidence.node-test.ts`; ported to playground with tests |
| 14 | Revocation lineage | AGI-CP `src/auth/revocation.ts` | IT | `test/revocation.node-test.ts` |
| 15 | Issuer policy | AGI-CP `src/auth/issuer-policy.ts` | IT | `test/issuer-policy.node-test.ts` |
| 16 | Signed capability request | AGI-CP `src/auth/capability-request.ts` | IT | `test/capability-request.node-test.ts` |
| 17 | Replay protection, delegation, signature, plugin registry | AGI-CP `src/auth/replay.ts`, `delegation.ts`, `signature.ts`, `src/plugins/` | IU | No dedicated test file found |
| 18 | TRACT passport / receipt schemas and runtime | AGI-CP `tract/` | IT | `tract/runtime/test/runtime.node-test.ts`; console has a Playwright visual test |
| 19 | AGI-CP / TRACT protocol specifications | AGI-CP `spec/` | D | |
| 20 | Requirements traceability matrix for PhaseForm | traceability-matrix `attached_assets/` | D | Pasted documents |
| 21 | Automated requirement↔code↔test linking | traceability-matrix | H | Repo contains an API scaffold (health endpoint) and UI kit only; no linking code. Playground stage is new illustrative code. |
| 22 | Repo health audit | traceability-matrix `.github/workflows/repo-health-audit.yml` | IU | |
| 23 | Self-healing adaptive device (PhaseForm roadmap, blueprint) | traceability-matrix `attached_assets/` | H | |
| 24 | Governance kernel: operating modes and policy rules | SOVEREIGN-LATTICE-GOVCORE `govcore/governance/kernel.py` | IT | `tests/test_governance.py`; ported to playground with tests |
| 25 | Human protection plane | GOVCORE `govcore/human/protection.py` | IT | `tests/test_human_protection.py` |
| 26 | Reasoning engine | GOVCORE `govcore/reasoning/engine.py` | IT | `tests/test_reasoning.py` |
| 27 | Router | GOVCORE `govcore/routing/router.py` | IT | `tests/test_routing.py` |
| 28 | Bounded agents | GOVCORE `govcore/agents/bounded_agents.py` | IT | `tests/test_agents.py` |
| 29 | Alignment with M-25-21, M-25-22, NIST AI RMF | GOVCORE docstrings | H | Stated, not assessed |
| 30 | PhaseForm policy schema validation | LES `policy_schema.py` (= private phaseform) | IU | No source test imports it directly (`_smoke_test.py` drives the pipeline via subprocess; coverage not verified). The playground port has unit tests. |
| 31 | PhaseForm event→action orchestrator | LES `orchestrator.py` | IU | As row 30. Playground port of `handle_event` mapping has unit tests. |
| 31a | Agent-spec encryption pack (`AgentSpecCrypto`, `EncryptedAgentPack`) | LES `celestial_agent/agent_spec_crypto.py` | IT | `_smoke_test.py`, `_smoke_manifest.py` |
| 32 | Manifest verification, release manifest | LES `manifest_verifier.py`, `release_manifest.py` | IT | `_smoke_manifest.py`, `_smoke_release_manifest.py` |
| 33 | Tamper tester, rotation guard, pack diff, profile manager, risk profile, template builder/packager/catalog, handoff bundle | LES | IT | Matching `_smoke_*.py` scripts |
| 34 | Policy rotator, vault watcher, event injector, state viewer, data reduction, pack builder | LES | IU | No dedicated smoke script found |
| 35 | Celestial glyph language + one-time-pad helper | LES `celestial_agent/celestial_language.py` | IU | No Python test in source repo; the playground port has a byte-for-byte cross-check test against the Python output |
| 36 | Aletheia lattice threat/control matrix and deployment architecture | LES `docs/` | D | |
| 37 | Deception simulation guardrails | LES `docs/deception_simulation_guardrails.md`, `deception_review_stub.py` | IT | `_smoke_deception_review_stub.py` (stub) |
| 38 | Security strength of the glyph encoding | LES | H | Glyph substitution is a keyed code, not encryption; confidentiality comes only from the one-time pad. Not evaluated. |
| 39 | AI Soul Framework concepts | AISoulFrameworkConcepts | H | Concept text and PDF |
| 40 | Recognition field | Recognitive-field (private) | H | HTML visualisation only |
| 41 | Celestial desktop agent | celestial_agent_desktop_upgrade (private) | IU | `app.py`, `celestial_core.py`; no tests found; not imported |
| 42 | Claim-promotion receipt (demo) | `playground/src/pipeline.js` | IT | `playground/tests/` |
| 43 | Hash-chained trace | `playground/src/pipeline.js` | IT | `playground/tests/` (tamper detection test) |
| 44 | Evidence-record schema | `schemas/evidence-record.schema.json` | D | |

**Fitted or empirical results (R): none.** No result data exists in any of the nine repositories at the reviewed commits.
