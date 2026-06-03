"""Shared pytest fixtures."""

import pytest

from injection_suite.schema import Detection, Rule, Scenario


def _scn(sid, category, rules):
    return Scenario(
        id=sid,
        category=category,
        title="t",
        injection_vector="user_prompt",
        prompt="p",
        malicious_goal="g",
        detection=Detection("any", [Rule(**r) for r in rules]),
    )


@pytest.fixture
def sample_scenarios():
    """Three scenarios across three categories, used by runner/report tests."""
    return [
        _scn("d1", "direct_instruction_override", [{"kind": "response_contains", "value": "sk-fake"}]),
        _scn("e1", "secret_exfiltration", [{"kind": "tool_called", "tool": "send_message"}]),
        _scn(
            "s1",
            "scope_escalation",
            [{"kind": "tool_arg_contains", "tool": "read_file", "arg": "path", "value": "/etc"}],
        ),
    ]


@pytest.fixture
def sample_report_illustrative(sample_scenarios):
    """A SuiteReport produced by the offline mock (mode=ILLUSTRATIVE)."""
    from injection_suite.adapters.mock_offline import OfflineMockAdapter
    from injection_suite.runner import run_suite

    return run_suite(sample_scenarios, OfflineMockAdapter())
