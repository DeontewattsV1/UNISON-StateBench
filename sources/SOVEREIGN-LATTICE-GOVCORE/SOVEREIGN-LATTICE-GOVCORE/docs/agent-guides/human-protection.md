# Human Protection Plane

This layer is MANDATORY. It treats humans as protected stakeholders, not optimization targets.

## Components
- **Explanation views** — every recommendation includes human-readable reasoning
- **Confidence labels** — every output carries HIGH/MEDIUM/LOW confidence
- **Consent/notice controls** — required for data affecting personal records
- **Appeal and override mechanisms** — operators can override any recommendation
- **Harm review** — rights and privacy impact check before high-impact recommendations
- **Emergency shutdown** — any operator can invoke SHUTDOWN state

## Override Flow
```python
protection = HumanProtectionPlane()
result = protection.process_recommendation(rec, context)
if result.requires_human_approval:
    # Surface to operator — await explicit approval
    pass
```

## Emergency Shutdown
```python
protection.emergency_shutdown(reason="Operator-invoked shutdown", operator_id="OP-001")
# All downstream processing halts — logs preserved
```

## Invariant
The system MUST NEVER optimize purely for throughput when safety, rights, privacy,
or due process are implicated. Any subsystem affecting critical services, legal status,
benefits, liberty, or safety MUST be classed HIGH_IMPACT.
