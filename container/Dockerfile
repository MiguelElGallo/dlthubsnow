FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --locked --no-dev

COPY container/entrypoint.sh /entrypoint.sh
RUN useradd --create-home --uid 1000 appuser \
    && chmod +x /entrypoint.sh \
    && chown -R appuser:appuser /app /entrypoint.sh

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
