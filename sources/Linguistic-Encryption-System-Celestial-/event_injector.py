
from __future__ import annotations
import argparse, json
from orchestrator import GLOBAL_ORCHESTRATOR

def main() -> None:
    parser = argparse.ArgumentParser(description="Inject simulated PhaseForm events into the local orchestrator.")
    parser.add_argument("--event", required=True, help="Event name, e.g. on_damage_detected")
    parser.add_argument("--context", default="{}", help="JSON object context")
    args = parser.parse_args()
    try:
        context = json.loads(args.context)
        if not isinstance(context, dict):
            raise ValueError("Context must be a JSON object.")
    except Exception as exc:
        raise SystemExit(f"Invalid --context JSON: {exc}")
    GLOBAL_ORCHESTRATOR.handle_event(args.event, context)
    print(f"Injected event: {args.event}")

if __name__ == "__main__":
    main()
