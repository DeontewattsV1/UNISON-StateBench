
from __future__ import annotations
import base64, hashlib, json, os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

def canonical_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

def derive_key(passphrase: str, salt: bytes) -> bytes:
    if not passphrase:
        raise ValueError("Passphrase is required.")
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(passphrase.encode("utf-8"))

@dataclass
class EncryptedAgentPack:
    manifest: Dict[str, Any]
    ciphertext_b64: str
    nonce_b64: str
    salt_b64: str
    signature_b64: str

class AgentSpecCrypto:
    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None) -> None:
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def export_private_key_b64(self) -> str:
        raw = self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return base64.b64encode(raw).decode("utf-8")

    @staticmethod
    def from_private_key_b64(value: str) -> "AgentSpecCrypto":
        raw = base64.b64decode(value)
        return AgentSpecCrypto(private_key=ed25519.Ed25519PrivateKey.from_private_bytes(raw))

    def public_key_b64(self) -> str:
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("utf-8")

    def encrypt_spec(self, spec: Dict[str, Any], passphrase: str) -> EncryptedAgentPack:
        plaintext = canonical_json(spec)
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = derive_key(passphrase, salt)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        manifest = {
            "schema_version": spec.get("schema_version", "1.0"),
            "creator": spec.get("creator", "TDD"),
            "public_key_b64": self.public_key_b64(),
            "spec_hash_sha256": hashlib.sha256(plaintext).hexdigest(),
            "ciphertext_hash_sha256": hashlib.sha256(ciphertext).hexdigest(),
            "content_type": "agent_spec",
            "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
            "salt_b64": base64.b64encode(salt).decode("utf-8"),
        }
        signature = self.private_key.sign(canonical_json(manifest) + ciphertext)
        return EncryptedAgentPack(
            manifest=manifest,
            ciphertext_b64=base64.b64encode(ciphertext).decode("utf-8"),
            nonce_b64=manifest["nonce_b64"],
            salt_b64=manifest["salt_b64"],
            signature_b64=base64.b64encode(signature).decode("utf-8"),
        )

    @staticmethod
    def verify_and_decrypt(pack: EncryptedAgentPack, passphrase: str) -> Dict[str, Any]:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(pack.manifest["public_key_b64"]))
        ciphertext = base64.b64decode(pack.ciphertext_b64)
        nonce = base64.b64decode(pack.nonce_b64)
        salt = base64.b64decode(pack.salt_b64)
        signature = base64.b64decode(pack.signature_b64)
        pub.verify(signature, canonical_json(pack.manifest) + ciphertext)
        cipher_hash = pack.manifest.get("ciphertext_hash_sha256")
        if cipher_hash and hashlib.sha256(ciphertext).hexdigest() != cipher_hash:
            raise ValueError("Ciphertext hash mismatch.")
        key = derive_key(passphrase, salt)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        data = json.loads(plaintext.decode("utf-8"))
        spec_hash = pack.manifest.get("spec_hash_sha256")
        if spec_hash and hashlib.sha256(canonical_json(data)).hexdigest() != spec_hash:
            raise ValueError("Spec hash mismatch.")
        return data
