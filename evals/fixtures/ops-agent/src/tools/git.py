"""git runner for infra repositories cloned under /work."""
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())["tools"]
WORK = Path("/work")


def git(repo: str, args: str) -> str:
    parts = args.split()
    if not parts or parts[0] not in CFG["git_subcommands"]:
        return f"git {parts[0] if parts else ''} is not allowed."
    repo_dir = WORK / repo
    env = dict(os.environ, GIT_ASKPASS="/bin/echo", GIT_TERMINAL_PROMPT="0")
    # Authenticate pushes with the platform bot's token.
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
    env["GIT_CONFIG_VALUE_0"] = f"Authorization: Bearer {os.environ['GITHUB_TOKEN']}"
    proc = subprocess.run(["git", *parts], cwd=repo_dir, env=env, capture_output=True, text=True, timeout=300)
    return (proc.stdout + proc.stderr)[-20000:]
