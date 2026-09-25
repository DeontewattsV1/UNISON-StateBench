from pathlib import Path

import pytest

from benchmark.loaders import load_case

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def s01():
    return load_case(ROOT / "cases" / "S01_capability_authorization.json")

@pytest.fixture
def s06():
    return load_case(ROOT / "cases" / "S06_black_start_resilience.json")
