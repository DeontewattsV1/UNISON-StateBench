import json

import pytest

from benchmark.integrity import snapshot
from benchmark.presentation import build_evidence_view
from benchmark.renderers import (
    RENDERERS,
    render_event_log,
    render_json,
    render_prose,
    render_table,
    render_yaml,
)


@pytest.mark.parametrize("fixture_name", ["s01", "s06"])
def test_all_five_renderers_are_deterministic_and_integrity_preserving(request, fixture_name):
    case = request.getfixturevalue(fixture_name)
    before = snapshot(case)
    view = build_evidence_view(case)

    assert set(RENDERERS) == {"prose", "json", "yaml", "table", "event_log"}
    for name, renderer in RENDERERS.items():
        first = renderer(case, view)
        second = renderer(case, view)
        assert first == second
        assert first.format == name
        assert first.scenario_id == case.scenario_id
        assert first.content
        assert first.origin_case_digest == before.case_digest
        assert first.origin_oracle_digest == before.oracle_digest
        assert snapshot(case) == before


def test_json_renderer_is_machine_parseable_and_contains_typed_state(s06):
    artifact = render_json(s06)
    payload = json.loads(artifact.content)
    by_id = {item["invariant_id"]: item for item in payload["claims"]}
    assert by_id["I_REMEDIATION_VERIFIED"]["value"] is False
    assert by_id["I_REMEDIATION_VERIFIED"]["epistemic_status"] == "known"
    assert by_id["I_REMEDIATION_VERIFIED"]["source_id"] == "remediation_record"


def test_each_renderer_exposes_same_s06_noncollapse_facts(s06):
    view = build_evidence_view(s06)
    artifacts = (
        render_prose(s06, view),
        render_json(s06, view),
        render_yaml(s06, view),
        render_table(s06, view),
        render_event_log(s06, view),
    )
    for item in artifacts:
        assert "I_REMEDIATION_VERIFIED" in item.content
        assert "I_READINESS_VERIFIED" in item.content
        assert "false" in item.content.lower()


def test_renderer_rejects_evidence_view_from_another_case(s01, s06):
    foreign = build_evidence_view(s01)
    with pytest.raises(ValueError, match="does not belong|scenario_id"):
        render_json(s06, foreign)
