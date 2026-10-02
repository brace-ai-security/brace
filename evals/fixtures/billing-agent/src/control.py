"""Operator control flags and sweep cursor, stored in ConfigMaps."""
from __future__ import annotations

import time
from pathlib import Path

import httpx

_SA = Path("/var/run/secrets/kubernetes.io/serviceaccount")
_API = "https://kubernetes.default.svc"


class KubeConfigMaps:
    def __init__(self, namespace: str):
        self.ns = namespace
        self.http = httpx.Client(verify=str(_SA / "ca.crt"), timeout=5.0)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {(_SA / 'token').read_text().strip()}"}

    def get(self, name: str) -> dict:
        r = self.http.get(f"{_API}/api/v1/namespaces/{self.ns}/configmaps/{name}", headers=self._headers())
        r.raise_for_status()
        return r.json().get("data") or {}

    def patch(self, name: str, data: dict) -> None:
        r = self.http.patch(
            f"{_API}/api/v1/namespaces/{self.ns}/configmaps/{name}",
            json={"data": data},
            headers={**self._headers(), "Content-Type": "application/merge-patch+json"},
        )
        r.raise_for_status()


class Halted(Exception):
    pass


class ControlFlag:
    def __init__(self, cms: KubeConfigMaps, name: str, ttl: float = 5.0):
        self.cms = cms
        self.name = name
        self.ttl = ttl
        self._checked = 0.0
        self._halted = False

    def halted(self) -> bool:
        if time.monotonic() - self._checked > self.ttl:
            try:
                self._halted = self.cms.get(self.name).get("halted", "false").lower() == "true"
            except httpx.HTTPError:
                self._halted = True
            self._checked = time.monotonic()
        return self._halted

    def check(self) -> None:
        if self.halted():
            raise Halted("operator halt flag set")
