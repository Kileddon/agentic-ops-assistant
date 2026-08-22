from collections.abc import Sequence
from math import sqrt


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    if len(left) != len(right):
        raise ValueError("Vectors must have the same dimension.")

    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        raise ValueError("Vectors must not have zero length.")

    dot_product = sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )

    return dot_product / (left_norm * right_norm)
