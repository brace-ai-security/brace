"""AP01, AP02, AP05, AP06: agents whose permission checks are off, too broad, or whose settings hold secrets."""
from __future__ import annotations

import bisect
import re
from pathlib import Path
from typing import Iterator

from ..agents import ACTIONS, BYPASS, GATED_BYPASS, GATED_CLI, GATED_FLAG_CLIS, SHORT_YOLO, SHORT_YOLO_CLI, alternation, \
    command_position
from ..jsonc import Lines
from ..limits import MAX_PER_LINE
from ..model import CheckContext, Document, Finding
from ..parse.dockerfile import is_dockerfile
from ..secrets import secret_kind
from .mentions import Mentions

# The same setting written as JSON anywhere: inside another file (a workflow passing Claude Code
# settings), inside a JSON string (a devcontainer command writing settings) or nested under
# another key. A match on the line ClaudeSettings already reports is left to it.
INLINE_DEFAULT_MODE = re.compile(r"\\?[\"']defaultMode\\?[\"'][ \t]*:[ \t]*\\?[\"']bypassPermissions\\?[\"']")
# Comment markers by file kind (see file_kind; "" is an extensionless script, Makefile or
# justfile), at the start of a line or after a space. Block comments (/* */, docstrings) are
# found by mentions.Regions.
COMMENT_MARKERS = {**dict.fromkeys((".yml", ".yaml", ".sh", ".bash", ".zsh", ".fish", ".py", ".toml", ".rb", ".ps1",
                                    ".env", ".mk", ".dockerfile", ""), ("#",)),
                   **dict.fromkeys((".ini", ".cfg"), ("#",)),
                   **dict.fromkeys((".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".go", ".rs", ".java",
                                    ".kt", ".scala", ".jsonc", ".groovy"), ("//",)),
                   **dict.fromkeys((".bat", ".cmd"), ("REM ", "rem ", "Rem ", "@REM ", "@rem ", "::"))}
LINE_COMMENTS = {".ini": ";", ".cfg": ";"}  # comment markers only at the start of a line (after whitespace)
MAKE_NAMES = {"makefile", "gnumakefile", "justfile", ".justfile"}
# Flags that count only next to a CLI that takes them: the CLI, and whether it must come first.
GATES = {GATED_BYPASS: (GATED_CLI, False), SHORT_YOLO: (SHORT_YOLO_CLI, True)}
CONTINUATION = ("\\", "^", "`")  # a line continued on the next (shell, cmd.exe, PowerShell)
CONTINUED_LINES = 20  # lines looked back through continuations for the CLI a gated flag belongs to
COMMAND_WINDOW = 4000  # characters looked back for the start of a gated flag's command
LIST_WINDOW = 500      # characters looked back for the list a gated flag is an item of
SEPARATOR = re.compile(r"&&|\|\||[;|&]")  # ends a simple command, as does a line break that is not continued
LIST_HEAD = re.compile(r"[ \t\n]{0,40}[\"']([^\"'\s,]{1,100})[\"'][ \t]{0,20},")
YAML_KEY = re.compile(r"^[ \t]*(?:-[ \t]+)?[\"']?([\w.\-]{1,80})[\"']?[ \t]*:")
AGENT_ACTION = re.compile(rf"^[ \t]*(?:-[ \t]+)?uses[ \t]*:[ \t]*[\"']?(?:{alternation(ACTIONS)})", re.I)
SPACES = re.compile(r"\s+")
SHELL_ALLOW_ALL = {"Bash", "Bash(*)", "Bash(:*)", "Bash(**)", "Bash(*:*)", "*"}


def file_kind(display: str) -> str:
    """The kind of file, as the extension its comments follow: a Dockerfile (`Dockerfile.dev`,
    `app.dockerfile`) is ".dockerfile", `.env.example` is ".env", a Jenkinsfile is ".groovy",
    a Makefile or justfile is ""; anything else is its own extension."""
    name = display.rsplit("/", 1)[-1].lower()
    if is_dockerfile(name):
        return ".dockerfile"
    if name == ".env" or name.startswith(".env."):
        return ".env"
    if name == "jenkinsfile" or name.startswith("jenkinsfile."):
        return ".groovy"
    if name in MAKE_NAMES:
        return ""
    return Path(name).suffix


def logical_start(text: str, lines: Lines, n: int) -> int:
    """Where line n's command starts: back through lines that end with a continuation."""
    first = n
    while first > 1 and n - first < CONTINUED_LINES:
        start, end = lines.span(first - 1)
        if not text[start:end].rstrip().endswith(CONTINUATION):
            break
        first -= 1
    return lines.span(first)[0]


def in_command(text: str, lines: Lines, n: int, m, cli, cli_first: bool) -> bool:
    """Whether the CLI is the command of the simple command that holds the flag (split at &&, ||,
    ;, |, & and line breaks that are not continued), so `npm install -g @google/gemini-cli &&
    apt-get install -y jq` or `deno run --allow-all x.ts && codex exec ...` does not count."""
    begin = max(logical_start(text, lines, n), m.start() - COMMAND_WINDOW)
    seps = [s.end() for s in SEPARATOR.finditer(text, begin, m.start())]
    start, end = seps[-1] if seps else begin, lines.span(n)[1]
    after = SEPARATOR.search(text, m.end(), end)
    stop = m.start() if cli_first else (after.start() if after else end)
    return any(command_position(text[start:c.start()]) for c in cli.finditer(text, start, stop))


def list_item(text: str, at: int, cli) -> bool:
    """Whether the flag at `at` is an item of a list whose first item is the CLI, written over
    several lines (`[\n    "gemini",\n    "--yolo",\n]`): the nearest unclosed bracket before it."""
    lo = max(0, at - LIST_WINDOW)
    i = max(text.rfind("[", lo, at), text.rfind("(", lo, at))
    if i < 0 or "]" in text[i:at] or ")" in text[i:at]:
        return False
    head = LIST_HEAD.match(text, i + 1)
    return bool(head and cli.fullmatch(head.group(1)))


def agent_key(line: str) -> bool:
    """A YAML key that names an agent CLI: `codex-args:`, `gemini_cli_args:`."""
    key = YAML_KEY.match(line)
    return bool(key) and any(name in key.group(1).lower() for name in GATED_FLAG_CLIS)


def agent_action_steps(text: str) -> list[tuple[int, int]]:
    """(first, last) line of each YAML list item (a workflow step) whose `uses:` is an agent
    action, found in one pass with a stack of the items enclosing each line."""
    found: list[tuple[int, int]] = []
    stack: list[list] = []  # [indent, first line, last line, uses an agent action]
    for n, line in enumerate(text.split("\n"), 1):
        body = line.lstrip()
        if not body or body.startswith("#"):
            continue
        indent = len(line) - len(body)
        while stack and stack[-1][0] >= indent:
            item = stack.pop()
            if item[3]:
                found.append((item[1], item[2]))
        for item in stack:
            item[2] = n
        if body.startswith("- "):
            stack.append([indent, n, n, False])
        if stack and AGENT_ACTION.match(line):
            stack[-1][3] = True
    found += [(item[1], item[2]) for item in stack if item[3]]
    return sorted(found)


def in_steps(steps: list[tuple[int, int]], n: int) -> bool:
    k = bisect.bisect_right(steps, (n, float("inf"))) - 1
    return k >= 0 and steps[k][0] <= n <= steps[k][1]


def comment_start(line: str, markers: tuple[str, ...]) -> int:
    """Index where a trailing comment starts (outside quotes), or len(line). In double quotes
    a backslash escapes the next character; single quotes have no escapes."""
    quote, i = "", 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        else:
            for m in markers:
                if line.startswith(m, i) and (i == 0 or line[i - 1] in " \t"):
                    return i
        i += 1
    return len(line)


class PermissionFlags:
    """Bypass flags and settings written as text in any file in the folder, except Markdown.

    Raw text, not parsed facts: these flags appear in shell scripts, workflows, code and
    config of every kind. A flag that is only mentioned (see mentions.py) is not reported.
    Files on this machine are read structurally only."""
    name = "permission-flags"
    emits = ("AP01", "AP02")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        src = doc.source
        kind = file_kind(src.display)
        if src.origin != "repo" or kind == ".md":
            return
        text = src.text
        lines = Lines(text)
        markers = COMMENT_MARKERS.get(kind, ())
        patterns = [BYPASS, GATED_BYPASS, SHORT_YOLO, INLINE_DEFAULT_MODE]
        perms = doc.permissions
        structural = doc.line_of(("permissions", "defaultMode")) \
            if perms is not None and perms.default_mode == "bypassPermissions" else 0
        mentions = Mentions(text, kind)
        steps: list[tuple[int, int]] | None = None
        for rx in patterns:
            gate = GATES.get(rx)
            per_line: dict[int, int] = {}
            comment_at: dict[int, int] = {}  # computed once per line, not per match
            for m in rx.finditer(text):
                n = lines.number(m.start())
                per_line[n] = per_line.get(n, 0) + 1
                if per_line[n] > MAX_PER_LINE:
                    continue
                start, end = lines.span(n)
                if n not in comment_at:
                    line = text[start:end]
                    lead = LINE_COMMENTS.get(kind)
                    comment_at[n] = start + (len(line) - len(line.lstrip()) if lead and line.lstrip().startswith(lead)
                                             else comment_start(line, markers) if markers else len(line))
                if m.start() >= comment_at[n] or (rx is INLINE_DEFAULT_MODE and n == structural):
                    continue
                if gate and not (in_command(text, lines, n, m, *gate) or list_item(text, m.start(), gate[0])):
                    if kind not in (".yml", ".yaml"):
                        continue
                    if steps is None:
                        steps = agent_action_steps(text)
                    if not (agent_key(text[start:end]) or in_steps(steps, n)):
                        continue
                if mentions.is_mention(start, text[start:end], n, m.start(), m.end()):
                    continue
                detail = "defaultMode: bypassPermissions" if rx is INLINE_DEFAULT_MODE else \
                    "-y (--yolo)" if rx is SHORT_YOLO else " ".join(m.group(0).split())
                yield Finding("AP02" if src.is_ci else "AP01", src.display, n, detail)


class ClaudeSettings:
    """Claude Code settings: allow-everything shell rules, bypass mode and secrets in env."""
    name = "claude-settings"
    emits = ("AP06", "AP01", "AP05")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        perms, where, at = doc.permissions, doc.source.display, doc.line_of
        if perms is None:
            return
        for rule in perms.allow:
            if SPACES.sub("", rule) in SHELL_ALLOW_ALL:
                yield Finding("AP06", where, at(("permissions", "allow")), f'allow "{rule}"')
        if perms.default_mode == "bypassPermissions":
            yield Finding("AP01", where, at(("permissions", "defaultMode")), "defaultMode: bypassPermissions")
        for k, v in (perms.env or {}).items():
            if isinstance(v, (str, int, float)) and ctx.secrets.secret_pair(k, v):
                yield Finding("AP05", where, at(("env", str(k))), f"env.{k} = <redacted>{secret_kind(v)}")
