"""Connects to the MCP servers in .mcp.json and exposes their tools to the model."""
import json
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.auth import UserToken

MCP_CONFIG = Path(__file__).resolve().parent.parent / ".mcp.json"


class MCPHub:
    def __init__(self, user_token: UserToken):
        self._user_token = user_token
        self._stack = AsyncExitStack()
        self.sessions: dict[str, ClientSession] = {}
        self.tool_index: dict[str, str] = {}  # tool name -> server name

    async def __aenter__(self):
        config = json.loads(MCP_CONFIG.read_text())["mcpServers"]
        for server_name, spec in config.items():
            env = dict(spec.get("env", {}))
            env["OAUTH_ACCESS_TOKEN"] = self._user_token.bearer
            params = StdioServerParameters(command=spec["command"], args=spec["args"], env=env)
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.sessions[server_name] = session
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def anthropic_tools(self) -> list[dict]:
        """Every tool every server offers, in Anthropic tool format."""
        tools = []
        for server_name, session in self.sessions.items():
            listing = await session.list_tools()
            for tool in listing.tools:
                self.tool_index[tool.name] = server_name
                tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                    }
                )
        return tools

    async def call(self, name: str, arguments: dict) -> str:
        server_name = self.tool_index[name]
        result = await self.sessions[server_name].call_tool(name, arguments)
        return "\n".join(c.text for c in result.content if getattr(c, "text", None))
