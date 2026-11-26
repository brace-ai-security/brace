"""Running the package as a module. Run it as `python -I -m open_agent_security <folder>`: without
-I, Python puts the current folder first on sys.path, so a scanned repository's own tomllib.py,
argparse.py or open_agent_security/ would be imported instead. The open-agent-security command,
tools/brace/scan.py, the GitHub Action and the pre-commit hook do not have this problem."""
import sys

from .cli import main

sys.exit(main())
