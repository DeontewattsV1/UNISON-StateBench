"""Kaggle-side orchestration for exact model keys selected at execution time."""

from __future__ import annotations

import json
from pathlib import Path

from .execute import execute_item
from .plan import build_v01_plan
from .records import append_jsonl, seal_result_files


def available_model_keys(kbench) -> tuple[str, ...]:
    """Snapshot exact model keys exposed by the current Kaggle runtime."""
    return tuple(sorted(str(key) for key in kbench.llms.keys()))


def validate_model_lineup(kbench, model_keys: list[str] | tuple[str, ...]) -> tuple[str, ...]:
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


def run_lineup(
    kbench,
    model_keys: list[str] | tuple[str, ...],
    *,
    output_dir: str | Path,
    run_id: str,
    root: str | Path = ".",
) -> dict:
    """Execute the complete 162-call plan for each exact Kaggle model key.

    The function refuses partial model-key resolution. Each model receives its own
    append-only JSONL file so interrupted runs retain completed structured observations.
    """

    lineup = validate_model_lineup(kbench, model_keys)
    plan = build_v01_plan(root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    availability = {
        "schema": "unison.empirical.kaggle-availability.v1",
        "run_id": run_id,
        "requested_model_keys": list(lineup),
        "available_model_keys": list(available_model_keys(kbench)),
        "source_revision": plan.source_revision,
        "plan_digest": plan.plan_digest,
    }
    (out / "model-availability.json").write_text(
        json.dumps(availability, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result_paths: list[Path] = []
    for model_key in lineup:
        llm = kbench.llms[model_key]
        safe_name = model_key.replace("/", "__").replace(":", "_")
        path = out / f"{safe_name}.jsonl"
        result_paths.append(path)
        completed = {
            record.item.plan_id
            for record in _load_existing(path)
            if record.succeeded
        }
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
                provider_metadata={"kaggle_model_key": model_key},
            )
            append_jsonl(path, record)

    manifest = seal_result_files(tuple(result_paths))
    manifest.update(
        {
            "run_id": run_id,
            "source_revision": plan.source_revision,
            "plan_digest": plan.plan_digest,
            "models": list(lineup),
        }
    )
    (out / "results-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _load_existing(path: Path):
    if not path.exists():
        return ()
    from .records import load_jsonl
    return load_jsonl(path)
