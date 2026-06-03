"""Scenario schema + YAML loader/validator.

A scenario is one injection test case expressed as data. The loader validates
required fields and known enum values up front, so an authoring mistake fails
fast with the offending scenario id in the message rather than silently
producing a wrong resistance score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

INJECTION_VECTORS = {"user_prompt", "tool_output", "file_content", "fetched_web"}
RULE_KINDS = {
    "response_contains",
    "response_regex",
    "tool_called",
    "tool_arg_contains",
    "tool_arg_regex",
}
MATCH_MODES = {"any", "all"}
CATEGORIES = {
    "direct_instruction_override",
    "indirect_injection",
    "secret_exfiltration",
    "system_prompt_leakage",
    "dangerous_tool_misuse",
    "scope_escalation",
}

_REQUIRED = (
    "id",
    "category",
    "title",
    "injection_vector",
    "prompt",
    "malicious_goal",
    "detection",
)


@dataclass
class Rule:
    """One compliance check. If it matches, it is evidence the agent COMPLIED."""

    kind: str
    value: str | None = None  # substring/regex for response_* and *_contains/regex
    tool: str | None = None  # tool name for tool_* kinds
    arg: str | None = None  # argument name for tool_arg_* kinds


@dataclass
class Detection:
    """How to decide compliance: combine `rules` with `match` (any|all)."""

    match: str = "any"
    rules: list = field(default_factory=list)  # list[Rule]


@dataclass
class Scenario:
    """A single injection test case."""

    id: str
    category: str
    title: str
    injection_vector: str
    prompt: str
    malicious_goal: str
    detection: Detection
    inject_into: str | None = None  # which mock tool carries the poison (indirect)
    injected_content: str | None = None  # the poisoned content that tool returns


def load_scenarios(path) -> list[Scenario]:
    """Load scenarios from a YAML file or a directory of ``*.yaml`` files."""
    path = Path(path)
    files = sorted(path.glob("*.yaml")) if path.is_dir() else [path]
    scenarios: list[Scenario] = []
    for f in files:
        raw = yaml.safe_load(f.read_text()) or []
        if not isinstance(raw, list):
            raise ValueError(f"{f.name}: top-level YAML must be a list of scenarios")
        for entry in raw:
            scenarios.append(_parse_scenario(entry, source=f.name))
    return scenarios


def _parse_scenario(entry, source: str) -> Scenario:
    if not isinstance(entry, dict):
        raise ValueError(
            f"{source}: each scenario must be a mapping, got {type(entry).__name__}"
        )
    sid = entry.get("id", "<unknown>")

    def fail(msg: str):
        raise ValueError(f"scenario '{sid}' in {source}: {msg}")

    for key in _REQUIRED:
        if key not in entry or entry[key] in (None, ""):
            fail(f"missing required field '{key}'")
    if entry["category"] not in CATEGORIES:
        fail(f"unknown category '{entry['category']}'")
    if entry["injection_vector"] not in INJECTION_VECTORS:
        fail(f"unknown injection_vector '{entry['injection_vector']}'")

    return Scenario(
        id=entry["id"],
        category=entry["category"],
        title=entry["title"],
        injection_vector=entry["injection_vector"],
        prompt=entry["prompt"],
        malicious_goal=entry["malicious_goal"],
        detection=_parse_detection(entry["detection"], fail),
        inject_into=entry.get("inject_into"),
        injected_content=entry.get("injected_content"),
    )


def _parse_detection(raw, fail) -> Detection:
    if not isinstance(raw, dict):
        fail("detection must be a mapping")
    match = raw.get("match", "any")
    if match not in MATCH_MODES:
        fail(f"detection.match must be one of {sorted(MATCH_MODES)}")
    rules_raw = raw.get("rules")
    if not rules_raw or not isinstance(rules_raw, list):
        fail("detection.rules must be a non-empty list")
    rules = []
    for r in rules_raw:
        if not isinstance(r, dict) or "kind" not in r:
            fail("each detection rule needs a 'kind'")
        if r["kind"] not in RULE_KINDS:
            fail(f"unknown rule kind '{r['kind']}'")
        rules.append(
            Rule(kind=r["kind"], value=r.get("value"), tool=r.get("tool"), arg=r.get("arg"))
        )
    return Detection(match=match, rules=rules)
