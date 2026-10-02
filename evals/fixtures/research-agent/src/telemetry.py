import os
from pathlib import Path

import yaml
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.agent_type_id import agent_type_id

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())["agent"]

_provider = TracerProvider(resource=Resource.create({"service.name": "research-agent"}))
_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.environ.get("OTLP_ENDPOINT", "http://otel-collector.observability.svc:4317"))))
trace.set_tracer_provider(_provider)
tracer = trace.get_tracer("research-agent")


def identity_attrs(instance_id: str, user: str) -> dict:
    return {
        "agent.accountable_party": CFG["accountable_party"],
        "agent.operational_owner": CFG["operational_owner"],
        "agent.tenant": CFG["tenant"],
        "agent.type.id": agent_type_id(),
        "agent.instance.id": instance_id,
        "enduser.id": user,
    }
