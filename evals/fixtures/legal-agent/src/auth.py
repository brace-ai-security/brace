"""Caller authentication and matter sessions.

The lawyer's identity comes only from a verified OIDC access token. The matter a session works on
is fixed when the session is opened, after a staffing and ethical-wall check against the conflicts
service. Nothing the model produces can change the session's user or matter.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

import httpx
import jwt
from fastapi import Header, HTTPException

from src.config import settings
from src.identity import workload_token

_jwks = jwt.PyJWKClient(settings["auth"]["jwks_url"], cache_keys=True, lifespan=300)


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    role: str  # associate | partner | paralegal


@dataclass
class Session:
    session_id: str
    principal: Principal
    matter_id: str
    matter_name: str
    trace_parent: str
    opened_at: float = field(default_factory=time.time)


_sessions: dict[str, Session] = {}


def authenticate(authorization: str = Header(...)) -> Principal:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        key = _jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=settings["auth"]["audience"],
            issuer=settings["auth"]["issuer"],
            leeway=settings["auth"]["leeway_seconds"],
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid token") from exc
    role = claims.get("hp_role")
    if role not in {"associate", "partner", "paralegal"}:
        raise HTTPException(403, "role not permitted")
    return Principal(user_id=claims["sub"], email=claims["email"], role=role)


def open_session(principal: Principal, matter_id: str, trace_parent: str) -> Session:
    """Check staffing and walls with the conflicts service, then pin the matter."""
    resp = httpx.get(
        f"{settings['conflicts']['base_url']}/v1/access-check",
        params={"user": principal.user_id, "matter": matter_id},
        headers={"Authorization": f"Bearer {workload_token(settings['conflicts']['audience'])}"},
        timeout=5,
    )
    if resp.status_code != 200:
        raise HTTPException(503, "conflicts service unavailable")
    body = resp.json()
    if body.get("staffed") is not True or body.get("screened") is not False:
        raise HTTPException(403, "not permitted on this matter")
    session = Session(
        session_id=secrets.token_urlsafe(24),
        principal=principal,
        matter_id=matter_id,
        matter_name=body["matter_name"],
        trace_parent=trace_parent,
    )
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str, principal: Principal) -> Session:
    session = _sessions.get(session_id)
    if session is None or session.principal.user_id != principal.user_id:
        raise HTTPException(404, "no such session")
    return session
