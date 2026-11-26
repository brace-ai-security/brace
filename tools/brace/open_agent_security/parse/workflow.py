"""GitHub Actions workflows: the pull_request_target trigger and whether a step runs an agent.

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
AGENT_USES = re.compile("|".join([alternation(ACTIONS) + r"[\w.\-]*", alternation(PACKAGES) + r"(?![\w-])"]), re.I)
PREFIX = (r"(?:(?:[A-Za-z_]\w{0,60}=\S{0,200}|"
          r"(?:sudo|env|nice|nohup|time|command|exec|timeout)(?:[ \t]{1,20}-{1,2}[\w=][\w=-]{0,29}){0,3}"
          r"(?:[ \t]{1,20}\d[\w.]{0,10})?|"  # timeout's duration
          r"if|!|then|do|else|npx(?:[ \t]{1,20}-y)?|bunx|pnpm[ \t]{1,20}dlx)[ \t]{1,20}){0,6}")
CLI_CALL = (PREFIX + rf"(?:(?:{alternation(CLIS)})(?![\w-])[^\n|;&]{{0,300}}?"
            r"[ \t](?:-p|--print|--prompt|exec|run|--message)(?![\w-])|"
            r"(?:gemini|qwen)[ \t]{1,20}[\"'])")  # Gemini CLI and Qwen Code also take the prompt as a quoted argument
AGENT_CLI = re.compile(r"(?:\brun:[ \t]*(?:[|>][ \t]*)?|[;&|][ \t]*|\$\([ \t]*)" + CLI_CALL)
AGENT_CLI_AT_START = re.compile(CLI_CALL)  # used with match(), inside a run block
RUN_BLOCK = re.compile(r"^(?:-[ \t]*)?run[ \t]*:[ \t]*[|>][-+0-9]*[ \t]*(?:#.*)?$")
STEP_NAME = re.compile(r"^-?[ \t]*name[ \t]*:")
PRT_LINE = re.compile(r"^(?:-\s*)?[\"']?pull_request_target[\"']?\s*(?::\s*)?(?:#.*)?$|^[\"']?pull_request_target[\"']?\s*:|"
                      r"^[\"']?on[\"']?\s*:.*\bpull_request_target\b|^\[.*\bpull_request_target\b")
WORKFLOW_FILE = re.compile(r"(?:^|/)\.github/workflows/[^/]+\.ya?ml$", re.I)


def is_workflow(display: str) -> bool:
    """A GitHub Actions workflow file, at the scanned root or in a nested project."""
    return bool(WORKFLOW_FILE.search(display))


def heuristic_lines(text: str):
    """(number, stripped line) for each line, cut to MAX_LINE characters."""
    for n, line in enumerate(text.split("\n"), 1):
        yield n, line[:MAX_LINE].strip()


def agent_step(text: str) -> bool:
    """Whether a workflow runs an agent: a vendor action or package, or an agent CLI in a command."""
    block = -1  # indentation of the `run: |` key whose block we are in, or -1
    for line in text.split("\n"):
        line = line[:MAX_LINE]
        s = line.strip()
        if not s:
            continue
        indent = len(line) - len(line.lstrip())
        if block >= 0 and indent <= block:
            block = -1
        if s.startswith("#") or STEP_NAME.match(s):
            continue
        if AGENT_USES.search(s) or AGENT_CLI.search(s) or (block >= 0 and AGENT_CLI_AT_START.match(s)):
            return True
        if block < 0 and RUN_BLOCK.match(s):
            block = indent + (s.index("run") if s.startswith("-") else 0)
    return False


def trigger_line(text: str) -> int | None:
    if "pull_request_target" not in text:
        return None
    for n, s in heuristic_lines(text):
        if "pull_request_target" in s and not s.startswith("#") and PRT_LINE.search(s):
            return n
    return None


class Workflow:
    name = "github-workflow"

    def claims(self, src: SourceFile) -> bool:
        return src.origin == "repo" and is_workflow(src.display)

    def parse(self, src: SourceFile, doc: Document) -> None:
        doc.workflow = WorkflowFacts(trigger_line(src.text), agent_step(src.text))
