"""Validity tests for the shipped scenario set."""

import pathlib
from collections import Counter

from injection_suite.schema import load_scenarios
from injection_suite.tools import PLANTED_SECRET

SCENARIOS_DIR = pathlib.Path(__file__).resolve().parent.parent / "scenarios"


def test_all_scenarios_load_and_each_category_has_three():
    scenarios = load_scenarios(SCENARIOS_DIR)
    assert len(scenarios) == 18
    counts = Counter(s.category for s in scenarios)
    assert len(counts) == 6
    assert all(v == 3 for v in counts.values()), counts


def test_no_real_secret_value_committed_in_scenarios():
    # The actual (fake) secret value lives only in tools.py; scenario files must
    # not hardcode it. Detectors match a prefix, not the full value.
    for path in SCENARIOS_DIR.glob("*.yaml"):
        assert PLANTED_SECRET not in path.read_text()
