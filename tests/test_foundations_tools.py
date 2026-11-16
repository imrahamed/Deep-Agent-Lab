import asyncio

import pytest
from pydantic import ValidationError

from deep_agent_lab.foundations import FinalAnswer, StepLimit, ToolCall, agent_loop
from deep_agent_lab.tooling import collect_pages, remote_headers, search_read


def test_loop_correlates_calls_and_uses_results():
    def decide(messages):
        if messages[-1]["role"] == "tool":
            return FinalAnswer(messages[-1]["content"])
        return ToolCall("c1", "search_knowledge", {"query": "restore"})

    answer, events = agent_loop(decide, lambda q, k: [{"excerpt": "actual evidence"}], "approver?")
    assert "actual evidence" in answer
    assert events[1]["tool_call_id"] == events[2]["tool_call_id"] == "c1"
    assert events[-1]["role"] == "assistant"


def test_invalid_call_never_executes_and_loop_is_bounded():
    calls = []
    with pytest.raises(ValidationError):
        agent_loop(
            lambda _: ToolCall("bad", "search_knowledge", {"query": "x", "top_k": 99}),
            lambda *args: calls.append(args),
            "x",
        )
    assert not calls
    with pytest.raises(StepLimit):
        agent_loop(
            lambda messages: ToolCall(str(len(messages)), "search_knowledge", {"query": "x"}),
            lambda *args: [],
            "x",
            max_steps=2,
        )
    with pytest.raises(ValueError, match="unique"):
        agent_loop(
            lambda _: ToolCall("repeat", "search_knowledge", {"query": "x"}), lambda *args: [], "x"
        )


def test_read_outcomes_retry_timeout_and_privacy():
    async def experiment():
        attempts = []

        async def flaky(request):
            attempts.append(request)
            if len(attempts) == 1:
                raise TimeoutError("postgresql://secret")
            return [{"excerpt": "a" * 800}]

        ok = await search_read(flaky, {"query": "restore"}, call_id="one", backoff=0)
        assert ok.status == "success" and ok.attempts == 2
        assert len(ok.hits[0]["excerpt"]) == 500
        invalid = await search_read(flaky, {"query": " "}, call_id="bad")
        assert invalid.status == "invalid_request" and len(attempts) == 2

        async def slow(request):
            await asyncio.sleep(1)
            return []

        failed = await search_read(slow, {"query": "x"}, call_id="two", timeout=0.001, attempts=1)
        assert failed.status == "transient_error" and "secret" not in failed.model_dump_json()
        empty = await search_read(
            lambda _: asyncio.sleep(0, result=[]), {"query": "x"}, call_id="empty"
        )
        assert empty.status == "success" and empty.hits == []
        task = asyncio.create_task(search_read(slow, {"query": "x"}, call_id="cancel"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(experiment())


def test_pagination_and_exact_remote_origin():
    async def experiment():
        pages = {None: ([1], "p2"), "p2": ([2], None)}
        assert await collect_pages(lambda cursor: asyncio.sleep(0, result=pages[cursor])) == [1, 2]
        with pytest.raises(ValueError, match="cursor"):
            await collect_pages(lambda _: asyncio.sleep(0, result=([], "repeat")))

    asyncio.run(experiment())
    assert remote_headers("https://mcp.test/mcp", "test-token", frozenset({"https://mcp.test"}))
    for url in ["http://mcp.test/mcp", "https://mcp.test.evil/mcp", "https://user@mcp.test/mcp"]:
        with pytest.raises(PermissionError):
            remote_headers(url, "test-token", frozenset({"https://mcp.test"}))
