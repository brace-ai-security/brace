# syntax=docker/dockerfile:1.10
FROM python:3.11.10-slim-bookworm@sha256:2a6386ad2db20e7f55073f69a98d6da2cf9f168e05e7487d2670c22e4ad2a1bd AS build
WORKDIR /src
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY pyproject.toml ./
COPY app ./app
RUN pip install --target /opt/site .
RUN python -m compileall -q app

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:8f3c1a6e2b9d4f7a0c5e8b1d3f6a9c2e5b8d1f4a7c0e3b6d9f2a5c8e1b4d7f0a
WORKDIR /app
ENV PYTHONPATH=/opt/site:/app \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ROOT=/app
COPY --from=build /opt/site /opt/site
COPY --from=build /src/app /app/app
COPY prompts /app/prompts
COPY config /app/config
COPY release/manifest.yaml /app/release/manifest.yaml
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-server-header"]
