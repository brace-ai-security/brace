"""OpenTelemetry spans for agent actions."""
import os
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_provider = TracerProvider(resource=Resource.create({"service.name": "support-agent"}))
_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=os.environ.get("OTLP_ENDPOINT",
                                                                 "http://otel-collector.observability.svc:4317")))
)
trace.set_tracer_provider(_provider)
tracer = trace.get_tracer("support-agent")


@contextmanager
def action_span(identity: dict, tool_name: str, context_tokens: int | None):
    """One span per tool call. Trace context comes from the active OTel context."""
    with tracer.start_as_current_span(f"execute_tool {tool_name}") as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", tool_name)
        span.set_attribute("gen_ai.agent.name", "support-agent")
        span.set_attribute("gen_ai.agent.version", identity["agent_type_id"])
        # Tenant, owner and run ID go in the audit record (src/audit.py).
        if context_tokens is not None:
            # usage.input_tokens of the call that chose this tool = full prompt size at decision time
            span.set_attribute("gen_ai.usage.input_tokens", context_tokens)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise
