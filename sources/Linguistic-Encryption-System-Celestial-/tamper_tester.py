
from __future__ import annotations
import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault"
MANIFESTS_DIR = BASE_DIR / "manifests"


def flip_byte(data: bytes) -> bytes:
    if not data:
        raise ValueError("Cannot tamper empty data")
    mutable = bytearray(data)
    mutable[0] ^= 0x01
    return bytes(mutable)


def tamper_enc(output_name: str) -> None:
    dst = VAULT_DIR / f"{output_name}.enc"
    dst.write_bytes(flip_byte(dst.read_bytes()))
    print(f"Tampered ciphertext written: {dst}")


def tamper_sig(output_name: str) -> None:
    dst = MANIFESTS_DIR / f"{output_name}.sig"
    dst.write_bytes(flip_byte(dst.read_bytes()))
    print(f"Tampered signature written: {dst}")


def tamper_json(output_name: str) -> None:
    dst = MANIFESTS_DIR / f"{output_name}.json"
    manifest = json.loads(dst.read_text(encoding="utf-8"))
    if "creator" in manifest and isinstance(manifest["creator"], str):
        manifest["creator"] = manifest["creator"] + "_tampered"
    elif "ciphertext_hash_sha256" in manifest and isinstance(manifest["ciphertext_hash_sha256"], str):
        current = manifest["ciphertext_hash_sha256"]
        manifest["ciphertext_hash_sha256"] = ("0" if current[:1] != "0" else "1") + current[1:]
    else:
        manifest["tampered"] = True
    dst.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Tampered manifest written: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create intentionally corrupted split-pack files for fail-closed testing.")
    parser.add_argument("--name", required=True, help="Base valid pack name, e.g. policy_a")
    parser.add_argument("--target", required=True, choices=["enc", "json", "sig"], help="Which file to tamper")
    parser.add_argument("--output-name", default=None, help="Base output name for tampered files")
    args = parser.parse_args()

    output_name = args.output_name or f"{args.name}_tampered_{args.target}"

    enc_src = VAULT_DIR / f"{args.name}.enc"
    json_src = MANIFESTS_DIR / f"{args.name}.json"
    sig_src = MANIFESTS_DIR / f"{args.name}.sig"

    if not enc_src.exists() or not json_src.exists() or not sig_src.exists():
        raise SystemExit("Source split pack is incomplete. Expected .enc, .json, and .sig files.")

    enc_dst = VAULT_DIR / f"{output_name}.enc"
    json_dst = MANIFESTS_DIR / f"{output_name}.json"
    sig_dst = MANIFESTS_DIR / f"{output_name}.sig"

    enc_dst.write_bytes(enc_src.read_bytes())
    json_dst.write_text(json_src.read_text(encoding="utf-8"), encoding="utf-8")
    sig_dst.write_bytes(sig_src.read_bytes())

    if args.target == "enc":
        tamper_enc(output_name)
    elif args.target == "json":
        tamper_json(output_name)
    elif args.target == "sig":
        tamper_sig(output_name)

    print(f"Tampered split pack ready under base name: {output_name}")


if __name__ == "__main__":
    main()
