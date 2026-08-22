# Agentic Ops Assistant

Secure assistant for operational and support workflows.

The assistant is designed to help investigate operational issues by combining knowledge retrieval, incident context, diagnostic tools, and controlled action execution. Sensitive actions must pass policy validation and require human approval.

## Development

Requirements:

- Python 3.13 or 3.14
- [uv](https://docs.astral.sh/uv/)

Install dependencies:

```bash
uv sync
```

Run tests and quality checks:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pre-commit run --all-files
```

## Repository layout

```text
src/agentic_ops_assistant/  Application package
tests/                      Automated tests
docs/                       Architecture notes and decisions
```

