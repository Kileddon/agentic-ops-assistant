# AGENTS.md

## Project

`agentic-ops-assistant` is a Python project for a secure operations assistant.

Keep the implementation small, explicit, tested, and easy to explain. Add a dependency, abstraction, or technology only when it solves a current project need.

## Project layout

- Application code: `src/agentic_ops_assistant/`
- Tests: `tests/`
- Architecture documentation: `docs/`
- Architecture Decision Records: `docs/adr/`

Use the `src` layout. Do not import application code from the repository root.

## Development commands

```bash
uv sync
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pre-commit run --all-files
```

Run relevant checks before handing off a change.

## Code conventions

- Target Python 3.13+.
- Use modern type annotations.
- Prefer small functions, clear names, and explicit control flow.
- Keep side effects at application boundaries.
- Prefer composition over inheritance.
- Do not introduce abstractions before a real boundary or variation exists.
- Avoid hidden global state and mutable default arguments.
- Do not use `Any` when a stable domain type can describe the data.
- Comments should explain why a decision exists, not restate code.

## Testing

- Add or update tests for changed behavior.
- Keep tests deterministic and independent from network services, real LLMs, and local machine state.
- Test observable behavior, not implementation details.

## Configuration and security

- Never commit secrets, tokens, passwords, or local `.env` files.
- Store configuration in environment variables and document required variables in `.env.example`.
- Treat LLM output and external tool input as untrusted data.
- Sensitive or destructive operations must have an explicit policy and human approval boundary.

## Documentation

Update documentation only when stable project knowledge changes:

- `PROJECT_STATE.md` for the current stable state;
- `ROADMAP.md` for near-term milestones;
- `ARCHITECTURE.md` when architecture changes;
- `docs/adr/` only for significant, lasting decisions.

## Git

- Keep commits small and focused.
- Do not mix feature work, dependency upgrades, refactoring, and formatting in one commit unless they are inseparable.
- Do not commit `.venv`, IDE settings, caches, or generated local files.
