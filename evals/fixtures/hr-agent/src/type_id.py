"""agent-type-id: SHA-256 over every identity-defining input.

Inputs (all, no exclusions):
  - every file under src/, prompts/ and config/, plus requirements.txt and Dockerfile
  - the image digest the pod runs
  - the model record (provider, requested ID, snapshot/alias label, adapter)
Canonical form: JSON with sorted keys, no whitespace, file paths relative to the repo root
in POSIX form, each file hashed as raw bytes. The same command runs in CI (to stamp the
release manifest) and at pod start (to refuse running under an identity it does not match).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
INPUT_DIRS = ("src", "prompts", "config")
INPUT_FILES = ("requirements.txt", "Dockerfile")
HASH_SCHEME = "acme-agent-type-id/v1"


def _file_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for d in INPUT_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file():
                out[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    for f in INPUT_FILES:
        out[f] = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    return out


def compute(image_digest: str, model: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not image_digest.startswith("sha256:") or len(image_digest) != 71:
        raise ValueError("image digest must be sha256:<64 hex>")
    for k in ("provider", "id", "pinning", "adapter"):
        if k not in model:
            raise ValueError(f"model record missing {k}")
    manifest = {"scheme": HASH_SCHEME, "image_digest": image_digest, "model": model, "files": _file_hashes()}
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest(), manifest


def model_record(cfg: dict[str, Any]) -> dict[str, Any]:
    m = cfg["model"]
    return {"provider": m["provider"], "id": m["id"], "pinning": m["pinning"], "adapter": m["adapter"]}


def verify_or_exit(expected: str, image_digest: str, model: dict[str, Any]) -> str:
    actual, _ = compute(image_digest, model)
    if actual != expected:
        print(f"agent-type-id mismatch: expected {expected}, computed {actual}", file=sys.stderr)
        sys.exit(78)
    return actual


if __name__ == "__main__":
    import yaml

    cfg = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
    tid, man = compute(sys.argv[1], model_record(cfg))
    json.dump({"agent_type_id": tid, "inputs": man}, sys.stdout, indent=2, sort_keys=True)
