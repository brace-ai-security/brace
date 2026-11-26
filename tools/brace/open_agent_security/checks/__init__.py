"""Checks: turn parsed facts into findings. Rule metadata lives in catalog.py."""
from .combos import LethalCombination
from .images import UnpinnedImages
from .mcp_servers import McpServers
from .permissions import ClaudeSettings, PermissionFlags
from .workflow import PullRequestTarget

# Order matters only for findings that tie on severity, rule, file and line.
BUILTIN = (PermissionFlags(), PullRequestTarget(), McpServers(), LethalCombination(), ClaudeSettings(),
           UnpinnedImages())
