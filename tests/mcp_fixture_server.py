"""Local MCP server for protocol-level integration tests (no external services)."""
import sys
from mcp.server.fastmcp import FastMCP

server = FastMCP("kurt-test", host="127.0.0.1", port=int(sys.argv[2]) if len(sys.argv) > 2 else 8000,
                 log_level="ERROR")


@server.tool()
def echo(text: str) -> str:
    """Echo a value to verify real tool calls."""
    return "echo:" + text


if __name__ == "__main__":
    server.run(transport=sys.argv[1] if len(sys.argv) > 1 else "stdio")
