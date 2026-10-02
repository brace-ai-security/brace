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
        span.set_attribute("agent.accountable_party", identity["accountable_party"])
        span.set_attribute("agent.operational_owner", identity["operational_owner"])
        span.set_attribute("agent.tenant", identity["tenant"])
        span.set_attribute("agent.type.id", identity["agent_type_id"])
        span.set_attribute("agent.instance.id", identity["agent_instance_id"])
        if context_tokens is None:
            span.set_attribute("agent.context.size.method", "unavailable")
        else:
            # usage.input_tokens of the call that chose this tool = full prompt size at decision time
            span.set_attribute("agent.context.size", context_tokens)
            span.set_attribute("agent.context.size.method", "measured")
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise
