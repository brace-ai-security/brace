#!/usr/bin/env python3
"""Deprecated launcher for the `brace` command; install the package and run `brace` instead.

`python tools/brace/brace.py <command>` runs any `brace` command (scan, init, items, hash,
check, export, import-results, map ..., plan) from a checkout or vendored copy. It is kept for
one release. Install the tools with `pip install "open-agent-security[record]"`. The code lives
in src/brace_tools/; importing this file gives the record checker (brace_tools.record.core).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

if __name__ == "__main__":
    from brace_tools.cli import main  # scan needs only the standard library; the rest say which extra is missing
    sys.exit(main())

from brace_tools.record import core as _real  # noqa: E402

sys.modules[__name__] = _real
