from typing import Protocol

import httpx2
from openai import OpenAI, OpenAIError


class EmbeddingGenerationError(RuntimeError):
    """Raised when a local language model cannot generate an embedding."""


class TextEmbedder(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...


class OllamaEmbeddingClient:
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

    def embed(self, text: str) -> tuple[float, ...]:
        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Text to embed must not be empty.")

        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=[normalized_text],
            )
        except OpenAIError as error:
            raise EmbeddingGenerationError(
                "Local language model could not generate an embedding.",
            ) from error

        if not response.data or not response.data[0].embedding:
            raise EmbeddingGenerationError(
                "Local language model returned an empty embedding.",
            )

        return tuple(response.data[0].embedding)
