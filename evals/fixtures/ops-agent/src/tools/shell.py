"""kubectl and helm runners."""
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())["tools"]


def _run(command: str, timeout: int = 120) -> str:
    proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
    return (proc.stdout + proc.stderr)[-20000:]


def kubectl(args: str, context: str) -> str:
    verb = args.split()[0] if args.split() else ""
    if verb not in CFG["kubectl_verbs"]:
        return f"kubectl {verb} is not allowed."
    return _run(f"kubectl --context {context} {args}")


def helm(args: str, context: str) -> str:
    return _run(f"helm --kube-context {context} {args}")
