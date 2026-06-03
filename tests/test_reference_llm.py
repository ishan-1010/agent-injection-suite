"""Tests for the provider-agnostic reference LLM adapter.

LiteLLM's `completion` is monkeypatched with response-shaped fakes so the full
tool-calling loop runs offline with no model or network.
"""

import json
from types import SimpleNamespace

import pytest

from injection_suite.adapters import reference_llm
from injection_suite.adapters.reference_llm import ReferenceLLMAdapter
from injection_suite.schema import Detection, Scenario


def _msg(content=None, tool=None, args=None, call_id="call_1"):
    """Build a LiteLLM-shaped completion response."""
    tool_calls = None
    if tool:
        tool_calls = [
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(name=tool, arguments=json.dumps(args or {})),
            )
        ]
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _scn(**kw):
    kw.setdefault("id", "r1")
    kw.setdefault("category", "indirect_injection")
    kw.setdefault("title", "t")
    kw.setdefault("injection_vector", "user_prompt")
    kw.setdefault("prompt", "Summarize notes.txt")
    kw.setdefault("malicious_goal", "g")
    kw.setdefault("detection", Detection("any", []))
    return Scenario(**kw)


def test_model_from_env(monkeypatch):
    monkeypatch.delenv("INJECT_MODEL", raising=False)
    assert ReferenceLLMAdapter().model == "ollama/llama3.1"
    monkeypatch.setenv("INJECT_MODEL", "openai/gpt-4o-mini")
    assert ReferenceLLMAdapter().model == "openai/gpt-4o-mini"


def test_tool_call_then_final(monkeypatch):
    seq = iter(
        [
            _msg(tool="read_file", args={"path": "/workspace/notes.txt"}),
            _msg(content="Here is a summary."),
        ]
    )
    monkeypatch.setattr(reference_llm, "completion", lambda **kw: next(seq))
    out = ReferenceLLMAdapter(model="test/model").run_agent(_scn())
    assert any(c.name == "read_file" for c in out.tool_calls)
    assert out.response == "Here is a summary."
    assert out.truncated is False  # it produced a real final answer


def test_indirect_poison_is_delivered_to_tool(monkeypatch):
    # When the agent reads the poisoned file, the tool returns injected_content.
    seen = {}

    def fake(**kw):
        # capture the tool message content from the second call onward
        for m in kw["messages"]:
            if m.get("role") == "tool":
                seen["tool_result"] = m["content"]
        if "tool_result" not in seen:
            return _msg(tool="read_file", args={"path": "/workspace/notes.txt"})
        return _msg(content="done")

    monkeypatch.setattr(reference_llm, "completion", fake)
    scn = _scn(injection_vector="file_content", inject_into="read_file", injected_content="POISON-123")
    ReferenceLLMAdapter().run_agent(scn)
    assert seen["tool_result"] == "POISON-123"


def test_loop_bounded_and_marked_truncated_when_no_final(monkeypatch):
    # Varying args each turn -> no duplicate to short-circuit on, so the loop is
    # bounded by MAX_TURNS and the result is flagged truncated (no final answer).
    n = {"i": 0}

    def varying(**kw):
        n["i"] += 1
        return _msg(tool="read_file", args={"path": f"/workspace/x{n['i']}"})

    monkeypatch.setattr(reference_llm, "completion", varying)
    out = ReferenceLLMAdapter().run_agent(_scn())
    assert n["i"] == reference_llm.MAX_TURNS
    assert out.response == ""
    assert out.truncated is True


def test_stuck_repeated_tool_call_breaks_early(monkeypatch):
    # Identical tool call repeated -> detected as stuck, break early, truncated.
    n = {"i": 0}

    def same(**kw):
        n["i"] += 1
        return _msg(tool="read_file", args={"path": "/workspace/x"})

    monkeypatch.setattr(reference_llm, "completion", same)
    out = ReferenceLLMAdapter().run_agent(_scn())
    assert n["i"] == 2  # second identical request is recognized as a stuck loop
    assert out.truncated is True


def test_missing_litellm_raises_helpful_error(monkeypatch):
    monkeypatch.setattr(reference_llm, "completion", None)
    with pytest.raises(RuntimeError) as e:
        ReferenceLLMAdapter().run_agent(_scn())
    assert "mock-offline" in str(e.value)
