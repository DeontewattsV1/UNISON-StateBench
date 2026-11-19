from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric import ed25519

from celestial_agent.agent_spec_crypto import canonical_json
from orchestrator import RuntimeState


BASE_DIR = Path(__file__).resolve().parent
SHADOW_DIR = BASE_DIR / "shadow_policies"
AUTH_DIR = BASE_DIR / "authorizations"

ALLOWED_TRIGGER_LEVELS = {"GRAVE", "CONDEMNED"}
NULL_RESULT = {
    "status": "terminated_without_content",
    "mode": "null_response",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str, root: Path) -> Path:
    candidate = Path(value)
    if candidate.exists():
        return candidate.resolve()
    p = root / value
    if p.exists():
        return p.resolve()
    if not value.endswith(".json"):
        p2 = root / f"{value}.json"
        if p2.exists():
            return p2.resolve()
    raise FileNotFoundError(f"Could not resolve file: {value}")


def verify_signed_shadow_policy(policy_path: Path) -> Dict[str, Any]:
    sig_path = policy_path.with_suffix(policy_path.suffix + ".sig")
    if not sig_path.exists():
        alt = policy_path.parent / f"{policy_path.stem}.sig"
        if alt.exists():
            sig_path = alt
        else:
            raise FileNotFoundError(f"Missing signature for policy: {policy_path}")

    policy = load_json(policy_path)
    public_key_b64 = policy.get("public_key_b64")
    if not public_key_b64:
        raise ValueError("Shadow policy missing public_key_b64")

    signature = sig_path.read_bytes()
    pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    pub.verify(signature, canonical_json(policy))
    return policy


def verify_authorization_ticket(ticket_path: Path, session_id: str) -> Dict[str, Any]:
    ticket = load_json(ticket_path)
    required = ["approved", "oversight_officer", "authorized_at_utc", "expires_at_utc", "session_id"]
    missing = [field for field in required if field not in ticket]
    if missing:
        raise ValueError(f"Authorization ticket missing fields: {missing}")
    if ticket["approved"] is not True:
        raise ValueError("Authorization ticket is not approved")
    if ticket["session_id"] != session_id:
        raise ValueError("Authorization ticket session_id mismatch")

    now = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(ticket["expires_at_utc"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        raise ValueError("Authorization ticket expired")
    return ticket


def choose_canned_response(policy: Dict[str, Any], session_id: str) -> str:
    corpus = policy.get("approved_canned_responses", [])
    if not corpus:
        raise ValueError("Shadow policy has no approved_canned_responses")
    rng = random.Random(session_id)
    return rng.choice(corpus)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supervised deception simulator for governance testing. This is not a live autonomous deception engine."
    )
    parser.add_argument("--classification", required=True, help="Classifier level, e.g. CAUTION, GRAVE, CONDEMNED")
    parser.add_argument("--session-id", required=True, help="Synthetic session identifier")
    parser.add_argument("--shadow-policy", default="example_shadow_policy", help="Signed shadow policy name or path")
    parser.add_argument("--authorization-ticket", default=None, help="Authorization ticket name or path")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    runtime = RuntimeState(state_dir="runtime_state")
    classification = args.classification.upper()

    payload: Dict[str, Any]

    def log(msg: str) -> None:
        runtime.log(msg)

    if classification not in ALLOWED_TRIGGER_LEVELS:
        payload = {
            "session_id": args.session_id,
            "classification": classification,
            "result": NULL_RESULT,
            "reason": "threshold_not_met",
        }
        if args.json:
            sink = io.StringIO()
            with contextlib.redirect_stdout(sink):
                log(f"deception_simulator_blocked session={args.session_id} reason=threshold classification={classification}")
            payload["audit_log"] = sink.getvalue().splitlines()
            print(json.dumps(payload, indent=2))
            return
        log(f"deception_simulator_blocked session={args.session_id} reason=threshold classification={classification}")
        print(json.dumps(payload, indent=2))
        return

    if not args.authorization_ticket:
        payload = {
            "session_id": args.session_id,
            "classification": classification,
            "result": NULL_RESULT,
            "reason": "authorization_missing",
        }
        if args.json:
            sink = io.StringIO()
            with contextlib.redirect_stdout(sink):
                log(f"deception_simulator_null session={args.session_id} reason=no_authorization classification={classification}")
            payload["audit_log"] = sink.getvalue().splitlines()
            print(json.dumps(payload, indent=2))
            return
        log(f"deception_simulator_null session={args.session_id} reason=no_authorization classification={classification}")
        print(json.dumps(payload, indent=2))
        return

    policy_path = resolve_path(args.shadow_policy, SHADOW_DIR)
    ticket_path = resolve_path(args.authorization_ticket, AUTH_DIR)
    policy = verify_signed_shadow_policy(policy_path)
    ticket = verify_authorization_ticket(ticket_path, args.session_id)
    response = choose_canned_response(policy, args.session_id)

    payload = {
        "session_id": args.session_id,
        "classification": classification,
        "policy_name": policy.get("policy_name"),
        "oversight_officer": ticket["oversight_officer"],
        "result": {
            "status": "generated",
            "mode": "canned_decoy_response",
            "content": response,
        },
        "guardrails": {
            "non_production": True,
            "network_actions": False,
            "external_routing": False,
            "approved_response_count": len(policy.get("approved_canned_responses", [])),
        },
    }

    if args.json:
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            log(f"deception_simulator_authorized session={args.session_id} officer={ticket['oversight_officer']} classification={classification}")
            log(f"deception_simulator_response_generated session={args.session_id} policy={policy.get('policy_name')} response_id={hash(response) & 0xffff}")
        payload["audit_log"] = sink.getvalue().splitlines()
        print(json.dumps(payload, indent=2))
        return

    log(f"deception_simulator_authorized session={args.session_id} officer={ticket['oversight_officer']} classification={classification}")
    log(f"deception_simulator_response_generated session={args.session_id} policy={policy.get('policy_name')} response_id={hash(response) & 0xffff}")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
