"""Agent identity: who is acting, for whom, and as which agent type.

The agent runs under its own Kubernetes service account. Its projected
service-account token is exchanged at the internal STS for short-lived,
audience-bound tokens. The launching user's token is never forwarded to an
integration; the user is carried as the delegated subject of the exchange.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path

import httpx

from app.settings import Settings

IDENTITY_FIELDS = (
    "accountable_party",
    "operational_owner",
    "tenant",
    "agent_type_id",
    "agent_instance_id",
    "trace_id",
)


@dataclass(frozen=True)
class RunIdentity:
    accountable_party: str
    operational_owner: str
    tenant: str
    agent_type_id: str
    agent_instance_id: str
    trace_id: str
    run_id: str
    delegated_subject: str
    agent_principal: str
    parent_instance_id: str | None = None
    role: str = "procurement"

    def __post_init__(self) -> None:
        for name in IDENTITY_FIELDS:
            if not getattr(self, name):
                raise ValueError(f"identity field {name} is empty")

    def child(self, role: str) -> "RunIdentity":
        return replace(
            self,
            agent_instance_id=f"inst-{uuid.uuid4()}",
            parent_instance_id=self.agent_instance_id,
            role=role,
        )


def new_instance_id() -> str:
    return f"inst-{uuid.uuid4()}"


def compute_agent_type_id(manifest: dict) -> str:
    """Content-derived agent type id over the frozen release manifest."""
    material = {
        "image_digest": manifest["image"]["digest"],
        "harness_digest": manifest["harness"]["digest"],
        "system_prompt": manifest["prompts"]["system"]["path"],
        "extractor_prompt": manifest["prompts"]["extractor"]["path"],
        "models": manifest["models"],
        "config": manifest["config"],
        "tools": manifest["tool_pins"],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "atid-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:40]


@dataclass
class _CachedToken:
    value: str
    expires_at: float


@dataclass
class TokenBroker:
    """Exchanges the workload token for audience-bound access tokens."""

    settings: Settings
    _cache: dict[tuple[str, str, str], _CachedToken] = field(default_factory=dict)

    def _workload_token(self) -> str:
        return Path(self.settings.workload_token_path).read_text().strip()

    async def token_for(self, audience: str, scope: str, ident: RunIdentity) -> str:
        key = (audience, scope, ident.tenant)
        cached = self._cache.get(key)
        if cached and cached.expires_at - 30 > time.time():
            return cached.value
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                self.settings.sts_url,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                    "subject_token": self._workload_token(),
                    "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
                    "audience": audience,
                    "scope": scope,
                    "resource": f"urn:bu:{ident.tenant}",
                    "actor_token": ident.delegated_subject,
                    "actor_token_type": "urn:example:params:subject-id",
                },
            )
            resp.raise_for_status()
            body = resp.json()
        token = _CachedToken(body["access_token"], time.time() + int(body["expires_in"]))
        self._cache[key] = token
        return token.value
