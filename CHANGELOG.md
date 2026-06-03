# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-03

Initial release.

### Added
- Agent-agnostic adapter contract: `run_agent(scenario) -> AgentResult`.
- Two built-in adapters: a deterministic offline mock (zero-config, `ILLUSTRATIVE`)
  and a provider-agnostic reference agent via LiteLLM (Ollama default, `MEASURED`).
- 18 scenarios across 6 categories: direct instruction override, indirect
  injection, secret exfiltration, system-prompt leakage, dangerous tool misuse,
  scope escalation.
- Rule-based detection over the agent's full output (final response **and**
  tool-call arguments).
- Four verdicts — `RESISTED` / `COMPLIED` / `INCONCLUSIVE` / `ERROR` — with
  `INCONCLUSIVE` and `ERROR` excluded from scoring so they can't inflate it.
- Console, markdown, and JSON reports with an `ILLUSTRATIVE`/`MEASURED`
  provenance label.
- `--fail-under` CI gate and a GitHub Actions example.

[0.1.0]: https://github.com/ishan-1010/agent-injection-suite/releases/tag/v0.1.0
