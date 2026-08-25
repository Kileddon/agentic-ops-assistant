from threading import Lock

from agentic_ops_assistant.embeddings.client import TextEmbedder


class CachingTextEmbedder:
    """Caches embeddings by input text for the lifetime of the process."""

    def __init__(self, embedder: TextEmbedder) -> None:
        self._embedder = embedder
        self._cache: dict[str, tuple[float, ...]] = {}
        self._lock = Lock()

    def embed(self, text: str) -> tuple[float, ...]:
        with self._lock:
            embedding = self._cache.get(text)

            if embedding is not None:
                return embedding

            embedding = self._embedder.embed(text)
            self._cache[text] = embedding

            return embedding
