"""AP01, AP02, AP05, AP06: agents whose permission checks are off, too broad, or whose settings hold secrets."""
from __future__ import annotations

import bisect
import re
from pathlib import Path
from typing import Iterator

from ..agents import ACTIONS, BYPASS, GATED_BYPASS, GATED_CLI, GATED_FLAG_CLIS, QUOTED_GATED_CLI, QUOTED_SHORT_YOLO_CLI, \
    SHORT_YOLO, SHORT_YOLO_CLI, alternation
from ..jsonc import Lines
from ..limits import MAX_OPEN_BRACKETS, MAX_PER_COMMAND, MAX_PER_LINE
from ..model import CheckContext, Document, Finding
from ..parse.dockerfile import is_dockerfile
from ..secrets import secret_kind
from ..agents import command_position
from .mentions import Mentions, yaml_blocks

# The same setting written as JSON anywhere: inside another file (a workflow passing Claude Code
# settings), inside a JSON string (a devcontainer command writing settings) or nested under
# another key. A match on the line ClaudeSettings already reports is left to it.
INLINE_DEFAULT_MODE = re.compile(r"\\?[\"']defaultMode\\?[\"'][ \t]*:[ \t]*\\?[\"']bypassPermissions\\?[\"']")
# Comment markers by file kind (see file_kind; "" is an extensionless script, Makefile or
# justfile), at the start of a line or after a space. Block comments (/* */, docstrings) are
# found by mentions.Regions.
COMMENT_MARKERS = {**dict.fromkeys((".yml", ".yaml", ".sh", ".bash", ".zsh", ".fish", ".py", ".toml", ".rb", ".ps1",
                                    ".env", ".mk", ".dockerfile", "", ".service", ".conf", ".pl", ".ex", ".exs",
                                    ".nix", ".properties"), ("#",)),
                   **dict.fromkeys((".ini", ".cfg"), ("#",)),
                   **dict.fromkeys((".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".go", ".rs", ".java",
                                    ".kt", ".scala", ".jsonc", ".groovy", ".code-workspace", ".json5", ".cs", ".swift",
                                    ".c", ".h", ".cpp", ".dart"), ("//",)),
                   **dict.fromkeys((".tf", ".hcl", ".php"), ("#", "//")),
                   ".lua": ("-- ",),  # with its space, so a `--flag` after a space is not a comment
                   **dict.fromkeys((".bat", ".cmd"), ("REM ", "rem ", "Rem ", "@REM ", "@rem ", "::"))}
LINE_COMMENTS = {".ini": ";", ".cfg": ";", ".service": ";"}  # comment markers only at the start of a line (after whitespace)
MAKE_NAMES = {"makefile", "gnumakefile", "justfile", ".justfile"}
# Flags that count only next to a CLI that takes them: the CLI as a word, the CLI as a quoted
# item, and whether the CLI must come before the flag (`npx -y @google/gemini-cli` is npx's -y).
GATES = {GATED_BYPASS: (GATED_CLI, QUOTED_GATED_CLI, False), SHORT_YOLO: (SHORT_YOLO_CLI, QUOTED_SHORT_YOLO_CLI, True)}
CONTINUATION = ("\\", "^", "`")  # a line continued on the next (shell, cmd.exe, PowerShell)
SEPARATOR = re.compile(r"&&|\|\||[;|]")  # ends a simple command, as does a line break that is not continued
JSON_SEPARATOR = re.compile(r"&&|\|\||[;|]|(?<!\\)\"")  # in JSON a string's quotes end one too (minified package.json)
INSTALL_TOOLS = frozenset("npm pnpm yarn bun pip pip3 pipx uv brew apt apt-get apk yum dnf".split())
INSTALL_VERBS = frozenset(("install", "add", "i"))
INSTALL_LOOKBACK = 300  # characters of a simple command before the CLI searched for an install command
CLI_CANDIDATES = 5      # CLI words in one simple command checked for one that is not an install argument
BRACKETS = re.compile(r"[()\[\]{}]")
FILE_EXT = re.compile(r"\.\w")                         # `gemini.ts`: a file named after the CLI
PROGRAM_EXT = re.compile(r"\.(?:exe|cmd)(?![\w.])", re.I)  # `gemini.exe`: the program
LONG_FLAG = re.compile(r"^--[\w-]{1,60}$")             # `--provider gemini`: the CLI name is the flag's value
# A YAML key whose value is a list of arguments for an agent (`gemini_cli_args`, `codex-args`),
# where a gated flag counts in an agent action's step even without the CLI's name beside it.
ARGS_KEY = re.compile(r"(?:^|[_-])(?:args|arguments)$")
# A `command:`, `cmd:` or `entrypoint:` key (JSON or YAML) whose value starts with a gated CLI.
COMMAND_KEY = re.compile(rf"[\"']?\b(?:command|cmd|entrypoint)[\"']?[ \t]*:[ \t]*\[?[ \t]*[\"']?(?:[\w.~-]{{0,100}}/)?"
                         rf"(?:{alternation(GATED_FLAG_CLIS)}|@google/gemini-cli|@qwen-code/|@github/copilot)(?![\w-])",
                         re.I)
YAML_ENTRY = re.compile(r"^([ \t]*)(-[ \t]+)?(?:[\"']?([\w.\-]{1,80})[\"']?[ \t]*:(?:[ \t]|$))?")
COMMAND_KEYS = frozenset(("command", "cmd", "entrypoint"))
# `NAME.push('--yolo')`, `NAME.append("--yolo")`, `NAME += ["--yolo"]`: the name an argument
# list is built under, matched on the reversed text before the flag so the match is anchored.
PUSHED_REVERSED = re.compile(r"^[\"'][ \t]{0,20}(?:\[[ \t]{0,20})?(?:\((?:hsup|dneppa|dnetxe|tfihsnu)\.|\[[ \t]{0,20}=\+[ \t]{0,20})"
                             r"([\w$]{1,60})")
SPAWN = re.compile(r"\b(?:spawn|spawnSync|exec|execSync|execFile|execFileSync|execa|Popen|run|call|check_call|"
                   r"check_output|Command|ProcessBuilder)[ \t]*\(")
SPAWN_WINDOW = 300  # characters around a use of a pushed-to name searched for the spawn call and CLI
NAME_USES = 50      # later uses of a pushed-to name looked at
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


class Brackets:
    """Open brackets enclosing an offset, from one forward pass (restarted when it goes back)."""

    def __init__(self, text: str):
        self.text, self.cursor, self.opens = text, 0, []

    def at(self, pos: int) -> list[int]:
        if pos < self.cursor:
            self.cursor, self.opens = 0, []
        for m in BRACKETS.finditer(self.text, self.cursor, pos):
            if m.group(0) in "([{":
                if len(self.opens) < MAX_OPEN_BRACKETS:
                    self.opens.append(m.start())
            elif self.opens:
                self.opens.pop()
        self.cursor = pos
        return self.opens


def install_argument(before: str) -> bool:
    """Whether a CLI after `before` (its simple command up to it) is an argument of an install
    command: `npm install -g @google/gemini-cli`, `pip install qwen`, `brew install gemini-cli`."""
    words = [w.strip("\"'[](),").rsplit("/", 1)[-1] for w in before.split()]
    tool = next((i for i, w in enumerate(words) if w in INSTALL_TOOLS), -1)
    return tool >= 0 and any(w in INSTALL_VERBS for w in words[tool + 1:])


class Gate:
    """Whether a gated flag (--yolo, --allow-all-tools, --allow-all, -y) belongs to a CLI that
    takes it. Everything is computed once per file and looked up per flag: line continuations,
    separators, CLI positions, the objects and YAML mappings whose command is the CLI."""

    def __init__(self, text: str, lines: Lines, kind: str, cli, quoted, cli_first: bool):
        self.text, self.lines, self.kind = text, lines, kind
        self.cli_first = cli_first
        sep = JSON_SEPARATOR if kind == ".json" else SEPARATOR
        self.seps = [(m.start(), m.end()) for m in sep.finditer(text)]
        self.sep_starts = [s for s, _ in self.seps]
        self.clis = [(m.start(), m.end()) for m in cli.finditer(text)]
        self.cli_starts = [s for s, _ in self.clis]
        self.quoted = [m.start() for m in quoted.finditer(text)]
        self.install: dict[int, bool] = {}
        self.first: list[int] | None = None   # first line of each line's logical command
        self.last: list[int] | None = None    # last line of each line's logical command
        self.per_command: dict[int, int] = {}
        self.brackets = Brackets(text)
        self._objects: set[int] | None = None   # `{` of objects whose command is the CLI
        self._mappings: list[int] | None = None  # YAML mapping of each line
        self._command_maps: set[int] = set()
        self._pushed: dict[str, bool] = {}

    def logical(self, n: int) -> tuple[int, int]:
        """The first and last line of line n's logical command (lines joined by continuations)."""
        if self.first is None:
            text, count = self.text, len(self.lines.breaks) + 1
            cont = [text[slice(*self.lines.span(k))].rstrip().endswith(CONTINUATION) for k in range(1, count + 1)]
            self.first, self.last = [0] * (count + 2), [0] * (count + 2)
            for k in range(1, count + 1):
                self.first[k] = self.first[k - 1] if k > 1 and cont[k - 2] else k
            for k in range(count, 0, -1):
                self.last[k] = self.last[k + 1] if k < count and cont[k - 1] else k
        return self.first[n], self.last[n]

    def counts(self, n: int, start: int, end: int) -> bool:
        return self.in_command(n, start, end) or self.listed(start) or self.in_object(start) \
            or self.in_mapping(n) or self.pushed(start)

    def in_command(self, n: int, start: int, end: int) -> bool:
        """The CLI is a word of the simple command that holds the flag (split at &&, ||, ;, | and
        line breaks that are not continued; in JSON also at string quotes), and not an argument
        of an install command. For -y the CLI must come before the flag."""
        first, last = self.logical(n)
        lo, hi = self.lines.span(first)[0], self.lines.span(last)[1]
        seen = self.per_command.get(lo, 0) + 1
        self.per_command[lo] = seen
        if seen > MAX_PER_COMMAND:
            return False
        k = bisect.bisect_left(self.sep_starts, start)
        begin = max(lo, self.seps[k - 1][1] if k else 0)
        stop = start if self.cli_first else min(hi, self.sep_starts[k] if k < len(self.sep_starts) else hi)
        i = bisect.bisect_left(self.cli_starts, begin)
        for c, ce in self.clis[i:i + CLI_CANDIDATES]:
            if c >= stop:
                return False
            if begin <= c and not (start <= c < end):
                if c not in self.install:
                    self.install[c] = install_argument(self.text[max(begin, c - INSTALL_LOOKBACK):c]) \
                        or not self.program(begin, c, ce)
                if not self.install[c]:
                    return True
        return False

    def program(self, begin: int, c: int, ce: int) -> bool:
        """Whether the CLI word at c..ce (in the simple command starting at begin) names the
        program, not a path, file or value: not followed by `/`, `=` or a file extension other
        than .exe/.cmd, not after `=` or a long flag (`--provider gemini`), and after `/` only as
        a path in command position (`/usr/local/bin/gemini`). For -y the CLI must be in command
        position. A package (`@google/gemini-cli`) is judged by install_argument alone."""
        text = self.text
        if text[c] == "@":
            return not self.cli_first or command_position(text[begin:c])
        before, after = text[c - 1:c] if c else "", text[ce:ce + 8]
        if after[:1] in ("/", "=") or before == "=" or (FILE_EXT.match(after) and not PROGRAM_EXT.match(after)):
            return False
        words = text[max(begin, c - INSTALL_LOOKBACK):c].split()
        if before.isspace() and words and LONG_FLAG.match(words[-1]):
            return False
        if self.cli_first or before == "/":
            return command_position(text[begin:c])
        return True

    def listed(self, start: int) -> bool:
        """A gated CLI is a quoted item before the flag in the list that holds it, or in the call
        that list is an argument of (`spawn("gemini", [\n  "--yolo"])`)."""
        opens = self.brackets.at(start)
        if not opens:
            return False
        lo = opens[-2] if len(opens) >= 2 and self.text[opens[-2]] == "(" else opens[-1]
        i = bisect.bisect_right(self.quoted, lo)
        return i < len(self.quoted) and self.quoted[i] < start

    def in_object(self, start: int) -> bool:
        """The innermost object holding the flag has `"command": "gemini"` (JSON, Zed agent_servers)."""
        if self._objects is None:
            self._objects = set()
            stack = Brackets(self.text)
            for m in COMMAND_KEY.finditer(self.text):
                braces = [o for o in stack.at(m.start()) if self.text[o] == "{"]
                if braces:
                    self._objects.add(braces[-1])
        if not self._objects:
            return False
        braces = [o for o in self.brackets.at(start) if self.text[o] == "{"]
        return bool(braces) and braces[-1] in self._objects

    def in_mapping(self, n: int) -> bool:
        """In YAML, the mapping that holds line n has `command: gemini` (or `command: [gemini]`,
        `command:` then `- gemini`): compose services, Kubernetes containers, agent configs."""
        if self.kind not in (".yml", ".yaml"):
            return False
        if self._mappings is None:
            self._mappings = self.yaml_mappings()
        return 0 < n < len(self._mappings) and self._mappings[n] in self._command_maps

    def yaml_mappings(self) -> list[int]:
        """The mapping id of each line, in one pass with a stack of (key column, mapping id, last
        key) per indentation level; ids of mappings whose command is the CLI go to _command_maps."""
        rows = self.text.split("\n")
        ids, stack, next_id = [0] * (len(rows) + 1), [], 1
        for n, line in enumerate(rows, 1):
            body = line.lstrip()
            if not body or body.startswith("#"):
                ids[n] = stack[-1][1] if stack else 0
                continue
            m = YAML_ENTRY.match(line)
            indent, item, key = len(m.group(1)), bool(m.group(2)), m.group(3)
            col = indent + (len(m.group(2)) if item else 0)
            if key:
                while stack and (stack[-1][0] > col or (item and stack[-1][0] >= col)):
                    stack.pop()
                if not stack or stack[-1][0] != col:
                    stack.append([col, next_id, ""])
                    next_id += 1
                stack[-1][2] = key.lower()
                if key.lower() in COMMAND_KEYS and COMMAND_KEY.search(line):
                    self._command_maps.add(stack[-1][1])
            else:
                while stack and stack[-1][0] > indent:
                    stack.pop()
                if item and stack and stack[-1][2] in COMMAND_KEYS and GATED_CLI.match(body[2:].lstrip(" \t\"'[")):
                    self._command_maps.add(stack[-1][1])
            ids[n] = stack[-1][1] if stack else 0
        return ids

    def pushed(self, start: int) -> bool:
        """`NAME.push('--yolo')` (or append, `NAME += [...]`) and later in the file a spawn, exec
        or subprocess call that passes NAME next to a gated CLI."""
        text = self.text
        m = PUSHED_REVERSED.match(text[max(0, start - 120):start][::-1])
        if not m:
            return False
        name = m.group(1)[::-1]
        if name not in self._pushed:
            self._pushed[name] = self.spawned(name, start)
        return self._pushed[name]

    def spawned(self, name: str, after: int) -> bool:
        text, pos = self.text, after
        for _ in range(NAME_USES):
            at = text.find(name, pos)
            if at < 0:
                return False
            pos = at + len(name)
            if (at and (text[at - 1].isalnum() or text[at - 1] in "_$")) or (pos < len(text) and (text[pos].isalnum()
                                                                                                or text[pos] in "_$")):
                continue
            window = text[max(0, at - SPAWN_WINDOW):at + SPAWN_WINDOW]
            if SPAWN.search(window) and GATED_CLI.search(window):
                return True
        return False


def args_key(key: str, in_agent_step: bool) -> bool:
    """A YAML key that holds an agent's arguments: one that names a CLI that takes gated flags
    (`codex-args`, `gemini_cli_args`), or any args key in an agent action's step. Never
    `mcp_config`, `settings` or `prompt`, whose -y or --yolo belongs to something else."""
    return bool(ARGS_KEY.search(key)) and (in_agent_step or any(name in key for name in GATED_FLAG_CLIS))


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
    config of every kind. A flag that is only mentioned (see mentions.py for the few structural
    cases) is not reported; anything else is, erring toward reporting.
    Files on this machine are read structurally only."""
    name = "permission-flags"
    emits = ("AP01", "AP02")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        src = doc.source
        kind = file_kind(src.display)
        settled = set()  # lines reported from parsed facts, whose text matches are not reported again
        for path, detail in doc.full_access:
            settled.add(doc.line_of(path))
            yield Finding("AP02" if src.is_ci else "AP01", src.display, doc.line_of(path), detail)
        if src.origin != "repo" or kind == ".md":
            return
        text = src.text
        lines = Lines(text)
        markers = COMMENT_MARKERS.get(kind, ())
        patterns = [BYPASS, GATED_BYPASS, SHORT_YOLO, INLINE_DEFAULT_MODE]
        perms = doc.permissions
        structural = doc.line_of(("permissions", "defaultMode")) \
            if perms is not None and perms.default_mode == "bypassPermissions" else 0
        mentions = Mentions(text, kind, settings="settings" in src.display.rsplit("/", 1)[-1].lower())
        steps: list[tuple[int, int]] | None = None
        owners: list[str] = []
        for rx in patterns:
            gate_args = GATES.get(rx)
            gate: Gate | None = None
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
                if m.start() >= comment_at[n] or (rx is INLINE_DEFAULT_MODE and n == structural) or n in settled:
                    continue
                if gate_args:
                    if gate is None:
                        gate = Gate(text, lines, kind, *gate_args)
                    if not gate.counts(n, m.start(), m.end()):
                        # -y counts only beside its CLI; --yolo and --allow-all-tools also as the
                        # value of an agent action's args key (`gemini_cli_args: --yolo`).
                        if kind not in (".yml", ".yaml") or rx is SHORT_YOLO:
                            continue
                        if steps is None:
                            steps, owners = agent_action_steps(text), yaml_blocks(text)[0]
                        if not args_key(owners[n] if n < len(owners) else "", in_steps(steps, n)):
                            continue
                if mentions.is_mention(start, text[start:comment_at[n]], n, m.start(), m.end()):
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
