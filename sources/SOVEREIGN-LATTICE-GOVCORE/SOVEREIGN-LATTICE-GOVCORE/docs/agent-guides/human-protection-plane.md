# Human Protection Plane

## Mandatory controls
The Human Protection Plane is not optional. It provides:
- Explanation views and confidence labels on every major output
- Consent or notice controls where required
- Appeal and override mechanisms
- Harm review for high-impact recommendations
- Emergency shutdown capability

## Implementation contract
Every agent recommendation MUST include:
```python
@dataclass
class AgentRecommendation:
    action:          str     # What to do
    evidence:        str     # Why (evidence backing)
    expected_effect: str     # What will happen if acted on
    risks:           str     # Risks of the action
    alternative:     str     # Reasonable alternative
    confidence:      float   # 0.0–1.0
    requires_human_approval: bool  # Always True for HIGH_IMPACT
```

## Shutdown
`HumanProtectionPlane.emergency_shutdown()` halts all agent activity immediately.
Logs the shutdown event to the audit ledger before halting.
