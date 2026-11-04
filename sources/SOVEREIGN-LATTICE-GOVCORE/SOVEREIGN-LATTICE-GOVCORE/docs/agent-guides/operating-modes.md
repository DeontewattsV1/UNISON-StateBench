# Operating Modes Reference

| Mode | Can Recommend | Can Prepare Actions | Can Execute | Human Approval |
|------|--------------|---------------------|-------------|----------------|
| ADVISORY | ✅ | ❌ | ❌ | Not required |
| ASSISTED | ✅ | ✅ | ❌ | Required before execution |
| BOUNDED | ✅ | ✅ | ✅ (reversible, pre-authorized) | Required per action |
| HIGH_IMPACT | ✅ | ✅ | ❌ | Always mandatory |

## High-impact triggers
- `impact_severity >= HIGH_IMPACT_THRESHOLD` (default 0.75)
- Rights-impact classification on the governance kernel policy
- Any subsystem touching: critical infrastructure, legal status, liberty, protected groups
- Network isolation, model quarantine, incident escalation

## Irreversibility rule
Agents MAY NOT take irreversible action without explicit human authorization.
Even in BOUNDED mode, actions are limited to reversible, pre-authorized tasks.
