"""Run the `brace` command line from this Action's own checkout: `python -I brace_run.py <command> ...`.

Under -I neither the workspace nor the script's folder is on sys.path, so a json.py or yaml.py in
the reviewed repository can never be imported; only the Action's src/ folder is added.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from brace_tools.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
