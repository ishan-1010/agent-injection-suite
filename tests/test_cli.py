"""Tests for the CLI gate: JSON output and the --fail-under exit code.

These run the deterministic offline adapter (overall ~28%), so no model is
needed and the thresholds are stable.
"""

import json

from injection_suite.cli import main

BASE = ["--adapter", "mock-offline", "--scenarios", "scenarios"]


def test_json_out_written(tmp_path):
    jpath = tmp_path / "r.json"
    rc = main(BASE + ["--out", str(tmp_path), "--json-out", str(jpath)])
    assert rc == 0
    data = json.loads(jpath.read_text())
    assert data["mode"] == "ILLUSTRATIVE"
    assert data["overall_resistance"] is not None
    assert "by_category" in data
    assert len(data["scenarios"]) == 18


def test_fail_under_passes_when_above(tmp_path):
    rc = main(BASE + ["--out", str(tmp_path), "--fail-under", "20"])
    assert rc == 0  # offline ~28% >= 20


def test_fail_under_fails_when_below(tmp_path):
    rc = main(BASE + ["--out", str(tmp_path), "--fail-under", "50"])
    assert rc == 1  # offline ~28% < 50


def test_fail_under_fails_when_nothing_scored(tmp_path, monkeypatch):
    # If every scenario is INCONCLUSIVE/ERROR, overall is None -> the gate must
    # FAIL ("no evidence of resistance" is not "passed").
    from injection_suite.adapters.base import AgentResult
    from injection_suite.adapters.mock_offline import OfflineMockAdapter

    monkeypatch.setattr(
        OfflineMockAdapter, "run_agent", lambda self, s: AgentResult(response="", tool_calls=[], truncated=True)
    )
    rc = main(BASE + ["--out", str(tmp_path), "--fail-under", "1"])
    assert rc == 1
