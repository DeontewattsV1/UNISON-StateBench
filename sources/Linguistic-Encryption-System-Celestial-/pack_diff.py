from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent
MANIFESTS_DIR = BASE_DIR / "manifests"
DECRYPTED_DIR = BASE_DIR / "decrypted"


def resolve_input(value: str, kind: str) -> Path:
    candidate = Path(value)
    if candidate.exists():
        return candidate.resolve()

    if kind == "manifest":
        p = MANIFESTS_DIR / (value if value.endswith(".json") else f"{value}.json")
        if p.exists():
            return p.resolve()
    elif kind == "policy":
        p = DECRYPTED_DIR / (value if value.endswith(".json") else f"{value}.json")
        if p.exists():
            return p.resolve()

    # auto mode fallback
    if kind == "auto":
        manifest_guess = MANIFESTS_DIR / (value if value.endswith(".json") else f"{value}.json")
        policy_guess = DECRYPTED_DIR / (value if value.endswith(".json") else f"{value}.json")
        if manifest_guess.exists():
            return manifest_guess.resolve()
        if policy_guess.exists():
            return policy_guess.resolve()

    raise FileNotFoundError(f"Could not resolve input: {value}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def summarize(left_path: Path, right_path: Path, diffs: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"added": 0, "removed": 0, "modified": 0, "type_changed": 0}
    for d in diffs:
        change = d["change"]
        counts[change] = counts.get(change, 0) + 1

    return {
        "left_file": str(left_path),
        "right_file": str(right_path),
        "difference_count": len(diffs),
        "counts": counts,
        "differences": diffs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two signed manifests or two decrypted policies before rotation.")
    parser.add_argument("--left", required=True, help="Left file path or base name")
    parser.add_argument("--right", required=True, help="Right file path or base name")
    parser.add_argument("--kind", choices=["auto", "manifest", "policy"], default="auto", help="How to resolve bare names")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    left_path = resolve_input(args.left, args.kind)
    right_path = resolve_input(args.right, args.kind)

    left = load_json(left_path)
    right = load_json(right_path)

    diffs = diff_values(left, right)
    payload = summarize(left_path, right_path, diffs)

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print("== PACK / POLICY DIFF ==")
    print(f"left_file: {payload['left_file']}")
    print(f"right_file: {payload['right_file']}")
    print(f"difference_count: {payload['difference_count']}")
    print("counts:")
    for k, v in payload["counts"].items():
        print(f"  {k}: {v}")

    if not diffs:
        print("\nNo differences.")
        return

    print("\nDifferences:")
    for d in diffs:
        print(f"- {d['path']} [{d['change']}]")
        print(f"    left:  {json.dumps(d['left'], ensure_ascii=False)}")
        print(f"    right: {json.dumps(d['right'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
