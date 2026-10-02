"""Tool registry.

Each agent role gets the tools listed for it in config/tools.yaml. The model
only sees schemas for those tools, and the loop rejects any call to a name
that is not in the run's registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Awaitable, Callable

import yaml

from app.identity import RunIdentity

DEFAULT_ROLE = "procurement"

Invoke = Callable[[dict[str, Any], RunIdentity], Awaitable[Any]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    invoke: Invoke
    target_field: str | None = None

    def target_of(self, args: dict[str, Any]) -> str:
        if self.target_field is None:
            return self.name
        return str(args.get(self.target_field, ""))

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {t.name: t for t in tools}

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [self._tools[n].schema() for n in self.names()]


@lru_cache(maxsize=1)
def _role_tools(path: str) -> dict[str, list[str]]:
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return {role: list(spec["tools"].keys()) for role, spec in cfg["roles"].items()}


def build_registry(role: str, ident: RunIdentity, deps) -> ToolRegistry:
    from app.tools import documents, erp, memory, payments, slack

    available: dict[str, Tool] = {}
    for module in (documents, erp, memory, payments, slack):
        for tool in module.tools(deps):
            available[tool.name] = tool

    roles = _role_tools(str(deps.settings.tools_path))
    allowed = roles.get(role, roles[DEFAULT_ROLE])
    return ToolRegistry([available[name] for name in allowed if name in available])
