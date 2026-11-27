"""The scanned folder: walk it, pick the files worth reading, read them safely.

Version-control, cache and dependency folders are never entered and are counted in a note
(a real `.git` folder, one holding HEAD, silently). Ignored folders are pruned, symlinks are
never followed, and files over the size limit are reported, not read. Skipping a file or
folder the rules need (agent config, CI, a Dockerfile or a script) makes the scan incomplete.
A symlink to a path inside the folder that the walk reads anyway (`CLAUDE.md -> AGENTS.md`,
`.claude/skills -> ../.agents/skills`) hides nothing, so it is only counted in a note.
"""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Iterator

from ..agents import BYPASS_BYTES, CONFIG_DIRS, CONFIG_FILE, config_dir, prose
from ..fsio import ReadFailure, contains, read, starts_with
from ..ignore import GlobSet
from ..limits import LISTED_FILES, LISTED_PATH_CHARS
from ..model import Skipped, SourceFile
from ..parse.dockerfile import is_dockerfile
from ..parse.mcp_json import ALL_SERVER_KEYS
from ..report.json_out import KEYS as JSON_REPORT_KEYS

VENV = "Python virtual environments"
DEPENDENCY_DIRS = {"node_modules", "site-packages", VENV}       # never entered; counted in one note
SKIPPED_DIRS = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
                "site-packages"}  # never entered; counted
VENV_NAMES = {".venv", "venv"}                                 # skipped and counted when they hold pyvenv.cfg
TEXT_EXT = {".json", ".jsonc", ".yaml", ".yml", ".toml", ".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs",
            ".cjs", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd", ".md", ".env", ".ini", ".cfg", ".go",
            ".rs", ".rb", ".java", ".kt", ".scala", ".groovy", ".mk", ".dockerfile", ".containerfile",
            # service and process definitions, editor workspaces, infrastructure, notebooks, other
            # languages and templates (comment markers for each are in checks/permissions.py)
            ".service", ".conf", ".code-workspace", ".tf", ".hcl", ".ipynb", ".php", ".cs", ".swift", ".lua", ".pl",
            ".c", ".h", ".cpp", ".ex", ".exs", ".dart", ".vue", ".svelte", ".html", ".nix", ".j2", ".jinja", ".tpl",
            ".properties", ".json5", ".txt"}
SHELL_STARTUP = {".zshrc", ".bashrc", ".bash_aliases", ".bash_profile", ".zprofile", ".profile", ".envrc", ".zshenv"}
TEXT_NAMES = {"makefile", "gnumakefile", "justfile", ".justfile", "jenkinsfile", ".mcp.json", "procfile",
              *SHELL_STARTUP}  # lowercased
CI_PATH = re.compile(r"(?:^|/)(?:\.github/workflows/|\.gitlab-ci\.ya?ml$|\.gitlab/|\.circleci/|\.buildkite/|Jenkinsfile$|"
                     r"azure-pipelines\.ya?ml$|bitbucket-pipelines\.ya?ml$|\.drone\.ya?ml$|\.woodpecker|\.tekton/)", re.I)
SCRIPT_EXT = {".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd", ""}
SCANNER = "open-agent-security"
REPORT_EXT = {".json", ".sarif", ".xml"}  # formats it writes that the walk can read (.xml only with a bypass marker)
JUNIT_HEAD = f'<testsuites name="{SCANNER}"'
JUNIT_HEAD_CHARS = 300


def own_report(rel: str, text: str) -> bool:
    """A JSON, SARIF, GitLab SAST or JUnit report this scanner wrote, such as report.json left in
    the scanned folder: scanning it would report the findings it lists, more each run. Only a
    .json or .sarif file the rules do not need, holding exactly one of those documents (parsed
    whole, strict JSON), or an .xml file (a kind the walk reads only for a bypass marker) that
    opens as its JUnit report, counts, so no script, workflow, Dockerfile or agent config can
    pass for one."""
    if Path(rel.lower()).suffix not in REPORT_EXT or required(rel, False) or SCANNER not in text:
        return False
    if rel.lower().endswith(".xml"):  # read only when it holds a bypass marker (see marked)
        return text.lstrip().startswith("<?xml") and JUNIT_HEAD in text[:JUNIT_HEAD_CHARS]
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return False
    if not isinstance(data, dict):
        return False
    keys = set(data)
    if data.get("scanner") == SCANNER:
        return isinstance(data.get("findings"), list) and "version" in data and keys <= JSON_REPORT_KEYS
    runs = data.get("runs")
    if isinstance(runs, list) and runs:
        return "version" in data and keys <= {"version", "$schema", "runs"} and all(
            isinstance(r, dict) and isinstance(r.get("tool"), dict) and isinstance(r["tool"].get("driver"), dict)
            and r["tool"]["driver"].get("name") == SCANNER for r in runs)
    scan = data.get("scan")
    return isinstance(scan, dict) and isinstance(scan.get("scanner"), dict) and scan["scanner"].get("id") == SCANNER \
        and "version" in data and isinstance(data.get("vulnerabilities"), list) \
        and keys <= {"version", "scan", "vulnerabilities", "schema", "remediations"}


def wanted(name: str) -> bool:
    low = name.lower()
    return (Path(low).suffix in TEXT_EXT or low in TEXT_NAMES or is_dockerfile(low)
            or low == ".env" or low.startswith(".env."))


def required(rel: str, agent: bool) -> bool:
    """Files the rules must read, so skipping one makes the scan incomplete: agent config,
    CI files, Dockerfiles and scripts (extensionless files are read only when they are scripts)."""
    return agent or bool(CI_PATH.search(rel)) or is_dockerfile(rel.lower()) \
        or Path(rel.lower()).suffix in SCRIPT_EXT


def skipped_dir(path: Path, name: str) -> str | None:
    """The name a built-in skip is counted under, '' for a real git folder (skipped silently),
    or None to enter the folder."""
    if name == ".git" and (path / name / "HEAD").is_file():
        return ""
    if name in SKIPPED_DIRS:
        return name
    if name in VENV_NAMES and (path / name / "pyvenv.cfg").is_file():
        return VENV
    return None


def gives_roles(rel: str) -> bool:
    """A folder whose path makes the files under it agent config or CI (`.claude`, `.cursor`,
    `.github`, `.github/workflows`): read through another path, they would lose that role."""
    return rel.rsplit("/", 1)[-1].lower() in CONFIG_DIRS or rel.lower().endswith(".github/workflows")


def marked(p: Path, limit: int) -> bool:
    """A regular file of a kind the walk does not read, within the size limit, that holds a
    bypass marker (BYPASS_BYTES): it is read as text, so no file kind hides a bypass. A byte
    search, cheap next to reading every file as text. Documentation (agents.prose) is never
    searched: it is not read for bypass flags."""
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and 0 < st.st_size <= limit and contains(p, BYPASS_BYTES, limit)


def is_script(p: Path) -> bool:
    """An extensionless file that starts with #! (a shell or Python script)."""
    return starts_with(p, b"#!")


class RepoCollector:
    """The scanned folder, walked in sorted order: entering folders (enter), choosing files
    (wanted, the config's include and agent-config globs) and reading them (read_file)."""
    name = "repo"

    def collect(self, ctx) -> Iterator[SourceFile | Skipped]:
        config = ctx.config
        root, limits = config.root, config.limits
        include, agent_config = GlobSet(config.include), GlobSet(config.agent_config)
        folder_errors: list[Skipped] = []

        def unreadable(err: OSError) -> None:
            name = Path(err.filename).relative_to(root).as_posix() if err.filename else "."
            must = name == "." or config_dir(name)  # the root, or a folder that holds agent config or CI
            folder_errors.append(Skipped(name + "/ (folder)", "unreadable", must))

        count = 0
        for dirpath, dirnames, filenames in os.walk(root, onerror=unreadable):
            yield from folder_errors
            folder_errors.clear()
            here = Path(dirpath)
            reldir = here.relative_to(root).as_posix()
            reldir = "" if reldir == "." else reldir + "/"
            yield from self.enter(ctx, here, reldir, dirnames)
            for name in sorted(filenames):
                rel = reldir + name
                configured = agent_config.match(rel)
                agent = configured or bool(CONFIG_FILE.search(rel))
                if not (wanted(name) or agent or include.match(rel)):
                    if ("." in name or not is_script(here / name)) and \
                            (prose(rel) or not marked(here / name, limits.max_file_bytes)):
                        continue
                count += 1
                if count > limits.max_files:
                    ctx.report.truncate(f"stopped after {limits.max_files} files; "
                                        "scan a smaller folder to cover the rest")
                    return
                if ctx.ignores.match(rel):
                    ctx.report.tally.files += 1
                    continue
                if os.path.islink(here / name) and not required(rel, agent) and self.read_anyway(ctx, here / name):
                    self.linked(ctx, rel)
                    continue
                item = self.read_file(here / name, rel, agent, configured, limits.max_file_bytes)
                if isinstance(item, SourceFile) and not agent and own_report(rel, item.text):
                    ctx.report.tally.own_reports += 1
                    continue
                yield item
        yield from folder_errors

    def enter(self, ctx, here: Path, reldir: str, dirnames: list[str]) -> Iterator[Skipped]:
        """Prune dirnames in place to the folders to walk: never version control, caches,
        dependencies, ignored folders or symlinks. A symlinked folder is reported (and makes the
        scan incomplete if it holds agent config or CI), unless the walk reads its target anyway
        and the link's own path gives nothing under it a role (see gives_roles)."""
        tally, kept = ctx.report.tally, []
        for d in sorted(dirnames):
            skip = skipped_dir(here, d)
            if skip:
                counts = tally.dependency_dirs if skip in DEPENDENCY_DIRS else tally.other_dirs
                counts[skip] = counts.get(skip, 0) + 1
            elif skip == "":
                continue
            elif ctx.ignores.prunes(reldir + d):
                tally.folders += 1
            elif not os.path.islink(here / d):
                kept.append(d)
            elif not gives_roles(reldir + d) and self.read_anyway(ctx, here / d):
                self.linked(ctx, reldir + d + "/")
            else:
                yield Skipped(reldir + d + "/ (folder)", "symlink", config_dir(reldir + d))
        dirnames[:] = kept

    @staticmethod
    def read_anyway(ctx, link: Path) -> bool:
        """Whether a symlink points inside the scanned folder at a path the walk reads itself: a
        folder it enters, or a file it reads (by name; not ignored, not in a skipped folder).
        The link is resolved, never opened."""
        root = Path(ctx.config.root).resolve()
        try:
            target = link.resolve()
            rel = target.relative_to(root).as_posix()
        except (OSError, RuntimeError, ValueError):
            return False
        parts = [] if rel == "." else rel.split("/")
        if any(p in SKIPPED_DIRS or p in VENV_NAMES for p in parts) or \
                any(ctx.ignores.prunes("/".join(parts[:k])) for k in range(1, len(parts))):
            return False
        if target.is_dir():
            return not parts or not ctx.ignores.prunes(rel)
        return target.is_file() and wanted(target.name) and not ctx.ignores.match(rel)

    @staticmethod
    def linked(ctx, rel: str) -> None:
        tally = ctx.report.tally
        tally.links_inside += 1
        if len(tally.link_names) < LISTED_FILES:
            tally.link_names.append(rel[:LISTED_PATH_CHARS])

    def read_file(self, path: Path, rel: str, agent: bool, configured: bool, limit: int) -> SourceFile | Skipped:
        """The file as text, or why it was skipped; skipping one the rules need makes the scan incomplete."""
        text = read(path, limit=limit, display=rel)
        if isinstance(text, ReadFailure):
            must = required(rel, agent) or (text.reason == "oversized" and not prose(rel) and contains(path, BYPASS_BYTES))
            return Skipped(text.display, text.reason, must, limit)
        return SourceFile(rel, "repo", text, is_ci=bool(CI_PATH.search(rel)), is_agent_config=agent,
                          server_keys=ALL_SERVER_KEYS if configured else None)
