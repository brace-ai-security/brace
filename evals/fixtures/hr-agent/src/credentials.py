"""Per-tool, per-employee, short-lived tokens for the agent's own workload identity.

The pod's projected service-account token (audience sts.acme.example, 10 min) is the
actor token. The employee's verified SSO token is the subject token. The STS returns an
RFC 8693 token whose `sub` is the employee, `act.sub` is this workload, `aud` is the
requested audience, `scope` is exactly one tool scope, and `cnf.x5t#S256` binds it to the
pod's mTLS certificate. Lifetime is 300 s: long enough for one approval-to-execute window
on a single call, short enough that a copied token is useless after the run.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

STS_URL = "https://sts.identity.svc.cluster.local/oauth2/token"
ACTOR_TOKEN_PATH = "/var/run/secrets/tokens/sts-token"
TOKEN_TTL_SECONDS = 300
REFRESH_MARGIN_SECONDS = 30


@dataclass
class _Cached:
    token: str
    expires_at: float


class CredentialBroker:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client  # configured with the pod's SPIFFE SVID for mTLS
        self._cache: dict[tuple[str, str, str], _Cached] = {}
        self._lock = asyncio.Lock()

    def _actor_token(self) -> str:
        # Re-read each time: kubelet rotates the projected token on disk.
        with open(ACTOR_TOKEN_PATH, encoding="utf-8") as fh:
            return fh.read().strip()

    async def token(self, *, audience: str, scope: str, subject_token: str, subject: str) -> str:
        key = (audience, scope, subject)
        async with self._lock:
            hit = self._cache.get(key)
            if hit and hit.expires_at - REFRESH_MARGIN_SECONDS > time.time():
                return hit.token
            resp = await self._client.post(
                STS_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                    "subject_token": subject_token,
                    "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
                    "actor_token": self._actor_token(),
                    "actor_token_type": "urn:ietf:params:oauth:token-type:jwt",
                    "audience": audience,
                    "scope": scope,
                    "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                    "requested_ttl": str(TOKEN_TTL_SECONDS),
                },
                timeout=3.0,
            )
            resp.raise_for_status()
            body = resp.json()
            ttl = min(int(body.get("expires_in", TOKEN_TTL_SECONDS)), TOKEN_TTL_SECONDS)
            self._cache[key] = _Cached(body["access_token"], time.time() + ttl)
            return body["access_token"]

    def drop_subject(self, subject: str) -> None:
        for key in [k for k in self._cache if k[2] == subject]:
            del self._cache[key]
