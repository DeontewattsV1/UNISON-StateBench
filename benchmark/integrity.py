"""Canonical/oracle integrity hashing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .models import CanonicalCase, OracleResult
from .oracle import derive_oracle


def canonical_json_bytes(model: CanonicalCase | OracleResult) -> bytes:
    payload = model.model_dump(mode="json", exclude_none=False)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(model: CanonicalCase | OracleResult) -> str:
    return hashlib.sha256(canonical_json_bytes(model)).hexdigest()


@dataclass(frozen=True, slots=True)
class IntegritySnapshot:
    case_digest: str
    oracle_digest: str


def snapshot(case: CanonicalCase) -> IntegritySnapshot:
    oracle = derive_oracle(case)
    return IntegritySnapshot(case_digest=digest(case), oracle_digest=digest(oracle))


def assert_unchanged(before: IntegritySnapshot, case: CanonicalCase) -> None:
    after = snapshot(case)
    if before != after:
        raise AssertionError(
            "Canonical state or deterministic oracle changed during evidence transformation"
        )
