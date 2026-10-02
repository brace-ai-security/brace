"""Content-derived fingerprint of this agent type.

Inputs: container image digest, harness source, system prompt, model id, agent config,
and the MCP server list. Same inputs give the same id; any change gives a new id.
"""
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dir_digest(path: Path) -> str:
    lines = []
    for f in sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = f.relative_to(path).as_posix()
        lines.append(f"{rel}\n{_sha256(f.read_bytes())}\n")
    return _sha256("".join(lines).encode())


@lru_cache(maxsize=1)
def agent_type_id() -> str:
    config = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
    inputs = [
        {"name": "container", "digest": _sha256(os.environ["IMAGE_DIGEST"].encode())},
        {"name": "harness", "digest": _dir_digest(ROOT / "src")},
        {"name": "system_prompt", "digest": _sha256((ROOT / "prompts" / "system.md").read_bytes())},
        {"name": "model", "digest": _sha256(f"{config['model']['provider']}/{config['model']['id']}".encode())},
        {"name": "config", "digest": _sha256((ROOT / "config" / "agent.yaml").read_bytes())},
        {"name": "mcp_servers", "digest": _sha256((ROOT / ".mcp.json").read_bytes())},
    ]
    inputs.sort(key=lambda i: i["name"])
    blob = json.dumps(inputs, separators=(",", ":"), sort_keys=True).encode()
    return "sha256:" + _sha256(blob)
