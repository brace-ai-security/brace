FROM python:3.12-slim@sha256:2be8daddbb82756f7d1f2c7ece706aadcb284bf6ab6d769ea695cc3ed6016743 AS base

ARG KUBECTL_VERSION=v1.31.2
ARG KUBECTL_SHA256=399e9d1995da80b64d2ef3606c1a239018660d8b35209fba3f7b0bc11c631c68

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl \
    && curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
    && echo "${KUBECTL_SHA256}  /usr/local/bin/kubectl" | sha256sum -c - \
    && chmod +x /usr/local/bin/kubectl \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY src/ src/
COPY prompts/ prompts/
COPY config/ config/

RUN useradd --uid 10001 --no-create-home agent
USER 10001
ENTRYPOINT ["python", "-m", "src.main"]
