# Why
Sovereign Lattice GovCore is a high-performance AI system for public-sector and critical-infrastructure operators. It enables retrieve, verify, synthesize, simulate, and recommend workflows under uncertainty while preserving human oversight and policy control. Built around bounded ANI components, not AGI, and optimized for provenance, controllability, and trustworthy decision support.

# What
Python/FastAPI orchestration stack aligned to M-25-21, M-25-22, NIST AI RMF, CISA ZTMM, and FIPS 203/204/205.
- `govcore/governance/` - Governance Kernel: mission policy, legal constraints, privacy rules, approval workflows, audit policy
- `govcore/evidence/` - Evidence Lattice: archived, live, and quarantined scenario channels — no silent promotion to fact
- `govcore/routing/` - Model Router: latency budgets, token budgets, cost controls, small-model-first dispatch
- `govcore/reasoning/` - Parallel Reasoning Engine: retrieval-backed synthesis, contradiction detection, policy compliance, risk scoring
- `govcore/agents/` - Agent Plane: Retrieval, Verification, Policy, Risk, Cyber Defense, PQC Migration, Audit agents
- `govcore/security/` - Security and Trust Plane: zero-trust, artifact signing, prompt-injection filtering
- `govcore/human/` - Human Protection Plane: explanation views, confidence labels, appeal/override, emergency shutdown

# How
- Install: `pip install -e ".[dev]"`
- Test: `make test`
- Demo: `python scripts/demo.py`
- API: `uvicorn govcore.api.server:app --port 8080`
- Env: copy `.env.example` → `.env`

# Progressive Disclosure
Load skills only for the specific task at hand.
- Commit conventions: `.claude/skills/git-commit.md`
- Build/test workflow: `.claude/skills/build-test-verify.md`
- Governance Kernel design: `docs/agent-guides/governance-kernel.md`
- Operating modes (Advisory/Assisted/Bounded/High-Impact): `docs/agent-guides/operating-modes.md`
- Human protection controls: `docs/agent-guides/human-protection-plane.md`
