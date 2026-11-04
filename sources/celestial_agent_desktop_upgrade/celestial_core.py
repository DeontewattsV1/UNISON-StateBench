from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SUPPORTED_CHARS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    " .,!?\"'_-:/\n"
)


def canonical_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def derive_key(passphrase: str, salt: bytes) -> bytes:
    if not passphrase:
        raise ValueError("Passphrase is required.")
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(passphrase.encode("utf-8"))


@dataclass
class SignedAgentPack:
    manifest: Dict[str, Any]
    ciphertext_b64: str
    nonce_b64: str
    salt_b64: str
    signature_b64: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "manifest": self.manifest,
                "ciphertext_b64": self.ciphertext_b64,
                "nonce_b64": self.nonce_b64,
                "salt_b64": self.salt_b64,
                "signature_b64": self.signature_b64,
            },
            indent=2,
            ensure_ascii=False,
        )

    @staticmethod
    def from_json(raw: str) -> "SignedAgentPack":
        data = json.loads(raw)
        return SignedAgentPack(
            manifest=data["manifest"],
            ciphertext_b64=data["ciphertext_b64"],
            nonce_b64=data["nonce_b64"],
            salt_b64=data["salt_b64"],
            signature_b64=data["signature_b64"],
        )


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

    def export_public_key_b64(self) -> str:
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("utf-8")

    @staticmethod
    def from_private_key_b64(value: str) -> "AgentSpecCrypto":
        raw = base64.b64decode(value)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw)
        return AgentSpecCrypto(private_key=private_key)

    def encrypt_and_sign(self, spec: Dict[str, Any], passphrase: str) -> SignedAgentPack:
        plaintext = canonical_json(spec)
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = derive_key(passphrase, salt)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

        manifest = {
            "schema_version": "1.0",
            "content_type": "agent_spec",
            "creator": spec.get("creator", "TDD"),
            "title": spec.get("title", "Celestial Agent Spec"),
            "public_key_b64": self.export_public_key_b64(),
            "plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
            "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
        }

        signature = self.private_key.sign(canonical_json(manifest) + ciphertext)
        return SignedAgentPack(
            manifest=manifest,
            ciphertext_b64=base64.b64encode(ciphertext).decode("utf-8"),
            nonce_b64=base64.b64encode(nonce).decode("utf-8"),
            salt_b64=base64.b64encode(salt).decode("utf-8"),
            signature_b64=base64.b64encode(signature).decode("utf-8"),
        )

    @staticmethod
    def verify_and_decrypt(pack: SignedAgentPack, passphrase: str) -> Dict[str, Any]:
        ciphertext = base64.b64decode(pack.ciphertext_b64)
        nonce = base64.b64decode(pack.nonce_b64)
        salt = base64.b64decode(pack.salt_b64)
        signature = base64.b64decode(pack.signature_b64)
        public_key_raw = base64.b64decode(pack.manifest["public_key_b64"])
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_raw)

        public_key.verify(signature, canonical_json(pack.manifest) + ciphertext)

        if hashlib.sha256(ciphertext).hexdigest() != pack.manifest["ciphertext_sha256"]:
            raise ValueError("Ciphertext hash mismatch.")

        key = derive_key(passphrase, salt)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)

        if hashlib.sha256(plaintext).hexdigest() != pack.manifest["plaintext_sha256"]:
            raise ValueError("Plaintext hash mismatch.")

        return json.loads(plaintext.decode("utf-8"))


class CelestialCodec:
    def __init__(self, seed: str) -> None:
        if not seed:
            raise ValueError("Seed is required.")
        self.seed = seed
        self.char_to_glyph = {ch: self._glyph_for(ch) for ch in SUPPORTED_CHARS}
        self.glyph_to_char = {glyph: ch for ch, glyph in self.char_to_glyph.items()}

    def _glyph_for(self, ch: str) -> str:
        digest = hashlib.sha256(f"{self.seed}:{ch}".encode("utf-8")).digest()[:2]
        return "".join(chr(0xE000 + b) for b in digest)

    def encode(self, text: str) -> str:
        encoded: List[str] = []
        for ch in text:
            encoded.append(self.char_to_glyph.get(ch, ch))
        return "".join(encoded)

    def decode(self, glyph_text: str) -> str:
        out: List[str] = []
        i = 0
        while i < len(glyph_text):
            pair = glyph_text[i : i + 2]
            if pair in self.glyph_to_char:
                out.append(self.glyph_to_char[pair])
                i += 2
            else:
                out.append(glyph_text[i])
                i += 1
        return "".join(out)


class WorkspaceError(Exception):
    pass


class SafeWorkspace:
    def __init__(self, root: str) -> None:
        root_path = Path(root).expanduser().resolve()
        root_path.mkdir(parents=True, exist_ok=True)
        self.root = root_path

    def resolve_safe(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if self.root not in target.parents and target != self.root:
            raise WorkspaceError("Blocked path outside workspace.")
        return target

    def write_text(self, relative_path: str, content: str, append: bool = False) -> str:
        target = self.resolve_safe(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as handle:
            handle.write(content)
        return str(target.relative_to(self.root))

    def read_text(self, relative_path: str) -> str:
        target = self.resolve_safe(relative_path)
        if not target.exists():
            raise WorkspaceError(f"File not found: {relative_path}")
        return target.read_text(encoding="utf-8")

    def list_files(self) -> List[str]:
        return sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_file())


class AgentRuntime:
    def __init__(self, workspace_root: str, seed: str) -> None:
        self.workspace = SafeWorkspace(workspace_root)
        self.codec = CelestialCodec(seed)
        self.loaded_spec: Optional[Dict[str, Any]] = None

    def load_spec(self, spec: Dict[str, Any]) -> None:
        self.loaded_spec = spec

    def compile_to_celestial(self, commands: str) -> str:
        return self.codec.encode(commands)

    def decode_from_celestial(self, encoded: str) -> str:
        return self.codec.decode(encoded)

    def execute(self, source: str, is_celestial: bool = False) -> str:
        commands = self.decode_from_celestial(source) if is_celestial else source
        output: List[str] = []
        for raw_line in commands.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            output.append(f"> {line}")
            output.append(self._execute_line(line))
        return "\n".join(output)

    def _execute_line(self, line: str) -> str:
        patterns = [
            (r'^MAKE FILE "([^"]+)"$', self._cmd_make_file),
            (r'^WRITE "([\s\S]*)" TO "([^"]+)"$', self._cmd_write),
            (r'^APPEND "([\s\S]*)" TO "([^"]+)"$', self._cmd_append),
            (r'^READ FILE "([^"]+)"$', self._cmd_read),
            (r'^LIST FILES$', self._cmd_list),
            (r'^HASH "([\s\S]*)"$', self._cmd_hash),
            (r'^MAKE FUNCTION "([^"]+)" LANG "([^"]+)" ARGS "([^"]*)" BODY "([\s\S]*)" TO "([^"]+)"$', self._cmd_make_function),
        ]
        for pattern, handler in patterns:
            match = re.match(pattern, line)
            if match:
                return handler(*match.groups())
        raise WorkspaceError(f"Unsupported command: {line}")

    def _cmd_make_file(self, path: str) -> str:
        self.workspace.write_text(path, "")
        return f"Created file: {path}"

    def _cmd_write(self, content: str, path: str) -> str:
        self.workspace.write_text(path, content, append=False)
        return f"Wrote {len(content)} chars to {path}"

    def _cmd_append(self, content: str, path: str) -> str:
        self.workspace.write_text(path, content, append=True)
        return f"Appended {len(content)} chars to {path}"

    def _cmd_read(self, path: str) -> str:
        return self.workspace.read_text(path)

    def _cmd_list(self) -> str:
        files = self.workspace.list_files()
        return "\n".join(files) if files else "(workspace is empty)"

    def _cmd_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _cmd_make_function(self, name: str, lang: str, args: str, body: str, path: str) -> str:
        template = self._render_function(name=name, lang=lang, args=args, body=body)
        self.workspace.write_text(path, template, append=False)
        return f"Generated {lang} function at {path}"

    @staticmethod
    def _render_function(name: str, lang: str, args: str, body: str) -> str:
        lang_normalized = lang.strip().lower()
        if lang_normalized == "python":
            indent_body = "\n".join(f"    {line}" for line in body.splitlines()) or "    pass"
            return f"def {name}({args}):\n{indent_body}\n"
        if lang_normalized in {"javascript", "js"}:
            indent_body = "\n".join(f"  {line}" for line in body.splitlines())
            return f"function {name}({args}) {{\n{indent_body}\n}}\n"
        if lang_normalized in {"typescript", "ts"}:
            indent_body = "\n".join(f"  {line}" for line in body.splitlines())
            return f"export function {name}({args}) {{\n{indent_body}\n}}\n"
        raise WorkspaceError(f"Unsupported language: {lang}")
