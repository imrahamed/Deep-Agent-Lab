from deep_agent_lab.rag.pipeline import RagService
from deep_agent_lab.settings import Settings


def doctor(settings: Settings, *, check_tracing: bool = False) -> dict:
    with RagService(settings) as rag:
        return {"mode": "live", **rag.health(check_tracing=check_tracing)}
