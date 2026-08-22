import pytest

from agentic_ops_assistant.embeddings.similarity import cosine_similarity


def test_cosine_similarity_returns_one_for_identical_vectors() -> None:
    result = cosine_similarity((1.0, 2.0), (1.0, 2.0))

    assert result == pytest.approx(1.0)


def test_cosine_similarity_returns_zero_for_orthogonal_vectors() -> None:
    result = cosine_similarity((1.0, 0.0), (0.0, 1.0))

    assert result == pytest.approx(0.0)


def test_cosine_similarity_rejects_vectors_with_different_dimensions() -> None:
    with pytest.raises(ValueError, match="Vectors must have the same dimension"):
        cosine_similarity((1.0, 2.0), (1.0,))


def test_cosine_similarity_rejects_zero_length_vector() -> None:
    with pytest.raises(ValueError, match="Vectors must not have zero length"):
        cosine_similarity((0.0, 0.0), (1.0, 2.0))
