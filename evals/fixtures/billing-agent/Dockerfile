FROM python:3.11-slim-bookworm@sha256:8f3aba466a471c0ab903dbd7cb979abd4bda370b04789d25440cc90372b50e04 AS build
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt \
 && pip install --no-cache-dir --prefix=/install pgvector psycopg-pool

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:a2c4e5e8f1b7d3c9e0f6a8b2d4c6e8f0a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1
COPY --from=build /install/lib/python3.11/site-packages /usr/lib/python3/dist-packages
WORKDIR /app
COPY src/ src/
COPY prompts/ prompts/
COPY config/ config/
COPY .mcp.json .mcp.json
COPY Dockerfile requirements.txt ./
USER 65532:65532
ENTRYPOINT ["python3", "-m", "src.main"]
CMD ["serve"]
