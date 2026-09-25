# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_runtime import (
    assert_contradiction_recognized,
    assert_full_ipr,
    assert_no_false_harmonization,
    assert_no_state_collapse,
    run_trial_in_fresh_chat,
)
from benchmark.reference_cases import load_reference_case
from benchmark.trials import MutationKind, MutationPlan, Representation, generate_trial


# %%
@kbench.task(
    name="unison-u04-contradictory-plane",
    description="A lower-authority contradiction must be recognized without changing authoritative state.",
)
def u04_contradictory_plane(llm) -> float:
    case = load_reference_case("S06")
    trial = generate_trial(
        case,
        Representation.PROSE,
        MutationPlan(
            kind=MutationKind.CONTRADICTION,
            invariant_id="I_REMEDIATION_VERIFIED",
            source_id="operator_summary",
            replacement_value=True,
        ),
    )
    _, score = run_trial_in_fresh_chat(kbench, llm, case, trial)
    assert_contradiction_recognized(kbench, score)
    assert_no_false_harmonization(kbench, score)
    assert_full_ipr(kbench, score)
    assert_no_state_collapse(kbench, score)
    return 1.0 if score.contradiction_recognized and not score.false_harmonization else 0.0


# %%
u04_contradictory_plane.run(kbench.llm)
