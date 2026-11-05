# UNISON — unified evidence, non-collapse and traceability

UNISON is the research identity; **UNISON-StateBench** is its benchmark and the home repository for the consolidated work. This repository now gathers eight related repositories under `sources/` (seven with full git history, one as a clean file copy), and puts one documentation layer and one demonstrator over them:

| Layer | Where |
|---|---|
| Evidence framework (admissibility, promotion receipts, non-collapse) | [docs/ADMISSIBILITY.md](docs/ADMISSIBILITY.md) |
| Claims register: what each imported method actually is | [docs/CLAIMS_REGISTER.md](docs/CLAIMS_REGISTER.md) |
| Testable experiments derived from each repo | [docs/FUTURE_WORK.md](docs/FUTURE_WORK.md) |
| Evidence-record JSON Schema | [schemas/evidence-record.schema.json](schemas/evidence-record.schema.json) |
| Traceability playground (static, in-browser) | [playground/](playground/README.md) |
| Provenance, commit SHAs, licenses, skipped material | [PROVENANCE.md](PROVENANCE.md) |
| Original StateBench README (benchmark usage, Guardian) | [docs/STATEBENCH.md](docs/STATEBENCH.md) |

## One system, one rule

Every repository contributes to a single pipeline that moves a claim from *unknown* towards *supported* only through explicit, hashed, receipted steps. The shared rule, from the UNISON non-collapse drafts: **no step may silently promote a state** — an observation is not evidence, evidence is not authorization, a local pass is not independent reproduction, and unknown never becomes known without a recorded transition.

## Role of each repository

| Repository | Visibility | Role in the unified system | Location |
|---|---|---|---|
| UNISON-StateBench | public | Core: typed invariants, deterministic oracle, state-collapse and non-collapse detection, benchmark corpus | repository root |
| AGI-CP | public | Capability protocol: fail-closed gate, evidence windows, revocation, TRACT receipts | `sources/AGI-CP/` |
| traceability-matrix | public | Requirements-traceability documents and an API/mockup scaffold; source of the requirement-to-evidence linking concept | `sources/traceability-matrix/` |
| Linguistic-Encryption-System-Celestial- | public | Policy packs, manifest verification, tamper testing, glyph encoding with one-time-pad transform; public copy of the PhaseForm runtime | `sources/Linguistic-Encryption-System-Celestial-/` |
| SOVEREIGN-LATTICE-GOVCORE | public | Governance kernel: operating modes, policy rules, approval and escalation | `sources/SOVEREIGN-LATTICE-GOVCORE/` |
| AISoulFrameworkConcepts | public | Concept document (framing only, no code) | `sources/AISoulFrameworkConcepts/` |
| phaseform_runtime_package_v6 | private (imported with owner approval) | Policy validation and event-to-action runtime | `sources/phaseform_runtime_package_v6/` (file copy, see PROVENANCE.md) |
| Recognitive-field | private (imported with owner approval) | Recognition-field visual dynamical model (attractor/turbulence probes) | `sources/Recognitive-field/` |
| celestial_agent_desktop_upgrade | private (imported with owner approval) | Desktop agent: signed/encrypted agent spec packs, glyph codec, sandboxed workspace command runtime | `sources/celestial_agent_desktop_upgrade/` |

## Running things

```bash
# StateBench (unchanged)
python -m pip install -e '.[dev]' && python -m pytest -q

# Playground
cd playground && npm test && npm run build && npm run smoke   # smoke needs Chrome
python3 -m http.server -d dist 8000                           # then open http://localhost:8000
```

The playground deploys to GitHub Pages via `.github/workflows/pages.yml` once merged to `main` and once Pages is enabled with the "GitHub Actions" source in repository settings.

## Hackathon submission

Meta Global AI Developer Hackathon package: [docs/hackathon/](docs/hackathon/).

## License

Repository root: MIT (see [LICENSE](LICENSE)). `guardian/` new source: Apache-2.0. Each directory under `sources/` keeps its own LICENSE; see [PROVENANCE.md](PROVENANCE.md) for the license review.
