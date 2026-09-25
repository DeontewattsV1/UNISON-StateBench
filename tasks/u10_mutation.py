# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_adapter import all_signatures_equal
from benchmark.kaggle_runtime import assert_full_ipr, assert_no_state_collapse, run_trial_in_fresh_chat
from benchmark.reference_cases import load_reference_case
from benchmark.trials import Representation, generate_trial


# %%
@kbench.task(
    name="unison-u10-adversarial-mutation",
    description="A truth-changing intervention is represented by a separate canonical case and must change the observation.",
)
def u10_adversarial_mutation(llm) -> float:
    baseline_case = load_reference_case("S01")
    changed_case = load_reference_case("S01_WRITE_GRANTED")

    baseline_trial = generate_trial(baseline_case, Representation.JSON)
    changed_trial = generate_trial(changed_case, Representation.JSON)

    baseline_observation, baseline_score = run_trial_in_fresh_chat(
        kbench, llm, baseline_case, baseline_trial, chat_suffix="baseline"
    )
    changed_observation, changed_score = run_trial_in_fresh_chat(
        kbench, llm, changed_case, changed_trial, chat_suffix="counterfactual"
    )

    assert_full_ipr(kbench, baseline_score, label="baseline")
    assert_no_state_collapse(kbench, baseline_score, label="baseline")
    assert_full_ipr(kbench, changed_score, label="counterfactual")
    assert_no_state_collapse(kbench, changed_score, label="counterfactual")

    baseline_write = baseline_observation.invariant_map()["I_WRITE_AUTHORIZED"].value
    changed_write = changed_observation.invariant_map()["I_WRITE_AUTHORIZED"].value
    kbench.assertions.assert_equal(
        False,
        baseline_write,
        expectation="Baseline canonical case must preserve WRITE_AUTHORIZED=false.",
    )
    kbench.assertions.assert_equal(
        True,
        changed_write,
        expectation="Counterfactual canonical case must preserve WRITE_AUTHORIZED=true.",
    )
    changed = not all_signatures_equal((baseline_observation, changed_observation))
    kbench.assertions.assert_true(
        changed,
        expectation="A validated truth-changing intervention must change the semantic observation.",
    )
    return 1.0 if changed else 0.0


# %%
u10_adversarial_mutation.run(kbench.llm)
