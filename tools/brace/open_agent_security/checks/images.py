"""AP10: base images not pinned to a digest.

A project check: an unpinned image only matters where an agent runs, so it reports only
when the folder shows an agent (agent config, an agent SDK, or another finding).
"""
from __future__ import annotations

from typing import Iterator

from ..model import CheckContext, Document, Finding, Image, Project


def unpinned(img: Image) -> bool:
    ref = img.ref
    return not (img.stage or "@sha256:" in ref or ref.lower() == "scratch"
                or ref.startswith(("$", "{")) or "{{" in ref)


class UnpinnedImages:
    name = "unpinned-images"
    emits = ("AP10",)
    scope = "project"

    def facts(self, doc: Document):
        """The unpinned base images of one file: all this check needs once the file is read."""
        images = tuple(img for img in doc.images if unpinned(img))
        return (doc.source.display, images) if images else None

    def run(self, project: Project, ctx: CheckContext) -> Iterator[Finding]:
        if not project.is_agent_repo:
            return
        for display, images in project.of(self):
            for img in images:
                yield Finding("AP10", display, img.line, f"FROM {img.ref}")
