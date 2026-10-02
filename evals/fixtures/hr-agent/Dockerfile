# syntax=docker/dockerfile:1.10
FROM python:3.12.7-slim-bookworm@sha256:032c52613401895aa3d418a4c5bf5c3ad0d5d6fe3c1e9b2c8b5d0a7e6f4c3b21 AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --require-hashes --only-binary=:all: --target /deps -r requirements.txt

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:7e4c1d2a9f3b8e60c5d47a19b2f03e8d6c1a5b94f7e2d03c8a6b1f5e9d4c2a70
ENV PYTHONPATH=/deps:/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /deps /deps
COPY --chown=0:0 requirements.txt Dockerfile ./
COPY --chown=0:0 src/ src/
COPY --chown=0:0 prompts/ prompts/
COPY --chown=0:0 config/ config/
USER 65532:65532
ENTRYPOINT ["python3"]
