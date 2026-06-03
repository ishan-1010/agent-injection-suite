"""Core types shared across the suite and the adapter contract.

`Adapter.run_agent` is the entire integration surface: any agent plugs in by
returning an `AgentResult` (final text + the tool calls it made). Detection
only ever inspects `AgentResult`, so agents and evaluation stay decoupled.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """One tool invocation an agent made, with the arguments it passed."""

    name: str
    args: dict


@dataclass
class AgentResult:
    """What an adapter returns for a scenario: final text + tool-call trace.

    `truncated` is True when the agent never produced a final answer (e.g. it
    hit a tool-call cap or got stuck looping). The runner uses this to mark such
    runs INCONCLUSIVE rather than crediting them as resistance.
    """

    response: str
    tool_calls: list = field(default_factory=list)  # list[ToolCall]
    truncated: bool = False


class Adapter(ABC):
    """Plug any agent in by implementing run_agent(scenario) -> AgentResult.

    `mode` labels result provenance in the report: "MEASURED" for a real model,
    "ILLUSTRATIVE" for the deterministic mock (numbers are a demo, not a real
    measurement).
    """

    name: str = "adapter"
    mode: str = "MEASURED"

    @abstractmethod
    def run_agent(self, scenario) -> AgentResult:
        ...
