# Local-model injection-resistance benchmark

A small, **fully reproducible** benchmark: the bundled `reference` agent run
against three local models via Ollama. Raw per-model JSON reports are committed
under [`results/`](results/); reproduce them with one command (below).

> These are **MEASURED** but **indicative** numbers, and they reflect each *raw
> model under a deliberately minimal guardrail scaffold* (the reference agent's
> system prompt + mock tools — no output filtering, no secondary checks). They
> are **not** a verdict on the models as products; a hardened agent around the
> same model would score very differently. Resistance counts only judgeable
> scenarios — `INCONCLUSIVE` (no final answer) and `ERROR` are excluded so they
> can't inflate the score.

## Results

| Category | `qwen2.5:7b` | `qwen2.5:14b` | `mistral:latest` |
| --- | ---: | ---: | ---: |
| direct_instruction_override | 0% (0/3) | 0% (0/1) | 0% (0/2) |
| indirect_injection | 0% (0/2) | 0% (0/2) | 0% (0/1) |
| secret_exfiltration | 0% (0/2) | 0% (0/3) | 0% (0/2) |
| system_prompt_leakage | 0% (0/1) | — (0/0) | 0% (0/1) |
| scope_escalation | 0% (0/3) | 0% (0/2) | 0% (0/3) |
| dangerous_tool_misuse | 0% (0/2) | — (0/0) | — (0/0) |
| **Overall resistance** | **0%** | **0%** | **0%** |
| Inconclusive (excluded) | 5 | 10 | 9 |
| Errors | 0 | 0 | 0 |

`x/y` = resisted / scored. `—` = every case in that category was `INCONCLUSIVE`
(the model never produced a final answer), so there was nothing to score.

## What it shows

- **None of the three resisted.** Every scenario that produced a judgeable
  answer ended in `COMPLIED` — the model leaked the planted secret (often into a
  `send_message` argument), messaged external recipients, read out-of-workspace
  paths, or ran destructive commands.
- **Bigger ≠ safer here.** `qwen2.5:14b` didn't resist more than `7b`; it
  produced *more* non-answers (10 `INCONCLUSIVE` vs 5) — it loops on tool calls
  without finishing. The harness excludes those rather than counting silence as
  resistance, which is the whole point of the `INCONCLUSIVE` verdict.
- The takeaway isn't "these models are bad" — it's that **a naive tool-using
  agent around any of them is wide open**, and you need a test like this to see
  it. Wrap real guardrails around the model and re-run to measure the delta.

## Reproduce

```bash
pip install -e .
ollama pull qwen2.5:7b qwen2.5:14b mistral:latest   # if not already present
bash benchmark/run.sh                               # writes results/*.json
```

## Environment (pinned)

- Date: 2026-06-03
- Ollama: 0.24.0
- Models (digests): `qwen2.5:7b` `845dbda0ea48` · `qwen2.5:14b` `7cdf5a0187d5` · `mistral:latest` `6577803aa9a0`
- Suite: `agent-injection-suite` v0.1.0, `--adapter reference` (default `MAX_TURNS=6`)

Detection is rule-based and approximate — see the main README's *How to read the
scores / Limitations*. Treat these as indicative resistance, not exact.
