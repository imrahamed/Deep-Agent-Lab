"""Read-only MCP transport for the same search used by the agent."""

from mcp.server.fastmcp import FastMCP

from deep_agent_lab.knowledge import Limit, Query, SearchMode, search_knowledge
from deep_agent_lab.settings import Settings

server = FastMCP("Deep Agent Lab knowledge")


@server.tool()
def search(query: Query, mode: SearchMode = "hybrid", top_k: Limit = 4) -> list[dict]:
    """Find citeable evidence in the configured lab corpus."""
    return [item.model_dump() for item in search_knowledge(Settings(), query, mode, top_k)]


if __name__ == "__main__":
    server.run(transport="stdio")
