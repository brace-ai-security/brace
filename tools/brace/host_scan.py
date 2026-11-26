"""Alias for open_agent_security.host_scan, so `import host_scan` and `python tools/brace/host_scan.py` keep working.

The code lives in open_agent_security/host_scan.py, the module that the open-agent-security package installs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from open_agent_security import host_scan as _real  # noqa: E402

if __name__ == "__main__":
    sys.exit(_real.main()) if hasattr(_real, "main") else None
else:
    sys.modules[__name__] = _real
