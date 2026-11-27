"""GitHub Actions workflows and local actions (`action.yml`): the pull_request_target trigger,
whether a step runs an agent, and the local actions and reusable workflows they use.

There is no YAML parser in the standard library, so these are line heuristics, not a step tree.
"""
from __future__ import annotations

import re

from ..agents import ACTIONS, CLIS, PACKAGES, alternation
from ..limits import MAX_LINE
from ..model import Document, SourceFile, WorkflowFacts

# Agent steps in a workflow: the vendors' actions and npm packages anywhere, and agent CLIs
# in command position, case-sensitive: after `run:`, a shell operator or `$(`, or at the start
# of a line inside a `run: |` block, behind any of a few bounded prefixes (`VAR=value`,
# `timeout 300`, `sudo`, `env`, `if !`, `then`, `npx -y`). Prose elsewhere (a github-script
# body, a comment template) that starts with "claude" is not a command.
AGENT_USES = re.compile(rf"(?:{alternation(ACTIONS)})[\w.\-]*|(?:{alternation(PACKAGES)})(?![\w-])", re.I)
PREFIX = (r"(?:(?:[A-Za-z_]\w{0,60}=\S{0,200}|"
          r"(?:sudo|env|nice|nohup|time|command|exec|timeout)(?:[ \t]{1,20}-{1,2}[\w=][\w=-]{0,29}){0,3}"
          r"(?:[ \t]{1,20}\d[\w.]{0,10})?|"  # timeout's duration
          r"if|!|then|do|else|npx(?:[ \t]{1,20}-y)?|bunx|pnpm[ \t]{1,20}dlx)[ \t]{1,20}){0,6}")
CLI_CALL = (PREFIX + rf"(?:(?:{alternation(CLIS)})(?![\w-])[^\n|;&]{{0,300}}?"
            r"[ \t](?:-p|--print|--prompt|exec|run|--message|--message-file|--yes-always)(?![\w-])|"
            r"(?:gemini|qwen)[ \t]{1,20}[\"'])")  # Gemini CLI and Qwen Code also take the prompt as a quoted argument
AGENT_CLI = re.compile(r"(?:\brun:[ \t]*(?:[|>][ \t]*)?|[;&|][ \t]*|\$\([ \t]*)" + CLI_CALL)
AGENT_CLI_AT_START = re.compile(CLI_CALL)  # used with match(), inside a run block
RUN_BLOCK = re.compile(r"^(?:-[ \t]*)?run[ \t]*:[ \t]*([|>])[-+0-9]*[ \t]*(?:#.*)?$")
JOINED_LINES = 20  # lines joined into one command: `\` continuations, or a folded `run: >` block
STEP_NAME = re.compile(r"^-?[ \t]*name[ \t]*:")
PRT_LINE = re.compile(r"^(?:-\s*)?[\"']?pull_request_target[\"']?\s*(?::\s*)?(?:#.*)?$|^[\"']?pull_request_target[\"']?\s*:|"
                      r"^[\"']?on[\"']?\s*:.*\bpull_request_target\b|^\[.*\bpull_request_target\b")
WORKFLOW_FILE = re.compile(r"(?:^|/)\.github/workflows/[^/]+\.ya?ml$", re.I)
ACTION_FILE = re.compile(r"(?:^|/)action\.ya?ml$", re.I)
LOCAL_USES = re.compile(r"^[ \t]*(?:-[ \t]+)?uses[ \t]*:[ \t]*[\"']?\./([^\s\"'#@]{0,300})", re.M)  # `./`: the repository's own action
MAX_LOCAL_USES = 50  # local actions and reusable workflows kept per file

# Events any GitHub user can cause (a comment, an issue, a discussion, a review), and
# workflow_run, which runs with secrets after a workflow a fork's pull request started.
OPEN_EVENTS = ("issue_comment", "issues", "discussion_comment", "discussion", "pull_request_review_comment",
               "pull_request_review", "workflow_run")
ON_KEY = re.compile(r"^[\"']?(?:on|true)[\"']?[ \t]*:[ \t]*(.*)$")  # YAML 1.1 reads a bare `on` as true
EVENT_KEY = re.compile(r"^(?:-[ \t]*)?[\"']?([a-z_]{1,40})[\"']?[ \t]*(?::|$)")
EVENT_WORD = re.compile(r"[a-z_]{1,40}")
# An actor or permission check: author_association, a comparison or allowlist on the actor,
# a collaborator-permission lookup, or (workflow_run) a check of where the triggering run came from.
ACTOR_GATE = re.compile(r"author_association|github\.(?:triggering_)?actor[ \t]*[!=]=|"
                        r"github\.event\.(?:comment|issue|review|discussion|sender)\.user\.login[ \t]*[!=]=|"
                        r"github\.event\.sender\.login[ \t]*[!=]=|"
                        r",[ \t]*github\.(?:triggering_)?actor[ \t]*\)|getCollaboratorPermissionLevel|"
                        r"/collaborators/[^\n]{0,200}/permission|check-user-permission|"
                        r"head_repository\.(?:full_name|fork)|workflow_run\.head_repository", re.I)
# The vendor actions that check the triggering actor's write access themselves unless told not to.
GATED_ACTION = re.compile(r"^[ \t]*(?:-[ \t]+)?uses[ \t]*:[ \t]*[\"']?(?:anthropics/claude-code-action|openai/codex-action)"
                          r"(?:@|[\"' \t]|$)", re.I | re.M)
OPENED_GATE = re.compile(r"(?:allowed_non_write_users|allow[-_]users)[ \t]*:[ \t]*[\"']?\*", re.I)


def is_workflow(display: str) -> bool:
    """A GitHub Actions workflow file, at the scanned root or in a nested project."""
    return bool(WORKFLOW_FILE.search(display))


def heuristic_lines(text: str):
    """(number, stripped line) for each line, cut to MAX_LINE characters."""
    for n, line in enumerate(text.split("\n"), 1):
        yield n, line[:MAX_LINE].strip()


def commands(text: str):
    """(command, inside a run block) for each line, with `\\` continuations and the lines of a
    folded `run: >` block joined into one (at most JOINED_LINES lines each), so a CLI call
    split over lines is seen whole. Comments and step names are left out."""
    block, folded, parts, in_block = -1, False, [], False  # block: indentation of the `run: |` key, or -1
    for line in text.split("\n"):
        line = line[:MAX_LINE]
        s = line.strip()
        if not s:
            continue
        indent = len(line) - len(line.lstrip())
        if block >= 0 and indent <= block:
            if parts:
                yield " ".join(parts), True
                parts = []
            block, folded = -1, False
        if s.startswith("#") or (not parts and STEP_NAME.match(s)):
            continue
        if not parts:
            in_block = block >= 0
        more = s.endswith("\\")
        parts.append(s[:-1].rstrip() if more else s)
        if (more or (folded and block >= 0)) and len(parts) < JOINED_LINES:
            continue
        joined, parts = " ".join(parts), []
        yield joined, in_block
        run = RUN_BLOCK.match(joined) if block < 0 else None
        if run:
            block, folded = indent + (joined.index("run") if joined.startswith("-") else 0), run.group(1) == ">"
    if parts:
        yield " ".join(parts), in_block


def agent_step(text: str) -> bool:
    """Whether a workflow runs an agent: a vendor action or package, or an agent CLI in a command."""
    return any(AGENT_USES.search(s) or AGENT_CLI.search(s) or (in_block and AGENT_CLI_AT_START.match(s))
               for s, in_block in commands(text))


def uncommented(s: str) -> str:
    """A YAML line without its trailing comment: a `#` after whitespace, outside quotes."""
    quote = ""
    for i, ch in enumerate(s):
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s


def trigger_line(text: str) -> int | None:
    if "pull_request_target" not in text:
        return None
    for n, s in heuristic_lines(text):
        s = uncommented(s)
        if "pull_request_target" in s and PRT_LINE.search(s):
            return n
    return None


def open_event(text: str) -> tuple[int | None, str]:
    """The first line, and name, of an OPEN_EVENTS trigger in the workflow's `on:` block (or an
    inline `on: issue_comment` / `on: [issues, push]`), or (None, "")."""
    if not any(e in text for e in OPEN_EVENTS):
        return None, ""
    inside = False
    for n, line in enumerate(text.split("\n"), 1):
        line = line[:MAX_LINE]
        body = uncommented(line.strip())
        if not body:
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            m = ON_KEY.match(body)
            inside = bool(m)
            if m:
                for w in EVENT_WORD.findall(m.group(1)):
                    if w in OPEN_EVENTS:
                        return n, w
            continue
        if inside:
            m = EVENT_KEY.match(body)
            if m and m.group(1) in OPEN_EVENTS and (body.startswith("-") or body.rstrip().endswith(":")
                                                     or ":" in body):
                return n, m.group(1)
    return None, ""


def open_agent(text: str) -> bool:
    """Whether an agent step runs without a vendor action's default write-access check: an agent
    other than claude-code-action or codex-action, or one of them with that check opened to anyone."""
    if OPENED_GATE.search(text):
        return True
    return agent_step(GATED_ACTION.sub("", text))


class Workflow:
    name = "github-workflow"

    def claims(self, src: SourceFile) -> bool:
        return src.origin == "repo" and (is_workflow(src.display) or bool(ACTION_FILE.search(src.display)))

    def parse(self, src: SourceFile, doc: Document) -> None:
        trigger = trigger_line(src.text) if is_workflow(src.display) else None
        uses = tuple(m.group(1).rstrip("/") for m in LOCAL_USES.finditer(src.text))[:MAX_LOCAL_USES]
        event, name = open_event(src.text) if is_workflow(src.display) else (None, "")
        agent = agent_step(src.text)
        doc.workflow = WorkflowFacts(trigger, agent, uses, event, name,
                                     bool(event and ACTOR_GATE.search(src.text)),
                                     bool(event and agent and open_agent(src.text)))
