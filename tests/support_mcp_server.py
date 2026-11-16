from mcp.server.fastmcp import FastMCP

from tests.support import fixture_search

server = FastMCP("unit-test-search")
@server.tool()
def search(query: str) -> list[dict]:
    return [row.model_dump() for row in fixture_search(query, 3)]
if __name__ == "__main__":
    server.run(transport="stdio")
