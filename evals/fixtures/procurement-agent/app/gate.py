"""Policy gate for tool calls.

Runs in the harness between the model's proposed call and the integration.
High-impact operations are denied unless a valid approval exists; when none
exists an approval request is opened and the call returns as pending.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.approvals import ApprovalStore
from app.identity import RunIdentity


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str
    policy_version: str
    approval_id: str | None = None
    pending: bool = False


class PolicyGate:
    def __init__(self, policy: dict, approvals: ApprovalStore):
        self.version: str = policy["version"]
        self.high_impact: frozenset[str] = frozenset(policy["high_impact_tools"])
        self.erp_read_prefixes: tuple[str, ...] = tuple(policy["erp"]["read_prefixes"])
        self.approvals = approvals

    async def authorize(self, ident: RunIdentity, tool, args: dict[str, Any]) -> Decision:
        if tool.name == "erp_call":
            operation = str(args.get("operation", ""))
            if not operation.startswith(self.erp_read_prefixes):
                return Decision(False, f"erp operation not permitted: {operation}", self.version)
            return Decision(True, "erp read operation", self.version)

        if tool.name == "post_slack_message":
            if args.get("external", False):
                return await self._require_approval(ident, tool, args)
            return Decision(True, "internal staff message", self.version)

        if tool.name in self.high_impact:
            return await self._require_approval(ident, tool, args)

        return Decision(True, "low-impact tool", self.version)

    async def _require_approval(self, ident: RunIdentity, tool, args: dict[str, Any]) -> Decision:
        target = tool.target_of(args)
        approval = await self.approvals.find_valid(ident, tool.name, target)
        if approval is not None:
            return Decision(True, "approved", self.version, approval_id=approval.id)
        approval_id = await self.approvals.request(ident, tool.name, target, args)
        return Decision(
            False,
            "approval required; request opened",
            self.version,
            approval_id=approval_id,
            pending=True,
        )
