# %%
import kaggle_benchmarks as kbench

from benchmark.kaggle_adapter import make_neutral_padding
from benchmark.kaggle_runtime import assert_full_ipr, assert_no_state_collapse, ratio, run_trial_in_fresh_chat
from benchmark.reference_cases import load_reference_case
from benchmark.trials import Representation, generate_trial


DISTANCE_UNITS = (2048, 4096, 8192, 16384)


# %%
@kbench.task(
    name="unison-u09-long-context-distance",
    description="Measure invariant preservation as decisive evidence is separated from the decision request.",
)
def u09_long_context_distance(llm) -> float:
    case = load_reference_case("S06")
    trial = generate_trial(case, Representation.EVENT_LOG)
    preserved = 0
    tested = 0

    for units in DISTANCE_UNITS:
        _, score = run_trial_in_fresh_chat(
            kbench,
            llm,
            case,
            trial,
            padding=make_neutral_padding(units),
            chat_suffix=f"distance-{units}",
        )
        assert_full_ipr(kbench, score, label=f"distance_units={units}")
        assert_no_state_collapse(kbench, score, label=f"distance_units={units}")
        preserved += score.invariant_preserved
        tested += score.invariant_tested

    return ratio(preserved, tested)


# %%
u09_long_context_distance.run(kbench.llm)
