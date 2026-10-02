"""Startup checks: compare the running artifacts with the release manifest."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from app.identity import compute_agent_type_id
from app.settings import Settings

log = logging.getLogger(__name__)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def running_state_mismatches(settings: Settings, manifest: dict) -> list[str]:
    mismatches: list[str] = []
    if settings.image_digest != manifest["image"]["digest"]:
        mismatches.append(f"image: running {settings.image_digest}")
    for name, entry in manifest["prompts"].items():
        path = settings.prompt_dir / Path(entry["path"]).name
        if not path.exists() or sha256_file(path) != entry["sha256"]:
            mismatches.append(f"prompt:{name}")
    for name in ("policy", "tools"):
        entry = manifest["config"][name]
        path = settings.policy_path if name == "policy" else settings.tools_path
        if sha256_file(path) != entry["sha256"]:
            mismatches.append(f"config:{name}")
    if settings.model_id != manifest["models"]["primary"]["model_id"]:
        mismatches.append("model:primary")
    if settings.extractor_model_id != manifest["models"]["extractor"]["model_id"]:
        mismatches.append("model:extractor")
    return mismatches


def startup_checks(settings: Settings) -> str:
    """Return the agent-type-id for this process."""
    manifest = settings.manifest
    mismatches = running_state_mismatches(settings, manifest)
    if mismatches:
        log.error("running state differs from release manifest: %s", ", ".join(mismatches))
    agent_type_id = compute_agent_type_id(manifest)
    log.info("agent_type_id=%s release=%s", agent_type_id, manifest["release"])
    return agent_type_id
