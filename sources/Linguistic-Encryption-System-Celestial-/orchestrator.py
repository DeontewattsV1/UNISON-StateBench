
from __future__ import annotations
import json, time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from policy_schema import validate_phaseform_policy

@dataclass
class RuntimePolicy:
    schema_version: str
    creator: str
    identity: Dict[str, Any]
    capabilities: Dict[str, bool]
    policy_logic: Dict[str, str]
    activated_at: float

class RuntimeState:
    def __init__(self, state_dir: str = "runtime_state") -> None:
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.rotations_dir = self.state_dir / "rotations"
        self.rotations_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.state_dir / "audit.log"
        self.active_policy_path = self.state_dir / "active_policy.json"
        self.active_policy = None
        if self.active_policy_path.exists():
            self.active_policy = RuntimePolicy(**json.loads(self.active_policy_path.read_text(encoding="utf-8")))

    def log(self, message: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

    def _atomic_write_json(self, path: Path, data: Dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)

    def save_policy(self, policy: RuntimePolicy) -> None:
        self.active_policy = policy
        self._atomic_write_json(self.active_policy_path, asdict(policy))
        self.log(f"policy_activated creator={policy.creator} project={policy.identity.get('project')}")

    def snapshot_active_policy(self, label: str | None = None):
        if not self.active_policy_path.exists():
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        target = self.rotations_dir / f"policy_{ts}{suffix}.json"
        target.write_text(self.active_policy_path.read_text(encoding="utf-8"), encoding="utf-8")
        self.log(f"policy_snapshot_created file={target.name}")
        return target

    def clear_policy(self) -> None:
        self.active_policy = None
        if self.active_policy_path.exists():
            self.active_policy_path.unlink()
        self.log("policy_cleared")

class ActionRegistry:
    def __init__(self, runtime: RuntimeState) -> None:
        self.runtime = runtime
        self.handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def register(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> None:
        self.handlers[name] = fn

    def execute(self, name: str, context: Dict[str, Any]) -> None:
        fn = self.handlers.get(name)
        if not fn:
            self.runtime.log(f"action_missing name={name}")
            return
        self.runtime.log(f"action_execute name={name}")
        fn(context)

class PhaseFormOrchestrator:
    def __init__(self, state_dir: str = "runtime_state") -> None:
        self.runtime = RuntimeState(state_dir=state_dir)
        self.actions = ActionRegistry(self.runtime)
        self.actions.register("INITIATE_L1_HEAL", self._initiate_l1_heal)
        self.actions.register("PURGE_MEMORY_AND_HALT", self._purge_memory_and_halt)
        self.actions.register("LOCK_AND_ALERT", self._lock_and_alert)
        self.actions.register("NO_OP", self._no_op)

    def activate_policy(self, decrypted_spec: Dict[str, Any], snapshot_previous: bool = True) -> RuntimePolicy:
        validated = validate_phaseform_policy(decrypted_spec)
        if snapshot_previous and self.runtime.active_policy_path.exists():
            self.runtime.snapshot_active_policy("pre_rotate")
        policy = RuntimePolicy(
            schema_version=validated["schema_version"],
            creator=validated["creator"],
            identity=validated["identity"],
            capabilities=validated["capabilities"],
            policy_logic=validated["policy_logic"],
            activated_at=time.time(),
        )
        self.runtime.save_policy(policy)
        return policy

    def handle_event(self, event_name: str, context: Optional[Dict[str, Any]] = None) -> None:
        if not self.runtime.active_policy:
            self.runtime.log(f"event_ignored no_active_policy event={event_name}")
            return
        context = context or {}
        action_name = self.runtime.active_policy.policy_logic.get(event_name, "NO_OP")
        self.runtime.log(f"event_received event={event_name} mapped_action={action_name}")
        self.actions.execute(action_name, context)

    def _initiate_l1_heal(self, context: Dict[str, Any]) -> None:
        self.runtime.log(f"L1_heal_sequence_started context={json.dumps(context, sort_keys=True)}")
        self.runtime.log("L1_heal_sequence_completed")

    def _purge_memory_and_halt(self, context: Dict[str, Any]) -> None:
        self.runtime.log("purging_runtime_memory")
        self.runtime.clear_policy()
        self.runtime.log("runtime_halted")

    def _lock_and_alert(self, context: Dict[str, Any]) -> None:
        self.runtime.log(f"lock_and_alert triggered context={json.dumps(context, sort_keys=True)}")

    def _no_op(self, context: Dict[str, Any]) -> None:
        self.runtime.log("no_op")

GLOBAL_ORCHESTRATOR = PhaseFormOrchestrator()

def handle_decrypted_policy(spec: Dict[str, Any]) -> None:
    policy = GLOBAL_ORCHESTRATOR.activate_policy(spec)
    GLOBAL_ORCHESTRATOR.runtime.log(
        f"policy_loaded role={policy.identity.get('role')} clearance={policy.identity.get('clearance')}"
    )
