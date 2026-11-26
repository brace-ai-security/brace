"""AP03: an agent workflow triggered by pull_request_target."""
from __future__ import annotations

from typing import Iterator

from ..model import CheckContext, Document, Finding


class PullRequestTarget:
    name = "pull-request-target"
    emits = ("AP03",)
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        wf = doc.workflow
        if wf and wf.trigger_line and wf.agent_step:
            yield Finding("AP03", doc.source.display, wf.trigger_line, "pull_request_target + agent step")
