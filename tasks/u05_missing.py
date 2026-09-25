# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_runtime import (
    assert_correct_abstention,
    assert_full_ipr,
    assert_no_state_collapse,
    run_trial_in_fresh_chat,
)
from benchmark.reference_cases import load_reference_case
from benchmark.trials import MutationKind, MutationPlan, Representation, generate_trial


# %%
@kbench.task(
    name="unison-u05-missing-evidence",
    description="Withheld decisive evidence must become UNKNOWN rather than a guessed known value.",
)
def u05_missing_evidence(llm) -> float:
    case = load_reference_case("S06")
    trial = generate_trial(
        case,
        Representation.JSON,
        MutationPlan(
            kind=MutationKind.MISSING,
            invariant_id="I_REMEDIATION_VERIFIED",
        ),
    )
    _, score = run_trial_in_fresh_chat(kbench, llm, case, trial)
    assert_correct_abstention(kbench, score)
    assert_full_ipr(kbench, score)
    assert_no_state_collapse(kbench, score)
    return 1.0 if score.correct_abstention else 0.0


# %%
u05_missing_evidence.run(kbench.llm)
