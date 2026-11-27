"""Ignore entries: gitignore-style path globs, the ignore file, and the inline ignore mark.

The same globs serve the config file's `ignore`, `include` and `agent-config` lists. Matching
uses no regexes built from user input and no backtracking, so a hostile pattern stays fast.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Collection, NamedTuple

from .catalog import RULE_ID_PATTERN
from .fsio import ReadFailure, read
from .limits import IGNORE_CACHE_FOLDERS, MAX_FLEX, MAX_IGNORES, MAX_PATTERN, MAX_SEGMENTS, MB
from .output import size_label

IGNORE_FILE = ".open-agent-security-ignore"
IGNORE_MARK = "open-agent-security: ignore"
STARS = re.compile(r"\*+")
TRAILING_COMMENT = re.compile(r"(?:^|\s)#.*$")
BUILTIN_RULE = re.compile(r"^AP\d\d$")  # a built-in rule ID's form, registered or not
RULE_PREFIX = re.compile(rf"^({RULE_ID_PATTERN})\s+(.+)$")  # `AP04 path`, or a plugin rule such as `ACME-01 path`


class PatternTooDeep(ValueError):
    """A pattern with more than MAX_SEGMENTS path segments."""


class PathGlob(NamedTuple):
    """One gitignore-style pattern, as parsed by parse_pattern."""
    rule: str | None     # only this rule, or every rule
    neg: bool            # `!pattern` re-includes
    segs: list[str]      # path segments; "**" crosses folders
    dir_only: bool       # trailing "/" matches folders only


def flex(entry: PathGlob) -> int:
    """The segments after the entry's first `**` (0 without one): its share of MAX_FLEX."""
    return len(entry.segs) - entry.segs.index("**") if "**" in entry.segs else 0


class SegmentGlob:
    """`*` and `?` within one path segment, split once. The literal head and tail are checked
    first, then each piece between stars is found leftmost (which is enough for `*`), so
    matching is about one pass over the name per piece."""

    __slots__ = ("pieces", "head", "tail", "fixed", "plain")

    def __init__(self, pat: str):
        self.pieces = pat.split("*")
        self.head, self.tail = self.pieces[0], self.pieces[-1]
        self.fixed = len(self.head) + len(self.tail) if len(self.pieces) > 1 else len(pat)
        self.plain = "?" not in pat

    def match(self, name: str) -> bool:
        if len(self.pieces) == 1:
            return len(name) == self.fixed and piece_at(self.head, name, 0)
        if self.fixed > len(name):
            return False
        if self.plain:
            if not (name.startswith(self.head) and name.endswith(self.tail)):
                return False
        elif not (piece_at(self.head, name, 0) and piece_at(self.tail, name, len(name) - len(self.tail))):
            return False
        pos, end = len(self.head), len(name) - len(self.tail)
        for piece in self.pieces[1:-1]:
            pos = find_piece(piece, name, pos, end)
            if pos < 0:
                return False
            pos += len(piece)
        return True


def piece_at(piece: str, name: str, at: int) -> bool:
    """Whether `piece` (literal characters and `?`) matches name at index `at`."""
    if "?" not in piece:
        return name.startswith(piece, at)
    return at + len(piece) <= len(name) and all(c == "?" or c == name[at + i] for i, c in enumerate(piece))


def find_piece(piece: str, name: str, start: int, end: int) -> int:
    """The first index in name[start:end] where `piece` matches, or -1."""
    if "?" not in piece:
        return name.find(piece, start, end)
    for i in range(start, end - len(piece) + 1):
        if piece_at(piece, name, i):
            return i
    return -1


def parse_pattern(line: str, rule: str | None = None) -> PathGlob | None:
    """One gitignore-style pattern: `!` negates; a leading `/` anchors to the scanned folder;
    a trailing `/` matches folders only; a pattern without `/` matches a name at any depth;
    `*` stays within one folder and `**` crosses folders. Raises PatternTooDeep for a pattern
    of more than MAX_SEGMENTS folders."""
    neg = line.startswith("!")
    line = line[1:] if neg else line
    dir_only = line.endswith("/")
    line = line.rstrip("/")
    anchored = line.startswith("/") or "/" in line
    segs = [STARS.sub("*", s) if s != "**" else s for s in line.lstrip("/").split("/") if s]
    if not segs:
        return None
    if not anchored:
        segs = ["**"] + segs
    segs = [s for i, s in enumerate(segs) if not (s == "**" and i and segs[i - 1] == "**")]
    if len(segs) > MAX_SEGMENTS:
        raise PatternTooDeep(line)
    return PathGlob(rule, neg, segs, dir_only)


def load_ignores(root: Path, limit: int = MB, rules: Collection[str] = ()) -> tuple[list[PathGlob], list[str]]:
    """Patterns from IGNORE_FILE. Each line: [RULE ]pattern [# comment].

    A line starting with `#` is a comment, and so is ` #...` after a pattern. An optional rule
    ID first (`AP04 .vscode/mcp.json`, or a registered plugin rule ID from `rules`) limits the
    entry to that rule; any other first word is part of the path (`LICENSE files/x.sh`). At most MAX_IGNORES
    entries of up to MAX_PATTERN characters are read. Patterns deeper than MAX_SEGMENTS folders,
    and patterns past the MAX_FLEX budget, are skipped with a note. A file that cannot be read
    (a symlink, too large, unreadable) is not applied, with a note. Returns (entries, notes)."""
    path = root / IGNORE_FILE
    text = read(path, limit=limit)
    if isinstance(text, ReadFailure):
        if not (path.is_symlink() or path.exists()):
            return [], []
        why = f"over {size_label(limit)}" if text.reason == "oversized" else \
            "a symlink" if text.reason == "symlink" else text.reason
        return [], [f"ignore file: {IGNORE_FILE} is {why}, so it was not applied"]
    out: list[PathGlob] = []
    too_deep = too_complex = budget = 0
    for raw in text.split("\n"):
        if len(raw) > 4 * MAX_PATTERN:
            continue  # far too long to be a pattern, even with a comment
        line = TRAILING_COMMENT.sub("", raw).strip()
        if not line or len(line) > MAX_PATTERN:
            continue
        rule = None
        m = RULE_PREFIX.match(line)
        if m and (m.group(1) in rules or BUILTIN_RULE.match(m.group(1))):
            rule, line = m.group(1), m.group(2).strip()
        try:
            entry = parse_pattern(line, rule)
        except PatternTooDeep:
            too_deep += 1
            continue
        if entry and budget + flex(entry) > MAX_FLEX:
            too_complex += 1
        elif entry:
            budget += flex(entry)
            out.append(entry)
        if len(out) >= MAX_IGNORES:
            break
    notes = []
    if too_deep:
        notes.append(f"ignore file: skipped {too_deep} pattern(s) of more than {MAX_SEGMENTS} folders")
    if too_complex:
        notes.append(f"ignore file: skipped {too_complex} pattern(s) past the limit of {MAX_FLEX} segments "
                     "after `**` in all")
    return out, notes


class GlobSet:
    """Path globs, evaluated in order (later entries win, `!` re-includes), against a path and
    each of its parent folders. The config's include and agent-config lists are GlobSets.

    Each distinct pattern runs as a small automaton over path segments. Its state after each
    folder is cached, so a file costs one step per pattern: the walk visits a folder once and
    every file in it reuses the folder's state. A pattern with more plain segments than the
    path has parts is skipped without any work, and states are computed only when needed."""

    def __init__(self, entries):
        self.entries = list(entries)
        self.negations = any(e.neg for e in self.entries)
        distinct = list(dict.fromkeys((tuple(e.segs), e.dir_only) for e in self.entries))
        at = {p: i for i, p in enumerate(distinct)}
        self.pattern_of = [at[(tuple(e.segs), e.dir_only)] for e in self.entries]
        self.patterns = [Pattern(list(segs), dir_only) for segs, dir_only in distinct]
        self.literal = any(p.literal for p in self.patterns)
        self._folders: dict[str, list] = {}  # folder -> per pattern: (states, matched) or None

    def _state(self, idx: int, folder: str) -> tuple:
        """Pattern idx after the folder's segments: (states, matched), where matched means the
        pattern matches this folder or one of its parents."""
        pattern, todo = self.patterns[idx], []
        while folder:
            row = self._folders.get(folder)
            if row is not None and row[idx] is not None:
                break
            todo.append(folder)
            folder = folder.rpartition("/")[0]
        cur = self._folders[folder][idx] if folder else pattern.start
        for f in reversed(todo):
            cur = pattern.step(cur, f.rpartition("/")[2])
            row = self._folders.get(f)
            if row is None:
                if len(self._folders) >= IGNORE_CACHE_FOLDERS:
                    self._folders.clear()
                row = self._folders[f] = [None] * len(self.patterns)
            row[idx] = cur
        return cur

    def match(self, rel: str, rule: str | None = None, is_dir: bool = False) -> bool:
        depth = rel.count("/") + 1
        folder, _, name = rel.rpartition("/")
        names = set(rel.split("/")) if self.literal else set()
        result = False
        for entry, idx in zip(self.entries, self.pattern_of):
            pattern = self.patterns[idx]
            if (entry.rule is not None and entry.rule != rule) or pattern.plain > depth \
                    or (pattern.literal and pattern.literal not in names):
                continue
            hit = self._state(idx, rel)[1] if is_dir else pattern.ends(self._state(idx, folder), name)
            if hit:
                result = not entry.neg
        return result


class Ignores(GlobSet):
    """Ignore entries: a GlobSet that can also say when a whole folder need not be walked."""

    def prunes(self, reldir: str) -> bool:
        """Skip walking a folder only when it is ignored for every rule and nothing re-includes."""
        return not self.negations and self.match(reldir, None, is_dir=True)


class Pattern:
    """One pattern as an automaton: a state is the number of segments matched so far, and
    `**` keeps its state while consuming a folder. As in git, a leading or inner `**` matches
    zero or more folders, but a trailing `**` (`X/**`) one or more: everything inside X, not X."""

    def __init__(self, segs: list[str], dir_only: bool):
        self.segs, self.dir_only, self.n = segs, dir_only, len(segs)
        self.trailing = bool(segs) and segs[-1] == "**"
        self.globs = [None if s == "**" else SegmentGlob(s) for s in segs]
        self.plain = sum(s != "**" for s in segs)       # path parts needed at least
        self.last = max((i for i, s in enumerate(segs) if s != "**"), default=-1)
        # a last segment without wildcards must be one of the path's names
        self.literal = segs[-1] if "*" not in segs[-1] and "?" not in segs[-1] else ""
        # reach[i]: state i and the states after it that `**` lets the pattern skip to
        self.reach = [frozenset(range(i, self._skip(i) + 1)) for i in range(self.n + 1)]
        self.start = (self.reach[0], False)

    def _skip(self, i: int) -> int:
        """The last state that `**` segments from state i let the pattern reach without consuming
        anything; a trailing `**` is never skipped, as it must consume at least one segment."""
        while i < self.n and self.segs[i] == "**" and not (self.trailing and i == self.n - 1):
            i += 1
        return i

    def step(self, cur: tuple, name: str) -> tuple:
        """The state after one more folder."""
        states, matched = cur
        if matched:
            return cur
        nxt: set[int] = set()
        for i in states:
            if i < self.n:
                glob = self.globs[i]
                if glob is None:
                    nxt |= self.reach[i]
                    if self.trailing and i == self.n - 1:
                        nxt.add(self.n)  # the trailing `**` has consumed a segment
                elif glob.match(name):
                    nxt |= self.reach[i + 1]
        return frozenset(nxt), self.n in nxt

    def ends(self, cur: tuple, name: str) -> bool:
        """Whether a file `name` in the folder matches: a parent folder matched, or one more
        segment completes the pattern (a trailing `**`, or the last plain segment)."""
        states, matched = cur
        if matched:
            return True
        if self.dir_only or not states:
            return False
        if max(states) > self.last:  # inside a `**` after the last plain segment, which takes the name
            return True
        return self.last in states and self.n in self.reach[self.last + 1] and self.globs[self.last].match(name)


def marked_lines(text: str) -> set[int]:
    """Line numbers that carry the inline ignore mark."""
    if IGNORE_MARK not in text:
        return set()
    return {n for n, ln in enumerate(text.split("\n"), 1) if IGNORE_MARK in ln}
