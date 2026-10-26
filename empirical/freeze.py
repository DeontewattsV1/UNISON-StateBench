"""Verification of the content-addressed UNISON-StateBench v0.1 source freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

FREEZE_SOURCE_REVISION = "df10125d05f8271c613213851214ad8d37554363"
FREEZE_TREE = "d0a499dff542dd32ddc1fe5d08835b2f1da1b7f9"


class FreezeViolation(RuntimeError):
    """Raised when empirical execution does not match the frozen source bytes."""


class FreezeCheck(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    expected_blob_sha: str
    actual_blob_sha: str
    matches: bool


class FreezeReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: str
    source_revision: str
    source_tree: str
    checks: tuple[FreezeCheck, ...]

    @property
    def valid(self) -> bool:
        return bool(self.checks) and all(item.matches for item in self.checks)


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def _protected_files(manifest: dict) -> dict[str, str]:
    files: dict[str, str] = {}
    for collection in ("baseline_cases", "counterfactual_cases"):
        for entry in manifest.get(collection, {}).values():
            files[entry["path"]] = entry["git_blob_sha"]
    corpus = manifest["corpus_manifest"]
    files[corpus["path"]] = corpus["git_blob_sha"]
    files.update(manifest["constitutional_core"])
    return files


def verify_frozen_workspace(root: str | Path = ".") -> FreezeReport:
    """Fail closed unless the working bytes match the recorded v0.1 freeze."""

    root_path = Path(root).resolve()
    manifest_path = root_path / "releases" / "v0.1.0-freeze.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    revision = manifest["source_revision"]

    if revision["commit_sha"] != FREEZE_SOURCE_REVISION:
        raise FreezeViolation(
            f"Freeze manifest commit {revision['commit_sha']} does not match "
            f"expected {FREEZE_SOURCE_REVISION}"
        )
    if revision["tree_sha"] != FREEZE_TREE:
        raise FreezeViolation(
            f"Freeze manifest tree {revision['tree_sha']} does not match expected {FREEZE_TREE}"
        )

    checks: list[FreezeCheck] = []
    for rel_path, expected_sha in sorted(_protected_files(manifest).items()):
        path = root_path / rel_path
        if not path.is_file():
            raise FreezeViolation(f"Frozen source file is missing: {rel_path}")
        actual_sha = git_blob_sha(path.read_bytes())
        checks.append(
            FreezeCheck(
                path=rel_path,
                expected_blob_sha=expected_sha,
                actual_blob_sha=actual_sha,
                matches=actual_sha == expected_sha,
            )
        )

    report = FreezeReport(
        version=manifest["version"],
        source_revision=revision["commit_sha"],
        source_tree=revision["tree_sha"],
        checks=tuple(checks),
    )
    if not report.valid:
        mismatches = [
            f"{item.path}: expected {item.expected_blob_sha}, got {item.actual_blob_sha}"
            for item in report.checks
            if not item.matches
        ]
        raise FreezeViolation(
            "Frozen v0.1 source bytes changed; empirical run refused:\n"
            + "\n".join(mismatches)
        )
    return report
