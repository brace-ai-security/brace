"""Claude Code settings: permission allow-rules, the default permission mode and env."""
from __future__ import annotations

import re

from ..model import Document, Permissions, SourceFile
from .mcp_json import is_json

SETTINGS_FILE = re.compile(r"(?:^|/)settings(?:\.local)?\.json$", re.I)


class ClaudeSettings:
    name = "claude-settings"

    def claims(self, src: SourceFile) -> bool:
        return is_json(src)

    def parse(self, src: SourceFile, doc: Document) -> None:
        data = doc.json()
        if not isinstance(data, dict):
            return
        perms = data.get("permissions")
        env = data.get("env")
        # A top-level env is agent config only next to permissions or in a settings file.
        env = env if isinstance(env, dict) and (isinstance(perms, dict) or SETTINGS_FILE.search(src.display)) else None
        if not isinstance(perms, dict) and env is None:
            return
        perms = perms if isinstance(perms, dict) else {}
        allow = perms.get("allow")
        doc.permissions = Permissions(
            allow=tuple(r for r in allow if isinstance(r, str)) if isinstance(allow, list) else (),
            default_mode=perms.get("defaultMode"), env=env)
