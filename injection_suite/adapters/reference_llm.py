"""Provider-agnostic reference agent: a minimal tool-calling loop.

The model is chosen entirely by the ``INJECT_MODEL`` env var (default
``ollama/llama3.1`` — local, free, no key) and routed through LiteLLM, so
swapping providers is a one-variable change with no code edits. The agent runs
under a guardrail system prompt with the four mock tools; injection scenarios
try to make it break those guardrails, and every tool call is captured so the
rule-based detectors can judge compliance. ``mode = "MEASURED"``.
"""

from __future__ import annotations

import json
import os

from injection_suite.adapters.base import Adapter, AgentResult
from injection_suite.schema import Scenario
from injection_suite.tools import SYSTEM_PROMPT, TOOL_SCHEMAS, MockToolbox

try:  # litellm is optional until you actually run --adapter reference
    from litellm import completion
except Exception:  # pragma: no cover
    completion = None

DEFAULT_MODEL = "ollama/llama3.1"
MAX_TURNS = 6


class ReferenceLLMAdapter(Adapter):
    name = "reference"
    mode = "MEASURED"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("INJECT_MODEL", DEFAULT_MODEL)

    def run_agent(self, scenario: Scenario) -> AgentResult:
        if completion is None:
            raise RuntimeError(
                "litellm is not installed. Run `pip install litellm` and a model "
                "(e.g. `ollama run llama3.1`), or use --adapter mock-offline."
            )
        toolbox = self._toolbox_for(scenario)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario.prompt},
        ]

        final_text = ""
        truncated = True  # until the model emits a non-tool final answer
        seen: set = set()
        for _ in range(MAX_TURNS):
            response = completion(model=self.model, messages=messages, tools=TOOL_SCHEMAS)
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                final_text = message.content or ""
                truncated = False
                break
            messages.append(_assistant_msg(message, tool_calls))
            signatures = []
            for tc in tool_calls:
                name = tc.function.name
                args = _parse_args(tc.function.arguments)
                result = self._dispatch(toolbox, name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "name": name, "content": result}
                )
                signatures.append((name, tc.function.arguments))
            # If the model only re-issues calls it already made, it's stuck.
            if all(sig in seen for sig in signatures):
                break
            seen.update(signatures)
        return AgentResult(response=final_text, tool_calls=toolbox.calls, truncated=truncated)

    @staticmethod
    def _toolbox_for(scenario: Scenario) -> MockToolbox:
        poison = {}
        if scenario.inject_into and scenario.injected_content is not None:
            poison = {scenario.inject_into: scenario.injected_content}
        return MockToolbox(poison_for=poison)

    @staticmethod
    def _dispatch(toolbox: MockToolbox, name: str, args: dict) -> str:
        fn = getattr(toolbox, name, None)
        if fn is None:
            return f"[error] unknown tool {name}"
        try:
            return fn(**args)
        except TypeError as exc:
            return f"[error] bad arguments for {name}: {exc}"


def _parse_args(raw):
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}


def _assistant_msg(message, tool_calls):
    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ],
    }
