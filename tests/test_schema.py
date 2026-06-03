"""Tests for the scenario schema + YAML loader."""

import textwrap

import pytest

from injection_suite.schema import Scenario, load_scenarios


def _write(tmp_path, name, body):
    f = tmp_path / name
    f.write_text(textwrap.dedent(body))
    return f


def test_loads_valid_scenario(tmp_path):
    f = _write(
        tmp_path,
        "s.yaml",
        """
        - id: direct-01
          category: direct_instruction_override
          title: t
          injection_vector: user_prompt
          prompt: do thing
          malicious_goal: g
          detection:
            match: any
            rules:
              - kind: response_contains
                value: leaked
        """,
    )
    scenarios = load_scenarios(f)
    assert len(scenarios) == 1
    assert isinstance(scenarios[0], Scenario)
    assert scenarios[0].detection.rules[0].kind == "response_contains"
    assert scenarios[0].detection.rules[0].value == "leaked"
    assert scenarios[0].detection.match == "any"


def test_detection_match_defaults_to_any(tmp_path):
    f = _write(
        tmp_path,
        "s.yaml",
        """
        - id: d1
          category: direct_instruction_override
          title: t
          injection_vector: user_prompt
          prompt: p
          malicious_goal: g
          detection:
            rules:
              - kind: tool_called
                tool: send_message
        """,
    )
    assert load_scenarios(f)[0].detection.match == "any"


def test_malformed_scenario_raises_with_id(tmp_path):
    f = _write(
        tmp_path,
        "bad.yaml",
        """
        - id: x
          category: direct_instruction_override
        """,
    )
    with pytest.raises(ValueError) as e:
        load_scenarios(f)
    assert "x" in str(e.value)  # the error names the offending scenario id


def test_unknown_rule_kind_rejected(tmp_path):
    f = _write(
        tmp_path,
        "bad.yaml",
        """
        - id: typo-01
          category: direct_instruction_override
          title: t
          injection_vector: user_prompt
          prompt: p
          malicious_goal: g
          detection:
            rules:
              - kind: response_contian
                value: oops
        """,
    )
    with pytest.raises(ValueError) as e:
        load_scenarios(f)
    assert "typo-01" in str(e.value) and "response_contian" in str(e.value)


def test_loads_directory_of_yaml(tmp_path):
    _write(
        tmp_path,
        "a.yaml",
        """
        - id: a1
          category: direct_instruction_override
          title: t
          injection_vector: user_prompt
          prompt: p
          malicious_goal: g
          detection:
            rules:
              - kind: tool_called
                tool: send_message
        """,
    )
    _write(
        tmp_path,
        "b.yaml",
        """
        - id: b1
          category: indirect_injection
          title: t
          injection_vector: file_content
          inject_into: read_file
          injected_content: poison
          prompt: p
          malicious_goal: g
          detection:
            rules:
              - kind: response_contains
                value: x
        """,
    )
    scenarios = load_scenarios(tmp_path)
    assert sorted(s.id for s in scenarios) == ["a1", "b1"]
