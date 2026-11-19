# Traceability playground

A static, in-browser demonstrator (plain HTML + ES modules, no build tool, no external services). A sample claim enters as `unknown`, evidence is attached and hashed, then each stage runs; every stage output is hashed (SHA-256 over canonical JSON) and chained to the previous step. The result is a demonstration claim-promotion receipt and a trace graph. The "Tamper" button edits one stage output and shows the chain verification fail.

| Stage | Label | Source |
|---|---|---|
| claim-intake | Implemented | UNISON typed state: claims enter as `unknown` |
| evidence-attach | Implemented | SHA-256 of each evidence item |
| evidence-window | Implemented | Port of AGI-CP `capability-gateway/src/auth/evidence.ts` |
| traceability-link | **Concept (illustrative)** | New code; traceability-matrix has RTM documents but no linking code |
| governance-gate | Implemented | Port of GovCore `GovernanceKernel.evaluate_operating_mode` + RULE-003 scenario separation |
| noncollapse-check | Implemented | Simplified port of `benchmark/state_collapse.py` |
| phaseform-step | Implemented | Port of `sources/phaseform_runtime_package_v6/policy_schema.py` + `orchestrator.py` `handle_event` (mapping only; no file I/O) |
| linguistic-transform | Implemented | Port of `celestial_language.py` glyph map + one-time pad, with round-trip check (decoder is new) |
| recognitive-field | Implemented (advisory) | Port of `flow()` and probe fate classification from `sources/Recognitive-field/recognitive-field-v3.html`; `Math.random` replaced by a seeded PRNG. Probe start comes from the claim hash. It is a visual dynamical model, not evidence, so it never gates promotion. |
| celestial-agent | Implemented | Port of `sources/celestial_agent_desktop_upgrade/celestial_core.py` `CelestialCodec`, `SafeWorkspace.resolve_safe` and the command parser (in-memory workspace; `MAKE FUNCTION` not ported). Checked byte-for-byte against the Python codec. |
| agi-cp-capability, ai-soul | **Concept (illustrative)** | Placeholders; no code ported |

"Implemented" means the logic is ported from source code and unit-tested here; it does not mean the source repository's own implementation was re-verified.

```bash
npm test          # unit tests (node:test, no dependencies)
npm run build     # copies to dist/
npm run smoke     # serves dist/ and loads it in headless Chrome (CHROME_BIN to override)
```

## Lattice

`lattice/` is the source of the in-browser lattice demonstrator (claim token, twelve stations, pressures, tamper). Stage functions match `src/stages.js`. Unit tests:

```bash
node --experimental-strip-types --test lattice/trace/stages.test.ts
```

The visual shell is the UNISON Trace app. This directory is the versioned source, not a second static site.
