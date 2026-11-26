"""Parsers: turn a source file into facts (MCP servers, permissions, images, workflow triggers)."""
from .claude_settings import ClaudeSettings
from .codex_toml import CodexToml
from .dockerfile import Dockerfile
from .mcp_json import McpJson
from .workflow import Workflow

BUILTIN = (Workflow(), Dockerfile(), McpJson(), CodexToml(), ClaudeSettings())
