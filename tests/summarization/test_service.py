from agentic_ops_assistant.investigation import InvestigationReport
from agentic_ops_assistant.summarization.models import GeneratedSummary
from agentic_ops_assistant.summarization.service import InvestigationSummaryService


class FakeSummaryClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def summarize(self, prompt: str) -> GeneratedSummary:
        self.prompts.append(prompt)
        return GeneratedSummary(
            summary="The payments API is degraded because of database timeouts.",
            possible_cause=None,
            uncertainty="The report does not confirm a root cause.",
        )


def test_summary_service_builds_prompt_and_returns_client_summary() -> None:
    client = FakeSummaryClient()
    service = InvestigationSummaryService(client)
    report = InvestigationReport(
        service="payments-api",
        service_status=None,
        knowledge_matches=(),
        proposed_action=None,
        policy_decision=None,
    )

    summary = service.summarize(report)

    assert summary == (
        "Summary: The payments API is degraded because of database timeouts.\n"
        "Possible cause: Not established.\n"
        "Uncertainty: The report does not confirm a root cause."
    )
    assert len(client.prompts) == 1
    assert "payments-api" in client.prompts[0]
