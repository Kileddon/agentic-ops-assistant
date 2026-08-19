\# Project State



\## Implemented



\- Python package with `src` layout

\- Dependency management and lockfile with `uv`

\- Isolated local environment in `.venv`

\- pytest test suite

\- Ruff formatting and linting

\- Strict mypy type checking

\- pre-commit hooks for local quality checks

\- Public GitHub repository



\## Current constraints



\- Python compatibility: 3.13 and 3.14

\- Application dependencies: none

\- Development dependencies: pytest, Ruff, mypy, pre-commit

\- Configuration uses environment variables; no secrets are committed



\## Application behavior



No operational workflow has been introduced yet. The next implementation step should define a small, read-only domain slice before adding LLMs, RAG, databases, or external integrations.



\## Key decisions



\- Use `uv` for dependency and environment management.

\- Use a `src` layout to test the installed package rather than source files from the repository root.

\- Keep quality checks strict from the start.

\- Avoid infrastructure and agent frameworks until a concrete application boundary requires them.

