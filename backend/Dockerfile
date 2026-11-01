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

# Collect static files (the admin's CSS and JS) into the image for WhiteNoise. Production
# settings need these variables to load; these placeholders exist only for this build step and
# are never used at runtime, where the host provides the real values.
RUN DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_SECRET_KEY=build-only \
    DJANGO_ALLOWED_HOSTS=localhost WEB_APP_URL=https://build.invalid \
    POSTGRES_DB=build POSTGRES_USER=build POSTGRES_PASSWORD=build POSTGRES_HOST=localhost \
    POSTGRES_PORT=5432 POSTMARK_SERVER_TOKEN=build-only DEFAULT_FROM_EMAIL=build@build.invalid \
    python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
