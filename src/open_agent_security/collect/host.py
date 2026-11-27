"""Agent and MCP settings on this machine (--host): a fixed list of files per OS, from host_scan.

These are a known list, so symlinks are followed (dotfile managers use them) and the larger
limit that ~/.claude.json needs applies. Paths are shown with ~ for the home folder.
"""
from __future__ import annotations

import platform
from pathlib import Path
from typing import Iterator

from .. import host_scan
from ..fsio import ReadFailure, read
from ..limits import HOST_FILE_BYTES
from ..model import Skipped, SourceFile


class HostCollector:
    name = "host"

    def collect(self, ctx) -> Iterator[SourceFile | Skipped]:
        config = ctx.config
        if not config.host:
            return
        home = Path.home()
        sources = host_scan.host_sources(home, platform.system(), None)
        sources.append({"client": "Claude Code (settings)", "path": home / ".claude" / "settings.json", "keys": []})
        for src in sources:
            path = Path(src["path"])
            if not path.exists():
                continue
            try:
                where = "~/" + path.relative_to(home).as_posix()
            except ValueError:
                where = str(path)
            text = read(path, follow=True, limit=HOST_FILE_BYTES, display=where)
            if isinstance(text, ReadFailure):
                yield Skipped(text.display, text.reason, True, HOST_FILE_BYTES)
            else:
                yield SourceFile(where, "host", text, is_agent_config=True, server_keys=tuple(src["keys"]),
                                 project=config.root)
