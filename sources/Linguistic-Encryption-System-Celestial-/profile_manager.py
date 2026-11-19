from __future__ import annotations

import argparse
import json

from risk_profile import delete_profile, get_threshold, list_profiles, load_profiles, set_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Edit, extend, inspect, and persist custom rotation risk profiles."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all available risk profiles")
    group.add_argument("--get", help="Show one profile threshold")
    group.add_argument("--set", nargs=2, metavar=("NAME", "THRESHOLD"), help="Create or update a profile")
    group.add_argument("--delete", help="Delete a custom profile")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if args.list:
        payload = {"profiles": load_profiles()}
    elif args.get:
        payload = {"name": args.get, "threshold": get_threshold(args.get)}
    elif args.set:
        name, threshold_raw = args.set
        payload = {
            "updated_profile": name,
            "profiles": set_profile(name, int(threshold_raw)),
        }
    elif args.delete:
        payload = {
            "deleted_profile": args.delete,
            "profiles": delete_profile(args.delete),
        }
    else:
        raise SystemExit("No action provided")

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    if "profiles" in payload:
        print("== RISK PROFILES ==")
        for name in sorted(payload["profiles"].keys()):
            print(f"{name}: {payload['profiles'][name]}")
    else:
        print(f"{payload['name']}: {payload['threshold']}")


if __name__ == "__main__":
    main()
