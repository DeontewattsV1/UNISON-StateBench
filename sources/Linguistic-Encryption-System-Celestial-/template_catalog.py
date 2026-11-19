from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "policy_templates"


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def diff_values(left: Any, right: Any, prefix: str = "") -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []

    if type(left) != type(right):
        diffs.append({
            "path": prefix or "$",
            "change": "type_changed",
            "left": left,
            "right": right,
        })
        return diffs

    if isinstance(left, dict):
        left_keys = set(left.keys())
        right_keys = set(right.keys())

        for key in sorted(left_keys - right_keys):
            diffs.append({
                "path": _join(prefix, str(key)),
                "change": "removed",
                "left": left[key],
                "right": None,
            })

        for key in sorted(right_keys - left_keys):
            diffs.append({
                "path": _join(prefix, str(key)),
                "change": "added",
                "left": None,
                "right": right[key],
            })

        for key in sorted(left_keys & right_keys):
            diffs.extend(diff_values(left[key], right[key], _join(prefix, str(key))))
        return diffs

    if isinstance(left, list):
        if left != right:
            max_len = max(len(left), len(right))
            for i in range(max_len):
                p = f"{prefix}[{i}]"
                if i >= len(left):
                    diffs.append({"path": p, "change": "added", "left": None, "right": right[i]})
                elif i >= len(right):
                    diffs.append({"path": p, "change": "removed", "left": left[i], "right": None})
                else:
                    diffs.extend(diff_values(left[i], right[i], p))
        return diffs

    if left != right:
        diffs.append({
            "path": prefix or "$",
            "change": "modified",
            "left": left,
            "right": right,
        })

    return diffs


def load_template(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_template(name: str) -> Path:
    candidate = Path(name)
    if candidate.exists():
        return candidate.resolve()
    p = TEMPLATE_DIR / (name if name.endswith(".json") else f"{name}.json")
    if p.exists():
        return p.resolve()
    raise FileNotFoundError(f"Could not resolve template: {name}")


def list_templates() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for path in sorted(TEMPLATE_DIR.glob("*.json")):
        try:
            data = load_template(path)
        except Exception:
            data = None
        items.append({
            "name": path.name,
            "path": str(path),
            "use_case": data.get("use_case") if isinstance(data, dict) else None,
            "risk_profile": data.get("governance", {}).get("risk_profile") if isinstance(data, dict) else None,
        })
    return items


def clone_template(source: Path, dest_name: str) -> Path:
    dest = TEMPLATE_DIR / (dest_name if dest_name.endswith(".json") else f"{dest_name}.json")
    if dest.exists():
        raise FileExistsError(f"Destination already exists: {dest}")
    shutil.copy2(source, dest)
    return dest


def summarize_diff(left_path: Path, right_path: Path, diffs: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"added": 0, "removed": 0, "modified": 0, "type_changed": 0}
    for d in diffs:
        counts[d["change"]] = counts.get(d["change"], 0) + 1
    return {
        "left_file": str(left_path),
        "right_file": str(right_path),
        "difference_count": len(diffs),
        "counts": counts,
        "differences": diffs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List, inspect, clone, and diff generated policy templates."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List available templates")
    group.add_argument("--inspect", help="Inspect one template by name or path")
    group.add_argument("--clone", nargs=2, metavar=("SOURCE", "DEST"), help="Clone a template")
    group.add_argument("--diff", nargs=2, metavar=("LEFT", "RIGHT"), help="Diff two templates")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if args.list:
        payload = {"templates": list_templates()}
    elif args.inspect:
        path = resolve_template(args.inspect)
        payload = {"template": str(path), "content": load_template(path)}
    elif args.clone:
        source = resolve_template(args.clone[0])
        dest = clone_template(source, args.clone[1])
        payload = {"cloned_from": str(source), "cloned_to": str(dest)}
    elif args.diff:
        left_path = resolve_template(args.diff[0])
        right_path = resolve_template(args.diff[1])
        diffs = diff_values(load_template(left_path), load_template(right_path))
        payload = summarize_diff(left_path, right_path, diffs)
    else:
        raise SystemExit("No action provided")

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    if "templates" in payload:
        print("== POLICY TEMPLATE CATALOG ==")
        if not payload["templates"]:
            print("(none)")
        for item in payload["templates"]:
            print(f"{item['name']} | use_case={item['use_case']} | risk_profile={item['risk_profile']}")
    elif "content" in payload:
        print(json.dumps(payload["content"], indent=2))
    elif "cloned_to" in payload:
        print(f"Cloned {payload['cloned_from']} -> {payload['cloned_to']}")
    else:
        print("== TEMPLATE DIFF ==")
        print(f"left_file: {payload['left_file']}")
        print(f"right_file: {payload['right_file']}")
        print(f"difference_count: {payload['difference_count']}")
        for k, v in payload["counts"].items():
            print(f"{k}: {v}")
        if payload["differences"]:
            print("\nDifferences:")
            for d in payload["differences"]:
                print(f"- {d['path']} [{d['change']}]")
        else:
            print("\nNo differences.")


if __name__ == "__main__":
    main()
