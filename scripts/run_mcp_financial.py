from gem_strategy_assistant.infrastructure.mcp_servers.financial_server import mcp

if __name__ == "__main__":
    print("Starting Financial MCP Server...")
    mcp.run(transport="stdio")