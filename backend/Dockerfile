FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv

RUN useradd --create-home app && mkdir /app && chown app /app
WORKDIR /app

# Install dependencies first so this layer is cached until pyproject.toml/uv.lock change.
# Local dev builds pass INSTALL_DEV=true to include pytest and ruff. The venv stays owned by
# root: the app only reads it, and a recursive chown would copy all of it into a new layer
# on every code change. --no-cache keeps uv's download cache out of the image.
ARG INSTALL_DEV=false
COPY pyproject.toml uv.lock ./
RUN if [ "$INSTALL_DEV" = "true" ]; then uv sync --frozen --no-cache; else uv sync --frozen --no-cache --no-dev; fi

COPY --chown=app . .
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
