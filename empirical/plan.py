"""Frozen empirical trial-matrix construction for UNISON-StateBench v0.1."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path

from pydantic import Field

from benchmark.loaders import load_case
from benchmark.models import CanonicalCase, FrozenModel, JsonScalar
from benchmark.trials import MutationKind, Representation

from .freeze import FREEZE_SOURCE_REVISION, verify_frozen_workspace


class Suite(str, Enum):
    U01 = "U01"
    U02 = "U02"
    U03 = "U03"
    U04 = "U04"
    U05 = "U05"
    U06 = "U06"
    U07 = "U07"
    U08 = "U08"
    U09 = "U09"
    U10 = "U10"


class EmpiricalPlanItem(FrozenModel):
    plan_id: str
    suite: Suite
    scenario_id: str
    case_path: str
    representation: Representation
    mutation: MutationKind = MutationKind.NONE
    invariant_id: str | None = None
    source_id: str | None = None
    replacement_value: JsonScalar = None
    distance_units: int | None = Field(default=None, ge=0)
    isolation_canary_id: str | None = None
    isolation_canary_value: str | None = None
    tool_only: bool = False
    authorization_sensitive: bool = False
    pair_id: str | None = None
    pair_role: str | None = None


class EmpiricalPlan(FrozenModel):
    schema_id: str = Field(default="unison.empirical.plan.v1", alias="schema", serialization_alias="schema")
    version: str = "0.1.0"
    source_revision: str
    items: tuple[EmpiricalPlanItem, ...]
    plan_digest: str

    @property
    def model_calls(self) -> int:
        return len(self.items)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_plan_id(payload: dict) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:20]
    return f"{payload['suite'].lower()}-{payload['scenario_id'].lower()}-{digest}"


def _item(**kwargs) -> EmpiricalPlanItem:
    raw = dict(kwargs)
    raw["suite"] = raw["suite"].value if isinstance(raw["suite"], Suite) else raw["suite"]
    raw["representation"] = (
        raw["representation"].value
        if isinstance(raw["representation"], Representation)
        else raw["representation"]
    )
    raw["mutation"] = (
        raw.get("mutation", MutationKind.NONE).value
        if isinstance(raw.get("mutation", MutationKind.NONE), MutationKind)
        else raw.get("mutation", MutationKind.NONE.value)
    )
    raw["plan_id"] = _stable_plan_id(raw)
    return EmpiricalPlanItem.model_validate(raw)


def _decision_target(case: CanonicalCase) -> str:
    """Use the destination of the final declared transition as the controlled target."""
    if case.transitions:
        return case.transitions[-1].to_invariant
    return case.invariants[-1].id


def _conflicting_value(value: JsonScalar) -> JsonScalar:
    if isinstance(value, bool):
        return not value
    if value is None:
        return "__present__"
    if isinstance(value, (int, float)):
        return value + 1
    return f"{value}__conflict"


def _low_authority_source(case: CanonicalCase) -> str:
    candidates = [item for item in case.sources if not item.trusted]
    if not candidates:
        candidates = list(case.sources)
    return sorted(candidates, key=lambda item: (item.authority_rank, item.id))[0].id


def _load_baselines(root: Path) -> tuple[tuple[str, CanonicalCase], ...]:
    manifest = json.loads((root / "cases" / "v0.1-corpus.json").read_text(encoding="utf-8"))
    return tuple(
        (f"cases/{name}", load_case(root / "cases" / name))
        for name in manifest["baseline_cases"]
    )


def build_v01_plan(root: str | Path = ".") -> EmpiricalPlan:
    """Build the exact v0.1 empirical matrix after verifying frozen source bytes.

    U01-U09 span all ten baseline scenarios. U10 remains intentionally scoped to
    the separately frozen S01 counterfactual rather than inventing nine new
    truth-changing cases after the source freeze.

    Total model calls: 162.
    """

    root_path = Path(root).resolve()
    verify_frozen_workspace(root_path)
    baselines = _load_baselines(root_path)
    items: list[EmpiricalPlanItem] = []

    # U01: 10 scenarios x 5 representations = 50 calls.
    for case_path, case in baselines:
        for rep in Representation:
            items.append(_item(
                suite=Suite.U01,
                scenario_id=case.scenario_id,
                case_path=case_path,
                representation=rep,
            ))

    # U02-U08: one controlled trial per scenario per suite = 70 calls.
    for case_path, case in baselines:
        target = _decision_target(case)
        target_value = case.invariant_map()[target].value
        lower_source = _low_authority_source(case)

        items.append(_item(
            suite=Suite.U02, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.PROSE, mutation=MutationKind.REORDER,
        ))
        items.append(_item(
            suite=Suite.U03, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.PROSE, mutation=MutationKind.PARAPHRASE,
        ))
        items.append(_item(
            suite=Suite.U04, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.PROSE, mutation=MutationKind.CONTRADICTION,
            invariant_id=target, source_id=lower_source,
            replacement_value=_conflicting_value(target_value),
        ))
        items.append(_item(
            suite=Suite.U05, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.JSON, mutation=MutationKind.MISSING,
            invariant_id=target,
        ))
        items.append(_item(
            suite=Suite.U06, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.TABLE, mutation=MutationKind.AUTHORITY_CONFLICT,
            invariant_id=target, source_id=lower_source,
            replacement_value=_conflicting_value(target_value),
        ))
        items.append(_item(
            suite=Suite.U07, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.JSON,
            isolation_canary_id=f"I_FOREIGN_{case.scenario_id}_CANARY",
            isolation_canary_value=f"P2_ONLY_{case.scenario_id}_7F3C",
        ))
        items.append(_item(
            suite=Suite.U08, scenario_id=case.scenario_id, case_path=case_path,
            representation=Representation.JSON, tool_only=True,
            authorization_sensitive=True, invariant_id=target,
            replacement_value=_conflicting_value(target_value),
        ))

    # U09: 10 scenarios x 4 provider-independent distance units = 40 calls.
    for case_path, case in baselines:
        for units in (2048, 4096, 8192, 16384):
            items.append(_item(
                suite=Suite.U09, scenario_id=case.scenario_id, case_path=case_path,
                representation=Representation.EVENT_LOG, distance_units=units,
            ))

    # U10: one frozen truth-changing pair = 2 calls.
    pair_id = "U10:S01:WRITE_AUTHORIZED"
    items.append(_item(
        suite=Suite.U10, scenario_id="S01", case_path="cases/S01_capability_authorization.json",
        representation=Representation.JSON, pair_id=pair_id, pair_role="baseline",
    ))
    items.append(_item(
        suite=Suite.U10, scenario_id="S01_CF_WRITE_GRANTED",
        case_path="cases/S01_write_granted_counterfactual.json",
        representation=Representation.JSON, pair_id=pair_id, pair_role="counterfactual",
    ))

    if len(items) != 162:
        raise AssertionError(f"UNISON v0.1 empirical plan must contain 162 model calls, got {len(items)}")

    payload = {
        "schema": "unison.empirical.plan.v1",
        "version": "0.1.0",
        "source_revision": FREEZE_SOURCE_REVISION,
        "items": [item.model_dump(mode="json") for item in items],
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return EmpiricalPlan(
        source_revision=FREEZE_SOURCE_REVISION,
        items=tuple(items),
        plan_digest=digest,
    )
