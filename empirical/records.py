"""Raw structured-observation preservation for UNISON empirical runs."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark.models import FrozenModel, StructuredObservation
from benchmark.scoring import TrialScore

from .plan import EmpiricalPlanItem


class EmpiricalRecord(FrozenModel):
    schema: str = "unison.empirical.record.v1"
    run_id: str
    model_id: str
    provider: str
    source_revision: str
    plan_digest: str
    item: EmpiricalPlanItem
    prompt_sha256: str
    observation: StructuredObservation | None = None
    score: TrialScore | None = None
    provider_metadata: dict[str, Any] = {}
    error: str | None = None
    started_at: str
    completed_at: str

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.observation is not None and self.score is not None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def append_jsonl(path: str | Path, record: EmpiricalRecord) -> None:
    """Append one durable JSON record and fsync before returning."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        record.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    with output.open("a", encoding="utf-8") as handle:
        handle.write(payload + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_jsonl(path: str | Path) -> tuple[EmpiricalRecord, ...]:
    records: list[EmpiricalRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(EmpiricalRecord.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"Invalid empirical record at line {line_number}") from exc
    return tuple(records)


def seal_result_files(paths: list[str | Path] | tuple[str | Path, ...]) -> dict[str, Any]:
    """Create a content manifest for append-only raw result files."""

    files = []
    total_records = 0
    for raw_path in sorted(Path(item) for item in paths):
        data = raw_path.read_bytes()
        records = load_jsonl(raw_path)
        files.append(
            {
                "path": str(raw_path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "records": len(records),
            }
        )
        total_records += len(records)
    manifest = {
        "schema": "unison.empirical.results-manifest.v1",
        "files": files,
        "total_records": total_records,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return manifest
