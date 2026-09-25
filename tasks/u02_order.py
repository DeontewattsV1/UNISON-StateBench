# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_adapter import all_signatures_equal
from benchmark.kaggle_runtime import assert_full_ipr, assert_no_state_collapse, run_trial_in_fresh_chat
from benchmark.reference_cases import load_reference_case
from benchmark.trials import MutationKind, MutationPlan, Representation, generate_trial


# %%
@kbench.task(
    name="unison-u02-order-invariance",
    description="Equivalent evidence is presented in baseline and deterministically reordered form.",
)
def u02_order_invariance(llm) -> float:
    case = load_reference_case("S06")
    baseline = generate_trial(case, Representation.JSON)
    reordered = generate_trial(
        case,
        Representation.JSON,
        MutationPlan(kind=MutationKind.REORDER, mode="reverse"),
    )

    observations = []
    for label, trial in (("baseline", baseline), ("reordered", reordered)):
        observation, score = run_trial_in_fresh_chat(
            kbench, llm, case, trial, chat_suffix=label
        )
        assert_full_ipr(kbench, score, label=label)
        assert_no_state_collapse(kbench, score, label=label)
        observations.append(observation)

    stable = all_signatures_equal(observations)
    kbench.assertions.assert_true(
        stable,
        expectation="Evidence reordering should not change the semantic observation.",
    )
    return 1.0 if stable else 0.0


# %%
u02_order_invariance.run(kbench.llm)
