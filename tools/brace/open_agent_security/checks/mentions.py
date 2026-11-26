"""Whether a bypass flag in text is only mentioned, not passed to an agent.

A flag is a mention only on positive evidence that it is not being passed: it is inside a
docstring or block comment, inside a string that is prose, compared or searched for, inside
a regular expression, or an item of a list named as a deny-list. Anything else counts,
including a lone quoted flag in an argument list. Every look-around is bounded, so the cost
per flag is constant, and each per-file pass (Regions, YAML parents) looks at each character
a bounded number of times.
"""
from __future__ import annotations

import bisect
import re

from ..agents import AGENT_COMMAND
from ..limits import MAX_OPEN_BRACKETS, MAX_PROSE

HEAD = 200             # characters before a list's opening bracket searched for its name
BRACKETS = re.compile(r"[()\[\]{}]")
# A name that says its list is blocked, as one of its word parts (`BLOCKED_FLAGS`, `denyList`,
# `disallowed-tools`, `GUARDS`); `UNSAFE_ARGS` or `dangerousFlags` name what is passed, not refused.
NAME_PART = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")
DENY_PART = re.compile(r"(?i)(?:block(?:ed|s|list)?|deny|denied|denylist|forbid(?:den|s)?|bans?|banned|disallow(?:ed|s)?|"
                       r"reject(?:ed|s)?|blacklist(?:ed)?|guard(?:ed|s)?)")
# A name assigned or keyed just before the list opens (`BLOCKED: list[str] = [`, `"deny": [`,
# `const DENY = new Set([`), matched on the reversed text so the match is anchored.
ASSIGNED_REVERSED = re.compile(r"^[ \t]{0,20}(?:\([ \t]{0,20}\w{1,40}(?:[ \t]{1,20}wen)?[ \t]{0,20})?"
                               r"(?:=[ \t]{0,20}(?:[^=:\n\"']{0,80}:)?|:)[ \t]{0,20}[\"']?([\w$-]{1,80})")
MEMBERSHIP = re.compile(r"\bin[ \t]{0,20}$")
FOR_LOOP = re.compile(r"\bfor\b")  # `for flag in [...]` passes each item; it is not a membership test
COMPARED_AFTER = re.compile(r"[ \t]{0,20}(?:not[ \t]{1,20}in\b|in\b|[!=]==?)")
COMPARED_BEFORE = re.compile(r"(?:[!=]==?|\.(?:includes|contains|has|indexOf|startswith|startsWith)\(|"
                             r"\bre\.\w{1,12}\(|\bRegExp\()[ \t]*[rRbB]?$")
FLAG_TOKEN = re.compile(r"(?<![\w-])--?[A-Za-z][\w-]*")
EXPANSION = re.compile(r"\$[\w{(]|`")  # `$AGENT`, `${X}`, `$(...)`: a command line built from parts
# Words of prose that a command line rarely holds.
PROSE_WORDS = frozenset("a an the to not never no do don't dont is are be use using pass passing with without this that "
                        "these here only refuse refusing refused avoid must should if when or and of for in on we you it "
                        "disallowed blocked forbidden allowed unsafe dangerous".split())
YAML_PLAIN = re.compile(r"^[ \t]*(?:-[ \t]+)?[\"']?[\w.\-]{1,80}[\"']?[ \t]*:[ \t]+(?![\"'|>\[{])")
YAML_KEY = re.compile(r"^[ \t]*(?:-[ \t]+)?[\"']?([\w.\-]{1,80})[\"']?[ \t]*:[ \t]*(?:#.*)?$")
TRIPLE = re.compile(r"\"\"\"|'''")
BLOCK_COMMENT_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".go", ".rs", ".java", ".kt",
                     ".jsonc"}
REGEX_LITERAL_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".rb"}


# Tokens outside strings in C-like files: a block or line comment, or a string's opening quote;
# in JavaScript and TypeScript also a lone slash, which may open a /regex/ literal.
CODE_TOKEN = re.compile(r"/\*|//|[\"'`]")
JS_CODE_TOKEN = re.compile(r"/\*|//|/|[\"'`]")
JS_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"}
# A slash opens a regex literal after an operator, an opening bracket, or one of these words.
REGEX_BEFORE_CHARS = "(=,:!&|?{};[+-*%<>~^"
REGEX_BEFORE_WORD = re.compile(r"(?<![\w$.])(?:return|typeof|case|yield|await|in|of|delete|void|throw|new|else|do)$")
REGEX_END = re.compile(r"\\[^\n]|[\[\]/\n]")  # inside a regex literal: an escape, a class bracket, its end
# The end of a string opened by each quote: its closing quote, or a line break for quotes that
# cannot span lines. A backslash escapes the next character, except in a Go raw string.
DOUBLE_END = re.compile(r'\\[\s\S]|"|\n')
SINGLE_END = re.compile(r"\\[\s\S]|'|\n")
TEMPLATE_END = re.compile(r"\\[\s\S]|`")
GO_RAW_END = re.compile("`")
RUST_DOUBLE_END = re.compile(r'\\[\s\S]|"')  # a Rust string may span lines
STRING_END = {'"': DOUBLE_END, "'": SINGLE_END, "`": TEMPLATE_END}
DOCSTRING_LOOKBACK = 50  # lines searched up for the `def ...:` or `class ...:` a docstring follows
DOCSTRING_INDENT = 200   # longest indentation before a docstring's opening quotes


class Regions:
    """Docstrings (Python) and /* block comments */ in one file, found once in a linear pass."""

    def __init__(self, text: str, suffix: str):
        self.starts: list[int] = []
        self.ends: list[int] = []
        if suffix == ".py":
            self.docstrings(text)
        elif suffix in BLOCK_COMMENT_EXT or suffix == ".groovy":
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
        regex literals, so `glob("src/*.ts")`, `"Accept": "*/*"` or `s.replace(/\\/*$/, "")` does
        not open one; nor does `\\/*`, and an unclosed `/*` hides nothing. Strings are skipped by
        their quotes (template literals and Go raw strings included); each character is looked
        at a bounded number of times."""
        tokens = JS_CODE_TOKEN if suffix in JS_EXT else CODE_TOKEN
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
            else:
                rx = GO_RAW_END if token == "`" and suffix == ".go" else \
                    RUST_DOUBLE_END if token == '"' and suffix == ".rs" else STRING_END[token]
                pos = m.end()
                while True:
                    e = rx.search(text, pos)
                    if not e:
                        return  # an unclosed string runs to the end of the file
                    pos = e.end()
                    if e.group(0)[0] != "\\":
                        break

    def inside(self, at: int) -> bool:
        k = bisect.bisect_right(self.starts, at) - 1
        return k >= 0 and at < self.ends[k]


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


def prose(s: str, flag: str) -> bool:
    """A sentence about the flag, not a command line: plain words, and no other flag or agent
    command, and nothing expanded: `npx @anthropic-ai/claude-code <flag> "fix the tests"` and
    `$AGENT <flag> on the repo` are command lines, not prose."""
    rest = s.replace(flag, " ")
    if AGENT_COMMAND.search(rest) or FLAG_TOKEN.search(rest) or EXPANSION.search(rest):
        return False
    return any(w.lower().strip(".,;:!?()") in PROSE_WORDS for w in rest.split())


def in_regex(line: str, start: int, end: int) -> bool:
    """Inside a /regex/ literal: a slash before and after, with an operator or bracket before the first."""
    i = line.rfind("/", max(0, start - HEAD), start)
    if i < 0 or line.find("/", end, end + HEAD) < 0 or any(q in line[i:start] for q in "\"'`"):
        return False
    before = line[max(0, i - HEAD):i].rstrip()
    return not before or before[-1] in "(=,:!&|?{;[" or before.endswith("return")


def deny_name(name: str) -> bool:
    """A name with a word part that says its items are refused (see DENY_PART)."""
    return any(DENY_PART.fullmatch(part) for part in NAME_PART.findall(name[:80]))


def deny_list(text: str, opens: list[int]) -> bool:
    """An item of a list, set or call whose assigned name or key reads as a deny-list, or that
    is tested for membership (`x in (...)`, not `for x in (...)`). `opens` are the brackets
    that enclose the item, innermost last."""
    for at in reversed(opens[-3:]):  # `frozenset({` and `new Set([` open twice
        head = text[max(text.rfind("\n", max(0, at - HEAD), at) + 1, at - HEAD):at]
        if MEMBERSHIP.search(head) and not FOR_LOOP.search(head):  # `if arg in ("--x", "--dangerously-skip-permissions"):`
            return True
        m = ASSIGNED_REVERSED.match(head[::-1])
        if m:
            return deny_name(m.group(1)[::-1])
        if not head.rstrip().endswith(("(", "[", "{")):
            return False
    return False


def yaml_deny_items(text: str) -> set[int]:
    """Line numbers (1-based) of YAML list items under a key that reads as a deny-list, found in
    one pass with a stack of the keys enclosing each line (one entry per indentation level, so
    its size is bounded by the line's indentation). An item's key is the nearest line above it
    that is indented less, or as much but is not itself an item."""
    items: set[int] = set()
    stack: list[tuple[int, bool, bool]] = []  # (indent, is an item, is a deny-list key)
    for n, line in enumerate(text.split("\n"), 1):
        body = line.lstrip()
        if not body or body.startswith("#"):
            continue
        indent, item = len(line) - len(body), body.startswith("- ")
        while stack and (stack[-1][0] > indent or (stack[-1][0] == indent and (stack[-1][1] or not item))):
            stack.pop()
        if item and stack and stack[-1][2]:
            items.add(n)
        key = YAML_KEY.match(line)
        stack.append((indent, item, bool(key and deny_name(key.group(1)))))
    return items


class Mentions:
    """Answers is_mention() for the flags found in one file."""

    def __init__(self, text: str, suffix: str):
        self.text, self.suffix = text, suffix
        self.yaml = suffix in (".yml", ".yaml")
        self._regions: Regions | None = None
        self._deny_items: set[int] | None = None  # YAML list items under a deny-list key
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
        """`line` is the text of line n (1-based) starting at offset line_start; start..end is the flag."""
        if self._regions is None:
            self._regions = Regions(self.text, self.suffix)
        if self._regions.inside(start):
            return True
        s, e, flag = start - line_start, end - line_start, self.text[start:end]
        if self._spans[0] != n:
            self._spans = (n, string_spans(line))
        span = string_around(self._spans[1], s, e)
        plain = YAML_PLAIN.match(line) if self.yaml and span is None else None
        if plain:
            return prose(line[plain.end():], flag)
        if span is None:
            return (self.suffix in REGEX_LITERAL_EXT and in_regex(line, s, e)) or self.yaml_listed(n)
        body = line[span[0] + 1:span[1]]
        return (len(body) <= MAX_PROSE and prose(body, flag)) or bool(COMPARED_AFTER.match(line, span[1] + 1)) \
            or bool(COMPARED_BEFORE.search(line[max(0, span[0] - HEAD):span[0]].rstrip())) or self.listed(n, start)

    def yaml_listed(self, n: int) -> bool:
        """Line n is an item of a YAML list under a deny-list key, quoted or not."""
        if not self.yaml:
            return False
        if self._deny_items is None:
            self._deny_items = yaml_deny_items(self.text)
        return n in self._deny_items

    def listed(self, n: int, start: int) -> bool:
        return self.yaml_listed(n) or deny_list(self.text, self.enclosing(start))
