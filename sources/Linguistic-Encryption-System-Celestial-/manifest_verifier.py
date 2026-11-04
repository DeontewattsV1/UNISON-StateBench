
from __future__ import annotations
import argparse, base64, hashlib, json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from celestial_agent.agent_spec_crypto import canonical_json


BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault"
MANIFESTS_DIR = BASE_DIR / "manifests"


def verify_split_pack(name: str) -> dict:
    enc_path = VAULT_DIR / f"{name}.enc"
    manifest_path = MANIFESTS_DIR / f"{name}.json"
    sig_path = MANIFESTS_DIR / f"{name}.sig"

    if not enc_path.exists():
        raise FileNotFoundError(f"Missing encrypted payload: {enc_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    if not sig_path.exists():
        raise FileNotFoundError(f"Missing signature: {sig_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ciphertext = enc_path.read_bytes()
    signature = sig_path.read_bytes()

    public_key_b64 = manifest.get("public_key_b64")
    if not public_key_b64:
        raise ValueError("Manifest missing public_key_b64")

    public_key = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    manifest_bytes = canonical_json(manifest)

    signature_valid = False
    signature_error = None
    try:
        public_key.verify(signature, manifest_bytes + ciphertext)
        signature_valid = True
    except InvalidSignature:
        signature_error = "Invalid Ed25519 signature"

    cipher_hash_expected = manifest.get("ciphertext_hash_sha256")
    cipher_hash_actual = hashlib.sha256(ciphertext).hexdigest()
    cipher_hash_valid = (cipher_hash_expected == cipher_hash_actual) if cipher_hash_expected else None

    return {
        "name": name,
        "creator": manifest.get("creator"),
        "schema_version": manifest.get("schema_version"),
        "content_type": manifest.get("content_type"),
        "signature_valid": signature_valid,
        "signature_error": signature_error,
        "ciphertext_hash_expected": cipher_hash_expected,
        "ciphertext_hash_actual": cipher_hash_actual,
        "ciphertext_hash_valid": cipher_hash_valid,
        "nonce_present": bool(manifest.get("nonce_b64")),
        "salt_present": bool(manifest.get("salt_b64")),
        "manifest_file": str(manifest_path),
        "ciphertext_file": str(enc_path),
        "signature_file": str(sig_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and verify a split PhaseForm policy pack on disk.")
    parser.add_argument("--name", required=True, help="Base pack name, e.g. policy_a")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    result = verify_split_pack(args.name)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("== SPLIT PACK VERIFICATION ==")
    for key in [
        "name",
        "creator",
        "schema_version",
        "content_type",
        "signature_valid",
        "signature_error",
        "ciphertext_hash_valid",
        "nonce_present",
        "salt_present",
        "manifest_file",
        "ciphertext_file",
        "signature_file",
    ]:
        print(f"{key}: {result[key]}")


if __name__ == "__main__":
    main()
