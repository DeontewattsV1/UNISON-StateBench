"""Content-addressed Kaggle runtime snapshots and frozen model lineups."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import Field

from benchmark.models import FrozenModel

from .freeze import FREEZE_SOURCE_REVISION
from .plan import EmpiricalPlan


class RuntimeSnapshot(FrozenModel):
    schema_id: str = Field(
        default="unison.empirical.runtime-snapshot.v1",
        alias="schema",
        serialization_alias="schema",
    )
    source_revision: str
    plan_digest: str
    available_model_keys: tuple[str, ...]
    runtime_metadata: dict[str, Any] = Field(default_factory=dict)
    snapshot_digest: str


class FrozenLineup(FrozenModel):
    schema_id: str = Field(
        default="unison.empirical.frozen-lineup.v1",
        alias="schema",
        serialization_alias="schema",
    )
    source_revision: str
    plan_digest: str
    runtime_snapshot_digest: str
    selected_model_keys: tuple[str, ...]
    model_count: int = Field(ge=1)
    calls_per_model: int = Field(ge=1)
    total_model_calls: int = Field(ge=1)
    lineup_digest: str


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(payload: dict) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def snapshot_runtime(
    kbench,
    plan: EmpiricalPlan,
    *,
    runtime_metadata: dict[str, Any] | None = None,
) -> RuntimeSnapshot:
    """Snapshot the exact model keys exposed by the current Kaggle runtime."""

    keys = tuple(sorted(str(key) for key in kbench.llms.keys()))
    if not keys:
        raise ValueError("Kaggle runtime exposed no model keys")

    payload = {
        "schema": "unison.empirical.runtime-snapshot.v1",
        "source_revision": plan.source_revision,
        "plan_digest": plan.plan_digest,
        "available_model_keys": list(keys),
        "runtime_metadata": runtime_metadata or {},
    }
    return RuntimeSnapshot(
        source_revision=plan.source_revision,
        plan_digest=plan.plan_digest,
        available_model_keys=keys,
        runtime_metadata=runtime_metadata or {},
        snapshot_digest=_digest(payload),
    )


def freeze_lineup(
    snapshot: RuntimeSnapshot,
    selected_model_keys: Iterable[str],
    *,
    calls_per_model: int,
) -> FrozenLineup:
    """Freeze an exact model lineup against one runtime availability snapshot."""

    selected = tuple(str(key) for key in selected_model_keys)
    if not selected:
        raise ValueError("At least one exact model key must be selected")
    if len(set(selected)) != len(selected):
        raise ValueError("Selected model lineup contains duplicate keys")
    if calls_per_model <= 0:
        raise ValueError("calls_per_model must be > 0")

    available = set(snapshot.available_model_keys)
    missing = tuple(key for key in selected if key not in available)
    if missing:
        raise ValueError(
            "Selected model keys are not present in the captured runtime snapshot: "
            + ", ".join(missing)
        )

    payload = {
        "schema": "unison.empirical.frozen-lineup.v1",
        "source_revision": snapshot.source_revision,
        "plan_digest": snapshot.plan_digest,
        "runtime_snapshot_digest": snapshot.snapshot_digest,
        "selected_model_keys": list(selected),
        "model_count": len(selected),
        "calls_per_model": calls_per_model,
        "total_model_calls": len(selected) * calls_per_model,
    }
    return FrozenLineup(
        source_revision=snapshot.source_revision,
        plan_digest=snapshot.plan_digest,
        runtime_snapshot_digest=snapshot.snapshot_digest,
        selected_model_keys=selected,
        model_count=len(selected),
        calls_per_model=calls_per_model,
        total_model_calls=len(selected) * calls_per_model,
        lineup_digest=_digest(payload),
    )


def validate_lineup_against_runtime(kbench, lineup: FrozenLineup) -> None:
    """Refuse execution if a frozen exact key is no longer available."""

    available = {str(key) for key in kbench.llms.keys()}
    missing = [key for key in lineup.selected_model_keys if key not in available]
    if missing:
        raise ValueError(
            "Frozen lineup cannot execute because these exact Kaggle keys are unavailable: "
            + ", ".join(missing)
        )


def write_snapshot(path: str | Path, snapshot: RuntimeSnapshot) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def write_lineup(path: str | Path, lineup: FrozenLineup) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(lineup.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def load_lineup(path: str | Path) -> FrozenLineup:
    return FrozenLineup.model_validate_json(Path(path).read_text(encoding="utf-8"))


def assert_lineup_matches_plan(lineup: FrozenLineup, plan: EmpiricalPlan) -> None:
    if lineup.source_revision != FREEZE_SOURCE_REVISION:
        raise ValueError("Frozen lineup source revision does not match UNISON v0.1")
    if lineup.source_revision != plan.source_revision:
        raise ValueError("Frozen lineup source revision does not match execution plan")
    if lineup.plan_digest != plan.plan_digest:
        raise ValueError("Frozen lineup plan digest does not match execution plan")
    if lineup.calls_per_model != plan.model_calls:
        raise ValueError("Frozen lineup calls_per_model does not match execution plan")
    if lineup.total_model_calls != lineup.model_count * plan.model_calls:
        raise ValueError("Frozen lineup total_model_calls is inconsistent")
