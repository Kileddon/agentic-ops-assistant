FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "agentic_ops_assistant.api:create_app_from_environment", "--factory", "--host", "0.0.0.0", "--port", "8000"]
