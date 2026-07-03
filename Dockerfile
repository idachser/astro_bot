FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY astro_bot ./astro_bot
COPY README.md ./
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--no-dev", "python", "-m", "astro_bot"]
