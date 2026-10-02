FROM golang:1.23.4-bookworm@sha256:3b1a7de61ce1ae141ca21d925d6c09c4e7f2001b253d724c2d7b24d496c85c37 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/cloudops-agent ./cmd/cloudops-agent

FROM gcr.io/distroless/static-debian12:nonroot@sha256:6ec5aa99dc335666e79dc64e4a6c8b89c33a543a1967f20d360922a80dd21f02
COPY --from=build /out/cloudops-agent /cloudops-agent
COPY --from=ghcr.io/northwind-platform/aws-ops-mcp@sha256:9f2c41d0b7e85a3c6f4e1d2a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c /aws-ops-mcp /opt/mcp/aws-ops-mcp
COPY prompts /prompts
COPY config /config
USER 65532:65532
ENTRYPOINT ["/cloudops-agent", "--config", "/config/agent.yaml"]
