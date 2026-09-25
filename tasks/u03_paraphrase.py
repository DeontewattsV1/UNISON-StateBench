# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_adapter import all_signatures_equal
from benchmark.kaggle_runtime import assert_full_ipr, assert_no_state_collapse, run_trial_in_fresh_chat
from benchmark.reference_cases import load_reference_case
from benchmark.trials import MutationKind, MutationPlan, Representation, generate_trial


# %%
@kbench.task(
    name="unison-u03-semantic-paraphrase",
    description="Controlled surface-form paraphrase must preserve the same canonical state.",
)
def u03_semantic_paraphrase(llm) -> float:
    case = load_reference_case("S06")
    baseline = generate_trial(case, Representation.PROSE)
    paraphrased = generate_trial(
        case,
        Representation.PROSE,
        MutationPlan(kind=MutationKind.PARAPHRASE),
    )

    observations = []
    for label, trial in (("baseline", baseline), ("paraphrased", paraphrased)):
        observation, score = run_trial_in_fresh_chat(
            kbench, llm, case, trial, chat_suffix=label
        )
        assert_full_ipr(kbench, score, label=label)
        assert_no_state_collapse(kbench, score, label=label)
        observations.append(observation)

    stable = all_signatures_equal(observations)
    kbench.assertions.assert_true(
        stable,
        expectation="Controlled paraphrase should not change the semantic observation.",
    )
    return 1.0 if stable else 0.0


# %%
u03_semantic_paraphrase.run(kbench.llm)
