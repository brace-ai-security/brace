"""sha256 over the image reference, harness, system prompt, model id, and config."""
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _tree(path: Path) -> str:
    files = sorted(p for p in path.rglob("*") if p.is_file() and not any(s.startswith((".", "__")) for s in p.relative_to(path).parts))
    return _h("".join(f"{p.relative_to(path).as_posix()}\n{_h(p.read_bytes())}\n" for p in files).encode())


@lru_cache(maxsize=1)
def agent_type_id() -> str:
    import yaml

    cfg = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
    inputs = {
        "config": _h((ROOT / "config" / "agent.yaml").read_bytes()),
        "container": _h(os.environ["IMAGE_REF"].encode()),
        "harness": _tree(ROOT / "src"),
        "model": _h(f"{cfg['model']['provider']}/{cfg['model']['id']}".encode()),
        "system_prompt": _h((ROOT / "prompts" / "system.md").read_bytes()),
    }
    doc = [{"name": k, "digest": v} for k, v in sorted(inputs.items())]
    return "sha256:" + _h(json.dumps(doc, separators=(",", ":"), sort_keys=True).encode())
