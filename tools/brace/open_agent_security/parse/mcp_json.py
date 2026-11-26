"""MCP server entries in JSON agent config.

Shapes read: `mcpServers` (Claude, Cursor, Windsurf, Gemini CLI, Qwen Code, Cline, Roo and
others), `mcp_servers`, `projects.<path>.mcpServers` (~/.claude.json), `servers` (VS Code
mcp.json), `mcp.servers` (VS Code settings.json), `mcp` (opencode, whose `command` is a list
and env is `environment`) and `context_servers` (Zed, whose `command` may be {path, args, env}).

Each entry becomes a Server whose command is normalised to the runner it wraps (env, exec,
sh -c, cmd /c, wsl, secret injectors such as `op run --`, `npx ...` written in `command`,
`uv tool run`, `npm exec`), so checks need not know every way a server can be launched.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

from ..agents import OPENCODE_FILE
from ..limits import MAX_VALUE, WRAPPER_DEPTH
from ..model import Document, Server, SourceFile

MCP_FILE = re.compile(r"(?:^|/)(?:\.?mcp|mcp[_\-]config|claude_desktop_config)\.jsonc?$|mcp", re.I)
URL_KEYS = ("url", "serverUrl", "httpUrl")
WRAPPERS = {"npx", "uvx", "bunx", "pnpx", "pnpm", "yarn", "npm", "uv", "pipx", "bun", "docker", "podman", "cmd",
            "bash", "sh", "zsh", "node", "python", "python3", "deno", "env", "exec", "wsl", "op", "dotenvx",
            "doppler", "infisical", "aws-vault", "direnv"}
RUNNERS = {"npx": "npm", "bunx": "npm", "pnpx": "npm", "uvx": "pypi"}  # fetch and run a package, from this ecosystem
# Longer spellings of a runner: (program, leading arguments) -> the runner they amount to.
ALIASES = {("uv", ("tool", "run")): "uvx", ("npm", ("exec",)): "npx", ("npm", ("x",)): "npx", ("pipx", ("run",)): "uvx",
           ("pnpm", ("dlx",)): "pnpx", ("yarn", ("dlx",)): "pnpx", ("bun", ("x",)): "bunx"}
CONTAINERS = {"docker", "podman", "nerdctl"}
SHELLS = {"bash", "sh", "zsh"}
SHELL_OPERATOR = re.compile(r"&&|\|\||[;|\n]")
ENV_VALUE_FLAGS = {"-u", "--unset", "-C", "--chdir"}
WSL_VALUE_FLAGS = {"-d", "--distribution", "-u", "--user", "--cd"}
# `<tool> run|exec ... -- cmd` runs cmd, usually with secrets or settings injected (op, dotenvx,
# doppler, infisical, aws-vault exec <profile> --, uv run --), except for these, whose `run`
# starts a script or container and pass what follows `--` to it as arguments.
RUN_PASSES_ARGS = {"npm", "pnpm", "yarn", "bun", "cargo", "go", "deno", "make", "just", "poetry", "pdm", "hatch"}
COMMON_KEYS = ("mcpServers", "mcp_servers", "projects.*.mcpServers", "mcp.servers", "context_servers")
ALL_SERVER_KEYS = COMMON_KEYS + ("servers", "mcp")
NOT_JSON = (".toml", ".yaml", ".yml")


def is_json(src: SourceFile) -> bool:
    """JSON parsers read host files, *.json and *.jsonc, and files the config names as agent config."""
    suffix = Path(src.display.lower()).suffix
    return suffix in (".json", ".jsonc") or ((src.origin == "host" or src.is_agent_config) and suffix not in NOT_JSON)


def repo_server_keys(rel: str) -> list[str]:
    return list(COMMON_KEYS) + (["servers"] if MCP_FILE.search(rel) else []) + \
        (["mcp"] if OPENCODE_FILE.search(rel) else [])


def launches(entry) -> bool:
    """An entry that starts or reaches a server, as opposed to a nested settings block."""
    return isinstance(entry, dict) and any(k in entry for k in ("command", "args", *URL_KEYS))


def servers_at(data, keys, project: Path | None = None) -> list[tuple[tuple, str, dict]]:
    """(json path, name, entry) under the given top-level keys. `projects.*.mcpServers` reads
    every project, or only `project` when one is given (the host scan)."""
    found: list[tuple[tuple, str, dict]] = []
    if not isinstance(data, dict):
        return found
    for key in keys:
        if key == "projects.*.mcpServers":
            projects = data.get("projects")
            if not isinstance(projects, dict):
                continue
            names = list(projects)
            if project is not None:
                p = Path(project).expanduser()
                want = {str(p.resolve() if p.exists() else p.absolute()), str(p.absolute())}
                names = [n for n in names if n in want][:1]
            for pn in names:
                block = projects.get(pn)
                if isinstance(block, dict) and isinstance(block.get("mcpServers"), dict):
                    found += [(("projects", pn, "mcpServers", str(n)), str(n), e)
                              for n, e in block["mcpServers"].items() if isinstance(e, dict)]
            continue
        path = tuple(key.split("."))
        val = data
        for part in path:
            val = val.get(part) if isinstance(val, dict) else None
        if isinstance(val, dict):
            found += [(path + (str(n),), str(n), e) for n, e in val.items()
                      if isinstance(e, dict) and (key != "mcp" or launches(e))]
    return found


def _prog(s: str) -> str:
    cmd = Path(s.replace("\\", "/")).name.lower()
    for suffix in (".cmd", ".exe", ".bat", ".ps1"):
        if cmd.endswith(suffix):
            return cmd[: -len(suffix)]
    return cmd


def split_words(s: str) -> list[str]:
    """A command line split like a shell (quotes group words; backslashes stay, for Windows
    paths), or on whitespace when the quoting is broken."""
    lex = shlex.shlex(s, posix=True)
    lex.whitespace_split, lex.escape, lex.commenters = True, "", ""
    try:
        return list(lex)
    except ValueError:
        return s.split()


def words(raw) -> list[str]:
    return [str(a) for a in raw if isinstance(a, (str, int, float))] if isinstance(raw, list) else []


def common_shape(entry: dict) -> dict:
    """Zed's `command: {path, args, env}`, opencode's `command: [program, ...]` and its
    `environment`, as the usual `command`, `args` and `env`."""
    cmd = entry.get("command")
    if isinstance(cmd, dict):
        entry = {**entry, "command": cmd.get("path"), "args": cmd.get("args"), "env": cmd.get("env", entry.get("env"))}
    elif isinstance(cmd, list):
        line = words(cmd) + words(entry.get("args"))
        entry = {**entry, "command": line[0] if line else "", "args": line[1:]}
    if "env" not in entry and isinstance(entry.get("environment"), dict):
        entry = {**entry, "env": entry["environment"]}
    return entry


def command_and_args(entry: dict) -> tuple[str, list[str]]:
    """The program and its arguments, normalised to the runner the entry launches."""
    raw_cmd = entry.get("command")
    raw_cmd = raw_cmd if isinstance(raw_cmd, str) else ""
    args = words(entry.get("args"))
    if not args and " " in raw_cmd.strip() and _prog(raw_cmd.split()[0]) in WRAPPERS:
        return resolve(split_words(raw_cmd))
    return resolve([raw_cmd, *args])


def resolve(words: list[str], depth: int = 0) -> tuple[str, list[str]]:
    """The program a command line runs, looking through `env [VAR=value...]`, `exec`, shell
    `-c` strings, `cmd /c` and runner aliases such as `uv tool run` and `npm exec`."""
    if not words:
        return "", []
    cmd, args = _prog(words[0]), list(words[1:])
    if depth >= WRAPPER_DEPTH:
        return cmd, args
    if cmd == "env":
        i = 0
        while i < len(args) and (args[i].startswith("-") or "=" in args[i]):
            i += 2 if args[i] in ENV_VALUE_FLAGS else 1
        return resolve(args[i:], depth + 1) if i < len(args) else (cmd, args)
    if cmd == "exec" and args:
        return resolve(args, depth + 1)
    if cmd == "wsl":
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if args[i] in WSL_VALUE_FLAGS else 1
            if args[i - 1] in ("-e", "--exec", "--"):
                break
        return resolve(args[i:], depth + 1) if i < len(args) else (cmd, args)
    if args[:1] in (["run"], ["exec"]) and "--" in args and cmd not in RUN_PASSES_ARGS | CONTAINERS:
        rest = args[args.index("--") + 1:]
        return resolve(rest, depth + 1) if rest else (cmd, args)
    if cmd == "direnv" and args[:1] == ["exec"] and len(args) > 2:
        return resolve(args[2:], depth + 1)
    if cmd in SHELLS and len(args) >= 2 and args[0] in ("-c", "-lc", "-ic"):
        return shell_string(args[1], depth + 1)
    if cmd in ("cmd", "powershell", "pwsh") and args and args[0].lower() in ("/c", "/k", "-c", "-command"):
        rest = args[1:]
        if len(rest) == 1 and " " in rest[0]:
            return shell_string(rest[0], depth + 1)
        return resolve(rest, depth + 1) if rest else (cmd, args)
    for (program, lead), runner in ALIASES.items():
        if cmd == program and tuple(args[:len(lead)]) == lead:
            return runner, args[len(lead):]
    return cmd, args


def shell_string(line: str, depth: int) -> tuple[str, list[str]]:
    """The command of a shell string worth checking: the first that fetches a package or
    starts a container (`cd /x && npx -y pkg`), else the last one."""
    found = [resolve(split_words(part), depth) for part in SHELL_OPERATOR.split(line[:MAX_VALUE]) if part.strip()]
    return next((c for c in found if c[0] in RUNNERS or c[0] in CONTAINERS), found[-1] if found else ("", []))


def entry_url(entry: dict) -> str:
    for k in URL_KEYS:
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:MAX_VALUE]
    return ""


def scalars(vals) -> dict:
    """The string and number values of an env or headers block, keys and values cut to MAX_VALUE;
    other shapes hold no literal secret."""
    if not isinstance(vals, dict):
        return {}
    return {str(k)[:MAX_VALUE]: v[:MAX_VALUE] if isinstance(v, str) else v for k, v in vals.items()
            if isinstance(v, (str, int, float))}


def to_server(path: tuple, name: str, raw: dict) -> Server:
    """One server. Its name, arguments and keys reach finding details, so each is cut to
    MAX_VALUE characters here: a finding then holds kilobytes, not a megabyte-long name, and
    the engine still sees any secret in what is kept whole when it redacts before cutting."""
    entry = common_shape(raw)
    cmd, args = command_and_args(entry)
    return Server(path, str(name)[:MAX_VALUE], cmd[:MAX_VALUE], tuple(a[:MAX_VALUE] for a in args),
                  scalars(entry.get("env")), scalars(entry.get("headers")), entry_url(entry), raw)


class McpJson:
    name = "mcp-json"

    def claims(self, src: SourceFile) -> bool:
        return is_json(src)

    def parse(self, src: SourceFile, doc: Document) -> None:
        keys = src.server_keys if src.server_keys is not None else repo_server_keys(src.display)
        doc.servers += [to_server(*s) for s in servers_at(doc.json(), keys, src.project)]
