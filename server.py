import os

from mcp.server.mcpserver import MCPServer


mcp = MCPServer("Threads MCP")


@mcp.tool()
def test_connection() -> str:
    """Test that the Threads MCP server is working."""
    return "Threads MCP server is working."


@mcp.tool()
def about() -> str:
    """Show what this MCP server is for."""
    return "This server connects ChatGPT to the user's Threads account."


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        json_response=True,
    )
