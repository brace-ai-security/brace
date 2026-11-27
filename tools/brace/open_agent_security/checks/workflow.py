"""AP03: an agent workflow triggered by pull_request_target, directly or through a local action
or reusable workflow in the same repository."""
from __future__ import annotations

from typing import Iterator

from ..model import CheckContext, Document, Finding, Project
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


LOCAL_DEPTH = 3  # local actions and reusable workflows followed from a workflow


class LocalAgentSteps:
    """AP03 for a pull_request_target workflow whose agent runs in a local composite action
    (`uses: ./.github/actions/review`) or reusable workflow (`uses: ./.github/workflows/x.yml`),
    followed up to LOCAL_DEPTH levels within the repository. Paths are relative to the root of
    the workflow's repository (the folder holding its .github)."""
    name = "pull-request-target-local"
    emits = ("AP03",)
    scope = "project"

    def facts(self, doc: Document):
        wf = doc.workflow
        if wf is None:
            return None
        direct = wf.agent_step or bool(wf.trigger_line and wf.local_uses and bypassed(doc, CheckContext()))
        return doc.source.display, wf.trigger_line, direct, wf.local_uses

    def run(self, project: Project, ctx: CheckContext) -> Iterator[Finding]:
        files = {display: (trigger, direct, uses) for display, trigger, direct, uses in project.of(self)}
        for display, (trigger, direct, uses) in files.items():
            if not trigger or direct or not uses:
                continue
            at = display.lower().rfind(".github/")
            root = display[:at] if at >= 0 else ""
            via = agent_via(files, root, uses)
            if via:
                yield Finding("AP03", display, trigger, f"pull_request_target + agent step in ./{via}")


def agent_via(files: dict, root: str, uses: tuple[str, ...]) -> str:
    """The first local action or reusable workflow, reached from `uses` within LOCAL_DEPTH levels,
    that runs an agent, or ''."""
    level, seen = [(u, u) for u in uses], set()
    for _ in range(LOCAL_DEPTH):
        nxt = []
        for first, use in level:
            for path in local_files(root, use):
                if path in files and path not in seen:
                    seen.add(path)
                    _, direct, more = files[path]
                    if direct:
                        return first or "action.yml"  # `uses: ./`: the root's action.yml
                    nxt += [(first, u) for u in more]
        level = nxt
    return ""


def local_files(root: str, use: str) -> list[str]:
    """The files a local `uses:` can name: a reusable workflow, or an action folder's action.yml
    (`uses: ./` names the repository root's)."""
    path = root + use
    if path.lower().endswith((".yml", ".yaml")):
        return [path]
    path += "/" if use else ""
    return [path + "action.yml", path + "action.yaml"]
