"""AP22: invisible characters in the files an agent reads as instructions.

Bidirectional controls (U+202A-U+202E, U+2066-U+2069), zero-width characters (U+200B-U+200D,
U+2060, and U+FEFF anywhere but the first character) and Unicode tag characters
(U+E0000-U+E007F) are invisible in an editor and in code review, but a model reads them, so a
rules file or tool description can carry text nobody reviewed.

Read in agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules, Cursor and
Windsurf rules, Copilot instructions and prompt files, .clinerules, SKILL.md, Claude Code
commands and subagents) and in agent config files (where MCP tool descriptions live).

Not reported, because text uses them visibly: a zero-width joiner or non-joiner with no ASCII
character beside it (emoji sequences, Persian and Indic scripts), and the tag characters of a
flag emoji (a run that follows U+1F3F4 WAVING BLACK FLAG). The finding names the code points
only; the hidden text itself is never printed (clean() drops these characters from any output).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterator

from ..agents import AGENT_MARKDOWN
from ..model import CheckContext, Document, Finding

HIDDEN = re.compile("[\u202a-\u202e\u2066-\u2069\u200b-\u200d\u2060\ufeff\U000e0000-\U000e007f]")
INSTRUCTIONS = re.compile(
    r"(?:^|/)(?:(?:CLAUDE|CLAUDE\.local|AGENTS|AGENT|GEMINI|QWEN|CONVENTIONS|SKILL)\.md|\.cursorrules|\.windsurfrules|"
    r"\.clinerules(?:/[^/\n]+)*|\.roorules(?:-[\w-]{1,40})?|\.cursor/rules/(?:[^/\n]+/)*[^/\n]+|"
    r"\.windsurf/rules/(?:[^/\n]+/)*[^/\n]+|\.roo/rules(?:-[\w-]{1,40})?/(?:[^/\n]+/)*[^/\n]+|"
    r"\.github/copilot-instructions\.md|\.github/instructions/(?:[^/\n]+/)*[^/\n]+\.md|"
    r"[^/\n]+\.(?:prompt|instructions|chatmode)\.md)$", re.I)
# The same characters written as JSON escapes in agent config (a tool description saved with
# json.dumps holds "\\u200b", not the character). Joiners are left out (escaped emoji use them),
# and so is a flag emoji's escaped tag run.
ESCAPED = re.compile(r"\\u(?:202[a-e]|206[6-9]|200b|2060|feff|db40\\udc[0-7][0-9a-f])", re.I)
ESCAPED_FLAG = re.compile(r"\\ud83c\\udff4(?:\\udb40\\udc[0-7][0-9a-f]){1,8}", re.I)
JOINERS = {"\u200c", "\u200d"}
FLAG = "\U0001f3f4"
TAG_FIRST, TAG_LAST = 0xE0000, 0xE007F
SHOWN = 4  # distinct code points named in a finding


def instruction_file(display: str) -> bool:
    return bool(INSTRUCTIONS.search(display) or AGENT_MARKDOWN.search(display))


def visible_use(text: str, i: int, ch: str) -> bool:
    """Whether the character at i is part of visible text: a joiner between non-ASCII characters,
    or a tag character in a flag emoji's tag run."""
    if ch in JOINERS:
        before = text[i - 1] if i else ""
        after = text[i + 1] if i + 1 < len(text) else ""
        return not (before.isascii() and before) and not (after.isascii() and after)
    if TAG_FIRST <= ord(ch) <= TAG_LAST:
        j = i
        while j > 0 and TAG_FIRST <= ord(text[j - 1]) <= TAG_LAST and i - j < 8:
            j -= 1
        return j > 0 and text[j - 1] == FLAG
    return False


def label(cp: int) -> str:
    if TAG_FIRST <= cp <= TAG_LAST:
        return f"U+{cp:04X} TAG"
    return f"U+{cp:04X} {unicodedata.name(chr(cp), 'UNNAMED')}"


class HiddenUnicode:
    name = "hidden-unicode"
    emits = ("AP22",)
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        src = doc.source
        if not (src.is_agent_config or instruction_file(src.display)):
            return
        text = src.text
        first = count = last = 0
        line = 1
        lines: set[int] = set()
        seen: dict[int, None] = {}
        for m in HIDDEN.finditer(text):
            i, ch = m.start(), m.group(0)
            if (ch == "\ufeff" and i == 0) or visible_use(text, i, ch):
                continue
            line += text.count("\n", last, i)
            last = i
            first = first or line
            count += 1
            lines.add(line)
            seen.setdefault(ord(ch), None)
        if src.is_agent_config and "\\u" in text:
            plain = ESCAPED_FLAG.sub("", text)
            line, last = 1, 0
            for m in ESCAPED.finditer(plain):
                line += plain.count("\n", last, m.start())
                last = m.start()
                esc = m.group(0).lower()
                cp = 0xE0000 + int(esc[-2:], 16) if esc.startswith("\\udb40") else int(esc[2:], 16)
                first = min(first, line) if first else line
                count += 1
                lines.add(line)
                seen.setdefault(cp, None)
        if count:
            names = [label(cp) for cp in list(seen)[:SHOWN]]
            more = f" and {len(seen) - SHOWN} more" if len(seen) > SHOWN else ""
            yield Finding("AP22", src.display, first,
                          f"{count} hidden character(s) on {len(lines)} line(s): {', '.join(names)}{more}")
