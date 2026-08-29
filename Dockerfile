FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && chown --recursive app:app /app

ENV PATH="/app/.venv/bin:$PATH"

USER app

CMD ["uvicorn", "agentic_ops_assistant.api:create_app_from_environment", "--factory", "--host", "0.0.0.0", "--port", "8000"]
