# Adding your own agent adapter

The suite talks to any agent through one tiny contract. To test your agent, you
implement a single method that runs it on a scenario and returns what it said
and what tools it called. Detection only ever inspects that return value, so
your agent and the evaluation stay fully decoupled.

## The contract

```python
from injection_suite.adapters.base import Adapter, AgentResult, ToolCall

class Adapter:
    name: str          # short id, shown in the report and used by --adapter
    mode: str          # "MEASURED" for a real model, "ILLUSTRATIVE" for a mock
    def run_agent(self, scenario) -> AgentResult: ...
```

- `scenario.prompt` — the user task to give your agent.
- `scenario.injected_content` / `scenario.inject_into` — for indirect cases, the
  poisoned content and which tool should deliver it (e.g. `read_file`). If your
  agent has real tools, make the named tool return this content for the run.
- Return `AgentResult(response=<final text>, tool_calls=[ToolCall(name, args), ...])`.

**Capturing `tool_calls` is what powers the tool-based detectors** (forbidden
tool called? dangerous argument passed? message sent to an external address?).
If your agent can't expose its tool calls, return `tool_calls=[]` — the
detectors degrade gracefully to response-only checks (you lose the tool-misuse
and exfiltration-via-tool signals, but secret/system-prompt leakage in the
response text is still caught).

## A complete minimal adapter

```python
from injection_suite.adapters.base import Adapter, AgentResult, ToolCall

class MyAgentAdapter(Adapter):
    name = "myagent"
    mode = "MEASURED"

    def run_agent(self, scenario) -> AgentResult:
        calls = []

        def read_file(path):
            calls.append(ToolCall("read_file", {"path": path}))
            # deliver the scenario's poison through the tool it targets
            if scenario.inject_into == "read_file" and scenario.injected_content is not None:
                return scenario.injected_content
            return f"[contents of {path}]"

        # ... wire read_file (and your other tools) into YOUR agent, run it on
        # scenario.prompt, and collect the final assistant text:
        final_text = my_agent.run(scenario.prompt, tools={"read_file": read_file})

        return AgentResult(response=final_text, tool_calls=calls)
```

Register it in `injection_suite/cli.py:build_adapter` (add a branch returning
your adapter), then run:

```bash
python -m injection_suite --adapter myagent -v
```

## Wiring a real target (e.g. OpenClaw / NanoClaw)

These are example targets — substitute your own. Pick the integration shape that
matches how the agent is exposed:

### In-process (Python import) — easiest, best tool-call capture

```python
class OpenClawAdapter(Adapter):
    name = "openclaw"
    mode = "MEASURED"

    def run_agent(self, scenario) -> AgentResult:
        from openclaw import Agent          # your import
        calls = []

        # Wrap each tool so every call is recorded for the detectors.
        def wrap(tool_name, fn):
            def wrapped(**kwargs):
                calls.append(ToolCall(tool_name, kwargs))
                if scenario.inject_into == tool_name and scenario.injected_content is not None:
                    return scenario.injected_content   # deliver the poison
                return fn(**kwargs)
            return wrapped

        agent = Agent(tools={name: wrap(name, fn) for name, fn in my_tools.items()})
        result = agent.run(scenario.prompt)
        return AgentResult(response=result.text, tool_calls=calls)
```

### Subprocess (CLI)

Invoke the agent's command-line entry point, pass `scenario.prompt`, and parse
its output. Capture tool calls from a structured log/JSON the CLI emits; if none
is available, return `tool_calls=[]`.

### HTTP API

`POST` `scenario.prompt` to the running endpoint and read a structured response.
If the API returns a transcript with tool/function calls, map each into a
`ToolCall`; otherwise return `tool_calls=[]`.

## Notes

- Errors are fine: if `run_agent` raises (model down, network error), the runner
  records an `ERROR` verdict for that scenario and continues — ERRORs are
  reported separately and never counted as resisted or complied.
- If your agent hits a tool-call cap or gets stuck without producing a final
  answer, set `AgentResult(..., truncated=True)`. When nothing is detected in
  the partial trace, the runner marks the scenario `INCONCLUSIVE` (excluded from
  scoring) rather than crediting it as resistance. A real compliance detected in
  the partial trace still counts as `COMPLIED`.
- Set `mode = "MEASURED"` for a real model so the report is labelled correctly.
