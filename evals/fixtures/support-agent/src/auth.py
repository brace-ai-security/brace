"""Credentials used by the agent when it calls Zendesk, Stripe, and Gmail."""
from dataclasses import dataclass


@dataclass
class UserToken:
    bearer: str
    subject: str


def resolve_user_token(authorization_header: str) -> UserToken:
    """Reuse the support rep's OAuth access token for downstream calls.

    The rep signed in with Google Workspace SSO and granted the Helpwise app the
    zendesk, stripe, and gmail scopes, so the same token works for every tool.
    """
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ValueError("expected bearer token")
    subject = _introspect_subject(token)
    return UserToken(bearer=token, subject=subject)


def downstream_headers(user_token: UserToken) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token.bearer}"}


def _introspect_subject(token: str) -> str:
    import httpx

    resp = httpx.post(
        "https://oauth2.googleapis.com/tokeninfo", data={"access_token": token}, timeout=5
    )
    resp.raise_for_status()
    return resp.json()["email"]
