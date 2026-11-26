"""Run open-agent-security from a checkout: `python3 -I tools/brace/scan.py [args]`.

The GitHub Action runs this file. Under -I the script's folder is not on sys.path, so it is
added here; nothing from the scanned folder is ever importable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from open_agent_security.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
