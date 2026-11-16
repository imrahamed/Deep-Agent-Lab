import asyncio

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from deep_agent_lab.knowledge import fixture_search
from deep_agent_lab.tooling import remote_mcp_search


def test_real_streamable_http_protocol_with_in_process_authenticated_transport():
    async def experiment():
        server = FastMCP(
            "Northstar HTTP fixture",
            stateless_http=True,
            json_response=True,
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["mcp.test"],
                allowed_origins=["https://mcp.test"],
            ),
        )

        @server.tool()
        def search(query: str) -> list[dict]:
            """Search the fictional Northstar policy corpus."""
            return [row.model_dump() for row in fixture_search(query, 3)]

        application = server.streamable_http_app()
        observed_headers = []

        async def authenticated(scope, receive, send):
            headers = dict(scope["headers"])
            observed_headers.append(headers.get(b"authorization"))
            assert headers.get(b"authorization") == b"Bearer scoped-fixture-token"
            await application(scope, receive, send)

        async with server.session_manager.run():
            result = await remote_mcp_search(
                "https://mcp.test/mcp",
                "scoped-fixture-token",
                frozenset({"https://mcp.test"}),
                "production restore",
                transport=httpx.ASGITransport(app=authenticated),
            )
        assert not result.isError
        assert "northstar-restore" in str(result.structuredContent or result.content)
        assert observed_headers and all(
            value == b"Bearer scoped-fixture-token" for value in observed_headers
        )

    asyncio.run(experiment())
