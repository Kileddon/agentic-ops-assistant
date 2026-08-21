from typing import Protocol

from agentic_ops_assistant.investigation import InvestigationReport
from agentic_ops_assistant.summarization.prompt import build_summary_prompt


class SummaryClient(Protocol):
    def summarize(self, prompt: str) -> str: ...


class InvestigationSummaryService:
    def __init__(self, client: SummaryClient) -> None:
        self._client = client

    def summarize(self, report: InvestigationReport) -> str:
        prompt = build_summary_prompt(report)
        return self._client.summarize(prompt)
