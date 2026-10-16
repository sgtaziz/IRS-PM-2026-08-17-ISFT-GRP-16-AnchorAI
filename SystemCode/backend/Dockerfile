FROM python:3.12-slim
# LightGBM links the system OpenMP runtime, which the slim image does not ship.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock alembic.ini ./
COPY anchorai ./anchorai
COPY migrations ./migrations
RUN uv sync --frozen --no-dev
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync anchorai db upgrade && uv run --no-sync anchorai db seed --demo && uv run --no-sync uvicorn anchorai.api.main:app --host 0.0.0.0 --port 8000"]
