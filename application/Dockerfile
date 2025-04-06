FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

RUN apk --no-cache add curl g++ gcc libxslt-dev linux-headers musl-dev postgresql-dev

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV FLASK_APP=aggregator.app

RUN adduser -D -h /app -u 1000 abuser

COPY crontab ./
RUN crontab ./crontab

USER abuser

CMD sh -c "gunicorn"

EXPOSE 8000
