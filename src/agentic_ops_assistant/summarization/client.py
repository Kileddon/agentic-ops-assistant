import httpx2
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from agentic_ops_assistant.summarization.models import GeneratedSummary


class SummaryGenerationError(RuntimeError):
    """Raised when a local language model cannot generate a summary."""


class OllamaSummaryClient:
    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434/v1/",
    ) -> None:
        if not model.strip():
            raise ValueError("Model name must not be empty.")

        self._model = model
        self._client = OpenAI(
            base_url=base_url,
            api_key="ollama",
            http_client=httpx2.Client(trust_env=False),
        )

    def summarize(self, prompt: str) -> GeneratedSummary:
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
        except OpenAIError as error:
            raise SummaryGenerationError(
                "Local language model could not generate a summary.",
            ) from error

        content = response.choices[0].message.content

        if content is None:
            raise SummaryGenerationError(
                "Local language model returned an empty summary.",
            )

        try:
            return GeneratedSummary.model_validate_json(content)
        except ValidationError as error:
            raise SummaryGenerationError(
                "Local language model returned an invalid summary.",
            ) from error
