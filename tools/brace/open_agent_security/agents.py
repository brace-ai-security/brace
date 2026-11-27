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
# and -base-action; opencode's action is published under both the sst and anomalyco orgs).
ACTIONS = ("anthropics/claude-code", "openai/codex-action", "google-github-actions/run-gemini-cli",
           "google-gemini/gemini-cli-action", "sst/opencode/github", "anomalyco/opencode/github")
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
# A gated CLI as a word (`gemini`), as its package's bare name (`gemini-cli`, `qwen-code`, also
# inside a URL or image such as `github.com/google-gemini/gemini-cli` or `gemini-cli/sandbox:0.1`)
# or as an npm package.
GATED_CLI = re.compile(rf"(?<![\w-])(?:{alternation(GATED_FLAG_CLIS)})(?![\w-])|(?<![\w-])(?:gemini-cli|qwen-code)(?![\w-])|"
                       r"@google/gemini-cli|@qwen-code/|@github/copilot|@charmland/crush", re.I)
# A variable or key named after a gated CLI (`GEMINI_FLAGS`, `QWEN_ARGS`, `codex_opts`): a gated
# flag assigned to it is meant for that CLI (`GEMINI_FLAGS="--yolo"`, then `gemini $GEMINI_FLAGS`).
GATED_NAME = re.compile(rf"(?:{alternation(GATED_FLAG_CLIS)})", re.I)
GATED_ASSIGN = re.compile(r"^[ \t]*(?:export[ \t]+|-[ \t]+)?[\"']?([A-Za-z_][\w.-]{0,80})[\"']?[ \t]*(?::=|\?=|\+=|::=|=|:)", re.M)

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
    # The SDKs' permission_mode / permissionMode, and the VS Code extension's initialPermissionMode
    r"\b(?:initial_?)?permission_?mode[\"']?[ \t]*[:=][ \t]*[\"']?bypassPermissions" + END + r"[\"']?|"
    r"--dangerously-allow-all" + END + "|"  # Amp: every tool call runs without asking
    # Codex's sandbox setting by any spelling: config.toml's sandbox_mode, the TypeScript SDK's
    # sandboxMode, and openai/codex-action's `sandbox:` input.
    # The value may be quoted once, three times (a TOML multi-line string) or with escaped quotes
    # (`codex exec -c sandbox_mode=\\"danger-full-access\\"`).
    r"\bsandbox(?:_?mode)?[\"']?[ \t]*[:=][ \t]*\\?[\"']{0,3}danger-full-access" + END + r"[\"']?", re.I)
# Bypasses only next to an agent CLI that takes them: Gemini/Qwen/Codex/Crush --yolo, and
# Copilot CLI's --allow-all-tools ("allow every tool without asking") and --allow-all.
GATED_BYPASS = re.compile(r"--(?:yolo|allow-all-tools|allow-all-paths|allow-all)" + END)
# A bypass written as a value on its own, whatever its key or variable is called
# (`CLAUDE_PERMISSION_MODE=bypassPermissions`, `setPermissionMode("bypassPermissions")`,
# `MODE = "bypassPermissions"`), and Gemini CLI's and Qwen Code's approval mode setting set to
# yolo. Reported only on lines no other bypass match reported.
BYPASS_VALUE = re.compile(r"(?<![\w-])(?:bypassPermissions|danger-full-access)" + END + "|"
                          r"\bapproval_?mode[\"']?[ \t]*[:=][ \t]*[\"']?yolo" + END, re.I)
# Bypass flags of other agent CLIs, each only next to its own CLI: Aider's --yes-always and
# Cursor's agent CLI's --force / -f (which runs every command unless denied; with -p).
AIDER_BYPASS = re.compile(r"--yes-always" + END)
AIDER_CLI = re.compile(r"(?<![\w-])aider(?:-chat)?(?![\w-])", re.I)
QUOTED_AIDER_CLI = re.compile(r"[\"'](?:[\w.~-]{0,100}/)?aider(?:\.exe|\.cmd)?[\"']", re.I)
CURSOR_BYPASS = re.compile(r"(?<![\w-])(?:--force|-f)" + END)
CURSOR_CLI = re.compile(r"(?<![\w-])cursor-agent(?![\w-])", re.I)
QUOTED_CURSOR_CLI = re.compile(r"[\"'](?:[\w.~-]{0,100}/)?cursor-agent(?:\.exe|\.cmd)?[\"']", re.I)
PRINT_FLAG = re.compile(r"(?<![\w-])(?:-p|--print)(?![\w-])")  # cursor-agent's headless mode
# Gemini CLI's, Qwen Code's and Crush's short -y (--yolo), only as an argument of one of them:
# after the CLI in the same command, so `npx -y @google/gemini-cli -p hi` (npx's own -y) does not count.
SHORT_YOLO = re.compile(r"(?<![\w-])-y(?![\w-])")
SHORT_YOLO_CLIS = ("gemini", "qwen", "crush")
SHORT_YOLO_CLI = re.compile(r"(?<![\w-])(?:gemini|qwen|crush)(?![\w-])|@google/gemini-cli|@qwen-code/qwen-code|"
                            r"@charmland/crush", re.I)
# The same CLIs as a quoted list item (`["gemini", "--yolo"]`, `"@google/gemini-cli"`), with an
# optional path and a version on a package.
QUOTED_GATED_CLI = re.compile(rf"[\"'](?:[\w.~-]{{0,100}}/)?(?:{alternation(GATED_FLAG_CLIS)})(?:\.exe|\.cmd)?[\"']|"
                              r"[\"'](?:@google/gemini-cli|@qwen-code/[\w-]{1,40}|@github/copilot|@charmland/crush)"
                              r"(?:@[\w.-]{1,40})?[\"']", re.I)
QUOTED_SHORT_YOLO_CLI = re.compile(r"[\"'](?:[\w.~-]{0,100}/)?(?:gemini|qwen|crush)(?:\.exe|\.cmd)?[\"']|"
                                   r"[\"'](?:@google/gemini-cli|@qwen-code/qwen-code|@charmland/crush)"
                                   r"(?:@[\w.-]{1,40})?[\"']", re.I)
# Words that may stand before a program in command position: wrappers, runners that fetch it
# and their subcommands, shell keywords, a line's lead-in (`RUN`, a YAML item's `-`) and openers.
# Flags, numbers (timeout's duration), `VAR=value` and YAML keys (`run:`) may stand there too.
COMMAND_PREFIX = frozenset("sudo doas env nice nohup time command exec timeout xargs npx bunx pnpx pnpm yarn npm bun uv "
                           "uvx dlx x run gh if ! then do else elif while until RUN - ( { $( ` & @".split())
INSTALL_WORDS = frozenset(("install", "add"))  # `npm install -g @google/gemini-cli`: an argument, not a command
PATH_HEAD = re.compile(r"^(?:[\w.~-]*/)+$")      # `/usr/local/bin/` before the program name
VAR_ASSIGN = re.compile(r"^[A-Za-z_]\w{0,60}=")
OPENS_ITEM = "\"'`[(,"  # the program is the first item of a string or list: `"gemini --yolo"`, `["gemini", ...]`


def command_position(before: str) -> bool:
    """Whether a program written after `before` (the text of its simple command up to it) is the
    command run, not an argument: only prefix words (COMMAND_PREFIX, flags, numbers, VAR=value,
    YAML keys) stand before it, or it opens a string or list, and no install command names it."""
    words = before.split()
    if any(w.strip("\"'[](),") in INSTALL_WORDS for w in words):
        return False
    tail = words[-1] if words and not before[-1:].isspace() else ""
    if tail:
        if tail[-1] in OPENS_ITEM:
            return True
        if not (PATH_HEAD.match(tail) or tail in COMMAND_PREFIX or (tail.endswith("$(") and
                                                                    command_position(tail[:-2] + " "))):
            return False
        words = words[:-1]
    return all(w in COMMAND_PREFIX or w.startswith("-") or w[:1].isdigit() or w.endswith(":") or VAR_ASSIGN.match(w)
               for w in words)


# Byte strings that mark a bypass: in files too large to read as text (which makes the scan
# incomplete), and in files of kinds the walk does not read (which are then read as text).
BYPASS_BYTES = (b"--dangerously-skip-permissions", b"--dangerously-bypass-approvals-and-sandbox",
                b"bypassPermissions", b"danger-full-access", b"sandbox_mode", b"--allow-all-tools", b"--yolo",
                b"--approval-mode", b"--dangerously-allow-all", b"--allow-all-paths", b"--yes-always")

# Files that configure an agent or its MCP servers, as paths ending a repository path.
CONFIG_FILES = (".mcp.json", "mcp.json", "mcp.jsonc", "mcp_config.json", "mcp-config.json",
                "claude_desktop_config.json", ".claude/settings.json", ".claude/settings.local.json",
                ".gemini/settings.json", ".qwen/settings.json", "opencode.json", "opencode.jsonc",
                "cline_mcp_settings.json", ".codex/config.toml", ".vscode/settings.json", ".cursor/mcp.json",
                ".roo/mcp.json", ".zed/settings.json", "crush.json", ".crush.json", ".amp/settings.json", ".cursor/cli.json")
CONFIG_FILE = re.compile(rf"(?:^|/)(?:{alternation(CONFIG_FILES)})$", re.I)
# General editor settings: agent config only when they hold MCP servers.
SHARED_SETTINGS = re.compile(r"(?:^|/)\.(?:vscode|zed)/settings\.json$", re.I)
# Files whose servers sit under a top-level `mcp` key: opencode and Crush.
MCP_KEY_FILE = re.compile(r"(?:^|/)(?:opencode\.jsonc?|\.?crush\.json)$", re.I)
CODEX_FILE = re.compile(r"(?:^|/)\.codex/config\.toml$", re.I)
# Folders that hold agent config or CI; a symlinked or unreadable one hides files the rules need.
CONFIG_DIRS = frozenset({".claude", ".github", ".gemini", ".qwen", ".codex", ".cursor", ".vscode", ".roo", ".zed",
                         ".amp", ".gitlab", ".circleci", ".buildkite", ".tekton", ".woodpecker"})


def config_dir(rel: str) -> bool:
    """A folder (repo-relative) that is, or is inside, a folder that holds agent config or CI."""
    return any(part.lower() in CONFIG_DIRS for part in rel.split("/"))


# Documentation: prose that names flags to explain them, never read for bypass flags (and never
# read because a byte search found one). Markdown, reStructuredText, AsciiDoc, Org, plain text
# and TeX, extensionless documents such as README or CHANGELOG, and the search indexes docs
# sites generate.
PROSE_EXT = frozenset((".md", ".mdc", ".mdx", ".qmd", ".rmd", ".markdown", ".mkd", ".rst", ".adoc", ".asciidoc", ".org", ".txt", ".tex"))
PROSE_NAME = re.compile(r"^(?:readme|changelog|changes|contributing|security|history|news|authors|contributors|"
                        r"license|licence|copying|notice|code_of_conduct|maintainers|todo|\.cursorrules|\.windsurfrules|"
                        r"\.clinerules|\.roorules)(?:[.-][\w.-]*)?$", re.I)
SEARCH_INDEX = re.compile(r"(?:^|/)(?:[\w.-]*search[_-]?index[\w.-]*\.(?:json|js)|[\w.-]+\.search\.json|"
                          r"(?:lunr|pagefind)[\w.-]*/[^\n]*)$", re.I)


def prose(display: str) -> bool:
    """A documentation file (see PROSE_EXT) or a docs site's search index, by its path."""
    name = display.rsplit("/", 1)[-1]
    low = name.lower()
    ext = low[low.rfind("."):] if "." in low.lstrip(".") else ""
    return ext in PROSE_EXT or (PROSE_NAME.match(name) is not None and ext in ("", *PROSE_EXT)) \
        or SEARCH_INDEX.search(display) is not None


# Markdown files whose YAML frontmatter configures an agent: Claude Code subagents, commands and
# skills, Gemini CLI commands, Codex prompts and shared agent folders.
AGENT_MARKDOWN = re.compile(r"(?:^|/)(?:\.claude/(?:agents|commands|skills)|\.gemini/commands|\.qwen/commands|\.codex|"
                            r"\.agents|\.cursor/(?:commands|rules))/(?:[^/\n]+/)*[^/\n]+\.md$", re.I)
