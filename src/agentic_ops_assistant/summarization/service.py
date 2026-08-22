from typing import Protocol

from agentic_ops_assistant.investigation import InvestigationReport
from agentic_ops_assistant.summarization.models import GeneratedSummary
from agentic_ops_assistant.summarization.prompt import build_summary_prompt


class SummaryClient(Protocol):
    def summarize(self, prompt: str) -> GeneratedSummary: ...


class InvestigationSummaryService:
    def __init__(self, client: SummaryClient) -> None:
        self._client = client

    def summarize(self, report: InvestigationReport) -> str:
        prompt = build_summary_prompt(report)
        generated_summary = self._client.summarize(prompt)

        return _format_summary(generated_summary)


def _format_summary(summary: GeneratedSummary) -> str:
    possible_cause = summary.possible_cause or "Not established."

    return "\n".join(
        (
            f"Summary: {summary.summary}",
            f"Possible cause: {possible_cause}",
            f"Uncertainty: {summary.uncertainty}",
        ),
    )
