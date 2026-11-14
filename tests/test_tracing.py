from uuid import uuid4

from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from deep_agent_lab.service import AgentService, RunRequest, open_checkpointer
from deep_agent_lab.settings import Settings


def test_observations_exclude_content_by_default(tmp_path, monkeypatch):
    from deep_agent_lab.tracing import Tracing

    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-lf-local-" + uuid4().hex,
        secret_key="sk-lf-local",
        base_url="https://langfuse.example.com",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
    )
    monkeypatch.setattr(Tracing, "_create_client", staticmethod(lambda settings: client))
    settings = Settings(
        _env_file=None,
        deep_lab_state_dir=tmp_path,
        deep_lab_mode="demo",
        langfuse_enabled=True,
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key="sk-lf-test",
        langfuse_capture_content=False,
    )
    with open_checkpointer(settings) as checkpointer:
        service = AgentService(settings, checkpointer)
        try:
            run = service.run(RunRequest(prompt="Who approves a production restore?"))
            assert run.trace_id
            client.flush()
            spans = exporter.get_finished_spans()
            assert {span.name for span in spans} == {
                "deep-lab.turn",
                "deep-lab.model",
                "deep-lab.search",
            }
            assert {f"{span.context.trace_id:032x}" for span in spans} == {run.trace_id}
            for span in spans:
                assert "langfuse.observation.input" not in span.attributes
                assert "langfuse.observation.output" not in span.attributes
        finally:
            service.close()
