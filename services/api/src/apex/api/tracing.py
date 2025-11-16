from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from .deps import settings


def setup_tracing():  # type: ignore[no-untyped-def]
    resource = Resource.create({"service.name": settings.SERVICE_NAME, "service.version": settings.APP_VERSION})
    provider = TracerProvider(resource=resource)
    if settings.OTEL_EXPORTER == "otlp" and settings.OTEL_ENDPOINT:
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_ENDPOINT)
    else:
        exporter = ConsoleSpanExporter()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


