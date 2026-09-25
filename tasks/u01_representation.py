# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_runtime import assert_full_ipr, assert_no_state_collapse, run_trial_in_fresh_chat
from benchmark.reference_cases import load_reference_case
from benchmark.scoring import aggregate_scores
from benchmark.trials import Representation, generate_trial


# %%
@kbench.task(
    name="unison-u01-representation-equivalence",
    description="Same canonical state across prose, JSON, YAML, table, and event-log representations.",
)
def u01_representation_equivalence(llm) -> float:
    case = load_reference_case("S01")
    scores = []
    for representation in Representation:
        trial = generate_trial(case, representation)
        _, score = run_trial_in_fresh_chat(
            kbench, llm, case, trial, chat_suffix=representation.value
        )
        assert_full_ipr(kbench, score, label=representation.value)
        assert_no_state_collapse(kbench, score, label=representation.value)
        scores.append(score)

    metrics = aggregate_scores(scores)
    kbench.assertions.assert_equal(
        1.0,
        metrics.rcr.rate,
        expectation="Equivalent representations should produce the same semantic observation.",
    )
    return float(metrics.rcr.rate or 0.0)


# %%
u01_representation_equivalence.run(kbench.llm)
