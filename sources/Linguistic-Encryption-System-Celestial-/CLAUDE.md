# CLAUDE.md

## Why

This repository is the operational substrate for evidence-bounded sovereign AI under the Architect's Manifesto. It exists so that agents reasoning on behalf of humans can be held to a discipline of provenance, temporal separation, and contradiction-checking — and so that every policy change lands through a signed, auditable, rollbackable pack rather than through free-form prompt edits. It is defensive-only by construction. No offensive capability is to be added, inferred, or implied.

## What

A policy-driven runtime with four load-bearing surfaces. The **prompt layer** (`prompts/`) encodes the Aletheia Lattice operational specification — archive/live/forecast channel separation, mandatory provenance, the five-check reasoning pipeline, and the five-state VOID→CONDEMNED immune layer. The **policy template layer** (`policy_templates/`) binds those prompt semantics to deployment-specific constraints via JSON schemas that declare capabilities, risk profiles, and approval gates. The **crypto layer** (`celestial_agent/agent_spec_crypto.py`) provides the Ed25519 signing and canonical-JSON primitives that every other component depends on. The **runtime layer** (top-level Python modules) packages, signs, verifies, rotates, audits, and hands off policy packs.

## How

Agents working in this repo must hold four invariants and escalate rather than bypass any of them.

First, **defensive-only is non-negotiable.** The flags `capabilities.can_generate_code` and `governance.defensive_only` in every policy template are load-bearing. Any change that would flip them, or any new module whose purpose is to attack rather than defend a system, is out of scope for this repository and should be refused.

Second, **secrets never land in git.** The `keys/`, `vault/`, `decrypted/`, `quarantine/`, `runtime_state/`, `manifests/`, `release_manifests/`, and `handoff_bundles/` directories are runtime-mutable state. They contain `.gitkeep` and nothing else in version control. A private key, encrypted pack, or signature file reaching `git add` is a policy violation, not a mistake to fix later. The `.gitignore` is the backstop; the rule is cultural first.

Third, **every change ships through a smoke test.** Files matching `_smoke_*.py` at the repo root are the contract tests for each runtime module. Adding a new module means adding its smoke test; changing an existing module means its smoke test still passes. The canonical end-to-end path is `python _smoke_operational_prompt_v1.py` — it packages, signs, manifests, bundles, and verifies in one run.

Fourth, **agentic behavior is advisory, not commanding.** The Aletheia Lattice prompt binds the runtime to propose rather than act. Any tool call or module added here must preserve that stance: it may recommend an action, it may prepare the artifacts, it may emit a signed proposal, but human approval gates the commit of any consequential change per `governance.human_approval_required_for`.

## Progressive Disclosure

Task-specific guidance lives in `.claude/skills/` (not yet populated — add as workflows stabilize). Architectural deep-dives, threat modeling, and deployment topology notes live in `docs/` — start with `docs/aletheia_lattice_dia_deployment_architecture_r2.md` for the deployment architecture and `docs/deception_simulation_guardrails.md` for the supervised-review boundary around any deception-adjacent work. The authoritative prompt specification is `prompts/aletheia_lattice_operational_system_prompt_v1.md`; read it before editing any policy template.

When extending the runtime, prefer adding a new policy template over modifying an existing one, prefer adding a new smoke test over broadening an existing one, and prefer surfacing uncertainty over eliminating it. The system is designed to let doubt propagate legibly; that is a feature, not a bug to smooth over.

Brand assets for Phaseform Security Solutions live in `branding/phaseform/` with usage notes in `branding/BRANDING.md`. The gold-and-dragon treatment is for consumer-facing material; the tech-blue treatment is for enterprise-facing material. Both point at the same underlying product.
