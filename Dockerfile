FROM python:3.11-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /uvx /bin/

COPY pyproject.toml /build/pyproject.toml
COPY uv.lock /build/uv.lock
COPY src /build/src

WORKDIR /build

RUN uv build
RUN uv pip compile pyproject.toml --universal --no-annotate --no-header -o /dist/requirements.txt


FROM python:3.11-slim-bookworm

COPY --from=builder /build/dist/ /dist/

COPY entrypoint.sh /entrypoint.sh

RUN sh -c "pip install /dist/alert_server-*.whl"

ENTRYPOINT [ "/entrypoint.sh" ]

