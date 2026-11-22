FROM ghcr.io/astral-sh/uv:0.11.21 AS uv
FROM python:3.12-slim AS builder

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV BACKEND_HOST=0.0.0.0 BACKEND_SERVE_FRONTEND=false
RUN useradd --system --no-create-home app
COPY --from=builder /app/.venv /app/.venv
COPY backend/ ./backend/
USER app
EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "backend.main"]
