import pytest
from pydantic import ValidationError

from agentic_ops_assistant.summarization.models import GeneratedSummary


def test_generated_summary_accepts_expected_fields() -> None:
    summary = GeneratedSummary(
        summary="Payments API is degraded because of database timeouts.",
        possible_cause="Connection pool exhaustion is a possible cause.",
        uncertainty="The report does not confirm a root cause.",
    )

    assert summary.possible_cause == "Connection pool exhaustion is a possible cause."


def test_generated_summary_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        GeneratedSummary.model_validate(
            {
                "summary": "Payments API is degraded.",
                "uncertainty": "Root cause is not confirmed.",
                "unexpected_field": "not allowed",
            },
        )
