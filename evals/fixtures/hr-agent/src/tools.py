"""Tool registry: the only tools this agent can see or call."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

import yaml

CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent / "config"


def load_yaml(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    kind: str
    qualified: str
    reason: str
    scope: str
    approval: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    server: str | None = None
    target_template: str | None = None
    fingerprint: str | None = None
    direct_route: dict[str, str] | None = field(default=None, hash=False)

    def target(self, subject: str) -> str:
        return (self.target_template or self.qualified).format(subject=subject)


class ToolRegistry:
    def __init__(self, raw: dict[str, Any]):
        self.policy_version: str = raw["policy_version"]
        self.servers: dict[str, dict[str, str]] = raw["servers"]
        self._tools: dict[str, ToolSpec] = {}
        for name, t in raw["tools"].items():
            if not t.get("reason"):
                raise ValueError(f"tool {name} has no task reason")
            if t["approval"] not in ("none", "subject"):
                raise ValueError(f"tool {name}: unknown approval mode")
            self._tools[name] = ToolSpec(
                name=name,
                kind=t["kind"],
                qualified=t.get("qualified", name),
                reason=t["reason"],
                scope=t["scope"],
                approval=t["approval"],
                input_schema=t["input_schema"],
                output_schema=t.get("output_schema"),
                server=t.get("server"),
                target_template=t.get("target"),
                fingerprint=t.get("fingerprint"),
                direct_route=t.get("direct_route"),
            )

    @classmethod
    def from_config(cls) -> "ToolRegistry":
        return cls(load_yaml("tools.yaml"))

    def get(self, name: str) -> ToolSpec | None:
        # Exact key lookup only; no prefix, case folding or alias matching.
        return self._tools.get(name)

    def by_qualified(self, qualified: str) -> ToolSpec | None:
        for spec in self._tools.values():
            if spec.qualified == qualified:
                return spec
        return None

    def model_schemas(self) -> list[dict[str, Any]]:
        return [
            {"name": s.name, "description": s.reason, "input_schema": s.input_schema}
            for s in self._tools.values()
        ]
