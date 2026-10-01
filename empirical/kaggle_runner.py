"""Kaggle-side orchestration for a content-addressed model lineup."""

from __future__ import annotations

import json
from pathlib import Path

from .execute import execute_item
from .lineup import (
    FrozenLineup,
    assert_lineup_matches_plan,
    validate_lineup_against_runtime,
    write_lineup,
)
from .plan import build_v01_plan
from .records import EmpiricalRecord, append_jsonl, load_jsonl, seal_result_files


def available_model_keys(kbench) -> tuple[str, ...]:
    """Return exact model keys exposed by the current Kaggle runtime."""
    return tuple(sorted(str(key) for key in kbench.llms.keys()))


def validate_model_lineup(kbench, model_keys: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Compatibility validator for interactive development.

    Publication runs should use run_frozen_lineup instead.
    """
    requested = tuple(model_keys)
    if not requested:
        raise ValueError("At least one exact Kaggle model key is required")
    if len(set(requested)) != len(requested):
        raise ValueError("Model lineup contains duplicate keys")
    available = set(available_model_keys(kbench))
    missing = [key for key in requested if key not in available]
    if missing:
        raise ValueError(
            "Requested models are unavailable in this Kaggle runtime: "
            + ", ".join(missing)
        )
    return requested


def _validate_existing_records(
    records: tuple[EmpiricalRecord, ...],
    *,
    run_id: str,
    model_key: str,
    source_revision: str,
    plan_digest: str,
) -> set[str]:
    """Validate resumable records so a new run cannot inherit stale successes."""
    completed: set[str] = set()
    for record in records:
        if record.run_id != run_id:
            raise ValueError(
                f"Existing result file contains run_id={record.run_id!r}, "
                f"expected {run_id!r}"
            )
        if record.model_id != model_key:
            raise ValueError(
                f"Existing result file contains model_id={record.model_id!r}, "
                f"expected {model_key!r}"
            )
        if record.source_revision != source_revision:
            raise ValueError("Existing result file source revision does not match frozen run")
        if record.plan_digest != plan_digest:
            raise ValueError("Existing result file plan digest does not match frozen run")
        if record.succeeded:
            if record.item.plan_id in completed:
                raise ValueError(
                    f"Existing result file contains duplicate successful plan_id "
                    f"{record.item.plan_id!r}"
                )
            completed.add(record.item.plan_id)
    return completed


def run_frozen_lineup(
    kbench,
    lineup: FrozenLineup,
    *,
    output_dir: str | Path,
    run_id: str,
    root: str | Path = ".",
) -> dict:
    """Execute the exact frozen lineup against the exact frozen v0.1 plan."""
    plan = build_v01_plan(root)
    assert_lineup_matches_plan(lineup, plan)
    validate_lineup_against_runtime(kbench, lineup)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_lineup(out / "executed-lineup.json", lineup)

    runtime_check = {
        "schema": "unison.empirical.execution-runtime-check.v1",
        "run_id": run_id,
        "available_model_keys": list(available_model_keys(kbench)),
        "selected_model_keys": list(lineup.selected_model_keys),
        "source_revision": plan.source_revision,
        "plan_digest": plan.plan_digest,
        "lineup_digest": lineup.lineup_digest,
    }
    (out / "execution-runtime-check.json").write_text(
        json.dumps(runtime_check, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result_paths: list[Path] = []
    for model_key in lineup.selected_model_keys:
        llm = kbench.llms[model_key]
        safe_name = model_key.replace("/", "__").replace(":", "_")
        path = out / f"{safe_name}.jsonl"
        result_paths.append(path)

        existing = _load_existing(path)
        completed = _validate_existing_records(
            existing,
            run_id=run_id,
            model_key=model_key,
            source_revision=plan.source_revision,
            plan_digest=plan.plan_digest,
        )

        for item in plan.items:
            if item.plan_id in completed:
                continue
            record = execute_item(
                kbench,
                llm,
                plan,
                item,
                root=root,
                run_id=run_id,
                model_id=model_key,
                provider=model_key.split("/", 1)[0] if "/" in model_key else "kaggle",
                provider_metadata={
                    "kaggle_model_key": model_key,
                    "lineup_digest": lineup.lineup_digest,
                },
            )
            append_jsonl(path, record)

    manifest = seal_result_files(tuple(result_paths))
    manifest.update(
        {
            "run_id": run_id,
            "source_revision": plan.source_revision,
            "plan_digest": plan.plan_digest,
            "lineup_digest": lineup.lineup_digest,
            "runtime_snapshot_digest": lineup.runtime_snapshot_digest,
            "models": list(lineup.selected_model_keys),
            "model_count": lineup.model_count,
            "calls_per_model": lineup.calls_per_model,
            "expected_total_model_calls": lineup.total_model_calls,
        }
    )
    (out / "results-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def run_lineup(
    kbench,
    model_keys: list[str] | tuple[str, ...],
    *,
    output_dir: str | Path,
    run_id: str,
    root: str | Path = ".",
) -> dict:
    """Interactive compatibility path.

    This validates exact keys but does not itself establish a publication freeze.
    Empirical publication runs should snapshot, freeze, then call run_frozen_lineup.
    """
    from .lineup import freeze_lineup, snapshot_runtime

    plan = build_v01_plan(root)
    snapshot = snapshot_runtime(
        kbench,
        plan,
        runtime_metadata={"execution_surface": "compatibility_run_lineup"},
    )
    requested = validate_model_lineup(kbench, model_keys)
    lineup = freeze_lineup(snapshot, requested, calls_per_model=plan.model_calls)
    return run_frozen_lineup(
        kbench,
        lineup,
        output_dir=output_dir,
        run_id=run_id,
        root=root,
    )


def _load_existing(path: Path) -> tuple[EmpiricalRecord, ...]:
    if not path.exists():
        return ()
    return load_jsonl(path)
