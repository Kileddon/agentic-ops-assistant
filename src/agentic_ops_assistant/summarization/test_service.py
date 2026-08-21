from agentic_ops_assistant.investigation import InvestigationReport
from agentic_ops_assistant.summarization.service import InvestigationSummaryService


class FakeSummaryClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def summarize(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "The service is degraded because of database timeouts."


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

    assert summary == "The service is degraded because of database timeouts."
    assert len(client.prompts) == 1
    assert "payments-api" in client.prompts[0]
