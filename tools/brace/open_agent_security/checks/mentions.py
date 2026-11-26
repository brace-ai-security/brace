"""Whether a bypass flag in text is only mentioned, not passed to an agent.

The scanner errs toward reporting: every heuristic that guessed a flag was "only mentioned"
from its wording (prose, refusal words, names) was beaten in one direction or the other, and a
missed bypass costs more than a false positive, which an inline mark or the ignore file
silences. So a flag is a mention only in these structural cases:

(a) inside a comment, docstring or block comment (comments are found by the caller; docstrings
    and block comments here, with a string-aware tokenizer);
(b) Markdown files are never read (the caller skips them);
(c) a quoted literal directly compared or searched for (`== "--flag"`, `"--flag" in x`,
    `.includes("--flag")`), an argument of grep, a shell `case` pattern, a JS `case '--flag':`
    label, the right side of a test in `[[ ]]`, `[ ]` or `test`, or a regular expression;
(d) a value under Claude Code settings' `permissions.deny` or `permissions.ask` in a JSON or
    YAML settings file;
(e) an item of a list assigned to a name whose last word refuses its items (`BLOCKED`,
    `deny`, `forbidden`), when the list names no agent CLI and the name is used in the file only
    for membership tests (`x in NAME`, `NAME.includes(x)`).

Anything else counts, including help text, prompts and error messages that name the flag.
Every look-around is bounded, and each per-file pass looks at each character a bounded
number of times.
"""
from __future__ import annotations

import bisect
import re

from ..agents import AGENT_COMMAND, command_position
from ..limits import MAX_OPEN_BRACKETS

HEAD = 200             # characters before a list's opening bracket searched for its name
LIST_SPAN = 4000       # characters after a list's opening bracket searched for its end
NAME_USES = 50         # uses of a deny-list's name checked; a name used more often is not a deny-list
BRACKETS = re.compile(r"[()\[\]{}]")
CLOSER = {"(": ")", "[": "]", "{": "}"}
# A name that says its list is refused: its last word is a deny word. `BLOCKED_FLAGS` (last word
# `flags`), `UNSAFE_ARGS`, `guard_cmd` or `blocks` do not qualify.
NAME_PART = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")
DENY_PART = re.compile(r"(?i)(?:block|blocked|blocklist|deny|denied|denylist|forbid|forbidden|ban|banned|"
                       r"disallow|disallowed|reject|rejected)")
SETTINGS_DENY = frozenset(("deny", "ask"))  # keys under Claude Code settings' `permissions`
# A name assigned or keyed just before the list opens (`BLOCKED: list[str] = [`, `"deny": [`,
# `const DENY = new Set([`), matched on the reversed text so the match is anchored.
ASSIGNED_REVERSED = re.compile(r"^[ \t]{0,20}(?:\([ \t]{0,20}\w{1,40}(?:[ \t]{1,20}wen)?[ \t]{0,20})?"
                               r"(?:=[ \t]{0,20}(?:[^=:\n\"']{0,80}:)?|:)[ \t]{0,20}[\"']?([\w$-]{1,80})")
MEMBERSHIP = re.compile(r"\bin[ \t]{0,20}$")
FOR_LOOP = re.compile(r"\bfor\b")  # `for flag in [...]` passes each item; it is not a membership test
ANY_ALL = re.compile(r"\b(?:any|all)[ \t]{0,20}\(")  # `any(f in cmd for f in NAME)`: a membership test
MEMBER_AFTER = re.compile(r"[ \t]{0,20}\.(?:includes|has|contains|indexOf|__contains__)\(")
COMPARED_AFTER = re.compile(r"[ \t]{0,20}(?:not[ \t]{1,20}in\b|in\b|[!=]==?)")
COMPARED_BEFORE = re.compile(r"(?:[!=]==?|\.(?:includes|contains|has|indexOf|startswith|startsWith|endswith|"
                             r"endsWith)\(|\bre\.\w{1,12}\(|\bRegExp\()[ \t]*[rRbB]?$")
# Tests of the flag rather than uses of it, in the flag's own simple command: an argument of a
# search tool (`grep -q -- "--flag"`), a `case` pattern (`--flag)`), a JS `case "--flag":` label,
# or the right side of a comparison in `[[ ]]`, `[ ]` or `test` (`[[ "$*" == *--flag* ]]`).
SEARCHED = re.compile(r"(?<![\w-])(?:grep|egrep|fgrep|rg|ag|ack|findstr|Select-String)(?![\w-])", re.I)
CASE_BEFORE = re.compile(r"(?:^|\bin)[ \t*\"']*$")
CASE_AFTER = re.compile(r"[*\"']{0,3}[ \t]{0,20}\)")
JS_CASE_BEFORE = re.compile(r"\bcase[ \t]{1,20}[\"'`]$")
JS_CASE_AFTER = re.compile(r"[\"'`][ \t]{0,20}:")
TESTED = re.compile(r"(?:\[\[?|\btest)[ \t][^\n]{0,200}?(?:==|!=|=~|=)[ \t]*[\"'*]*$")
YAML_KEY = re.compile(r"^[ \t]*(?:-[ \t]+)?[\"']?([\w.\-]{1,80})[\"']?[ \t]*:[ \t]*(?:#.*)?$")
TRIPLE = re.compile(r"\"\"\"|'''")
BLOCK_COMMENT_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".go", ".rs", ".java", ".kt",
                     ".scala", ".groovy", ".jsonc"}
# Triple-quoted strings, which may span lines and hold `/*`: Groovy (and Jenkinsfiles) has both
# kinds; Kotlin, Java text blocks and Scala have """.
TRIPLE_QUOTES = {".groovy": ('"""', "'''"), ".kt": ('"""',), ".java": ('"""',), ".scala": ('"""',)}
REGEX_LITERAL_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".rb"}
STRUCTURED_EXT = {".json", ".jsonc", ".yml", ".yaml"}  # where settings keys and deny-list keys are read


# Tokens outside strings in C-like files: a block or line comment, or a string's opening quote
# (triple quotes and Rust raw strings `r#"..."#` where the language has them); in JavaScript and
# TypeScript also a lone slash, which may open a /regex/ literal.
RAW_OPEN = r'(?<!\w)r#{0,16}"'


def code_tokens(suffix: str) -> re.Pattern:
    alternatives = ["/\\*", "//", *(["/"] if suffix in JS_EXT else []), *([RAW_OPEN] if suffix == ".rs" else []),
                    *map(re.escape, TRIPLE_QUOTES.get(suffix, ())), "[\"'`]"]
    return re.compile("|".join(alternatives))


JS_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"}
# A slash opens a regex literal after an operator, an opening bracket, or one of these words.
REGEX_BEFORE_CHARS = "(=,:!&|?{};[+-*%<>~^"
REGEX_BEFORE_WORD = re.compile(r"(?<![\w$.])(?:return|typeof|case|yield|await|in|of|delete|void|throw|new|else|do)$")
REGEX_END = re.compile(r"\\[^\n]|[\[\]/\n]")  # inside a regex literal: an escape, a class bracket, its end
# The end of a string opened by each quote: its closing quote, or a line break for quotes that
# cannot span lines. A backslash escapes the next character, except in a Go raw string.
DOUBLE_END = re.compile(r'\\[\s\S]|"|\n')
SINGLE_END = re.compile(r"\\[\s\S]|'|\n")
TEMPLATE_END = re.compile(r"\\[\s\S]|`|\$\{")  # in a template literal: an escape, its end, an embedded expression
EMBEDDED = re.compile(r"[{}\"'`]|/\*|//")  # inside `${...}`: braces, strings, nested templates, comments
TEMPLATE_DEPTH = 50  # template literals nested through `${...}` that are followed
GO_RAW_END = re.compile("`")
RUST_DOUBLE_END = re.compile(r'\\[\s\S]|"')  # a Rust string may span lines
STRING_END = {'"': DOUBLE_END, "'": SINGLE_END, "`": re.compile(r"\\[\s\S]|`")}
DOCSTRING_LOOKBACK = 50  # lines searched up for the `def ...:` or `class ...:` a docstring follows
DOCSTRING_INDENT = 200   # longest indentation before a docstring's opening quotes


class Regions:
    """Docstrings (Python) and /* block comments */ in one file, found once in a linear pass."""

    def __init__(self, text: str, suffix: str):
        self.starts: list[int] = []
        self.ends: list[int] = []
        self.comments = suffix in BLOCK_COMMENT_EXT  # the regions are block comments, not docstrings
        if suffix == ".py":
            self.docstrings(text)
        elif self.comments:
            self.block_comments(text, suffix)

    def add(self, start: int, end: int) -> None:
        self.starts.append(start)
        self.ends.append(end)

    def docstrings(self, text: str) -> None:
        """Each triple-quoted string is skipped whole; it is a docstring only at the start of the
        module or directly after a `def ...:` or `class ...:` line. An argument or value that
        happens to start a line (`run(\n    \"\"\"claude ... \"\"\", shell=True)`) is not one, and an
        unclosed one (a syntax error) hides nothing. The start of the current line is tracked as
        the pass moves forward, so each character is looked at a bounded number of times."""
        pos = scanned = line_start = 0
        while True:
            m = TRIPLE.search(text, pos)
            if not m:
                return
            close = text.find(m.group(0), m.end())
            if close < 0:
                return
            nl = text.rfind("\n", scanned, m.start())
            line_start, scanned = (nl + 1 if nl >= 0 else line_start), m.start()
            if m.start() - line_start <= DOCSTRING_INDENT \
                    and text[line_start:m.start()].strip(" \t") in ("", "r", "R", "u", "U") and opens_docstring(text, line_start):
                self.add(m.end(), close + 3)
            pos = close + 3

    def block_comments(self, text: str, suffix: str) -> None:
        """Block comments outside string literals, `//` comments and (JavaScript, TypeScript)
        regex literals, so `glob("src/*.ts")`, `"Accept": "*/*"`, `s.replace(/\\/*$/, "")` or a
        Jenkinsfile's `junit '**/target/*.xml'` does not open one; nor does `\\/*`, and an unclosed
        `/*` hides nothing. Strings are skipped by their quotes (template literals with their
        `${...}`, Go and Rust raw strings, triple quotes); each character is looked at a bounded
        number of times."""
        tokens = code_tokens(suffix)
        pos = 0
        while True:
            m = tokens.search(text, pos)
            if not m:
                return
            token = m.group(0)
            if token == "//":
                nl = text.find("\n", m.end())
                pos = len(text) if nl < 0 else nl + 1
            elif token == "/*":
                close = text.find("*/", m.end())
                if close < 0 or text[m.start() - 1:m.start()] == "\\":
                    pos = m.end()
                    continue
                self.add(m.start(), close + 2)
                pos = close + 2
            elif token == "/":
                pos = regex_literal_end(text, m.start()) if regex_starts(text, m.start()) else m.end()
            elif token.startswith("r") or len(token) == 3:  # a raw or triple-quoted string
                close = '"' + "#" * token.count("#") if token.startswith("r") else token
                end = text.find(close, m.end())
                pos = len(text) if end < 0 else end + len(close)
            elif token == "`" and suffix in JS_EXT:
                pos = template_end(text, m.end(), 0)
            else:
                rx = GO_RAW_END if token == "`" and suffix == ".go" else \
                    RUST_DOUBLE_END if token == '"' and suffix == ".rs" else STRING_END[token]
                pos = string_end(text, m.end(), rx)

    def inside(self, at: int) -> bool:
        k = bisect.bisect_right(self.starts, at) - 1
        return k >= 0 and at < self.ends[k]


def string_end(text: str, pos: int, rx: re.Pattern) -> int:
    """The offset after the string whose body starts at pos (an unclosed one runs to the end)."""
    while True:
        e = rx.search(text, pos)
        if not e:
            return len(text)
        pos = e.end()
        if e.group(0)[0] != "\\":
            return pos


def template_end(text: str, pos: int, depth: int) -> int:
    """The offset after the template literal whose body starts at pos, `${...}` expressions
    (and templates nested in them, up to TEMPLATE_DEPTH) skipped as code."""
    while True:
        e = TEMPLATE_END.search(text, pos)
        if not e:
            return len(text)
        pos = e.end()
        if e.group(0) == "`":
            return pos
        if e.group(0) == "${":
            pos = embedded_end(text, pos, depth + 1)


def embedded_end(text: str, pos: int, depth: int) -> int:
    """The offset after the `}` that closes a template's `${` expression starting at pos."""
    braces = 1
    while True:
        e = EMBEDDED.search(text, pos)
        if not e:
            return len(text)
        pos, token = e.end(), e.group(0)
        if token == "{":
            braces += 1
        elif token == "}":
            braces -= 1
            if not braces:
                return pos
        elif token == "`":
            if depth < TEMPLATE_DEPTH:
                pos = template_end(text, pos, depth)
        elif token == "//":
            nl = text.find("\n", pos)
            pos = len(text) if nl < 0 else nl + 1
        elif token == "/*":
            close = text.find("*/", pos)
            pos = len(text) if close < 0 else close + 2
        else:
            pos = string_end(text, pos, STRING_END[token])


def regex_starts(text: str, at: int) -> bool:
    """Whether the slash at `at` opens a regex literal (JavaScript's rule of thumb): it follows an
    operator, an opening bracket, a keyword such as `return`, or nothing; else it divides."""
    before = text[max(0, at - HEAD):at].rstrip()
    return not before or before[-1] in REGEX_BEFORE_CHARS or bool(REGEX_BEFORE_WORD.search(before))


def regex_literal_end(text: str, at: int) -> int:
    """The offset after the regex literal opened at `at`: its closing slash outside a [class],
    or the end of the line (a literal cannot span lines)."""
    pos, in_class = at + 1, False
    while True:
        e = REGEX_END.search(text, pos)
        if not e:
            return len(text)
        pos, ch = e.end(), e.group(0)
        if ch == "\n" or (ch == "/" and not in_class):
            return pos
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False


def opens_docstring(text: str, line_start: int) -> bool:
    """Whether a statement starting at line_start can be a docstring: nothing but blank lines and
    comments before it (the module docstring), or a `def`/`class` header (its last line, such as
    `) -> int:`, for a header split over lines) as the code line before it."""
    end = line_start - 1
    for _ in range(DOCSTRING_LOOKBACK):
        if end < 0:
            return True
        begin = text.rfind("\n", 0, end) + 1
        line = text[begin:end].strip()
        end = begin - 1
        if line and not line.startswith("#"):
            code = line.split("#", 1)[0].rstrip()
            return code.endswith(":") and code.startswith(("def ", "async def ", "class ", ")"))
    return False




def string_spans(line: str) -> list[tuple[int, int]]:
    """(open quote, close quote) of each quoted string on a line; an unclosed one runs to the end."""
    spans, quote, opened, i = [], "", 0, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                spans.append((opened, i))
                quote = ""
        elif ch in "\"'`":
            quote, opened = ch, i
        i += 1
    if quote:
        spans.append((opened, len(line)))
    return spans


def string_around(spans: list[tuple[int, int]], start: int, end: int) -> tuple[int, int] | None:
    """The quoted string that holds start..end, if any."""
    k = bisect.bisect_left(spans, (start,)) - 1  # the last string opened before start
    if k >= 0 and spans[k][1] >= end:
        return spans[k]
    return None


def tested(before: str, after: str) -> bool:
    """Whether the flag is searched for or compared, not passed (see SEARCHED, CASE_*, TESTED);
    `before` is its line up to the flag, `after` what follows it."""
    window = before[-HEAD * 5:]
    command = window[max(window.rfind("&"), window.rfind(";"), window.rfind("|")) + 1:]
    return bool(SEARCHED.search(command) or TESTED.search(command)
                or (CASE_AFTER.match(after) and CASE_BEFORE.search(command))
                or (JS_CASE_AFTER.match(after) and JS_CASE_BEFORE.search(window)))


def runs_agent(line: str) -> bool:
    """A line whose command is an agent CLI (`  claude --flag -p x`, `RUN codex exec ...`)."""
    agent = AGENT_COMMAND.search(line, 0, HEAD)
    before = line[:agent.start()] if agent else ""
    return bool(agent) and not any(c in before for c in "\"'`([{,*") and command_position(before)


def in_regex(line: str, start: int, end: int) -> bool:
    """Inside a /regex/ literal: a slash before and after, with an operator or bracket before the first."""
    i = line.rfind("/", max(0, start - HEAD), start)
    if i < 0 or line.find("/", end, end + HEAD) < 0 or any(q in line[i:start] for q in "\"'`"):
        return False
    before = line[max(0, i - HEAD):i].rstrip()
    return not before or before[-1] in "(=,:!&|?{;[" or before.endswith("return")


def deny_name(name: str) -> bool:
    """A name whose last word says its items are refused (see DENY_PART)."""
    parts = NAME_PART.findall(name[:80])
    return bool(parts) and bool(DENY_PART.fullmatch(parts[-1]))


def head_name(text: str, at: int) -> str | None:
    """The name assigned or keyed just before the bracket at `at`, if any."""
    head = text[max(text.rfind("\n", max(0, at - HEAD), at) + 1, at - HEAD):at]
    m = ASSIGNED_REVERSED.match(head[::-1])
    return m.group(1)[::-1] if m else None


def list_end(text: str, at: int) -> int:
    """The offset of the bracket that closes the one at `at`, or -1 past LIST_SPAN characters."""
    depth = 0
    for m in BRACKETS.finditer(text, at, min(len(text), at + LIST_SPAN)):
        depth += 1 if m.group(0) in "([{" else -1
        if not depth:
            return m.start()
    return -1


def membership_use(text: str, at: int, end: int) -> bool:
    """Whether the use of a name at at..end is a membership test: `x in NAME` (not a `for` loop,
    unless inside `any(`/`all(`), or `NAME.includes(x)`, `.has(`, `.contains(`."""
    if MEMBER_AFTER.match(text, end):
        return True
    line = text[max(text.rfind("\n", max(0, at - HEAD), at) + 1, at - HEAD):at]
    if not MEMBERSHIP.search(line):
        return False
    return not FOR_LOOP.search(line) or bool(ANY_ALL.search(line))


def only_membership(text: str, name: str, assigned: int) -> bool:
    """Every use of `name` in the file other than its assignment (the one ending near `assigned`)
    is a membership test; a name used more than NAME_USES times is not checked and does not count."""
    if not name or not (name[0].isalpha() or name[0] in "_$"):
        return False
    pos, uses = 0, 0
    while True:
        at = text.find(name, pos)
        if at < 0:
            return True
        end, pos = at + len(name), at + len(name)
        if (at and (text[at - 1].isalnum() or text[at - 1] in "_$")) or (end < len(text) and
                                                                         (text[end].isalnum() or text[end] in "_$")):
            continue
        if assigned - HEAD <= at < assigned:  # the assignment itself
            continue
        uses += 1
        if uses > NAME_USES or not membership_use(text, at, end):
            return False


class Mentions:
    """Answers is_mention() for the flags found in one file."""

    def __init__(self, text: str, suffix: str, settings: bool = False):
        """`settings`: the file is a settings file (rule (d) applies)."""
        self.text, self.suffix, self.settings = text, suffix, settings
        self.yaml = suffix in (".yml", ".yaml")
        self.structured = suffix in STRUCTURED_EXT
        self._regions: Regions | None = None
        self._yaml_items: set[int] | None = None  # YAML list items that are mentions under (d) or (e)
        self._lists: dict[int, bool] = {}       # opening bracket -> its items are mentions
        self._cursor, self._opens = 0, []
        self._spans: tuple[int, list] = (0, [])  # the quoted strings of the last line looked at

    def enclosing(self, at: int) -> list[int]:
        """Open brackets enclosing offset `at`, from one forward pass (restarted when `at` goes back)."""
        if at < self._cursor:
            self._cursor, self._opens = 0, []
        for m in BRACKETS.finditer(self.text, self._cursor, at):
            if m.group(0) in "([{":
                if len(self._opens) < MAX_OPEN_BRACKETS:
                    self._opens.append(m.start())
            elif self._opens:
                self._opens.pop()
        self._cursor = at
        return self._opens

    def is_mention(self, line_start: int, line: str, n: int, start: int, end: int) -> bool:
        """`line` is the text of line n (1-based, its trailing comment removed) starting at offset
        line_start; start..end is the flag."""
        if self._regions is None:
            self._regions = Regions(self.text, self.suffix)
        if self._regions.inside(start):
            # A block comment never hides a line that runs an agent: if the tokenizer misread a
            # string as opening one, that line is still code.
            return not (self._regions.comments and runs_agent(line))
        s, e = start - line_start, end - line_start
        if tested(line[:s], line[e:e + HEAD]):
            return True
        if self._spans[0] != n:
            self._spans = (n, string_spans(line))
        span = string_around(self._spans[1], s, e)
        if span is None:
            return (self.suffix in REGEX_LITERAL_EXT and in_regex(line, s, e)) or self.yaml_listed(n)
        return bool(COMPARED_AFTER.match(line, span[1] + 1)) \
            or bool(COMPARED_BEFORE.search(line[max(0, span[0] - HEAD):span[0]].rstrip())) \
            or self.listed(n, start, line_start + span[0])

    def yaml_listed(self, n: int) -> bool:
        """Line n is an item of a YAML list that is a mention under (d) or (e), quoted or not."""
        if not self.yaml:
            return False
        if self._yaml_items is None:
            self._yaml_items = yaml_mention_items(self.text, self.settings)
        return n in self._yaml_items

    def listed(self, n: int, start: int, opened: int) -> bool:
        """An item of a list that is a mention under (d) or (e); brackets inside the flag's own
        string (opened at `opened`, such as `"Bash(claude --flag:*)"`) do not enclose it."""
        if self.yaml_listed(n):
            return True
        opens = [o for o in self.enclosing(start) if o < opened]
        if not opens:
            return False
        inner = opens[-1]
        if inner not in self._lists:
            self._lists[inner] = self.mention_list(opens)
        return self._lists[inner]

    def mention_list(self, opens: list[int]) -> bool:
        """Whether the items of the innermost list in `opens` are mentions: the list is tested
        for membership (`x in (...)`, not `for x in (...)`), or it is (d) or (e)."""
        text = self.text
        for at in reversed(opens[-3:]):  # `frozenset({` and `new Set([` open twice
            head = text[max(text.rfind("\n", max(0, at - HEAD), at) + 1, at - HEAD):at]
            if MEMBERSHIP.search(head) and not FOR_LOOP.search(head):  # `if arg in ("--x", "--flag"):`
                return True
            name = head_name(text, at)
            if name:
                return self.named_list(opens, at, name.strip("\"'"))
            if not head.rstrip().endswith(("(", "[", "{")):
                return False
        return False

    def named_list(self, opens: list[int], at: int, name: str) -> bool:
        """(d) or (e) for the list opened at `at` and assigned to `name`."""
        text = self.text
        if self.structured and self.settings and name in SETTINGS_DENY:
            outer = [o for o in opens if o < at]
            if outer and (head_name(text, outer[-1]) or "").strip("\"'") == "permissions":
                return True  # (d)
        if not deny_name(name):
            return False
        close = list_end(text, at)
        if close < 0 or AGENT_COMMAND.search(text, at, close):
            return False
        return self.structured or only_membership(text, name, at)  # (e)


def yaml_mention_items(text: str, settings: bool) -> set[int]:
    """Line numbers (1-based) of YAML list items under a key that is (d) `permissions.deny` or
    `.ask` in a settings file, or (e) a deny-list name whose items name no agent CLI. Found in one
    pass with a stack of the keys enclosing each line (one entry per indentation level). An item's
    key is the nearest line above it that is indented less, or as much but is not itself an item."""
    items: set[int] = set()
    groups: dict[int, list] = {}  # key line -> [deny-list key, items, an item names an agent]
    stack: list[tuple[int, bool, str, int]] = []  # (indent, is an item, key, key line)
    for n, line in enumerate(text.split("\n"), 1):
        body = line.lstrip()
        if not body or body.startswith("#"):
            continue
        indent, item = len(line) - len(body), body.startswith("- ")
        while stack and (stack[-1][0] > indent or (stack[-1][0] == indent and (stack[-1][1] or not item))):
            stack.pop()
        if item and stack and stack[-1][3] in groups:
            group = groups[stack[-1][3]]
            group[1].append(n)
            group[2] = group[2] or bool(AGENT_COMMAND.search(line))
        key = YAML_KEY.match(line)
        name = key.group(1) if key else ""
        if name and (deny_name(name) or (settings and name in SETTINGS_DENY and len(stack) and
                                         stack[-1][2] == "permissions")):
            groups[n] = [settings and name in SETTINGS_DENY and bool(stack) and stack[-1][2] == "permissions", [], False]
        stack.append((indent, item, name, n))
    for settings_key, lines, agent in groups.values():
        if settings_key or not agent:
            items.update(lines)
    return items
