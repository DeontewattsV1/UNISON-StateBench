
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from celestial_agent.agent_spec_crypto import AgentSpecCrypto, canonical_json


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "policy_templates"
VAULT_DIR = BASE_DIR / "vault"
MANIFESTS_DIR = BASE_DIR / "manifests"
KEYS_DIR = BASE_DIR / "keys"
RELEASE_DIR = BASE_DIR / "release_manifests"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def resolve_template(name: str) -> Path:
    candidate = Path(name)
    if candidate.exists():
        return candidate.resolve()
    p = TEMPLATE_DIR / (name if name.endswith(".json") else f"{name}.json")
    if p.exists():
        return p.resolve()
    raise FileNotFoundError(f"Could not resolve template: {name}")


def load_or_create_crypto() -> AgentSpecCrypto:
    key_path = KEYS_DIR / "creator_private_key.b64"
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return AgentSpecCrypto.from_private_key_b64(key_path.read_text(encoding="utf-8").strip())
    crypto = AgentSpecCrypto()
    key_path.write_text(crypto.export_private_key_b64(), encoding="utf-8")
    return crypto


def build_release_record(
    *,
    template_path: Path,
    pack_name: str,
    release_name: str,
    release_notes: str,
    crypto: AgentSpecCrypto,
) -> Dict[str, Any]:
    pack_enc = VAULT_DIR / f"{pack_name}.enc"
    pack_manifest = MANIFESTS_DIR / f"{pack_name}.json"
    pack_sig = MANIFESTS_DIR / f"{pack_name}.sig"

    if not pack_enc.exists() or not pack_manifest.exists() or not pack_sig.exists():
        raise FileNotFoundError("Split pack is incomplete. Expected .enc, .json, and .sig files.")

    template = json.loads(template_path.read_text(encoding="utf-8"))
    template_hash = sha256_file(template_path)
    pack_manifest_json = json.loads(pack_manifest.read_text(encoding="utf-8"))
    governance = template.get("governance", {}) if isinstance(template, dict) else {}
    identity = template.get("identity", {}) if isinstance(template, dict) else {}

    return {
        "schema_version": "1.0.0",
        "content_type": "phaseform_release_manifest",
        "release_name": release_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "creator": template.get("creator", "TDD"),
        "public_key_b64": crypto.public_key_b64(),
        "template": {
            "file": str(template_path),
            "sha256": template_hash,
            "use_case": template.get("use_case"),
            "system_role": template.get("system_role"),
            "project": identity.get("project"),
        },
        "governance": {
            "risk_profile": governance.get("risk_profile"),
            "max_risk": governance.get("max_risk"),
        },
        "pack": {
            "name": pack_name,
            "ciphertext_file": str(pack_enc),
            "manifest_file": str(pack_manifest),
            "signature_file": str(pack_sig),
            "hashes": {
                "ciphertext_sha256": sha256_file(pack_enc),
                "manifest_sha256": sha256_file(pack_manifest),
                "signature_sha256": sha256_file(pack_sig),
            },
            "pack_manifest_creator": pack_manifest_json.get("creator"),
            "pack_manifest_schema_version": pack_manifest_json.get("schema_version"),
        },
        "release_notes": release_notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bundle template metadata, selected risk profile, pack hashes, and release notes into one signed handoff record."
    )
    parser.add_argument("--template", required=True, help="Template name or path from policy_templates/")
    parser.add_argument("--pack-name", required=True, help="Existing split pack base name")
    parser.add_argument("--release-notes", required=True, help="Release notes string for the handoff record")
    parser.add_argument("--release-name", default=None, help="Optional release record base name. Defaults to <pack-name>_release")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    template_path = resolve_template(args.template)
    release_name = args.release_name or f"{args.pack_name}_release"
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    crypto = load_or_create_crypto()
    record = build_release_record(
        template_path=template_path,
        pack_name=args.pack_name,
        release_name=release_name,
        release_notes=args.release_notes,
        crypto=crypto,
    )

    record_path = RELEASE_DIR / f"{release_name}.json"
    sig_path = RELEASE_DIR / f"{release_name}.sig"

    signature = crypto.private_key.sign(canonical_json(record))
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    sig_path.write_bytes(signature)

    payload = {
        "release_manifest_file": str(record_path),
        "release_signature_file": str(sig_path),
        "release_name": release_name,
        "pack_name": args.pack_name,
        "template_file": str(template_path),
        "risk_profile": record["governance"]["risk_profile"],
        "max_risk": record["governance"]["max_risk"],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print("== RELEASE MANIFEST ==")
    for k, v in payload.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
