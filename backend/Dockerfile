FROM python:3.14-alpine AS builder

RUN apk add --no-cache build-base zlib-dev

WORKDIR /app

# Add uv to the container according to docs recommendations
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

# Install dependencies. Use a cache mount to potentially speed this up
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --locked --no-install-project

COPY ./app ./app

# Install with application code
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --locked --compile-bytecode

FROM python:3.14-alpine

# SQLAlchemy concurrency depends on the C++ STL
RUN apk add --no-cache libstdc++

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

COPY --from=builder --chown=appuser:appgroup /app/.venv ./.venv
COPY --from=builder --chown=appuser:appgroup /app/app ./app

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
# Run 4 uvicorn workers, managed by gUnicorn
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
