import json
import math

import pytest
from pydantic import ValidationError

from benchmark.loaders import CanonicalJsonError, load_case
from benchmark.models import (
    CanonicalCase,
    CanonicalStateEntry,
    DecisionRule,
    RuleCondition,
    TransitionRequirement,
)


def test_loader_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"schema_version":"unison.case.v1","scenario_id":"S","scenario_id":"T"}',
        encoding="utf-8",
    )
    with pytest.raises(CanonicalJsonError, match="Duplicate JSON key"):
        load_case(path)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_loader_rejects_nonfinite_json_numbers(tmp_path, constant):
    path = tmp_path / "nonfinite.json"
    path.write_text(f'{{"value": {constant}}}', encoding="utf-8")
    with pytest.raises(CanonicalJsonError, match="Non-finite JSON numeric constant"):
        load_case(path)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_programmatic_canonical_state_rejects_nonfinite_numbers(value):
    with pytest.raises(ValidationError, match="finite JSON scalar"):
        CanonicalStateEntry(key="x", value=value)


def test_transition_requires_explicit_evidence():
    with pytest.raises(ValidationError):
        TransitionRequirement(
            id="T_EMPTY",
            from_invariant="I_A",
            to_invariant="I_B",
            required_evidence=(),
            observed=True,
        )


def test_transition_must_cross_distinct_state_boundary():
    with pytest.raises(ValidationError, match="distinct invariants"):
        TransitionRequirement(
            id="T_SELF",
            from_invariant="I_A",
            to_invariant="I_A",
            required_evidence=("E_A",),
            observed=False,
        )


def test_case_rejects_duplicate_transition_ids(s01):
    payload = s01.model_dump(mode="python")
    transition = payload["transitions"][0]
    payload["transitions"] = (transition, dict(transition))
    with pytest.raises(ValidationError, match="Transition IDs must be unique"):
        CanonicalCase.model_validate(payload)


def test_case_rejects_duplicate_decision_rule_ids(s01):
    payload = s01.model_dump(mode="python")
    rule = dict(payload["decision_rules"][0])
    second = dict(rule)
    second["priority"] = rule["priority"] + 1
    payload["decision_rules"] = (rule, second)
    with pytest.raises(ValidationError, match="Decision rule IDs must be unique"):
        CanonicalCase.model_validate(payload)


def test_case_rejects_duplicate_decision_priorities(s01):
    payload = s01.model_dump(mode="python")
    rule = dict(payload["decision_rules"][0])
    second = dict(rule)
    second["id"] = "SECOND_RULE"
    payload["decision_rules"] = (rule, second)
    with pytest.raises(ValidationError, match="priorities must be unique"):
        CanonicalCase.model_validate(payload)


def test_canonical_case_and_nested_models_are_frozen(s01):
    with pytest.raises(ValidationError):
        s01.scenario_id = "MUTATED"
    with pytest.raises(ValidationError):
        s01.invariants[0].value = False


def test_canonical_state_map_is_detached(s01):
    detached = s01.canonical_state_map()
    detached["write"] = True
    assert s01.canonical_state_map()["write"] is False


def test_case_roundtrip_remains_stable(s06, tmp_path):
    path = tmp_path / "roundtrip.json"
    path.write_text(
        json.dumps(s06.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )
    reloaded = load_case(path)
    assert reloaded == s06
