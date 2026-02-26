"""Observability for papa-lang — OpenTelemetry (v0.4)."""

from typing import Optional


class PapaTracer:
    """OpenTelemetry tracer for papa-lang agents. pip install papa-lang[otel]"""

    def __init__(self, service_name: str = "papa-lang", backend: str = "otel"):
        self.service_name = service_name
        self._tracer = None
        if backend == "otel":
            self._setup_otel()

    def _setup_otel(self) -> None:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import Resource
            resource = Resource.create({"service.name": self.service_name})
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
        except ImportError:
            raise ImportError("Run: pip install papa-lang[otel]") from None

    def trace_agent(self, agent_name: str, hrs: float, verdict: str) -> None:
        if self._tracer is None:
            return
        from opentelemetry import trace
        with self._tracer.start_as_current_span(f"papa.agent.{agent_name}") as span:
            span.set_attribute("papa.agent.name", agent_name)
            span.set_attribute("papa.hrs.score", hrs)
            span.set_attribute("papa.hrs.verdict", verdict)
            span.set_attribute("papa.lang.version", "0.4.0")


class ConsoleTracer(PapaTracer):
    """Zero-dependency tracer for local development."""

    def trace_agent(self, agent_name: str, hrs: float, verdict: str) -> None:
        print(f"[papa-trace] agent={agent_name} hrs={hrs:.3f} verdict={verdict}")


def get_tracer(mode: str, service_name: str = "papa-lang") -> Optional[PapaTracer]:
    if mode == "otel":
        return PapaTracer(service_name, "otel")
    if mode == "console":
        return ConsoleTracer(service_name, "console")
    return None
