"""Configured Ollama model used by the application and course."""
from langchain_ollama import ChatOllama

from deep_agent_lab.settings import Settings


def local_model(settings: Settings) -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_chat_model,
        base_url=str(settings.ollama_url).rstrip("/"),
        num_ctx=settings.ollama_context_tokens,
        num_predict=1536,
        temperature=0,
        reasoning=False,
        client_kwargs={"timeout": settings.request_timeout_seconds, "trust_env": False},
        profile={"max_input_tokens": settings.ollama_context_tokens, "tool_calling": True},
    )
