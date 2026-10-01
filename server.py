from mcp.server import MCPServer

mcp = MCPServer("Threads MCP")


@mcp.tool()
def test_connection() -> str:
    """Test that the Threads MCP server is working."""
    return "Threads MCP server is working."


@mcp.tool()
def about() -> str:
    """Show what this MCP server is for."""
    return "This server will connect ChatGPT to the user's Threads account."


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
    )
