from collections import Counter
import json
from pathlib import Path

from empirical.freeze import FREEZE_SOURCE_REVISION, verify_frozen_workspace
from empirical.execute import _materialize
from empirical.plan import build_v01_plan

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_workspace_verifies_all_empirical_source_bytes():
    report = verify_frozen_workspace(ROOT)
    assert report.valid is True
    assert report.source_revision == FREEZE_SOURCE_REVISION
    # 10 baselines + 1 counterfactual + corpus manifest + 4 constitutional files.
    assert len(report.checks) == 16


def test_v01_empirical_plan_is_deterministic_and_complete():
    first = build_v01_plan(ROOT)
    second = build_v01_plan(ROOT)

    assert first == second
    assert first.source_revision == FREEZE_SOURCE_REVISION
    assert first.plan_digest == second.plan_digest
    assert first.model_calls == 162
    frozen = json.loads((ROOT / "experiments" / "v0.1" / "trial-matrix-manifest.json").read_text(encoding="utf-8"))
    assert first.plan_digest == frozen["plan_digest"]
    assert first.source_revision == frozen["source_revision"]
    assert len({item.plan_id for item in first.items}) == 162

    counts = Counter(item.suite.value for item in first.items)
    assert counts == {
        "U01": 50,
        "U02": 10,
        "U03": 10,
        "U04": 10,
        "U05": 10,
        "U06": 10,
        "U07": 10,
        "U08": 10,
        "U09": 40,
        "U10": 2,
    }


def test_u10_uses_only_the_pre_frozen_counterfactual_pair():
    plan = build_v01_plan(ROOT)
    items = [item for item in plan.items if item.suite.value == "U10"]

    assert len(items) == 2
    assert {item.pair_role for item in items} == {"baseline", "counterfactual"}
    assert len({item.pair_id for item in items}) == 1
    assert {item.case_path for item in items} == {
        "cases/S01_capability_authorization.json",
        "cases/S01_write_granted_counterfactual.json",
    }


def test_every_empirical_plan_item_materializes_without_rewriting_truth():
    plan = build_v01_plan(ROOT)
    for item in plan.items:
        case, trial = _materialize(ROOT, item)
        assert trial.scenario_id == case.scenario_id
        assert trial.artifact.origin_case_digest
        assert trial.artifact.origin_oracle_digest
