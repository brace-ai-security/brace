"""AP04, AP05, AP07, AP08: one MCP server at a time (unpinned package, literal secret, plain HTTP, container escape)."""
from __future__ import annotations

import re
from typing import Iterator
from urllib.parse import urlsplit

from ..limits import MAX_VALUE
from ..model import CheckContext, Document, Finding
from ..parse.mcp_json import CONTAINERS, RUNNERS
from ..secrets import opaque, random_token, secret_kind, secret_name, url_path_secret

LOOPBACK = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal"}
# Flags whose next argument is a value, not the package, from the npm/npx, uv/uvx, bunx and
# pnpm/yarn dlx documentation. --header carries a header (often a credential), never a package.
VALUE_FLAGS = {
    # npm and npx
    "--cache", "--cache-dir", "--registry", "--userconfig", "--globalconfig", "--prefix", "--node-options", "--call",
    "-c", "--workspace", "-w", "--loglevel", "--script-shell", "--cafile", "--proxy", "--https-proxy", "--tag",
    "--otp", "--include", "--omit", "--auth-type",
    # uv and uvx
    "--python", "-p", "--with", "--with-editable", "--with-requirements", "--index", "--default-index",
    "--index-url", "-i", "--extra-index-url", "--find-links", "-f", "--constraint", "--constraints", "--override",
    "--overrides", "--build-constraint", "--build-constraints", "--directory", "--project", "--config-file",
    "--env-file", "--python-preference", "--refresh-package", "--reinstall-package", "--upgrade-package", "-P",
    "--keyring-provider", "--index-strategy", "--resolution", "--prerelease", "--exclude-newer", "--link-mode",
    "--color", "--allow-insecure-host", "--config",
    # pnpm, yarn and bun
    "--dir", "-C", "--cwd", "--reporter",
    # deno
    "--import-map", "--lock", "--cert", "--location", "--seed",
    # MCP bridges such as mcp-remote, passed through a runner
    "--header", "-H"}
PACKAGE_FLAGS = {"--package", "--from"}  # their value is the package to check
GIT_SOURCE = re.compile(r"\.git(?:[@#]|$)")
GIT_COMMIT = re.compile(r"[@#][0-9a-f]{40}$")
WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
ROOT_MOUNT = re.compile(r"(?:^|,)(?:source|src)=/(?:,|$)")
EXACT_NPM = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
EXACT_PY = re.compile(r"^\d+(?:\.\d+)*(?:(?:a|b|rc|\.post|\.dev)\d+)*$")
# What pins a download from a URL: a full commit SHA in its path or ref, or an integrity hash.
URL_PINNED = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])|[#?&](?:sha256|sha384|sha512|integrity)=", re.I)
SHORT_FLAG = re.compile(r"^-[A-Za-z]$")
# What a package argument looks like, as shown in a finding: a registry name or spec, or a URL.
PACKAGE_SHAPE = re.compile(r"^(?:@[\w.\-~]{1,214}/)?[\w.\-~]{1,214}"
                           r"(?:(?:[@=<>!~^]{1,2}|\[)[\w.\-+*^~<>=!,\[\] ]{0,200})?$|"
                           r"^(?:https?|git\+[a-z]{1,10}|github|file|npm|jsr):[\w.\-~:/@#?=&%+]{1,2000}$", re.I)


def packages(cmd: str, args) -> list[str]:
    """The packages a runner will fetch: every --package/--from (and npx -p) value, or else the
    first positional argument. Flags and the values of value-taking flags are skipped."""
    explicit, i = [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return explicit or args[i + 1:i + 2]
        if not a.startswith("-"):
            return explicit or [a]
        flag, eq, val = a.partition("=")
        if flag in PACKAGE_FLAGS or (RUNNERS.get(cmd) == "npm" and flag == "-p"):
            if eq:
                explicit.append(val)
            elif i + 1 < len(args):
                explicit.append(args[i + 1])
                i += 1
        elif not eq and i + 1 < len(args) and not args[i + 1].startswith("-") and (
                flag in VALUE_FLAGS or secret_name(flag) or (SHORT_FLAG.match(flag) and random_token(args[i + 1]))):
            i += 1  # skip the flag's value; any other flag is taken to be a switch
        i += 1
    return explicit


def with_packages(args) -> list[str]:
    """The extra packages of `uvx --with a,b pkg` or `uv run --with a cmd`: every --with value
    before the package or command, which they install alongside it."""
    out, i = [], 0
    while i < len(args) and args[i] != "--" and args[i].startswith("-"):
        flag, eq, val = args[i].partition("=")
        if flag == "--with":
            if not eq and i + 1 < len(args):
                val, i = args[i + 1], i + 1
            out += [p.strip() for p in val.split(",") if p.strip()]
        elif not eq and i + 1 < len(args) and not args[i + 1].startswith("-") and flag in VALUE_FLAGS:
            i += 1
        i += 1
    return out


def fetched(cmd: str, args) -> tuple[str, list[str]]:
    """The packages a server fetches at start, and the runner whose versioning they follow:
    a runner's package (see packages()), plus `--with` packages of uvx and `uv run`."""
    if cmd == "uv" and args[:1] == ("run",):
        return "uvx", with_packages(args[1:])
    if cmd not in RUNNERS:
        return cmd, []
    return cmd, list(packages(cmd, args)) + (with_packages(args) if RUNNERS[cmd] == "pypi" else [])


def is_pinned(pkg: str, cmd: str = "npx") -> bool:
    """True for local paths and for exact versions: npm `pkg@1.2.3` (npx, bunx, pnpx), Python
    `pkg==1.2` / `pkg@1.2` (uvx), Deno `npm:pkg@1.2.3` / `jsr:@scope/pkg@1.2.3`. A git source is
    pinned only by a commit, a URL only by a commit SHA or an integrity hash. Tags and ranges
    (`@1`, `@next`) are not pinned."""
    if not pkg:
        return True
    if pkg.startswith(("git+", "github:")) or GIT_SOURCE.search(pkg):
        return bool(GIT_COMMIT.search(pkg))  # a git source is pinned only by commit
    if pkg.lower().startswith(("http:", "https:")):
        return bool(URL_PINNED.search(pkg))  # a URL serves whatever it holds today
    if pkg.startswith((".", "/", "~", "file:")) or WINDOWS_PATH.match(pkg):
        return True  # a local path: not a download
    if RUNNERS.get(cmd) == "deno":
        if not pkg.startswith(("npm:", "jsr:")):
            return True  # a local script
        pkg = pkg[4:]
    elif RUNNERS.get(cmd) == "pypi":
        if "==" in pkg:
            return bool(EXACT_PY.match(pkg.split("==", 1)[1].split("[")[0].split(";")[0].strip()))
        if "@" in pkg:
            return bool(EXACT_PY.match(pkg.rsplit("@", 1)[1]))
        return False
    body = pkg[1:] if pkg.startswith("@") else pkg
    return "@" in body and bool(EXACT_NPM.match(body.rsplit("@", 1)[1]))


def shown_package(pkg: str) -> str:
    """The package as a finding shows it: only a value shaped like a package or URL, never one
    that may be a credential passed where a package was expected."""
    return pkg if PACKAGE_SHAPE.match(pkg) and not opaque(pkg) and not random_token(pkg) else "<redacted>"


def docker_escape(args) -> str:
    """The first container-escape option in docker/podman arguments, or ''."""
    for i, a in enumerate(args):
        a = a[:MAX_VALUE]
        nxt = args[i + 1][:MAX_VALUE] if i + 1 < len(args) else ""
        flag, eq, val = a.partition("=")
        val = val if eq else nxt
        if (flag == "--privileged" and (not eq or val.lower() in ("true", "1"))) or "/var/run/docker.sock" in a:
            return a
        if flag in ("--network", "--net", "--pid", "--ipc", "--uts", "--userns") and val.lower() == "host":
            return f"{flag} host"
        if flag in ("-v", "--volume") and (val.startswith("/:") or val == "/"):
            return f"{flag} {val}"
        if flag == "--mount" and ROOT_MOUNT.search(val):
            return "--mount source=/"
        if flag == "--cap-add" and val.upper() in ("ALL", "SYS_ADMIN", "CAP_SYS_ADMIN"):
            return f"--cap-add {val}"
    return ""


def plain_http_host(url: str) -> str:
    """The host of a plain-HTTP URL that leaves this machine, or ''."""
    try:
        u = urlsplit(url.strip())
        host = (u.hostname or "").lower()
    except ValueError:
        return ""
    if u.scheme.lower() == "http" and host and host not in LOOPBACK \
            and not host.endswith((".localhost", ".local")) and not host.startswith("127."):
        return host
    return ""


class McpServers:
    name = "mcp-servers"
    emits = ("AP04", "AP05", "AP07", "AP08")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        where = doc.source.display
        for s in doc.servers:
            line = doc.line_of(s.path)
            runner, pkgs = fetched(s.command, s.args)
            pkg = next((p for p in pkgs if p and not is_pinned(p, runner)), "")
            if pkg:
                yield Finding("AP04", where, line, f"{s.name}: {s.command} {shown_package(pkg)}")
            if s.command in CONTAINERS:
                hit = docker_escape(s.args)
                if hit:
                    yield Finding("AP08", where, line, f"{s.name}: {hit}")
            for section, vals in (("env", s.env), ("headers", s.headers)):
                for k, v in vals.items():
                    if ctx.secrets.secret_pair(k, v):
                        yield Finding("AP05", where, doc.line_of(s.path + (section, k)),
                                      f"{s.name}: {section}.{k} = <redacted>{secret_kind(v)}")
            # A remote URL in `url`, or passed to a bridge such as mcp-remote run by a runner.
            urls = (s.url, *(s.args if s.command in RUNNERS else ()))
            if ctx.secrets.secret_in_command((*s.args, s.url)) or \
                    any(url_path_secret(u) for u in urls if u.lower().startswith(("http:", "https:"))):
                note = secret_kind(" ".join((*s.args, s.url)))
                yield Finding("AP05", where, line, f"{s.name}: secret in arguments or URL (<redacted>){note}")
            host = next((h for h in (plain_http_host(u) for u in urls if u.lower().startswith("http:")) if h), "")
            if host:
                yield Finding("AP07", where, line, f"{s.name}: http://{host}")
