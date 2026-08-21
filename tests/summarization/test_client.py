import pytest

from agentic_ops_assistant.summarization.client import OllamaSummaryClient


def test_ollama_summary_client_rejects_blank_model_name() -> None:
    with pytest.raises(ValueError, match="Model name must not be empty"):
        OllamaSummaryClient(model="   ")


def test_ollama_summary_client_rejects_blank_prompt() -> None:
    client = OllamaSummaryClient(model="qwen2.5:3b")

    with pytest.raises(ValueError, match="Prompt must not be empty"):
        client.summarize("   ")
