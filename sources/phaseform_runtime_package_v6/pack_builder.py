
from __future__ import annotations
import argparse, base64, json
from pathlib import Path
from celestial_agent.agent_spec_crypto import AgentSpecCrypto

BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault"
MANIFESTS_DIR = BASE_DIR / "manifests"
KEYS_DIR = BASE_DIR / "keys"

def ensure_dirs() -> None:
    for d in [VAULT_DIR, MANIFESTS_DIR, KEYS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def load_or_create_crypto() -> AgentSpecCrypto:
    key_path = KEYS_DIR / "creator_private_key.b64"
    if key_path.exists():
        return AgentSpecCrypto.from_private_key_b64(key_path.read_text(encoding="utf-8").strip())
    crypto = AgentSpecCrypto()
    key_path.write_text(crypto.export_private_key_b64(), encoding="utf-8")
    return crypto

def main() -> None:
    parser = argparse.ArgumentParser(description="Build a split policy pack for PhaseForm.")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--passphrase", required=True)
    args = parser.parse_args()
    ensure_dirs()
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    crypto = load_or_create_crypto()
    pack = crypto.encrypt_spec(policy, passphrase=args.passphrase)
    (VAULT_DIR / f"{args.name}.enc").write_bytes(base64.b64decode(pack.ciphertext_b64))
    (MANIFESTS_DIR / f"{args.name}.json").write_text(json.dumps(pack.manifest, indent=2), encoding="utf-8")
    (MANIFESTS_DIR / f"{args.name}.sig").write_bytes(base64.b64decode(pack.signature_b64))
    print(f"Built split pack: {args.name}")
    print(f"  vault/{args.name}.enc")
    print(f"  manifests/{args.name}.json")
    print(f"  manifests/{args.name}.sig")

if __name__ == "__main__":
    main()
