
from typing import Any, Dict, List

ALLOWED_CLEARANCE = {"L1", "L2", "L3", "L4_SOVEREIGN"}
ALLOWED_POLICY_ACTIONS = {"INITIATE_L1_HEAL", "PURGE_MEMORY_AND_HALT", "LOCK_AND_ALERT", "NO_OP"}
ALLOWED_CAPABILITIES = {"can_generate_code", "can_access_l3_controller", "can_reconfigure_l2", "can_bypass_leash"}

class PolicyValidationError(ValueError):
    pass

def require_fields(obj: Dict[str, Any], fields: List[str], ctx: str) -> None:
    missing = [f for f in fields if f not in obj]
    if missing:
        raise PolicyValidationError(f"{ctx} missing required fields: {missing}")

def validate_phaseform_policy(spec: Dict[str, Any]) -> Dict[str, Any]:
    require_fields(spec, ["schema_version", "creator", "identity", "capabilities", "policy_logic"], "root")
    identity = spec["identity"]
    capabilities = spec["capabilities"]
    policy_logic = spec["policy_logic"]
    if not isinstance(identity, dict) or not isinstance(capabilities, dict) or not isinstance(policy_logic, dict):
        raise PolicyValidationError("identity, capabilities, and policy_logic must be objects")
    require_fields(identity, ["role", "clearance", "project"], "identity")
    if identity["clearance"] not in ALLOWED_CLEARANCE:
        raise PolicyValidationError(f"Unsupported clearance: {identity['clearance']}")
    unknown_caps = set(capabilities) - ALLOWED_CAPABILITIES
    if unknown_caps:
        raise PolicyValidationError(f"Unknown capabilities: {sorted(unknown_caps)}")
    if capabilities.get("can_bypass_leash") is True:
        raise PolicyValidationError("can_bypass_leash=true is not allowed")
    for trigger, action in policy_logic.items():
        if not isinstance(trigger, str) or not isinstance(action, str):
            raise PolicyValidationError("policy_logic keys and values must be strings")
        if action not in ALLOWED_POLICY_ACTIONS:
            raise PolicyValidationError(f"Unsupported policy action: {action}")
    return spec
