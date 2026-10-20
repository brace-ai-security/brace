"""Runtime settings, read once from the environment at process start."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"missing required setting {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    erp_mcp_url: str
    payments_api_url: str
    slack_api_url: str
    sts_url: str
    oidc_issuer: str
    oidc_audience: str
    oidc_jwks_url: str
    workload_token_path: str
    slack_signing_secret_path: str
    mail_gateway_hmac_path: str
    model_id: str
    extractor_model_id: str
    manifest_path: Path
    prompt_dir: Path
    policy_path: Path
    tools_path: Path
    operational_owner: str
    image_digest: str

    @property
    def policy(self) -> dict:
        return _load_yaml(self.policy_path)

    @property
    def manifest(self) -> dict:
        return _load_yaml(self.manifest_path)

    @property
    def budgets(self) -> dict:
        return self.policy["budgets"]


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root = Path(_env("APP_ROOT", "/app"))
    return Settings(
        database_url=_env("DATABASE_URL"),
        erp_mcp_url=_env("ERP_MCP_URL"),
        payments_api_url=_env("PAYMENTS_API_URL"),
        slack_api_url=_env("SLACK_API_URL", "https://slack.com/api"),
        sts_url=_env("STS_URL"),
        oidc_issuer=_env("OIDC_ISSUER"),
        oidc_audience=_env("OIDC_AUDIENCE", "procurement-agent"),
        oidc_jwks_url=_env("OIDC_JWKS_URL"),
        workload_token_path=_env(
            "WORKLOAD_TOKEN_PATH", "/var/run/secrets/tokens/procurement-agent"
        ),
        slack_signing_secret_path=_env(
            "SLACK_SIGNING_SECRET_PATH", "/var/run/secrets/slack/signing-secret"
        ),
        mail_gateway_hmac_path=_env(
            "MAIL_GATEWAY_HMAC_PATH", "/var/run/secrets/mail/hmac-key"
        ),
        model_id=_env("MODEL_ID"),
        extractor_model_id=_env("EXTRACTOR_MODEL_ID"),
        manifest_path=root / "release" / "manifest.yaml",
        prompt_dir=root / "prompts",
        policy_path=root / "config" / "policy.yaml",
        tools_path=root / "config" / "tools.yaml",
        operational_owner=_env("OPERATIONAL_OWNER", "team-procurement-platform"),
        image_digest=_env("IMAGE_DIGEST"),
    )
