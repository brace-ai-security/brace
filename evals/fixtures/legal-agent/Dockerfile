FROM python:3.12-slim@sha256:2b0079146a74e23bf4ae8f6a28e1b484c6292f6fb904cbb51825b4a19812fcd8 AS build
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes --target /deps -r requirements.txt
COPY src/ src/
COPY graph/ graph/
COPY prompts/ prompts/
COPY config/ config/

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:8a1f2b0e4c7d93a5b6e2f1c0d9e8b7a6f5e4d3c2b1a09f8e7d6c5b4a3928170f
WORKDIR /app
COPY --from=build /deps /deps
COPY --from=build /build /app
ENV PYTHONPATH=/deps:/app \
    PYTHONDONTWRITEBYTECODE=1
USER 65532:65532
ENTRYPOINT ["python3", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]
