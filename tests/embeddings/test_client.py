import pytest

from agentic_ops_assistant.embeddings.client import OllamaEmbeddingClient


def test_ollama_embedding_client_rejects_blank_model_name() -> None:
    with pytest.raises(ValueError, match="Model name must not be empty"):
        OllamaEmbeddingClient(model="   ")


def test_ollama_embedding_client_rejects_blank_text() -> None:
    client = OllamaEmbeddingClient(model="nomic-embed-text")

    with pytest.raises(ValueError, match="Text to embed must not be empty"):
        client.embed("   ")
