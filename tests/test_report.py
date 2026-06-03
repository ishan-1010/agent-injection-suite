"""Tests for the markdown/console reporter."""

from injection_suite.report import render_markdown, write_report


def test_markdown_has_mode_and_caveat(sample_report_illustrative):
    md = render_markdown(sample_report_illustrative)
    assert "MODE: ILLUSTRATIVE" in md
    assert "indicative resistance" in md.lower()
    assert "Detection is rule-based and approximate" in md


def test_markdown_lists_categories(sample_report_illustrative):
    md = render_markdown(sample_report_illustrative)
    assert "direct_instruction_override" in md


def test_write_report_creates_file(sample_report_illustrative, tmp_path):
    path = write_report(sample_report_illustrative, tmp_path, adapter_name="mock-offline")
    assert path.exists() and path.suffix == ".md"
    assert "MODE: ILLUSTRATIVE" in path.read_text()
