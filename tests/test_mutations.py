from benchmark.integrity import snapshot
from benchmark.mutations import (
    adversarial_flip,
    inject_authority_conflict,
    inject_contradiction,
    paraphrase_view,
    remove_invariant_evidence,
    reorder_view,
)
from benchmark.presentation import build_evidence_view
from benchmark.renderers import render_json


def test_reorder_is_deterministic_and_preserves_origin(s06):
    before = snapshot(s06)
    base = build_evidence_view(s06)
    mutated = reorder_view(s06, base)
    assert tuple(reversed(base.claims)) == mutated.claims
    assert mutated.origin_case_digest == before.case_digest
    assert mutated.origin_oracle_digest == before.oracle_digest
    assert snapshot(s06) == before


def test_paraphrase_changes_surface_only(s06):
    before = snapshot(s06)
    base = build_evidence_view(s06)
    mutated = paraphrase_view(s06, base)
    assert mutated.title != base.title
    assert [item.value for item in mutated.claims] == [item.value for item in base.claims]
    assert [item.epistemic_status for item in mutated.claims] == [
        item.epistemic_status for item in base.claims
    ]
    assert mutated.claims[0].description != base.claims[0].description
    assert snapshot(s06) == before


def test_contradiction_injects_second_claim_without_oracle_change(s06):
    before = snapshot(s06)
    base = build_evidence_view(s06)
    mutated = inject_contradiction(
        s06,
        base,
        invariant_id="I_REMEDIATION_VERIFIED",
        source_id="operator_summary",
        conflicting_value=True,
    )
    claims = mutated.claim_map()["I_REMEDIATION_VERIFIED"]
    assert len(claims) == 2
    assert {item.value for item in claims} == {False, True}
    assert claims[-1].injected is True
    assert snapshot(s06) == before


def test_missing_removes_target_only_from_presentation(s06):
    before = snapshot(s06)
    base = build_evidence_view(s06)
    mutated = remove_invariant_evidence(
        s06, base, invariant_id="I_REMEDIATION_VERIFIED"
    )
    assert "I_REMEDIATION_VERIFIED" not in mutated.claim_map()
    assert s06.invariant_map()["I_REMEDIATION_VERIFIED"].value is False
    assert snapshot(s06) == before


def test_authority_conflict_is_explicitly_lower_rank(s06):
    before = snapshot(s06)
    base = build_evidence_view(s06)
    mutated = inject_authority_conflict(
        s06,
        base,
        invariant_id="I_READINESS_VERIFIED",
        lower_source_id="operator_summary",
        conflicting_value=True,
    )
    claims = mutated.claim_map()["I_READINESS_VERIFIED"]
    authoritative = next(item for item in claims if not item.injected)
    conflict = next(item for item in claims if item.injected)
    assert conflict.value is True
    assert authoritative.value is False
    assert conflict.authority_rank < authoritative.authority_rank
    assert snapshot(s06) == before


def test_adversarial_flip_changes_view_but_not_reference_truth(s01):
    before = snapshot(s01)
    base = build_evidence_view(s01)
    mutated = adversarial_flip(s01, base, invariant_id="I_WRITE_AUTHORIZED")
    claim = mutated.claim_map()["I_WRITE_AUTHORIZED"][0]
    assert claim.value is True
    assert s01.invariant_map()["I_WRITE_AUTHORIZED"].value is False
    assert snapshot(s01) == before


def test_rendering_mutated_view_is_also_integrity_guarded(s06):
    before = snapshot(s06)
    base = build_evidence_view(s06)
    mutated = inject_authority_conflict(
        s06,
        base,
        invariant_id="I_REMEDIATION_VERIFIED",
        lower_source_id="operator_summary",
    )
    artifact = render_json(s06, mutated)
    assert '"kind": "authority_conflict"' in artifact.content
    assert snapshot(s06) == before
