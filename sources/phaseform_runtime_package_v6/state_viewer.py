
from __future__ import annotations
import argparse, json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "runtime_state"
ACTIVE = STATE_DIR / "active_policy.json"
AUDIT = STATE_DIR / "audit.log"

def main() -> None:
    parser = argparse.ArgumentParser(description="View active policy and recent audit/events.")
    parser.add_argument("--tail", type=int, default=20, help="Number of audit lines to show")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    args = parser.parse_args()
    active = json.loads(ACTIVE.read_text(encoding="utf-8")) if ACTIVE.exists() else None
    audit_lines = AUDIT.read_text(encoding="utf-8").splitlines() if AUDIT.exists() else []
    recent = audit_lines[-args.tail:]
    event_lines = [line for line in recent if any(token in line for token in ["event_received", "action_execute", "policy_activated", "policy_rotated", "policy_rollback", "L1_heal_sequence_started", "lock_and_alert", "runtime_halted"])]
    payload = {"active_policy": active, "recent_audit": recent, "recent_events": event_lines}
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print("== ACTIVE POLICY ==")
    print(json.dumps(active, indent=2) if active else "(none)")
    print("\n== RECENT AUDIT ==")
    print("\n".join(recent) if recent else "(none)")
    print("\n== RECENT EVENTS ==")
    print("\n".join(event_lines) if event_lines else "(none)")

if __name__ == "__main__":
    main()
