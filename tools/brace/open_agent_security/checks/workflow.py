"""AP03: an agent workflow triggered by pull_request_target."""
from __future__ import annotations

from typing import Iterator

from ..model import CheckContext, Document, Finding
from .permissions import PermissionFlags


class PullRequestTarget:
    name = "pull-request-target"
    emits = ("AP03",)
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        wf = doc.workflow
        if wf and wf.trigger_line and (wf.agent_step or bypassed(doc, ctx)):
            yield Finding("AP03", doc.source.display, wf.trigger_line, "pull_request_target + agent step")


def bypassed(doc: Document, ctx: CheckContext) -> bool:
    """A workflow that passes an agent a bypass flag (an AP02 finding) runs an agent, whatever the
    step looks like (`cat prompt.txt | claude --dangerously-skip-permissions`)."""
    return any(True for _ in PermissionFlags().run(doc, ctx))
