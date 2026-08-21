import httpx2
from openai import OpenAI, OpenAIError


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

    def summarize(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        try:
            response = self._client.responses.create(
                model=self._model,
                input=prompt,
            )
        except OpenAIError as error:
            raise SummaryGenerationError(
                "Local language model could not generate a summary.",
            ) from error

        summary = response.output_text.strip()
        if not summary:
            raise SummaryGenerationError(
                "Local language model returned an empty summary.",
            )

        return summary
