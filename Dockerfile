FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY tools/pyproject.toml tools/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY tools/src/ src/
COPY rest/src/models/ src/models/
COPY tools/main.py .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
