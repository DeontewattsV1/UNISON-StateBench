# Governance Kernel Architecture

## Purpose
The Governance Kernel is the command and policy layer. It holds:
- Mission policy and legal constraints
- Privacy rules and rights-impact classifications
- Approval workflows and waiver logic
- Audit policy and escalation rules

## OperatingMode enum
```
ADVISORY      → system only recommends
ASSISTED      → system prepares actions for approval
BOUNDED       → system performs reversible, pre-authorized tasks in narrow scopes
HIGH_IMPACT   → always requires human approval, enhanced logging, continuous monitoring
```

## Escalation logic
`impact_severity` (0.0–1.0) drives escalation. Any subsystem affecting:
- Critical services, legal status, benefits, liberty, safety, or protected groups
is automatically classified HIGH_IMPACT.

## Adding a new policy rule
1. Add to `GovernanceKernel._POLICY_RULES` dict
2. Set `rights_impact` flag if applicable
3. Write test in `tests/test_governance.py`
4. Update the audit log schema if new fields are needed
