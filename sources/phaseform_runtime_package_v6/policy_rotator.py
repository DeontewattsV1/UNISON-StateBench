
from __future__ import annotations
import argparse, json
from pathlib import Path
from orchestrator import GLOBAL_ORCHESTRATOR
from policy_schema import validate_phaseform_policy

BASE_DIR = Path(__file__).resolve().parent
DECRYPTED_DIR = BASE_DIR / "decrypted"
ROTATIONS_DIR = BASE_DIR / "runtime_state" / "rotations"

def list_candidates() -> list[Path]:
    return sorted(DECRYPTED_DIR.glob("*.json"))

def list_backups() -> list[Path]:
    return sorted(ROTATIONS_DIR.glob("*.json"))

def activate_from_file(path: Path) -> None:
    spec = json.loads(path.read_text(encoding="utf-8"))
    validate_phaseform_policy(spec)
    GLOBAL_ORCHESTRATOR.activate_policy(spec, snapshot_previous=True)
    GLOBAL_ORCHESTRATOR.runtime.log(f"policy_rotated source={path.name}")

def rollback_from_file(path: Path) -> None:
    spec = json.loads(path.read_text(encoding="utf-8"))
    validate_phaseform_policy(spec)
    GLOBAL_ORCHESTRATOR.activate_policy(spec, snapshot_previous=False)
    GLOBAL_ORCHESTRATOR.runtime.log(f"policy_rollback source={path.name}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Atomically rotate or roll back PhaseForm policies.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--activate", help="Activate decrypted policy filename from decrypted/")
    group.add_argument("--rollback-last", action="store_true", help="Roll back to most recent rotation snapshot")
    group.add_argument("--rollback-file", help="Roll back to a specific snapshot filename from runtime_state/rotations/")
    group.add_argument("--list", action="store_true", help="List decrypted policies and rollback snapshots")
    args = parser.parse_args()

    if args.list:
        print("Decrypted policies:")
        for p in list_candidates():
            print(f"  {p.name}")
        print("Rotation snapshots:")
        for p in list_backups():
            print(f"  {p.name}")
        return

    if args.activate:
        target = DECRYPTED_DIR / args.activate
        if not target.exists():
            raise SystemExit(f"Policy not found: {target}")
        activate_from_file(target)
        print(f"Activated policy: {target.name}")
        return

    if args.rollback_last:
        backups = list_backups()
        if not backups:
            raise SystemExit("No rotation snapshots available.")
        target = backups[-1]
        rollback_from_file(target)
        print(f"Rolled back to: {target.name}")
        return

    if args.rollback_file:
        target = ROTATIONS_DIR / args.rollback_file
        if not target.exists():
            raise SystemExit(f"Snapshot not found: {target}")
        rollback_from_file(target)
        print(f"Rolled back to: {target.name}")

if __name__ == "__main__":
    main()
