#!/usr/bin/env python3
"""Deprecated launcher for the BRACE record checker; use the `brace` command instead.

`python tools/brace/brace.py <command>` keeps working for one release. Install the tools with
`pip install "open-agent-security[record]"` and run `brace <command>`. The code lives in
src/brace_tools/record/core.py; importing this file aliases that module.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

if __name__ == "__main__" and sys.argv[1:2] == ["scan"]:  # the scanner needs only the standard library
    from open_agent_security.cli import main as _scan_main
    sys.exit(_scan_main(sys.argv[2:]))

try:
    from brace_tools.record import core as _real
except ModuleNotFoundError as exc:
    if exc.name not in ("yaml", "jsonschema"):
        raise
    sys.stderr.write('brace.py needs PyYAML. Install it with: pip install pyyaml '
                     '(or pip install "open-agent-security[record]")\n')
    sys.exit(2)

if __name__ == "__main__":
    sys.exit(_real.main())
sys.modules[__name__] = _real
