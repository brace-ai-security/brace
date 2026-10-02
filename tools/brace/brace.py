#!/usr/bin/env python3
"""BRACE record checker.

Reads the `.brace/` record folder in a codebase and decides GO or NO-GO
against the BRACE sign-off checklist.

  brace.py init  [--dir .]
  brace.py items [--json]
  brace.py hash  [--dir .] [--manifest .brace/manifest.yaml]
  brace.py check [--dir .] [--approvals github|git|off] [--strict] [--json out.json]

Exit codes: 0 GO (or command succeeded), 1 NO-GO, 2 invalid input or usage error.
Requires Python 3.10+ and PyYAML. Uses `jsonschema` when installed; otherwise a
built-in validator for the subset of JSON Schema the bundled schemas use.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML
    sys.stderr.write("brace.py needs PyYAML. Install it with: pip install pyyaml\n")
    sys.exit(2)

try:  # optional
    from jsonschema import Draft202012Validator as _JSValidator
except ImportError:  # pragma: no cover - depends on environment
    _JSValidator = None

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE / "schemas"
ITEMS_FILE = HERE / "brace_items.json"
TEMPLATE_DIR = HERE / "templates" / ".brace"

EXIT_GO = 0
EXIT_NOGO = 1
EXIT_INVALID = 2

GATE_ORDER = ["G1", "G2", "G3"]
OUTCOMES = ["pass", "gap", "na", "not_reviewed"]


class InputError(Exception):
    """Invalid input or usage: exit code 2."""

    def __init__(self, messages):
        if isinstance(messages, str):
            messages = [messages]
        self.messages = list(messages)
        super().__init__("\n".join(self.messages))


# --------------------------------------------------------------------------
# Item data
# --------------------------------------------------------------------------

def load_items() -> list[dict]:
    try:
        return json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"Can't read the item list {ITEMS_FILE}: {exc}")


# --------------------------------------------------------------------------
# YAML loading and schema validation
# --------------------------------------------------------------------------

def _normalize(value):
    """Turn YAML dates into ISO strings so schemas can treat them as text."""
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    return value


def load_yaml(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{path}: can't read file ({exc.strerror or exc})")
    try:
        return _normalize(yaml.safe_load(text))
    except yaml.YAMLError as exc:
        raise InputError(f"{path}: not valid YAML ({exc})")


_SCHEMAS: dict[str, dict] = {}


def load_schema(name: str) -> dict:
    if name not in _SCHEMAS:
        path = SCHEMA_DIR / f"{name}.schema.json"
        try:
            _SCHEMAS[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputError(f"Can't read schema {path}: {exc}")
    return _SCHEMAS[name]


def _fmt_path(parts) -> str:
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += ("." if out else "") + str(p)
    return out or "(top level)"


def _type_name(v) -> str:
    if v is None:
        return "nothing"
    if isinstance(v, bool):
        return "true/false"
    if isinstance(v, int):
        return "a number"
    if isinstance(v, float):
        return "a number"
    if isinstance(v, str):
        return "text"
    if isinstance(v, list):
        return "a list"
    if isinstance(v, dict):
        return "a mapping"
    return type(v).__name__


_TYPE_WORDS = {
    "string": "text",
    "integer": "a whole number",
    "number": "a number",
    "boolean": "true/false",
    "array": "a list",
    "object": "a mapping",
    "null": "empty",
}


def _is_type(v, t: str) -> bool:
    if t == "string":
        return isinstance(v, str)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "array":
        return isinstance(v, list)
    if t == "object":
        return isinstance(v, dict)
    if t == "null":
        return v is None
    return False


def _builtin_validate(schema: dict, inst, path: list, root: dict, errors: list) -> None:
    """Validate the JSON Schema subset used by the bundled schemas.

    Supported: $ref (to #/$defs/...), type, enum, const, pattern, minLength,
    minItems, items, properties, required, patternProperties,
    additionalProperties (boolean or schema), oneOf, anyOf.
    """
    where = _fmt_path(path)
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise InputError(f"schema uses unsupported $ref {ref}")
        _builtin_validate(root["$defs"][ref[len("#/$defs/"):]], inst, path, root, errors)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(inst, t) for t in types):
            want = " or ".join(_TYPE_WORDS.get(t, t) for t in types)
            errors.append(f"{where}: should be {want}, but is {_type_name(inst)}")
            return
    if "enum" in schema and inst not in schema["enum"]:
        allowed = ", ".join(json.dumps(x) for x in schema["enum"])
        errors.append(f"{where}: {json.dumps(inst)} is not allowed; use one of {allowed}")
    if "const" in schema and inst != schema["const"]:
        errors.append(f"{where}: should be {json.dumps(schema['const'])}")
    if isinstance(inst, str):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errors.append(f"{where}: should not be empty")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errors.append(f"{where}: {inst!r} doesn't match the expected format ({schema['pattern']})")
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errors.append(f"{where}: needs at least {schema['minItems']} entr{'y' if schema['minItems'] == 1 else 'ies'}")
        if "items" in schema:
            for i, v in enumerate(inst):
                _builtin_validate(schema["items"], v, path + [i], root, errors)
    if isinstance(inst, dict):
        for key in schema.get("required", []):
            if key not in inst:
                errors.append(f"{where}: '{key}' is required")
        props = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for key, v in inst.items():
            matched = False
            if key in props:
                matched = True
                _builtin_validate(props[key], v, path + [key], root, errors)
            for pat, sub in patterns.items():
                if re.search(pat, key):
                    matched = True
                    _builtin_validate(sub, v, path + [key], root, errors)
            if not matched:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{_fmt_path(path + [key])}: unknown field '{key}'")
                elif isinstance(extra, dict):
                    _builtin_validate(extra, v, path + [key], root, errors)
    for kw in ("oneOf", "anyOf"):
        if kw in schema:
            ok = 0
            for sub in schema[kw]:
                sub_errors: list = []
                _builtin_validate(sub, inst, path, root, sub_errors)
                if not sub_errors:
                    ok += 1
            if kw == "oneOf" and ok != 1:
                errors.append(f"{where}: must match exactly one allowed form (matched {ok})")
            if kw == "anyOf" and ok == 0:
                errors.append(f"{where}: doesn't match any allowed form")


def _oneof_hint(err) -> str:
    # Plain-language hint for the manifest's value/path rule.
    req = [s.get("required") for s in err.schema.get("oneOf", []) if isinstance(s, dict)]
    if req and all(isinstance(r, list) and len(r) == 1 for r in req):
        names = " or ".join(r[0] for r in req)
        return f"needs exactly one of {names}"
    return "must match exactly one allowed form"


def validate(name: str, inst, label: str) -> list[str]:
    schema = load_schema(name)
    errors: list[str] = []
    if _JSValidator is not None:
        validator = _JSValidator(schema)
        for err in sorted(validator.iter_errors(inst), key=lambda e: list(map(str, e.absolute_path))):
            where = _fmt_path(list(err.absolute_path))
            if err.validator == "oneOf":
                msg = _oneof_hint(err)
            elif err.validator == "additionalProperties":
                msg = err.message.replace("Additional properties are not allowed", "unknown field")
            else:
                msg = err.message
            errors.append(f"{where}: {msg}")
    else:
        _builtin_validate(schema, inst, [], schema, errors)
    return [f"{label}: {e}" for e in errors]


# --------------------------------------------------------------------------
# agent-type-id
# --------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _dir_files(root: Path) -> list[str]:
    """Relative POSIX paths of all files under root, skipping dotfiles and dot-dirs."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            full = Path(dirpath) / fn
            if full.is_file():
                out.append(full.relative_to(root).as_posix())
    return sorted(out)


def input_digest(entry: dict, base: Path) -> str:
    if "value" in entry:
        return hashlib.sha256(entry["value"].encode("utf-8")).hexdigest()
    target = base / entry["path"]
    if target.is_file():
        return _sha256_file(target)
    if target.is_dir():
        h = hashlib.sha256()
        for rel in _dir_files(target):
            h.update(f"{rel}\n{_sha256_file(target / rel)}\n".encode("utf-8"))
        return h.hexdigest()
    raise InputError(f"manifest input '{entry.get('name')}': path {entry['path']} does not exist")


def agent_type_id(manifest: dict, base: Path) -> str:
    """Hash procedure:
    1. digest per input: sha256 of the UTF-8 value; sha256 of a file's bytes; for a
       directory, sha256 over "<relpath>\\n<sha256 hex>\\n" for each file in sorted
       relative-POSIX-path order, skipping dotfiles and dot-directories.
    2. JSON-serialize [{"name", "digest"}] sorted by name, separators=(",", ":"),
       sort_keys=True, UTF-8.
    3. agent-type-id = "sha256:" + sha256 hex of that serialization.
    """
    names = [i["name"] for i in manifest["inputs"]]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise InputError(f"manifest: input names must be unique; repeated: {', '.join(dupes)}")
    entries = sorted(
        ({"name": i["name"], "digest": input_digest(i, base)} for i in manifest["inputs"]),
        key=lambda e: e["name"],
    )
    blob = json.dumps(entries, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise InputError(f"manifest {path} does not exist")
    data = load_yaml(path)
    errors = validate("manifest", data, str(path))
    if errors:
        raise InputError(errors)
    return data


# --------------------------------------------------------------------------
# git helpers
# --------------------------------------------------------------------------

def git(cwd: Path, *args: str) -> str | None:
    try:
        res = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def git_toplevel(cwd: Path) -> Path | None:
    out = git(cwd, "rev-parse", "--show-toplevel")
    return Path(out) if out else None


def git_latest_commit(top: Path, rel: str) -> str | None:
    out = git(top, "log", "-n1", "--format=%H", "--", rel)
    return out or None


def git_is_clean(top: Path, rel: str) -> bool:
    out = git(top, "status", "--porcelain", "--", rel)
    return out == ""


def git_blob_sha(top: Path, rel: str) -> str | None:
    return git(top, "hash-object", "--", rel)


# --------------------------------------------------------------------------
# GitHub API (urllib only)
# --------------------------------------------------------------------------

class GitHubError(Exception):
    pass


class GitHub:
    def __init__(self, token: str, repo: str, api: str = "https://api.github.com"):
        self.token = token
        self.repo = repo
        self.api = api.rstrip("/")
        self._team_cache: dict[tuple, bool] = {}

    def _request(self, url: str):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "brace-check",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                link = resp.headers.get("Link", "") if resp.headers else ""
                return json.loads(body) if body else None, link
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None, ""
            raise GitHubError(f"GitHub API returned {exc.code} for {url}")
        except urllib.error.URLError as exc:
            raise GitHubError(f"Can't reach the GitHub API ({exc.reason})")

    def _url(self, path: str, params: dict | None = None) -> str:
        url = self.api + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return url

    def get(self, path: str, params: dict | None = None):
        data, _ = self._request(self._url(path, params))
        return data

    def get_all(self, path: str, params: dict | None = None) -> list:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url = self._url(path, params)
        out: list = []
        while url:
            data, link = self._request(url)
            if data is None:
                break
            if not isinstance(data, list):
                raise GitHubError(f"Unexpected GitHub API response for {path}")
            out.extend(data)
            url = _next_link(link)
        return out

    def is_team_member(self, org: str, slug: str, login: str) -> bool:
        key = (org.lower(), slug.lower(), login.lower())
        if key not in self._team_cache:
            try:
                data = self.get(f"/orgs/{org}/teams/{slug}/memberships/{login}")
            except GitHubError as exc:
                raise GitHubError(
                    f"{exc}. Reading membership of @{org}/{slug} needs a token with read:org "
                    "(in CI, set the BRACE_GITHUB_TOKEN secret; the workflow passes it as GITHUB_TOKEN)."
                )
            self._team_cache[key] = bool(data) and data.get("state") == "active"
        return self._team_cache[key]


def _next_link(header: str) -> str | None:
    for part in (header or "").split(","):
        m = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"', part)
        if m and m.group(2) == "next":
            return m.group(1)
    return None


def current_pr_number() -> int | None:
    """The PR this workflow run is for, when running on a pull_request event."""
    if os.environ.get("GITHUB_EVENT_NAME", "") not in ("pull_request", "pull_request_review", "pull_request_target"):
        return None
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        return None
    try:
        event = json.loads(Path(path).read_text(encoding="utf-8"))
        return int(event["pull_request"]["number"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _approver_match(gh: GitHub, login: str, approvers: list[str]) -> str | None:
    for a in approvers:
        name = a[1:] if a.startswith("@") else a
        if "/" in name:
            org, slug = name.split("/", 1)
            if gh.is_team_member(org, slug, login):
                return a
        elif name.lower() == login.lower():
            return a
    return None


def verify_github(gh: GitHub, top: Path, rel: str, approvers: list[str], current_pr: int | None):
    """Return (ok, detail, pending) for one exception or N/A file.

    The most recent commit that touched the file must belong to a merged PR (or the
    PR this run is checking) with an APPROVED review by a configured approver who
    is not the PR author, and the file must be unchanged since that approval.
    """
    if not git_is_clean(top, rel):
        return False, "the file has changes that are not committed", False
    sha = git_latest_commit(top, rel)
    if not sha:
        return False, "the file is not committed", False
    local_blob = git_blob_sha(top, rel)
    pulls = gh.get_all(f"/repos/{gh.repo}/commits/{sha}/pulls")
    candidates = [p for p in pulls if p.get("merged_at") or (current_pr and p.get("number") == current_pr)]
    if not candidates:
        return False, f"its latest change ({sha[:7]}) is not part of a merged pull request", False
    problems = []
    for pr in candidates:
        number = pr["number"]
        author = ((pr.get("user") or {}).get("login") or "").lower()
        reviews = gh.get_all(f"/repos/{gh.repo}/pulls/{number}/reviews")
        latest: dict[str, dict] = {}
        for r in reviews:  # API returns reviews in chronological order
            login = ((r.get("user") or {}).get("login") or "")
            if r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
                latest[login.lower()] = r
        approved = [r for r in latest.values() if r.get("state") == "APPROVED"]
        if not approved:
            problems.append(f"PR #{number} has no approving review")
            continue
        for r in approved:
            login = r["user"]["login"]
            if login.lower() == author:
                problems.append(f"PR #{number} was approved only by its author @{login}")
                continue
            who = _approver_match(gh, login, approvers)
            if not who:
                problems.append(f"PR #{number} approver @{login} is not a configured approver")
                continue
            content = gh.get(f"/repos/{gh.repo}/contents/{urllib.parse.quote(rel)}", {"ref": r.get("commit_id", "")})
            if not content or content.get("sha") != local_blob:
                problems.append(f"the file changed after @{login} approved PR #{number}")
                continue
            pending = not pr.get("merged_at")
            note = f"approved by @{login} ({who}) in PR #{number}"
            if pending:
                note += " (counts once the PR is merged)"
            return True, note, pending
    return False, "; ".join(dict.fromkeys(problems)), False


# --------------------------------------------------------------------------
# init / items / hash
# --------------------------------------------------------------------------

def cmd_init(args) -> int:
    target = Path(args.dir) / ".brace"
    if target.exists():
        print(f"{target} already exists. Not overwriting it.", file=sys.stderr)
        return EXIT_INVALID
    shutil.copytree(TEMPLATE_DIR, target)
    print(f"Created {target}/ with deployment.yaml, record.yaml, manifest.yaml, exceptions/, na/.")
    print("Next steps:")
    print("  1. Fill in deployment.yaml (task, stakes and autonomy rating, roles, approvers).")
    print("  2. Edit manifest.yaml, then run: brace.py hash  and copy the id into deployment.yaml.")
    print("  3. Review each item in record.yaml and record its outcome and evidence.")
    print(f"  4. Copy {HERE / 'templates' / 'CODEOWNERS.example'} and {HERE / 'templates' / 'brace-check.yml'} into your repo.")
    print("  5. Run: brace.py check")
    return EXIT_GO


def cmd_items(args) -> int:
    items = load_items()
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return EXIT_GO
    for i in items:
        star = "*" if i["top3"] else " "
        print(f"{i['id']} {i['gate']} {star} {i['title']:<62} lead: {i['lead_role']}")
    print(f"\n{len(items)} items. * = top 3 in its aspect.")
    return EXIT_GO


def cmd_hash(args) -> int:
    base = Path(args.dir)
    manifest_path = Path(args.manifest) if args.manifest else base / ".brace" / "manifest.yaml"
    manifest = load_manifest(manifest_path)
    print(agent_type_id(manifest, base))
    return EXIT_GO


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------

def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)


class Checker:
    def __init__(self, base: Path, approvals: str | None, strict: bool):
        self.base = base
        self.brace = base / ".brace"
        self.approvals_arg = approvals
        self.strict = strict
        self.reasons: list[str] = []
        self.warnings: list[str] = []
        self.items_out: dict[str, dict] = {}

    # -- loading -----------------------------------------------------------
    def load(self):
        errors: list[str] = []
        dep_path = self.brace / "deployment.yaml"
        rec_path = self.brace / "record.yaml"
        for p in (dep_path, rec_path):
            if not p.is_file():
                errors.append(f"{p} is missing. Run `brace.py init` to create the record folder.")
        if errors:
            raise InputError(errors)

        def load_and_validate(path: Path, schema: str):
            try:
                data = load_yaml(path)
            except InputError as exc:
                errors.extend(exc.messages)
                return None
            errs = validate(schema, data, str(path.relative_to(self.base)))
            errors.extend(errs)
            return None if errs else data

        self.deployment = load_and_validate(dep_path, "deployment")
        self.record = load_and_validate(rec_path, "record")
        self.exceptions: dict[str, dict] = {}
        self.na_files: dict[str, dict] = {}
        for sub, schema, store in (("exceptions", "exception", self.exceptions), ("na", "na", self.na_files)):
            folder = self.brace / sub
            if not folder.is_dir():
                continue
            for p in sorted(folder.iterdir()):
                if p.suffix == ".yml":
                    errors.append(f"{p.relative_to(self.base)}: use the .yaml extension")
                    continue
                if p.suffix != ".yaml":
                    continue
                data = load_and_validate(p, schema)
                if data is not None:
                    store[p.stem] = data

        self.catalog = {i["id"]: i for i in load_items()}
        if self.record is not None:
            unknown = sorted(set(self.record["items"]) - set(self.catalog))
            for u in unknown:
                errors.append(f".brace/record.yaml: {u} is not a BRACE checklist item")
        for store, sub in ((self.exceptions, "exceptions"), (self.na_files, "na")):
            for stem, data in store.items():
                if data["item"] not in self.catalog:
                    errors.append(f".brace/{sub}/{stem}.yaml: {data['item']} is not a BRACE checklist item")

        self.manifest = None
        if self.deployment is not None:
            ati = self.deployment.get("agent_type_id") or {}
            if ati.get("manifest"):
                try:
                    self.manifest = load_manifest(self.base / ati["manifest"])
                except InputError as exc:
                    errors.extend(exc.messages)
        if errors:
            raise InputError(errors)

    # -- approval mode -----------------------------------------------------
    def resolve_approvals(self):
        approvals_cfg = self.deployment.get("approvals") or {}
        provider = approvals_cfg.get("provider", "none")
        self.approvers = approvals_cfg.get("approvers") or []
        mode = self.approvals_arg
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        if mode is None:
            if provider == "github" and token and repo:
                mode = "github"
            elif git_toplevel(self.base):
                mode = "git"
            else:
                mode = "off"
        self.mode = mode
        self.gh = None
        self.top = None
        if mode in ("github", "git"):
            self.top = git_toplevel(self.base)
            if self.top is None:
                raise InputError(f"--approvals {mode} needs {self.base} to be inside a git repository.")
        if mode == "github":
            missing = [n for n, v in (("GITHUB_TOKEN", token), ("GITHUB_REPOSITORY", repo)) if not v]
            if missing:
                raise InputError(f"--approvals github needs these environment variables: {', '.join(missing)}.")
            if not self.approvers:
                raise InputError("--approvals github needs approvals.approvers in .brace/deployment.yaml.")
            api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
            self.gh = GitHub(token, repo, api)
            self.current_pr = current_pr_number()

    def check_approval(self, item_id: str, kind: str, path: Path) -> None:
        label = f"{item_id}'s {kind} ({path.relative_to(self.brace).as_posix()})"
        if self.mode == "off":
            self._unverified(item_id, f"{label}: approval not verified (--approvals off).")
            return
        rel = path.resolve().relative_to(self.top.resolve()).as_posix()
        if self.mode == "git":
            if git_latest_commit(self.top, rel) is None:
                self._block(item_id, f"{label} is not committed. It must be added through a reviewed pull request.")
            elif not git_is_clean(self.top, rel):
                self._block(item_id, f"{label} has changes that are not committed.")
            else:
                self._unverified(item_id, f"{label}: committed, but approval not verified (--approvals git checks only that the file is committed).")
            return
        try:
            ok, detail, pending = verify_github(self.gh, self.top, rel, self.approvers, self.current_pr)
        except GitHubError as exc:
            raise InputError(f"Can't verify approval for {label}: {exc}")
        if ok:
            self.items_out[item_id].setdefault("approval", detail)
            if pending:
                self.warnings.append(f"{label}: {detail}.")
        else:
            self._block(item_id, f"{label} is not approved: {detail}. "
                                 "It needs an approving review from a configured approver who did not open the pull request.")

    # -- helpers -----------------------------------------------------------
    def _block(self, item_id: str | None, msg: str) -> None:
        self.reasons.append(msg)
        if item_id and item_id in self.items_out:
            self.items_out[item_id]["status"] = "blocked"
            self.items_out[item_id]["problems"].append(msg)

    def _unverified(self, item_id: str, msg: str) -> None:
        if self.strict:
            self._block(item_id, msg + " --strict treats this as blocking.")
        else:
            self.warnings.append(msg)
            self.items_out[item_id]["problems"].append(msg)

    # -- rules -------------------------------------------------------------
    def run(self) -> dict:
        self.load()
        self.resolve_approvals()
        records = self.record["items"]

        # Rule 2: classification
        cls = self.deployment.get("classification")
        fields = ["stakes", "autonomy", "rationale", "approved_by"]
        if not cls:
            self._block(None, "deployment.yaml has no classification (stakes and autonomy rating). A missing rating blocks release.")
            high = True
        else:
            missing = [f for f in fields if _blank(cls.get(f))]
            if missing:
                self._block(None, f"The classification in deployment.yaml is missing: {', '.join(missing)}. "
                                  "An incomplete rating blocks release.")
            high = cls.get("stakes") != "low" or cls.get("autonomy") != "low"
        self.high = high

        no_lead: list[str] = []
        for item_id, meta in self.catalog.items():
            rec = records.get(item_id)
            self.items_out[item_id] = {
                "gate": meta["gate"],
                "title": meta["title"],
                "outcome": rec["outcome"] if rec else "missing",
                "status": "ok",
                "problems": [],
            }
            # Rule 3
            if rec is None:
                self._block(item_id, f"{item_id} is missing from record.yaml. Every item needs a result.")
                continue
            lead = rec.get("lead")
            if _blank(lead) or str(lead).strip().upper().startswith("TODO"):
                no_lead.append(item_id)
            outcome = rec["outcome"]
            if outcome == "not_reviewed":
                self._block(item_id, f"{item_id} has not been reviewed yet (outcome: not_reviewed).")
            elif outcome == "pass":
                self.rule_pass(item_id, rec)
            elif outcome == "na":
                self.rule_na(item_id, rec)
            elif outcome == "gap":
                self.rule_gap(item_id, meta, rec)
            if rec.get("exception") and outcome != "gap":
                self.warnings.append(f"{item_id} names exception '{rec['exception']}' but is marked {outcome}; the exception is ignored.")
            if rec.get("na") and outcome != "na":
                self.warnings.append(f"{item_id} names N/A file '{rec['na']}' but is marked {outcome}; it is ignored.")

        if no_lead:
            self.warnings.append(f"{len(no_lead)} item(s) have no named lead (empty or TODO): {', '.join(no_lead)}.")
        self.rule_exception_files(records)
        self.rule_agent_type_id()
        return self.result()

    def rule_pass(self, item_id, rec):
        good = [e for e in rec.get("evidence") or [] if not _blank(e.get("link")) and not _blank(e.get("date"))]
        if not good:
            self._block(item_id, f"{item_id} is marked pass but has no evidence with both a link and a date.")

    def rule_na(self, item_id, rec):
        stem = rec.get("na")
        if not stem:
            self._block(item_id, f"{item_id} is marked N/A but names no N/A file. Add .brace/na/{item_id}-<reason>.yaml and set na: to its name.")
            return
        data = self.na_files.get(stem)
        path = self.brace / "na" / f"{stem}.yaml"
        if data is None:
            self._block(item_id, f"{item_id} is marked N/A, but .brace/na/{stem}.yaml does not exist.")
            return
        if data["item"] != item_id:
            self._block(item_id, f".brace/na/{stem}.yaml is for {data['item']}, not {item_id}.")
            return
        missing = [f for f in ("reason", "evidence", "reviewer") if _blank(data.get(f))]
        if missing:
            self._block(item_id, f"{item_id}'s N/A file .brace/na/{stem}.yaml is missing: {', '.join(missing)}. "
                                 "Every N/A needs a reason, evidence, and a reviewer.")
            return
        self.check_approval(item_id, "N/A decision", path)

    def rule_gap(self, item_id, meta, rec):
        gate = meta["gate"]
        if gate == "G1":
            self._block(item_id, f"{item_id} is G1 and marked gap. G1 items can't be waived. Release is blocked.")
            return
        if gate == "G3" and self.high:
            why = "high stakes or high autonomy" if self.deployment.get("classification") else "not rated, so it counts as high stakes"
            self._block(item_id, f"{item_id} is G3 and marked gap. This deployment is {why}, so G3 gaps can't be "
                                 "accepted as risk. Release is blocked.")
            return
        stem = rec.get("exception")
        if not stem:
            self._block(item_id, f"{item_id} is {gate} and marked gap with no risk acceptance. Fix it, or add "
                                 f".brace/exceptions/{item_id}-<slug>.yaml, set exception: to its name, and get it approved.")
            return
        data = self.exceptions.get(stem)
        path = self.brace / "exceptions" / f"{stem}.yaml"
        if data is None:
            self._block(item_id, f"{item_id} points to exception '{stem}', but .brace/exceptions/{stem}.yaml does not exist.")
            return
        if data["item"] != item_id:
            self._block(item_id, f".brace/exceptions/{stem}.yaml is for {data['item']}, not {item_id}.")
            return
        missing = [f for f in ("threat", "affected_systems", "compensating_controls", "accepted_by",
                               "accepted_on", "remediation_owner", "tracking") if _blank(data.get(f))]
        if not missing:
            for i, c in enumerate(data["compensating_controls"]):
                if _blank(c.get("control")) or _blank(c.get("evidence")):
                    missing.append(f"compensating_controls[{i}] control or evidence")
        if missing:
            self._block(item_id, f"{item_id}'s risk acceptance .brace/exceptions/{stem}.yaml is missing: "
                                 f"{', '.join(missing)}. A blank exception counts as an open gap.")
            return
        self.check_approval(item_id, "risk acceptance", path)

    def rule_exception_files(self, records):
        for stem, data in self.exceptions.items():
            item_id = data["item"]
            gate = self.catalog[item_id]["gate"]
            rel = f".brace/exceptions/{stem}.yaml"
            if gate == "G1":
                self._block(item_id, f"{rel} is a risk acceptance for {item_id}, a G1 item. G1 items can't be waived. "
                                     "Remove the file and fix the gap.")
            elif gate == "G3" and self.high:
                self._block(item_id, f"{rel} is a risk acceptance for {item_id}, a G3 item. This deployment is high "
                                     "stakes or high autonomy, so G3 risk acceptances aren't allowed.")
            if not stem.startswith(f"{item_id}-") and stem != item_id:
                self.warnings.append(f"{rel} is for {item_id}; name it {item_id}-<slug>.yaml.")
            if (records.get(item_id) or {}).get("exception") != stem:
                self.warnings.append(f"{rel} is not used by record.yaml.")
        for stem, data in self.na_files.items():
            if (records.get(data["item"]) or {}).get("na") != stem:
                self.warnings.append(f".brace/na/{stem}.yaml is not used by record.yaml.")

    def rule_agent_type_id(self):
        ati = self.deployment.get("agent_type_id") or {}
        self.computed_id = None
        if self.manifest is None:
            return
        self.computed_id = agent_type_id(self.manifest, self.base)
        recorded = ati.get("value")
        if not recorded:
            self._block(None, f"deployment.yaml has a manifest but no agent_type_id value. Record {self.computed_id} and review this release.")
        elif recorded != self.computed_id:
            self._block(None, f"agent-type-id changed: re-review required. deployment.yaml has {recorded}; "
                              f"the manifest now gives {self.computed_id}.")

    def result(self) -> dict:
        counts = {g: {o: 0 for o in OUTCOMES + ["missing"]} for g in GATE_ORDER}
        for item in self.items_out.values():
            counts[item["gate"]][item["outcome"]] += 1
        return {
            "decision": "NO-GO" if self.reasons else "GO",
            "reasons": self.reasons,
            "warnings": self.warnings,
            "approvals": self.mode,
            "strict": self.strict,
            "agent_type_id": {"recorded": (self.deployment.get("agent_type_id") or {}).get("value"),
                              "computed": self.computed_id},
            "counts": counts,
            "items": self.items_out,
        }


def render_summary(res: dict) -> str:
    lines = []
    lines.append("BRACE check")
    lines.append(f"Approvals: {res['approvals']}{' (strict)' if res['strict'] else ''}")
    lines.append("")
    header = f"{'':4}{'pass':>6}{'gap':>6}{'na':>6}{'not rev.':>10}{'missing':>9}"
    lines.append(header)
    totals = {k: 0 for k in OUTCOMES + ["missing"]}
    for g in GATE_ORDER:
        c = res["counts"][g]
        for k in totals:
            totals[k] += c[k]
        lines.append(f"{g:4}{c['pass']:>6}{c['gap']:>6}{c['na']:>6}{c['not_reviewed']:>10}{c['missing']:>9}")
    lines.append(f"{'All':4}{totals['pass']:>6}{totals['gap']:>6}{totals['na']:>6}{totals['not_reviewed']:>10}{totals['missing']:>9}")
    if res["reasons"]:
        lines.append("")
        lines.append(f"Blocking ({len(res['reasons'])}):")
        lines.extend(f"  - {r}" for r in res["reasons"])
    if res["warnings"]:
        lines.append("")
        lines.append(f"Warnings ({len(res['warnings'])}):")
        lines.extend(f"  - {w}" for w in res["warnings"])
    lines.append("")
    lines.append(f"Decision: {res['decision']}")
    return "\n".join(lines)


def cmd_check(args) -> int:
    checker = Checker(Path(args.dir), args.approvals, args.strict)
    res = checker.run()
    print(render_summary(res))
    if args.json:
        text = json.dumps(res, indent=2, ensure_ascii=False) + "\n"
        if args.json == "-":
            sys.stdout.write(text)
        else:
            Path(args.json).write_text(text, encoding="utf-8")
    return EXIT_GO if res["decision"] == "GO" else EXIT_NOGO


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

class _Parser(argparse.ArgumentParser):
    def error(self, message):  # exit 2 with a plain message
        self.print_usage(sys.stderr)
        raise InputError(f"{self.prog}: {message}")


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="brace.py", description="Check a BRACE record folder (.brace/) and decide GO or NO-GO.")
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser)

    s = sub.add_parser("init", help="create .brace/ from the templates")
    s.add_argument("--dir", default=".", help="repository root (default: .)")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("items", help="list the 53 checklist items")
    s.add_argument("--json", action="store_true", help="print JSON")
    s.set_defaults(func=cmd_items)

    s = sub.add_parser("hash", help="print the agent-type-id for a manifest")
    s.add_argument("--dir", default=".", help="repository root; manifest paths are relative to it (default: .)")
    s.add_argument("--manifest", help="manifest file (default: <dir>/.brace/manifest.yaml)")
    s.set_defaults(func=cmd_hash)

    s = sub.add_parser("check", help="validate .brace/ and decide GO or NO-GO")
    s.add_argument("--dir", default=".", help="repository root holding .brace/ (default: .)")
    s.add_argument("--approvals", choices=["github", "git", "off"],
                   help="how to verify exception and N/A approvals (default: github when configured and "
                        "GITHUB_TOKEN/GITHUB_REPOSITORY are set, else git inside a repository, else off)")
    s.add_argument("--strict", action="store_true", help="treat unverified approvals as blocking")
    s.add_argument("--json", metavar="FILE", help="also write the result as JSON to FILE ('-' for stdout)")
    s.set_defaults(func=cmd_check)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except InputError as exc:
        print("Invalid input. Fix these and run again:", file=sys.stderr)
        for m in exc.messages:
            print(f"  - {m}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
