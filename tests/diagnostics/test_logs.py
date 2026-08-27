import pytest

from agentic_ops_assistant.diagnostics.logs import redact_log_line, search_log_lines


def test_redact_log_line_removes_common_secret_formats() -> None:
    line = "token=abc password: hunter2 Authorization: Bearer jwt-value"

    assert redact_log_line(line) == (
        "token=[REDACTED] password: [REDACTED] Authorization: Bearer [REDACTED]"
    )


def test_search_log_lines_matches_all_query_terms_and_limits_results() -> None:
    matches = search_log_lines(
        ("database timeout", "database connected", "database timeout again"),
        "database timeout",
        limit=1,
    )

    assert matches == ("database timeout",)


def test_search_log_lines_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        search_log_lines(("line",), "  ")
