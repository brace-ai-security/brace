#!/usr/bin/env python3
"""Pre-scan a repository for code that looks like a BRACE control but often fails.

Each hit is a place for the reviewer to read, not a finding. The `ask` on each hit
says what to check to confirm or dismiss it.

Usage: python prescan.py REPO [--out FILE]

Patterns live in ../prescan/patterns.yaml. Writes JSON (default REPO/brace-prescan.json):
  {"hits": [{"id": "H001", "pattern": "P01", "item": "B01", "title": ..., "file": ...,
             "line": 41, "text": ..., "ask": ...}],
   "capped": [{"pattern": "P07", "found": 60, "kept": 25}], ...}
"""
import argparse
import fnmatch
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

PATTERNS_FILE = Path(__file__).resolve().parent.parent / "prescan" / "patterns.yaml"
MAX_HITS_PER_PATTERN = 25
MAX_TEXT = 200
MAX_FILE_BYTES = 2_000_000
MAX_LINE_CHARS = 2_000  # longer lines are usually minified or generated

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "brace-challenges"}
SKIP_DIR_PREFIXES = ("brace-findings",)
SKIP_FILE_PREFIXES = ("brace-findings", "brace-prescan")
SKIP_FILE_GLOBS = ("*.min.js", "*.bundle.js", "*.bundled.js", "*.min.css", "*.map", "*.lock",
                   "package-lock.json", "pnpm-lock.yaml")
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*(\s|/|$))")

LANGUAGE_GLOBS = {
    "python": ["*.py", "*.pyi"],
    "typescript": ["*.ts", "*.tsx", "*.mts", "*.cts"],
    "javascript": ["*.js", "*.jsx", "*.mjs", "*.cjs"],
    "go": ["*.go"],
    "yaml": ["*.yaml", "*.yml"],
    "json": ["*.json", "*.jsonc"],
    "hcl": ["*.tf", "*.tfvars", "*.hcl"],
    "dockerfile": ["Dockerfile", "Dockerfile.*", "*.Dockerfile", "*.dockerfile", "Containerfile"],
    "shell": ["*.sh", "*.bash", "*.zsh"],
    "toml": ["*.toml"],
    "env": [".env", ".env.*", "*.env"],
}


def load_patterns(path=PATTERNS_FILE):
    try:
        import yaml
    except ImportError:
        sys.exit("prescan.py needs PyYAML to read patterns.yaml. Install it with: pip install pyyaml")
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        sys.exit(f"{path}: expected a list of patterns")
    patterns, errors, seen = [], [], set()
    for p in data:
        pid = p.get("id", "?")
        missing = [k for k in ("id", "item", "title", "regex", "ask") if not p.get(k)]
        if missing:
            errors.append(f"{pid}: missing {', '.join(missing)}")
            continue
        if pid in seen:
            errors.append(f"{pid}: duplicate id")
        seen.add(pid)
        langs = p.get("languages") or []
        unknown = [l for l in langs if l not in LANGUAGE_GLOBS]
        if unknown:
            errors.append(f"{pid}: unknown languages {unknown}")
        globs = p.get("file_glob") or [g for l in langs for g in LANGUAGE_GLOBS.get(l, [])]
        if not globs:
            errors.append(f"{pid}: no languages or file_glob")
        try:
            rx = re.compile(p["regex"])
        except re.error as e:
            errors.append(f"{pid}: bad regex: {e}")
            continue
        window = int(p.get("window") or 0)
        if window and not re.sub(r"^\(\?i\)", "", p["regex"]).startswith("^"):
            errors.append(f"{pid}: a pattern with window must start with ^")
        patterns.append({**p, "_rx": rx, "_globs": globs, "_window": window,
                         "_comments": bool(p.get("include_comments"))})
    if errors:
        sys.exit(f"{path}: invalid patterns:\n  " + "\n  ".join(errors))
    return patterns


def glob_match(rel, globs):
    name = rel.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in globs)


def walk(repo):
    for root, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(SKIP_DIR_PREFIXES))
        for f in sorted(files):
            if f.startswith(SKIP_FILE_PREFIXES) or any(fnmatch.fnmatchcase(f, g) for g in SKIP_FILE_GLOBS):
                continue
            full = Path(root) / f
            if full.is_symlink() or not full.is_file():
                continue
            yield full, full.relative_to(repo).as_posix()


def scan(repo, patterns):
    repo = Path(repo).resolve()
    found = {p["id"]: [] for p in patterns}
    counts = Counter()
    files_scanned = 0
    for full, rel in walk(repo):
        applicable = [p for p in patterns if glob_match(rel, p["_globs"])]
        if not applicable:
            continue
        try:
            if full.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = full.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        files_scanned += 1
        lines = raw.decode("utf-8", errors="replace").splitlines()
        is_comment = [bool(COMMENT_LINE.match(l)) for l in lines]
        for p in applicable:
            rx, window = p["_rx"], p["_window"]
            for i, line in enumerate(lines):
                if len(line) > MAX_LINE_CHARS or (is_comment[i] and not p["_comments"]):
                    continue
                subject = "\n".join(lines[i:i + window + 1]) if window else line
                if not rx.search(subject):
                    continue
                counts[p["id"]] += 1
                if len(found[p["id"]]) < MAX_HITS_PER_PATTERN:
                    found[p["id"]].append((rel, i + 1, line.strip()[:MAX_TEXT]))
    hits, capped = [], []
    for p in patterns:
        for rel, lineno, text in found[p["id"]]:
            hits.append({
                "id": f"H{len(hits) + 1:03d}", "pattern": p["id"], "item": p["item"],
                "title": p["title"], "file": rel, "line": lineno, "text": text, "ask": p["ask"].strip(),
            })
        if counts[p["id"]] > MAX_HITS_PER_PATTERN:
            capped.append({"pattern": p["id"], "item": p["item"], "found": counts[p["id"]],
                           "kept": MAX_HITS_PER_PATTERN})
    return {
        "repo": str(repo),
        "patterns_file": str(PATTERNS_FILE),
        "files_scanned": files_scanned,
        "note": "Hits are places to read, not findings. Answer each hit's ask before citing it.",
        "capped": capped,
        "hits": hits,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo")
    ap.add_argument("--out", help="output JSON (default REPO/brace-prescan.json)")
    ap.add_argument("--patterns", default=str(PATTERNS_FILE), help=argparse.SUPPRESS)
    args = ap.parse_args()
    repo = Path(args.repo)
    if not repo.is_dir():
        sys.exit(f"{repo} is not a directory")
    patterns = load_patterns(args.patterns)
    result = scan(repo, patterns)
    out = Path(args.out) if args.out else repo / "brace-prescan.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    per_item = Counter(h["item"] for h in result["hits"])
    print(f"Scanned {result['files_scanned']} files with {len(patterns)} patterns: "
          f"{len(result['hits'])} hits written to {out}")
    for item in sorted(per_item):
        print(f"  {item}: {per_item[item]}")
    for c in result["capped"]:
        print(f"  capped {c['pattern']} ({c['item']}): {c['found']} matches, kept {c['kept']}")


if __name__ == "__main__":
    main()
