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

The playground publishes through `.github/workflows/pages.yml` when GitHub Pages is enabled with the GitHub Actions source. Until that setting is on, the workflow reports the skip and exits successfully. Playground tests still run in the Playground and evidence schema workflow.

## Hackathon submission

Meta Global AI Developer Hackathon package: [docs/hackathon/](docs/hackathon/).

#Model experiments 

# UNISON\-Bench Cloud v0\.1 — PRIVATE PILOT / PUBLIC\-SYNTHETIC INPUTS ONLY

**Status:** LOCAL SYNTHETIC CONFORMANCE PASSED · MODAL NOT RUN · RELEASE HOLD\.

**PI:** Deonté O’dell Watts · ORCID 0009\-0005\-8586\-3650 · GoodShyt Group Inc\. · deonte@goodshyt\.fun
**Classification:** CONFIDENTIAL — PROPRIETARY implementation notes; supplied synthetic fixtures carry no confidential records\.
**AI disclosure:** Original code and technical drafting generated with OpenAI assistance for PI review\. No authorship, patentability, novelty, security certification or independent empirical validation is asserted by this package\.

## Research integration boundary

UNISON is the framework identity\. The published public benchmark is [UNISON\-StateBench](https://github.com/DeontewattsV1/UNISON-StateBench)\. It has a frozen canonical oracle, S01/S06 original fixtures and U01–U10 trial suite; **this separate project intentionally does not import or alter those frozen files**\. Its synthetic scenarios `PILOT-S01` and `PILOT-S06` are analogues only, not duplicates\. Existing U01–U10 empirical 162\-call matrix remains NOT RUN here\. This package computes only synthetic per\-trial diagnostics, not published IPR/RCR/CRR/FHR/CAL/PLR/AIR or the frozen SCR\.

The invariant structure is `I_k=(value, epistemic_status, provenance, authority)`; `False` is distinct from `Unknown`, and a sequence of boundaries is never automatically promoted into an authorized transition\.

## Artifact map

- `unison_cloud/` — isolated typed examples, deterministic evaluator, receipt hashing and CLI\.
- `cloud_app.py` — Modal Functions only; no web endpoint and no raw\-data input route\.
- `tests/` — failure and indeterminate state regressions\.
- `dashboard/` — localhost read\-only status with two optional native WebMCP tools\.
- `scripts/check_privacy.py` — conservative source\-level static gate\.
- `docs/` — deployment, release gates, threat model\.
- `main.tex`, `references.bib`, `figures/`, `data.json`, `manifest.txt` — provenance\-controlled research packaging\.
- `.github/workflows/verify.yml` — intended CI; no remote CI run yet\.

## Local quick start

```bash
python -m unittest discover -s tests -v
python scripts/check_privacy.py
python -m unison_cloud.cli local
python -m http.server 8765
# then visit http://localhost:8765/dashboard/
```

To compare frozen canonical component bytes with an existing local upstream checkout &#40;without copying or uploading them&#41;:

```bash
python scripts/verify_local_upstream.py --repo /path/to/UNISON-StateBench
```

After a local or approved remote synthetic run, update the localhost dashboard only from a verified, allowlisted report using `PYTHONPATH=. python scripts/update_dashboard.py reports/<report>.json`\. Neither command uploads any upstream research files\.

Review [Deployment instructions](docs/DEPLOYMENT.md) before any Modal remote action\.

## Claims and falsifiers

1. &#91;DERIVED, T2&#93; The synthetic implementation preserves typed epistemic distinctions\. Dies if a trial promotes `unknown` to `known` without being flagged\.
2. &#91;DERIVED, T2&#93; Its synthetic transition detector catches unqualified authorization/readiness promotions\. Dies if an injected unsupported transition produces PASS\.
3. &#91;DERIVED, T2&#93; Evaluation success never authorizes production action\. Dies if PASS enables an execution capability\.
4. &#91;CONJECTURE, T3&#93; The same architecture can isolate a future approved version of the real UNISON experiment\. This remains untested; falsify with an actual approved private staging run, reproducible source/corpus digest comparison and adversarial assessment\.

These are implementation claims; **none** is a new scientific discovery\. The provenance and canonical scientific authorship remain with original sources and the PI as applicable\. No source\-derived claims are elevated into independently verified facts\.

**© 2026 Deonté O’dell Watts — ORCID 0009\-0005\-8586\-3650 \| GoodShyt Group Inc\. \| deonte@goodshyt\.fun \| First articulated for this cloud pilot 2026\-11\-06\.**
## License

Repository root: MIT (see [LICENSE](LICENSE)). `guardian/` new source: Apache-2.0. Each directory under `sources/` keeps its own LICENSE; see [PROVENANCE.md](PROVENANCE.md) for the license review.
