from __future__ import annotations
import argparse
import contextlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List

from manifest_verifier import verify_split_pack
from pack_diff import diff_values
from policy_rotator import activate_from_file
from risk_profile import get_threshold, list_profiles

BASE_DIR = Path(__file__).resolve().parent
DECRYPTED_DIR = BASE_DIR / "decrypted"
ACTIVE_POLICY = BASE_DIR / "runtime_state" / "active_policy.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_policy(name: str) -> Path:
    candidate = Path(name)
    if candidate.exists():
        return candidate.resolve()
    p = DECRYPTED_DIR / (name if name.endswith(".json") else f"{name}.json")
    if p.exists():
        return p.resolve()
    raise FileNotFoundError(f"Could not resolve decrypted policy: {name}")


def diff_risk_score(differences: List[Dict[str, Any]]) -> int:
    score = 0
    for d in differences:
        path = d["path"]
        if path.startswith("identity.clearance"):
            score += 5
        elif path.startswith("capabilities."):
            score += 4
        elif path.startswith("policy_logic."):
            score += 3
        elif path.startswith("identity.role") or path.startswith("identity.project"):
            score += 2
        else:
            score += 1
    return score


def build_payload(pack_name: str, policy_path: Path, reference_path: Path | None) -> Dict[str, Any]:
    manifest_result = verify_split_pack(pack_name)
    candidate_policy = load_json(policy_path)

    differences: List[Dict[str, Any]] = []
    reference_file = None
    if reference_path is not None and reference_path.exists():
        reference_policy = load_json(reference_path)
        differences = diff_values(reference_policy, candidate_policy)
        reference_file = str(reference_path)

    risk_score = diff_risk_score(differences)
    return {
        "pack_name": pack_name,
        "candidate_policy": str(policy_path),
        "reference_policy": reference_file,
        "manifest_verification": manifest_result,
        "difference_count": len(differences),
        "risk_score": risk_score,
        "differences": differences,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Guard policy rotation by requiring manifest verification and either a reusable risk profile or a numeric diff-risk threshold."
    )
    parser.add_argument("--pack-name", required=True, help="Split pack base name, e.g. policy_b")
    parser.add_argument(
        "--policy",
        default=None,
        help="Candidate decrypted policy path or base name. Defaults to matching decrypted/<pack-name>.json",
    )
    parser.add_argument(
        "--reference-policy",
        default=None,
        help="Reference decrypted policy path or base name. Defaults to runtime_state/active_policy.json when present.",
    )
    threshold_group = parser.add_mutually_exclusive_group()
    threshold_group.add_argument(
        "--max-risk",
        type=int,
        default=None,
        help="Optional maximum allowed diff-risk score before activation is blocked.",
    )
    threshold_group.add_argument(
        "--risk-profile",
        choices=list_profiles(),
        default=None,
        help="Reusable approval tier: low, medium, or strict.",
    )
    parser.add_argument("--activate", action="store_true", help="Activate the candidate policy only if all checks pass.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    policy_path = resolve_policy(args.policy or args.pack_name)

    if args.reference_policy:
        reference_path = resolve_policy(args.reference_policy)
    else:
        reference_path = ACTIVE_POLICY if ACTIVE_POLICY.exists() else None

    payload = build_payload(args.pack_name, policy_path, reference_path)
    manifest_ok = bool(payload["manifest_verification"]["signature_valid"]) and (
        payload["manifest_verification"]["ciphertext_hash_valid"] in (True, None)
    )

    effective_max_risk = args.max_risk
    if args.risk_profile:
        effective_max_risk = get_threshold(args.risk_profile)

    risk_ok = effective_max_risk is None or payload["risk_score"] <= effective_max_risk

    payload["manifest_ok"] = manifest_ok
    payload["risk_ok"] = risk_ok
    payload["max_risk"] = effective_max_risk
    payload["risk_profile"] = args.risk_profile
    payload["activation_allowed"] = manifest_ok and risk_ok

    if args.activate and payload["activation_allowed"]:
        if args.json:
            sink = io.StringIO()
            with contextlib.redirect_stdout(sink):
                activate_from_file(policy_path)
            payload["activation_log"] = sink.getvalue().splitlines()
        else:
            activate_from_file(policy_path)
        payload["activated"] = True
    else:
        payload["activated"] = False

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print("== ROTATION GUARD ==")
    print(f"pack_name: {payload['pack_name']}")
    print(f"candidate_policy: {payload['candidate_policy']}")
    print(f"reference_policy: {payload['reference_policy']}")
    print(f"manifest_ok: {payload['manifest_ok']}")
    print(f"risk_score: {payload['risk_score']}")
    print(f"risk_profile: {payload['risk_profile']}")
    print(f"max_risk: {payload['max_risk']}")
    print(f"risk_ok: {payload['risk_ok']}")
    print(f"activation_allowed: {payload['activation_allowed']}")
    print(f"activated: {payload['activated']}")
    print(f"difference_count: {payload['difference_count']}")

    mv = payload["manifest_verification"]
    print("\nManifest verification:")
    print(f"  creator: {mv['creator']}")
    print(f"  schema_version: {mv['schema_version']}")
    print(f"  signature_valid: {mv['signature_valid']}")
    print(f"  ciphertext_hash_valid: {mv['ciphertext_hash_valid']}")

    if payload["differences"]:
        print("\nDifferences:")
        for d in payload["differences"]:
            print(f"- {d['path']} [{d['change']}]")
    else:
        print("\nDifferences: none")


if __name__ == "__main__":
    main()
