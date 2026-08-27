import re

_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(password|secret|token|api[_-]?key)\b(\s*[=:]\s*)([^\s,;]+)",
)
_BEARER_CREDENTIAL = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def redact_log_line(line: str) -> str:
    redacted = _SENSITIVE_ASSIGNMENT.sub(r"\1\2[REDACTED]", line)
    return _BEARER_CREDENTIAL.sub("Bearer [REDACTED]", redacted)


def search_log_lines(
    log_lines: tuple[str, ...],
    query: str,
    *,
    limit: int = 20,
) -> tuple[str, ...]:
    normalized_query = query.strip().casefold()
    if not normalized_query:
        raise ValueError("Log search query must not be blank.")
    if limit <= 0:
        raise ValueError("Log search result limit must be positive.")

    query_terms = tuple(normalized_query.split())
    matches = (line for line in log_lines if all(term in line.casefold() for term in query_terms))
    return tuple(match for _, match in zip(range(limit), matches, strict=False))
