"""Typed outcomes and bounded, cancellable reads; not a write-retry wrapper."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, Field, ValidationError

from deep_agent_lab.foundations import SearchArgs


class ToolOutcome(BaseModel):
    call_id: str
    status: Literal[
        "success", "invalid_request", "permission_denied", "transient_error", "internal_error"
    ]
    hits: list[dict] = Field(default_factory=list)
    error_code: str | None = None
    attempts: int = 0


async def search_read(
    operation: Callable[[SearchArgs], Awaitable[list[dict]]],
    arguments: dict,
    *,
    call_id: str,
    timeout: float = 1,
    attempts: int = 2,
    backoff: float = 0.01,
    excerpt_chars: int = 500,
) -> ToolOutcome:
    """Timeout applies per attempt. Cancellation propagates to the async transport."""
    if not call_id or timeout <= 0 or not 1 <= attempts <= 5 or backoff < 0 or excerpt_chars < 1:
        raise ValueError("Invalid read policy")
    try:
        request = SearchArgs.model_validate(arguments)
    except ValidationError:
        return ToolOutcome(call_id=call_id, status="invalid_request", error_code="schema")
    for attempt in range(1, attempts + 1):
        try:
            async with asyncio.timeout(timeout):
                rows = await operation(request)
            hits = [
                {**row, "excerpt": row.get("excerpt", "")[:excerpt_chars]}
                for row in rows[: request.top_k]
            ]
            return ToolOutcome(call_id=call_id, status="success", hits=hits, attempts=attempt)
        except PermissionError:
            return ToolOutcome(call_id=call_id, status="permission_denied", attempts=attempt)
        except (TimeoutError, httpx.TimeoutException, httpx.ConnectError):
            if attempt == attempts:
                return ToolOutcome(
                    call_id=call_id,
                    status="transient_error",
                    error_code="unavailable",
                    attempts=attempt,
                )
            await asyncio.sleep(backoff * 2 ** (attempt - 1))
        except Exception:
            # Never echo exceptions containing URLs, tokens or raw provider responses.
            return ToolOutcome(
                call_id=call_id, status="internal_error", error_code="backend", attempts=attempt
            )
    raise AssertionError("unreachable")


async def collect_pages(fetch: Callable, *, max_pages: int = 10) -> list:
    """An MCP list_* response may contain nextCursor. Detect cycles and bound work."""
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    cursor = None
    seen = set()
    rows = []
    for _ in range(max_pages):
        items, next_cursor = await fetch(cursor)
        rows.extend(items)
        if next_cursor is None:
            return rows
        if next_cursor in seen:
            raise ValueError("Repeated pagination cursor")
        seen.add(next_cursor)
        cursor = next_cursor
    raise ValueError("Pagination budget exhausted")


def remote_headers(url: str, token: str, allowed_origins: frozenset[str]) -> dict:
    """Supply an externally obtained OAuth token only to an exact trusted HTTPS origin."""
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if (
        parsed.scheme != "https"
        or origin not in allowed_origins
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.hostname
    ):
        raise PermissionError("Untrusted MCP endpoint")
    if not token or any(c.isspace() for c in token):
        raise ValueError("Invalid bearer token")
    return {"Authorization": f"Bearer {token}"}


async def remote_mcp_search(
    url: str,
    token: str,
    allowed_origins: frozenset[str],
    query: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
):
    """Real Streamable HTTP client. OAuth discovery/login belongs to the identity layer."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    headers = remote_headers(url, token, allowed_origins)
    # Redirects stay off: do not forward a bearer token to another destination.
    async with httpx.AsyncClient(
        headers=headers, timeout=10, follow_redirects=False, transport=transport
    ) as http:
        async with streamable_http_client(url, http_client=http) as (reader, writer, _):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                return await session.call_tool("search", {"query": query})
