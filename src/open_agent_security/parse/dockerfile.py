"""Dockerfiles and Containerfiles: the base images in FROM lines.

Continuation lines and heredoc bodies are skipped, so a SQL "FROM" inside a RUN is not an image.
Comment lines never continue an instruction, and a `# escape=`` ` parser directive changes the
continuation character.
"""
from __future__ import annotations

import bisect
import re
from pathlib import Path

from ..limits import MAX_PER_FILE
from ..model import Document, Image, SourceFile

FROM_LINE = re.compile(r"^[ \t]*FROM[ \t]+(?:--platform=\S+[ \t]+)?(\S+)(?:[ \t]+AS[ \t]+(\S+))?", re.I | re.M)
# Dockerfile heredocs (`RUN <<EOF`, `COPY <<-"EOF" /x`); not `<<<` here-strings or `a << b`.
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")
HEREDOC_INSTRUCTIONS = {"RUN", "COPY", "ADD"}
# `Dockerfile.<tag>` is a Dockerfile unless the tag is a known non-Docker extension.
DIRECTIVE = re.compile(r"^[ \t]*#[ \t]*([A-Za-z]+)[ \t]*=[ \t]*(\S*)[ \t]*$")
NOT_DOCKER = {".py", ".go", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".rb", ".rs", ".java", ".kt", ".md", ".txt", ".json",
              ".jsonc", ".yaml", ".yml", ".toml", ".sh", ".bash", ".zsh", ".ps1", ".ini", ".cfg", ".env"}


def is_dockerfile(low: str) -> bool:
    """`Dockerfile`, `Containerfile`, `Dockerfile.<tag>`, `Containerfile.<tag>`, `*.dockerfile` and
    `*.containerfile` (a lowercased path)."""
    name = Path(low).name
    if name in ("dockerfile", "containerfile") or name.endswith((".dockerfile", ".containerfile")):
        return True
    return name.startswith(("dockerfile.", "containerfile.")) and Path(name).suffix not in NOT_DOCKER


class Dockerfile:
    name = "dockerfile"

    def claims(self, src: SourceFile) -> bool:
        return src.origin == "repo" and is_dockerfile(src.display.lower())

    def parse(self, src: SourceFile, doc: Document) -> None:
        lines = src.text.split("\n")
        escape = escape_char(lines)
        body = heredoc_bodies(lines, escape) if "<<" in src.text else set()
        stages, continued = set(), False
        for n, line in enumerate(lines, 1):
            if n in body or is_comment(line):
                continue
            prev, continued = continued, line.rstrip().endswith(escape)
            if prev:
                continue  # part of the previous instruction, e.g. a SQL "FROM" inside RUN
            m = FROM_LINE.match(line)
            if not m:
                continue
            img, alias = m.group(1), m.group(2)
            doc.images.append(Image(img, n, img.lower() in stages))
            if len(doc.images) > MAX_PER_FILE:
                return  # one more than the findings cap, so the cap still shows the file is cut short
            if alias:
                stages.add(alias.lower())


def is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def escape_char(lines: list[str]) -> str:
    """The line-continuation character: `\\`, or the one an `# escape=` parser directive sets.
    Directives come before any other line; the first line that is not one ends them."""
    for line in lines:
        m = DIRECTIVE.match(line)
        if not m:
            break
        if m.group(1).lower() == "escape" and m.group(2) in ("`", "\\"):
            return m.group(2)
    return "\\"


def heredoc_bodies(lines: list[str], escape: str) -> set[int]:
    """Line numbers inside heredoc bodies of RUN, COPY and ADD. A heredoc whose end word never
    comes is not one, so it hides nothing after it."""
    ends: dict[str, list[int]] = {}
    for n, line in enumerate(lines, 1):
        ends.setdefault(line.strip(), []).append(n)
    body: set[int] = set()
    instruction, continued, n = "", False, 1
    while n <= len(lines):
        line = lines[n - 1]
        if is_comment(line):
            n += 1
            continue
        if not continued:
            instruction = line.split(None, 1)[0].upper() if line.strip() else ""
        continued = line.rstrip().endswith(escape)
        h = HEREDOC.search(line) if instruction in HEREDOC_INSTRUCTIONS else None
        if h:
            at = ends.get(h.group(2), [])
            k = bisect.bisect_right(at, n)
            if k < len(at):
                body.update(range(n + 1, at[k] + 1))
                n, continued = at[k] + 1, False
                continue
        n += 1
    return body
