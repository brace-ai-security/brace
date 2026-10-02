"""Agent workload identity, instance identity, and release identity."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from src.config import ROOT, release, settings, tools_config

# Projected service-account tokens, one per audience, rotated by the kubelet (see k8s/deployment.yaml).
_TOKEN_DIR = Path("/var/run/secrets/agent-tokens")
_AUDIENCE_FILES = {
    "api://conflicts": "conflicts",
    "api://qdrant-matter-index": "qdrant",
    "api://agent-memory": "memory",
    "api://smtp-relay": "smtp",
}


def workload_token(audience: str) -> str:
    """Return the agent's own short-lived token for one downstream audience.

    The token's subject is the agent's Kubernetes service account
    (system:serviceaccount:counsel-research:counsel-research-agent), never the lawyer.
    """
    name = _AUDIENCE_FILES.get(audience)
    if name is None:
        raise PermissionError(f"no token issued for audience {audience}")
    return (_TOKEN_DIR / name / "token").read_text().strip()


POD_NAME = os.environ.get("POD_NAME", "local")


def new_instance_id() -> str:
    """One instance id per research run, assigned by the harness."""
    return f"{POD_NAME}/{uuid.uuid4()}"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_type_id() -> str:
    manifest = json.loads((ROOT / release["models"]["drafting"]["manifest"]).read_text())
    material = {
        "image": release["image"],
        "graph_version": settings["service"]["graph_version"],
        "prompt_version": settings["service"]["prompt_version"],
        "model": f"{manifest['model_id']}@{manifest['version']}",
        "base_model": manifest["base_model"],
        "tools": _sha256_file(ROOT / "config" / "tools.yaml"),
        "settings": _sha256_file(ROOT / "config" / "settings.yaml"),
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "atid:" + hashlib.sha256(canonical.encode()).hexdigest()[:32]


class ReleaseMismatch(RuntimeError):
    pass


def verify_release() -> None:
    """Refuse to start if the running configuration does not match the approved release."""
    manifest = json.loads((ROOT / release["models"]["drafting"]["manifest"]).read_text())
    if settings["service"]["prompt_version"] != release["prompt_version"]:
        raise ReleaseMismatch("prompt version")
    if settings["service"]["graph_version"] != release["graph_version"]:
        raise ReleaseMismatch("graph version")
    if settings["service"]["policy_version"] != release["policy_version"]:
        raise ReleaseMismatch("policy version")
    first = manifest["files"][0]["sha256"]
    if f"sha256:{first}" != release["models"]["drafting"]["weights_digest"]:
        raise ReleaseMismatch("drafting weights")
    if os.environ.get("IMAGE_DIGEST", release["image"]) != release["image"]:
        raise ReleaseMismatch("image")
    if set(tools_config["tools"]) - {"search_documents", "read_document", "recall_preferences",
                                     "save_preference", "email_draft"}:
        raise ReleaseMismatch("tool set")


AGENT_TYPE_ID = compute_type_id()
