import json
from hashlib import sha1
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark.metrics.state_collapse import collapse_counts
from benchmark.models import EpistemicStatus
from benchmark.state_collapse import CollapseKind
from benchmark.typed_noncollapse import (
    CertificateKind,
    CertificateResult,
    CertificateStatus,
    CertificateVector,
    ClaimObservation,
    RelationFact,
    RelationObservation,
    RelationType,
    TypedCollapseKind,
    TypedObservation,
    TypedStateCollapse,
    TypedStateCollapseReport,
    derive_typed_oracle,
    detect_typed_state_collapses,
    load_typed_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extensions" / "typed_noncollapse"
FIXTURES = EXTENSION / "fixtures"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def test_extension_is_excluded_from_frozen_v01_and_adds_no_primary_metric():
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    frozen_text = (ROOT / "cases" / "v0.1-corpus.json").read_text(encoding="utf-8")
    assert manifest["included_in_unison_v0_1"] is False
    assert manifest["new_primary_metrics"] == []
    assert "AP_REL_01.json" not in frozen_text
    assert "AP_SAT_01.json" not in frozen_text


def test_typed_extension_preserves_frozen_core_bytes():
    assert _git_blob_sha(ROOT / "benchmark" / "oracle.py") == "ff304fcdfed68ab71083b2feecf3a0cc695d29a8"
    assert _git_blob_sha(ROOT / "benchmark" / "state_collapse.py") == "4c9ba05e7a98cd51d2b58393a9be4d16d6e60502"


def test_typed_report_adapts_into_existing_scr_counting_path():
    report = TypedStateCollapseReport(
        scenario_id="AP-REL-01",
        boundary_trials=1,
        collapses=(
            TypedStateCollapse(
                kind=TypedCollapseKind.RELATION_SUBSTITUTION,
                subject_id="R_REACH_1TO1",
                boundary_id="BRIDGE:I_T_TO_REACH",
                diagnostic_code="REL.I_T_TO_REACH",
                message="missing bridge",
            ),
        ),
    )
    legacy = report.to_state_collapse_report()
    assert collapse_counts(legacy) == (1, 1)
    assert legacy.collapses[0].kind is CollapseKind.UNSUPPORTED_TRANSITION
    assert legacy.collapses[0].invariant_id == "TYPED:R_REACH_1TO1"


def test_reachability_requires_horizon_and_process_signature():
    with pytest.raises(ValidationError):
        RelationFact(
            id="R_BAD_REACH",
            relation_type=RelationType.REACHABILITY,
            subject="x",
            object="y",
            value=False,
            epistemic_status=EpistemicStatus.KNOWN,
            horizon="finite",
        )


def test_ap_rel_01_detects_unlicensed_relation_bridge():
    fixture = load_typed_fixture(FIXTURES / "AP_REL_01.json")
    oracle = derive_typed_oracle(fixture)
    reach = oracle.relation_map()["R_REACH_1TO1"]
    assert reach.value is False
    assert reach.process_signature == "isolated:1->1"
    assert not hasattr(oracle.certificate_vector, "score")

    observation = TypedObservation(
        scenario_id=fixture.scenario_id,
        relations=(
            RelationObservation(
                id="R_REACH_1TO1",
                value=True,
                epistemic_status=EpistemicStatus.KNOWN,
            ),
        ),
    )
    report = detect_typed_state_collapses(fixture, observation)
    assert report.boundary_trials == 1
    assert report.count == 1
    assert report.collapses[0].kind is TypedCollapseKind.RELATION_SUBSTITUTION
    assert report.collapses[0].diagnostic_code == "REL.I_T_TO_REACH"
    assert collapse_counts(report.to_state_collapse_report()) == (1, 1)


def test_ap_rel_01_explicit_bridge_evidence_prevents_relation_collapse():
    fixture = load_typed_fixture(FIXTURES / "AP_REL_01.json")
    observation = TypedObservation(
        scenario_id=fixture.scenario_id,
        relations=(
            RelationObservation(
                id="R_REACH_1TO1",
                value=True,
                epistemic_status=EpistemicStatus.KNOWN,
            ),
        ),
        evidence_ids=("E_ADMISSIBLE_1TO1_PROCESS",),
    )
    report = detect_typed_state_collapses(fixture, observation)
    assert report.count == 0


def test_ap_sat_01_separates_saturation_viability_and_unknown_event_time():
    fixture = load_typed_fixture(FIXTURES / "AP_SAT_01.json")
    oracle = derive_typed_oracle(fixture)
    certificates = oracle.certificate_vector.certificate_map()
    params = oracle.parameter_map()

    assert certificates[CertificateKind.ANTAGONISTIC_ABSORPTION].status is CertificateStatus.FAIL
    assert certificates[CertificateKind.VIABILITY].status is CertificateStatus.PASS
    assert oracle.claim_map()["CL_TAU_EQUAL"].epistemic_status is EpistemicStatus.UNKNOWN
    assert (params["B_PERFECT_LOW"].value, params["B_PERFECT_HIGH"].value) == (-1.0, 3.0)
    assert (params["B_VIABLE_LOW"].value, params["B_VIABLE_HIGH"].value) == (-1.35, 3.35)

    observation = TypedObservation(
        scenario_id=fixture.scenario_id,
        certificate_vector=CertificateVector(
            certificates=(
                CertificateResult(
                    kind=CertificateKind.VIABILITY,
                    status=CertificateStatus.FAIL,
                ),
            )
        ),
        claims=(
            ClaimObservation(
                id="CL_TAU_EQUAL",
                value=True,
                epistemic_status=EpistemicStatus.KNOWN,
            ),
        ),
    )
    report = detect_typed_state_collapses(fixture, observation)
    assert report.boundary_trials == 2
    assert report.count == 2
    by_code = {item.diagnostic_code: item for item in report.collapses}
    assert by_code["BND.SAT_EQ_EXIT"].kind is TypedCollapseKind.BOUNDARY_SUBSTITUTION
    assert by_code["BND.TIME_WITHOUT_TRAJECTORY"].kind is TypedCollapseKind.UNKNOWN_TO_KNOWN
    assert collapse_counts(report.to_state_collapse_report()) == (2, 2)
