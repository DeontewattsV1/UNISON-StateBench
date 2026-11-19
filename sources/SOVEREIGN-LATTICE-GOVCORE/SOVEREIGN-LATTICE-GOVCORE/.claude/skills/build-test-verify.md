---
name: build-test-verify
description: Build, test, and verify workflow for Sovereign Lattice GovCore.
---

## Setup
```bash
cp .env.example .env
pip install -e ".[dev]"
```

## Test
```bash
pytest tests/ -v --tb=short
pytest tests/test_governance.py -v   # governance kernel only
pytest tests/test_agents.py -v       # agent plane only
```

## Verify operating modes
```bash
python -c "
from govcore.governance.kernel import GovernanceKernel, OperatingMode
k = GovernanceKernel()
print(k.evaluate_operating_mode({'impact_severity': 0.9}))  # should be HIGH_IMPACT
"
```

## Key invariants
- High-impact actions ALWAYS require human approval — no exceptions
- Scenario outputs CANNOT be promoted to the evidence layer
- Agents operate in advisory mode only unless explicitly elevated
- Every recommendation includes: action, evidence, expected_effect, risks, alternatives
