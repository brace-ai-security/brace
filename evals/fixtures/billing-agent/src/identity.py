"""Verified run context and agent-type identity."""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

import jwt

ROOT = Path(__file__).resolve().parent.parent

IDP_ISSUER = "https://idp.ledgerly.io/"
IDP_JWKS_URL = "https://idp.ledgerly.io/.well-known/jwks.json"
AUDIENCE = "billing-agent"

TYPE_ID_INPUTS = ["Dockerfile", "requirements.txt", ".mcp.json", "src", "prompts", "config"]
_IGNORED_SUFFIXES = {".pyc", ".md", ".lock"}

_jwks = jwt.PyJWKClient(IDP_JWKS_URL, cache_keys=True, lifespan=300)


@dataclass(frozen=True)
class RunContext:
    tenant_id: str
    accountable_party: str
    operational_owner: str
    agent_type_id: str
    agent_instance_id: str
    trace_id: str
    parent_instance_id: str | None = None

    def child(self, agent_type_id: str) -> "RunContext":
        return replace(
            self,
            agent_type_id=agent_type_id,
            agent_instance_id=f"inst-{uuid.uuid4().hex[:16]}",
            parent_instance_id=self.agent_instance_id,
        )


def compute_agent_type_id(model_id: str, image_digest: str | None = None, root: Path = ROOT) -> str:
    image_digest = image_digest or os.environ.get("IMAGE_DIGEST", "unknown")
    h = hashlib.sha256()
    h.update(f"image\0{image_digest}\n".encode())
    h.update(f"model\0{model_id}\n".encode())
    for rel in TYPE_ID_INPUTS:
        p = root / rel
        if not p.exists():
            continue
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
        for f in files:
            if f.suffix in _IGNORED_SUFFIXES or "__pycache__" in f.parts:
                continue
            h.update(f.relative_to(root).as_posix().encode() + b"\0")
            h.update(hashlib.sha256(f.read_bytes()).digest())
    return "bat-" + h.hexdigest()[:40]


def context_from_token(token: str, cfg: dict, agent_type_id: str, trace_id: str) -> RunContext:
    key = _jwks.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        key.key,
        algorithms=["RS256", "ES256"],
        audience=AUDIENCE,
        issuer=IDP_ISSUER,
        options={"require": ["exp", "iat", "sub", "ledgerly/tenant"]},
    )
    return RunContext(
        tenant_id=claims["ledgerly/tenant"],
        accountable_party=f"user:{claims['sub']}",
        operational_owner=cfg["agent"]["operational_owner"],
        agent_type_id=agent_type_id,
        agent_instance_id=f"inst-{uuid.uuid4().hex[:16]}",
        trace_id=trace_id,
    )


def scheduler_context(tenant_id: str, cfg: dict, agent_type_id: str) -> RunContext:
    return RunContext(
        tenant_id=tenant_id,
        accountable_party="service:dunning-scheduler",
        operational_owner=cfg["agent"]["operational_owner"],
        agent_type_id=agent_type_id,
        agent_instance_id=f"inst-{uuid.uuid4().hex[:16]}",
        trace_id=uuid.uuid4().hex,
    )
