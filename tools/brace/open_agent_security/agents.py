"""What the rules know about agents, declared once: CLIs, packages, actions, bypass flags and
the files and folders that hold agent configuration.

Every rule that needs one of these lists imports it from here, so they cannot drift apart.
"""
from __future__ import annotations

import re

# Agent CLIs, by the program name they are run as.
CLIS = ("claude", "codex", "gemini", "qwen", "copilot", "crush", "aider", "opencode", "cursor-agent", "goose", "amp")
# CLIs that take a bare --yolo, --allow-all or --allow-all-tools (generic flags elsewhere, such
# as Deno's --allow-all or YOLO object detection), so those count only next to one of these.
GATED_FLAG_CLIS = ("gemini", "qwen", "codex", "crush", "copilot")
PACKAGES = ("@anthropic-ai/claude-code", "@openai/codex", "@google/gemini-cli", "@qwen-code/qwen-code",
            "@github/copilot", "@charmland/crush", "opencode-ai")
# GitHub Actions, as the start of a `uses:` reference (anthropics/claude-code covers its -action
# and -base-action).
ACTIONS = ("anthropics/claude-code", "openai/codex-action", "google-github-actions/run-gemini-cli",
           "google-gemini/gemini-cli-action", "sst/opencode/github")
# Agent SDKs and frameworks in code: signs that an agent runs in the folder.
SDKS = (r"claude[_\-]agent[_\-]sdk", r"@anthropic-ai/claude-agent-sdk", r"claude-code-sdk", r"\bfrom agents import\b",
        r"@openai/agents", r"\bopenai-agents\b", r"\blanggraph\b", r"\bcrewai\b", r"\bautogen_agentchat\b",
        r"\bautogen_core\b", r"\bpyautogen\b", r"^[ \t]*(?:import|from)[ \t]+autogen\b", r"\bmcpServers\b",
        r"\bmcp_servers\b", r"modelcontextprotocol")


def alternation(names) -> str:
    return "|".join(re.escape(n) for n in names)


CLI_NAME = re.compile(rf"(?<![\w-])(?:{alternation(CLIS)})(?![\w-])")
# An agent command in any form: a vendor package or action, or a CLI name as a program
# (`claude`, `claude.exe`, `/usr/local/bin/claude`) or package (`claude-code`, `gemini-cli`).
AGENT_COMMAND = re.compile(rf"{alternation(PACKAGES)}|{alternation(ACTIONS)}|"
                           rf"(?<![\w.])(?:{alternation(CLIS)})(?:-[a-z]{{1,20}}){{0,2}}(?:\.exe|\.cmd)?(?![\w.])")
GATED_CLI = re.compile(rf"(?<![\w-])(?:{alternation(GATED_FLAG_CLIS)})(?![\w-])|@google/gemini-cli|@qwen-code/|"
                       r"@github/copilot", re.I)

AGENT_SIGNAL = re.compile("|".join(SDKS) + "|" + alternation(ACTIONS) + "|" + alternation(PACKAGES), re.M)

# Agent permission bypasses (Claude Code, Codex, Gemini CLI, Qwen Code, Copilot CLI and their
# SDKs). A flag and its value may be split by `=`, by any whitespace, line breaks included (a
# folded YAML scalar), by a YAML list's `- ` (`- --permission-mode` then `- bypassPermissions`),
# or be two items of a list (`"--sandbox", "danger-full-access"`); every gap is bounded, so
# matching stays linear.
END = r"(?![\w-])"  # a flag or value ends here (so --yolo does not match --yolo-weights)
GAP = r"(?:=[\"']?|[\"']\s{0,200},\s{0,200}[\"']|\s{1,200}(?:-[ \t]{1,20})?[\"']?)"
BYPASS = re.compile(
    r"--dangerously-skip-permissions" + END + r"|--dangerously-bypass-approvals-and-sandbox" + END + "|"
    r"--permission-mode" + GAP + "bypassPermissions" + END + "|"
    r"--approval-mode" + GAP + "yolo" + END + "|"
    r"(?:--sandbox|(?<![\w-])-s)" + GAP + "danger-full-access" + END + "|"
    r"\b(?:permission_?mode|permissionMode)[\"']?[ \t]*[:=][ \t]*[\"']?bypassPermissions" + END + r"[\"']?|"
    r"\bsandbox_mode[\"']?[ \t]*[:=][ \t]*[\"']?danger-full-access" + END + r"[\"']?", re.I)
# Bypasses only next to an agent CLI that takes them: Gemini/Qwen/Codex/Crush --yolo, and
# Copilot CLI's --allow-all-tools ("allow every tool without asking") and --allow-all.
GATED_BYPASS = re.compile(r"--(?:yolo|allow-all-tools|allow-all)" + END)
# Byte strings that mark a bypass, for files too large to read as text.
BYPASS_BYTES = (b"--dangerously-skip-permissions", b"--dangerously-bypass-approvals-and-sandbox",
                b"bypassPermissions", b"danger-full-access", b"--allow-all-tools")

# Files that configure an agent or its MCP servers, as paths ending a repository path.
CONFIG_FILES = (".mcp.json", "mcp.json", "mcp.jsonc", "mcp_config.json", "mcp-config.json",
                "claude_desktop_config.json", ".claude/settings.json", ".claude/settings.local.json",
                ".gemini/settings.json", ".qwen/settings.json", "opencode.json", "opencode.jsonc",
                "cline_mcp_settings.json", ".codex/config.toml", ".vscode/settings.json", ".cursor/mcp.json",
                ".roo/mcp.json", ".zed/settings.json")
CONFIG_FILE = re.compile(rf"(?:^|/)(?:{alternation(CONFIG_FILES)})$", re.I)
# General editor settings: agent config only when they hold MCP servers.
SHARED_SETTINGS = re.compile(r"(?:^|/)\.(?:vscode|zed)/settings\.json$", re.I)
OPENCODE_FILE = re.compile(r"(?:^|/)opencode\.jsonc?$", re.I)
CODEX_FILE = re.compile(r"(?:^|/)\.codex/config\.toml$", re.I)
# Folders that hold agent config or CI; a symlinked or unreadable one hides files the rules need.
CONFIG_DIRS = frozenset({".claude", ".github", ".gemini", ".qwen", ".codex", ".cursor", ".vscode", ".roo", ".zed",
                         ".gitlab", ".circleci", ".buildkite", ".tekton", ".woodpecker"})


def config_dir(rel: str) -> bool:
    """A folder (repo-relative) that is, or is inside, a folder that holds agent config or CI."""
    return any(part.lower() in CONFIG_DIRS for part in rel.split("/"))
