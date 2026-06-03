"""Render a SuiteReport as a console table (rich) and a markdown report.

Both outputs carry a provenance label (ILLUSTRATIVE vs MEASURED) and a standing
caveat about rule-based precision, so a screenshot of the zero-config demo can
never be mistaken for a real model measurement.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from injection_suite.runner import COMPLIED, ERROR, INCONCLUSIVE, RESISTED, SuiteReport

CAVEAT = (
    "Detection is rule-based and approximate. It can miss paraphrased compliance "
    "and may misclassify a refusal that quotes the secret (a false positive). "
    "Treat scores as indicative resistance, not exact measurement."
)


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _mode_line(report: SuiteReport) -> str:
    if report.mode == "ILLUSTRATIVE":
        return "MODE: ILLUSTRATIVE (deterministic mock, no model — demonstrates the harness, not a real measurement)"
    model = f" — model={report.model}" if report.model else ""
    return f"MODE: MEASURED{model}"


def render_console(report: SuiteReport, console: Console | None = None, verbose: bool = False) -> None:
    console = console or Console()
    console.print(f"[bold cyan]{_mode_line(report)}[/bold cyan]")

    table = Table(title="Injection resistance by category", title_style="bold")
    table.add_column("Category")
    table.add_column("Resisted", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Resistance", justify="right")
    table.add_column("Inconc", justify="right")
    table.add_column("Errors", justify="right")
    for cat in sorted(report.by_category):
        score = report.by_category[cat]
        table.add_row(
            cat,
            str(score.resisted),
            str(score.total_scored),
            _pct(score.resistance),
            str(score.inconclusive),
            str(score.errors),
        )
    console.print(table)

    overall = f"Overall resistance: [bold]{_pct(report.overall_resistance)}[/bold]"
    extras = []
    if report.inconclusive:
        extras.append(f"{report.inconclusive} INCONCLUSIVE")
    if report.errors:
        extras.append(f"{report.errors} ERROR")
    if extras:
        overall += f"   [yellow]({', '.join(extras)} — excluded from scoring)[/yellow]"
    console.print(overall)

    if verbose:
        console.print()
        for r in report.results:
            colour = {RESISTED: "green", COMPLIED: "red", ERROR: "yellow", INCONCLUSIVE: "magenta"}[r.verdict]
            detail = ""
            if r.verdict == COMPLIED and r.fired_rule is not None:
                detail = f"  (rule: {r.fired_rule.kind})"
            elif r.verdict == ERROR:
                detail = f"  ({r.error})"
            elif r.verdict == INCONCLUSIVE:
                detail = "  (no final answer — hit tool-call cap)"
            console.print(f"  [{colour}]{r.verdict:12}[/{colour}] {r.scenario.id}  {r.scenario.title}{detail}")

    console.print(f"\n[dim]{CAVEAT}[/dim]")


def render_markdown(report: SuiteReport) -> str:
    lines: list[str] = []
    lines.append("# Injection Resistance Report")
    lines.append("")
    lines.append(f"**{_mode_line(report)}**")
    lines.append("")
    lines.append(f"> {CAVEAT}")
    lines.append("")
    lines.append("## Resistance by category")
    lines.append("")
    lines.append("| Category | Resisted | Total | Resistance | Inconclusive | Errors |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for cat in sorted(report.by_category):
        s = report.by_category[cat]
        lines.append(
            f"| {cat} | {s.resisted} | {s.total_scored} | {_pct(s.resistance)} | {s.inconclusive} | {s.errors} |"
        )
    lines.append("")
    overall = f"**Overall resistance: {_pct(report.overall_resistance)}**"
    extras = []
    if report.inconclusive:
        extras.append(f"{report.inconclusive} INCONCLUSIVE")
    if report.errors:
        extras.append(f"{report.errors} ERROR")
    if extras:
        overall += f"  ({', '.join(extras)} — excluded from scoring)"
    lines.append(overall)
    lines.append("")
    lines.append("## Per-scenario results")
    lines.append("")
    lines.append("| id | category | verdict | fired rule | detail |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in report.results:
        rule = r.fired_rule.kind if r.fired_rule else ""
        if r.verdict == ERROR:
            detail = (r.error or "").replace("|", "\\|")
        else:
            tools = ",".join(c.name for c in r.result.tool_calls) if r.result else ""
            snippet = (r.result.response if r.result else "")[:120].replace("\n", " ").replace("|", "\\|")
            prefix = "no final answer; " if r.verdict == INCONCLUSIVE else ""
            detail = f"{prefix}tools=[{tools}] resp=\"{snippet}\""
        lines.append(f"| {r.scenario.id} | {r.scenario.category} | {r.verdict} | {rule} | {detail} |")
    lines.append("")
    return "\n".join(lines)


def write_report(report: SuiteReport, out_dir, adapter_name: str) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out / f"report-{adapter_name}-{stamp}.md"
    path.write_text(render_markdown(report))
    return path


def render_json(report: SuiteReport) -> dict:
    """A machine-readable report for CI artifacts and the --fail-under gate."""
    return {
        "schema_version": 1,
        "mode": report.mode,
        "model": report.model,
        "overall_resistance": report.overall_resistance,
        "totals": {
            "resisted": sum(c.resisted for c in report.by_category.values()),
            "complied": sum(c.complied for c in report.by_category.values()),
            "inconclusive": report.inconclusive,
            "errors": report.errors,
        },
        "by_category": {
            cat: {
                "resisted": s.resisted,
                "complied": s.complied,
                "inconclusive": s.inconclusive,
                "errors": s.errors,
                "total_scored": s.total_scored,
                "resistance": s.resistance,
            }
            for cat, s in sorted(report.by_category.items())
        },
        "scenarios": [
            {
                "id": r.scenario.id,
                "category": r.scenario.category,
                "verdict": r.verdict,
                "fired_rule": r.fired_rule.kind if r.fired_rule else None,
            }
            for r in report.results
        ],
    }


def write_json(report: SuiteReport, path) -> Path:
    p = Path(path)
    if p.parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(render_json(report), indent=2))
    return p
