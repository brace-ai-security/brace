"""Checks: turn parsed facts into findings. Rule metadata lives in catalog.py."""
from .autoapprove import AutoApproval
from .combos import LethalCombination
from .hidden_unicode import HiddenUnicode
from .images import UnpinnedImages
from .mcp_servers import ConfigSecrets, McpServers
from .permissions import ClaudeSettings, PermissionFlags
from .remote_code import RemoteCode
from .workflow import LocalAgentSteps, OpenTrigger, PullRequestTarget

# Order matters only for findings that tie on severity, rule, file and line.
BUILTIN = (PermissionFlags(), PullRequestTarget(), McpServers(), LethalCombination(), ClaudeSettings(),
           UnpinnedImages(), ConfigSecrets(), LocalAgentSteps(), OpenTrigger(), AutoApproval(), HiddenUnicode(),
           RemoteCode())
