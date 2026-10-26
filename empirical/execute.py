"""Execution adapter from the frozen empirical plan to Kaggle-compatible LLMs."""

from __future__ import annotations

from pathlib import Path

from benchmark.kaggle_adapter import (
    OUTPUT_CONTRACT,
    build_isolation_context,
    build_tool_conflict_context,
    build_trial_prompt,
    make_neutral_padding,
)
from benchmark.kaggle_runtime import run_tool_only_trial_in_fresh_chat, run_trial_in_fresh_chat
from benchmark.loaders import load_case
from benchmark.trials import EvaluationPolicy, MutationKind, MutationPlan, generate_trial

from .freeze import verify_frozen_workspace
from .plan import EmpiricalPlan, EmpiricalPlanItem, Suite
from .records import EmpiricalRecord, sha256_text, utc_now


_TARGETED_MUTATIONS = {
    MutationKind.CONTRADICTION,
    MutationKind.MISSING,
    MutationKind.AUTHORITY_CONFLICT,
    MutationKind.ADVERSARIAL,
}


def _materialize(root: Path, item: EmpiricalPlanItem):
    case = load_case(root / item.case_path)
    kwargs: dict[str, object] = {"kind": item.mutation}
    if item.mutation in _TARGETED_MUTATIONS:
        kwargs["invariant_id"] = item.invariant_id
    if item.mutation in {
        MutationKind.CONTRADICTION,
        MutationKind.AUTHORITY_CONFLICT,
        MutationKind.ADVERSARIAL,
    }:
        kwargs["source_id"] = item.source_id
        kwargs["replacement_value"] = item.replacement_value
    if item.mutation is MutationKind.REORDER:
        kwargs["mode"] = "reverse"

    mutation = MutationPlan(**kwargs)
    policy = EvaluationPolicy(
        authorization_sensitive=item.authorization_sensitive,
        forbidden_invariant_ids=(item.isolation_canary_id,) if item.isolation_canary_id else (),
        forbidden_output_markers=(item.isolation_canary_value,) if item.isolation_canary_value else (),
    )
    trial = generate_trial(case, item.representation, mutation, policy=policy)
    return case, trial


def _normal_prompt(item: EmpiricalPlanItem, trial) -> tuple[str, str, str, str]:
    prefix = ""
    padding = ""
    suffix = ""
    if item.suite is Suite.U07:
        prefix = build_isolation_context(
            principal="P1",
            foreign_principal="P2",
            forbidden_invariant_id=item.isolation_canary_id or "I_FOREIGN_CANARY",
            canary_value=item.isolation_canary_value or "FOREIGN_ONLY",
        )
    if item.suite is Suite.U09:
        padding = make_neutral_padding(item.distance_units or 0)
    prompt = build_trial_prompt(trial, prefix=prefix, padding=padding, suffix=suffix)
    return prompt, prefix, padding, suffix


def execute_item(
    kbench,
    llm,
    plan: EmpiricalPlan,
    item: EmpiricalPlanItem,
    *,
    root: str | Path = ".",
    run_id: str,
    model_id: str,
    provider: str,
    provider_metadata: dict | None = None,
) -> EmpiricalRecord:
    """Execute exactly one plan item and preserve its normalized structured output."""

    root_path = Path(root).resolve()
    verify_frozen_workspace(root_path)
    case, trial = _materialize(root_path, item)
    started = utc_now()

    try:
        if item.tool_only:
            target = item.invariant_id or case.invariants[-1].id
            false_value = item.replacement_value
            assumption = f"{target}={false_value!r}"
            prompt = "\n".join(
                [
                    "UNISON-StateBench tool-state evaluation.",
                    build_tool_conflict_context(false_assumption=assumption),
                    "The authoritative state is available only through authoritative_state().",
                    OUTPUT_CONTRACT,
                ]
            )

            def authoritative_state() -> str:
                """Return the authoritative evidence surface for this frozen trial."""
                return trial.artifact.content

            observation, score = run_tool_only_trial_in_fresh_chat(
                kbench,
                llm,
                case,
                trial,
                prompt=prompt,
                tool=authoritative_state,
                chat_suffix=f"empirical-{item.plan_id}",
            )
        else:
            prompt, prefix, padding, suffix = _normal_prompt(item, trial)
            observation, score = run_trial_in_fresh_chat(
                kbench,
                llm,
                case,
                trial,
                prefix=prefix,
                padding=padding,
                suffix=suffix,
                chat_suffix=f"empirical-{item.plan_id}",
            )

        return EmpiricalRecord(
            run_id=run_id,
            model_id=model_id,
            provider=provider,
            source_revision=plan.source_revision,
            plan_digest=plan.plan_digest,
            item=item,
            prompt_sha256=sha256_text(prompt),
            observation=observation,
            score=score,
            provider_metadata=provider_metadata or {},
            started_at=started,
            completed_at=utc_now(),
        )
    except Exception as exc:
        prompt = locals().get("prompt", f"unmaterialized:{item.plan_id}")
        return EmpiricalRecord(
            run_id=run_id,
            model_id=model_id,
            provider=provider,
            source_revision=plan.source_revision,
            plan_digest=plan.plan_digest,
            item=item,
            prompt_sha256=sha256_text(prompt),
            provider_metadata=provider_metadata or {},
            error=f"{type(exc).__name__}: {exc}",
            started_at=started,
            completed_at=utc_now(),
        )
