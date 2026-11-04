"""
Celestial Language Module
=========================

This module provides a proof-of-concept implementation of a constructed
language that encodes messages into sequences of alien-like glyphs and
secures them with a simple one-time-pad helper.

Author credit:
  The celestial language concept and implementation were created by TDD.
  Please retain this credit if you reuse or modify this module.
"""

from __future__ import annotations

import hashlib
import secrets
import string
from typing import Dict, List, Tuple


class CelestialLanguage:
    """Generate glyph alphabets and perform encoding and encryption."""

    def __init__(self, seed: str) -> None:
        if not seed:
            raise ValueError("seed is required")
        self.seed = seed
        self.glyph_map = self._generate_glyphs()

    def _generate_glyphs(self) -> Dict[str, str]:
        charset = string.ascii_letters + string.digits + " .,!?-_:/"
        glyphs: Dict[str, str] = {}
        used = set()

        for ch in charset:
            counter = 0
            glyph = None
            while glyph is None or glyph in used:
                digest = hashlib.sha256(f"{self.seed}|{ch}|{counter}".encode("utf-8")).digest()[:4]
                candidate = "".join(
                    chr(0xE000 + (byte >> 4)) + chr(0xE000 + (byte & 0x0F))
                    for byte in digest
                )
                glyph = candidate
                counter += 1
            used.add(glyph)
            glyphs[ch] = glyph
        return glyphs

    def encode_message(self, message: str) -> str:
        parts: List[str] = []
        for ch in message:
            parts.append(self.glyph_map.get(ch, ch))
        return "".join(parts)

    def encrypt_bytes(self, data: bytes) -> Tuple[bytes, bytes]:
        key = secrets.token_bytes(len(data))
        ciphertext = bytes(a ^ b for a, b in zip(data, key))
        return ciphertext, key

    def decrypt_bytes(self, ciphertext: bytes, key: bytes) -> bytes:
        if len(ciphertext) != len(key):
            raise ValueError("Ciphertext and key lengths do not match")
        return bytes(a ^ b for a, b in zip(ciphertext, key))


__all__ = ["CelestialLanguage"]
