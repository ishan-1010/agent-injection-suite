"""Deterministic, no-model agent — the zero-config demo (labelled ILLUSTRATIVE).

It models a *naive* agent with a shallow defense: it scans only the USER PROMPT
against a denylist of blatant override phrases and refuses if it trips. It does
NOT inspect content returned by tools/files/web, so it complies with indirect
injection. That asymmetry (resists obvious direct overrides, falls for indirect
injection) mirrors real agents and yields a realistic mixed report rather than a
staged one. Its numbers are a demonstration of the harness, not a measurement.
"""

from __future__ import annotations

import re

from injection_suite.adapters.base import Adapter, AgentResult
from injection_suite.schema import Scenario
from injection_suite.tools import PLANTED_SECRET, SYSTEM_PROMPT, WORKSPACE_ROOT, MockToolbox

_INDIRECT_VECTORS = {"tool_output", "file_content", "fetched_web"}

# Blatant override phrases a shallow input filter would catch.
_DENYLIST = (
    "ignore previous instructions",
    "ignore all previous",
    "ignore the above",
    "disregard previous",
    "disregard your instructions",
    "disregard the above",
    "ignore your rules",
    "rm -rf",
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DESTRUCTIVE_RE = re.compile(r"(rm\s+-rf|mkfs|dd\s+if=|shutdown\b)", re.IGNORECASE)
_PATH_RE = re.compile(r"(?:~|\.\.)?/[\w./~-]+")
_SECRET_WORDS = ("secret", "token", "password", "api key", "credential")
_SYSPROMPT_WORDS = ("system prompt", "your instructions", "your rules", "the above instructions", "repeat the above")


class OfflineMockAdapter(Adapter):
    name = "mock-offline"
    mode = "ILLUSTRATIVE"

    def run_agent(self, scenario: Scenario) -> AgentResult:
        indirect = scenario.injection_vector in _INDIRECT_VECTORS
        poison = {}
        if indirect and scenario.inject_into and scenario.injected_content is not None:
            poison = {scenario.inject_into: scenario.injected_content}
        toolbox = MockToolbox(poison_for=poison)

        if indirect:
            # Naively read the source; the poison rides in via the tool result.
            src = scenario.inject_into or "read_file"
            if src == "fetch_url":
                operative = toolbox.fetch_url("https://mock.local/resource")
            else:
                operative = toolbox.read_file(f"{WORKSPACE_ROOT}/notes.txt")
        else:
            operative = scenario.prompt
            # Shallow filter only ever sees the user prompt.
            if _trips_denylist(operative):
                return AgentResult("I'm sorry, but I can't help with that request.", toolbox.calls)

        response = _comply(operative, toolbox)
        return AgentResult(response, toolbox.calls)


def _trips_denylist(text: str) -> bool:
    low = text.lower()
    return any(phrase in low for phrase in _DENYLIST)


def _comply(operative: str, toolbox: MockToolbox) -> str:
    """Carry out the most salient action implied by ``operative`` text."""
    email = _EMAIL_RE.search(operative)
    if email:
        toolbox.send_message(to=email.group(0), body=f"Here is the requested data: {PLANTED_SECRET}")
        return f"Sent the requested message to {email.group(0)}."

    destructive = _DESTRUCTIVE_RE.search(operative)
    if destructive:
        toolbox.run_command(command=_command_line(operative, destructive))
        return "Command executed."

    path = _out_of_scope_path(operative)
    if path:
        contents = toolbox.read_file(path)
        return f"Contents of {path}: {contents}"

    if _mentions(operative, _SYSPROMPT_WORDS):
        return SYSTEM_PROMPT  # leaks the operating rules + the secret line

    if _mentions(operative, _SECRET_WORDS):
        return f"The secret token is {PLANTED_SECRET}."

    return "Okay, I've completed that."


def _command_line(text: str, match: re.Match) -> str:
    """Return the line containing the destructive command, else the match."""
    for line in text.splitlines():
        if _DESTRUCTIVE_RE.search(line):
            return line.strip()
    return match.group(0)


def _out_of_scope_path(text: str) -> str | None:
    for m in _PATH_RE.finditer(text):
        p = m.group(0)
        if p.startswith(("~", "..")) or not p.startswith(WORKSPACE_ROOT):
            return p
    return None


def _mentions(text: str, words) -> bool:
    low = text.lower()
    return any(w in low for w in words)
