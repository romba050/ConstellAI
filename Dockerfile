# ConstellAI server image (used by the Hugging Face Space).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

# Spaces runs containers as UID 1000.
RUN useradd -m -u 1000 user
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY atlas ./atlas
COPY web ./web
COPY data/atlas.json.gz ./data/atlas.json.gz
COPY data/curated ./data/curated
RUN mkdir -p data/cache && chown -R user:user /app/data

USER user
EXPOSE 7860
CMD ["uvicorn", "atlas.server:app", "--host", "0.0.0.0", "--port", "7860"]
