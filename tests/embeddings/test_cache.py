from agentic_ops_assistant.embeddings.cache import CachingTextEmbedder


class CountingEmbedder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str) -> tuple[float, ...]:
        self.calls.append(text)
        return (float(len(self.calls)),)


def test_caching_embedder_reuses_embedding_for_same_text() -> None:
    delegate = CountingEmbedder()
    embedder = CachingTextEmbedder(delegate)

    first_embedding = embedder.embed("Database timeout")
    second_embedding = embedder.embed("Database timeout")

    assert first_embedding == (1.0,)
    assert second_embedding == (1.0,)
    assert delegate.calls == ["Database timeout"]


def test_caching_embedder_keeps_embeddings_for_different_texts_separate() -> None:
    delegate = CountingEmbedder()
    embedder = CachingTextEmbedder(delegate)

    first_embedding = embedder.embed("Database timeout")
    second_embedding = embedder.embed("Cache eviction")

    assert first_embedding == (1.0,)
    assert second_embedding == (2.0,)
    assert delegate.calls == ["Database timeout", "Cache eviction"]
