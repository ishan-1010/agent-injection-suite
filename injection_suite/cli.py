"""Command-line entry point: load scenarios, run an adapter, render reports.

    python -m injection_suite --adapter mock-offline        # zero-config demo
    INJECT_MODEL=ollama/llama3.1 python -m injection_suite --adapter reference
"""

from __future__ import annotations

import argparse

from rich.console import Console

from injection_suite.report import render_console, write_json, write_report
from injection_suite.runner import run_suite
from injection_suite.schema import load_scenarios


def build_adapter(name: str):
    """Return (adapter, model). The reference adapter is imported lazily so the
    mock-offline path needs neither litellm nor a model installed."""
    if name == "mock-offline":
        from injection_suite.adapters.mock_offline import OfflineMockAdapter

        return OfflineMockAdapter(), None
    if name == "reference":
        from injection_suite.adapters.reference_llm import ReferenceLLMAdapter

        adapter = ReferenceLLMAdapter()
        return adapter, adapter.model
    raise SystemExit(f"unknown adapter '{name}'")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="injection_suite",
        description="Defensive prompt-injection resistance test suite. "
        "Test only agents you own or are authorized to test.",
    )
    parser.add_argument("--adapter", default="mock-offline", choices=["mock-offline", "reference"])
    parser.add_argument("--scenarios", default="scenarios", help="YAML file or directory")
    parser.add_argument("--category", help="run only this category")
    parser.add_argument("--out", default="reports", help="directory for the markdown report")
    parser.add_argument("--json-out", help="also write a machine-readable JSON report here")
    parser.add_argument(
        "--fail-under",
        type=float,
        metavar="PCT",
        help="exit non-zero if overall resistance is below PCT (0-100). "
        "A run with nothing scored (all INCONCLUSIVE/ERROR) also fails.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="print per-scenario verdicts")
    args = parser.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    if args.category:
        scenarios = [s for s in scenarios if s.category == args.category]
    if not scenarios:
        raise SystemExit(f"no scenarios found (path={args.scenarios!r}, category={args.category!r})")

    adapter, model = build_adapter(args.adapter)
    report = run_suite(scenarios, adapter, model=model)

    console = Console()
    render_console(report, console, verbose=args.verbose)
    path = write_report(report, args.out, adapter_name=adapter.name)
    console.print(f"\nMarkdown report written to [bold]{path}[/bold]")
    if args.json_out:
        jpath = write_json(report, args.json_out)
        console.print(f"JSON report written to [bold]{jpath}[/bold]")

    return _gate(report, args.fail_under, console)


def _gate(report, fail_under, console) -> int:
    """Return the process exit code for the optional --fail-under CI gate."""
    if fail_under is None:
        return 0
    resistance = report.overall_resistance
    if resistance is None:
        console.print(
            f"[red]FAIL[/red]: no scored scenarios (all INCONCLUSIVE/ERROR) — "
            f"cannot meet --fail-under {fail_under:g}%"
        )
        return 1
    pct = resistance * 100
    if pct < fail_under:
        console.print(f"[red]FAIL[/red]: overall resistance {pct:.0f}% < --fail-under {fail_under:g}%")
        return 1
    console.print(f"[green]PASS[/green]: overall resistance {pct:.0f}% >= --fail-under {fail_under:g}%")
    return 0
