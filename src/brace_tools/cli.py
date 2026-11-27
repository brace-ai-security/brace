"""The `brace` command line."""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["scan"]:
        from open_agent_security.cli import main as scan_main
        return scan_main(argv[1:])
    if argv[:1] in (["--version"], ["-V"]):
        from brace_tools import __version__
        print(f"brace {__version__}")
        return 0
    sys.stderr.write("usage: brace scan [args]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
