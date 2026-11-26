"""Ignore entries: the ignore file, gitignore-style globs and the inline mark."""
import json
import os
import shutil
import subprocess

import pytest
from support import FLAG, TOKEN, TOOL_DIR, config, report, result, rules, scan, six_servers, write

from open_agent_security import ignore
from open_agent_security.ignore import IGNORE_FILE, Ignores, load_ignores, parse_pattern
from open_agent_security.limits import MAX_SEGMENTS


def test_jsonc_inline_ignore(tmp_path):
    write(tmp_path, ".mcp.json", '{"mcpServers": {\n "s": {"command": "npx", "args": ["x"]} // open-agent-security: ignore\n,'
                                 '\n "t": {"command": "node", "env": {"K": "' + TOKEN + '"}}}}\n')
    assert rules(tmp_path) == ["AP05"]


def test_ignores(tmp_path):
    write(tmp_path, "a.sh", "claude --dangerously-skip-permissions  # open-agent-security: ignore\n")
    write(tmp_path, "fixtures/b.sh", "claude --dangerously-skip-permissions\n")
    write(tmp_path, IGNORE_FILE, "fixtures/\n")
    assert rules(tmp_path) == []


@pytest.mark.parametrize("pattern,path,hit", [
    ("fixtures", "fixtures/b.sh", True),
    ("fixtures", "src/fixtures/b.sh", True),
    ("/fixtures/", "src/fixtures/b.sh", False),
    ("/fixtures/", "fixtures/b.sh", True),
    ("docs/*.sh", "docs/x/y.sh", False),
    ("docs/**/*.sh", "docs/x/y.sh", True),
    ("*.sh", "deep/er/z.sh", True),
])
def test_ignore_patterns(tmp_path, pattern, path, hit):
    write(tmp_path, path, "claude --dangerously-skip-permissions\n")
    write(tmp_path, IGNORE_FILE, pattern + "\n")
    assert (rules(tmp_path) == []) is hit


def test_ignore_negation_and_rule_scope(tmp_path):
    write(tmp_path, "fixtures/a.sh", "claude --dangerously-skip-permissions\n")
    write(tmp_path, "fixtures/keep.sh", "claude --dangerously-skip-permissions\n")
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "npx", "args": ["x"], "env": {"K": TOKEN}}}}))
    write(tmp_path, IGNORE_FILE, "# comment\nfixtures/\n!fixtures/keep.sh\nAP04 .mcp.json\n")
    assert sorted((f.rule, f.file) for f in result(tmp_path).findings) == [("AP01", "fixtures/keep.sh"),
                                                                            ("AP05", ".mcp.json")]


def test_documented_ignore_example_works(tmp_path):
    doc = (TOOL_DIR / "SCAN.md").read_text(encoding="utf-8")
    block = doc.split("```text\n", 1)[1].split("```", 1)[0]
    write(tmp_path, IGNORE_FILE, block)
    for p in ("fixtures/a.sh", "build/out.sh", "docs/x/y.sh", "fixtures/keep.sh"):
        write(tmp_path, p, "claude --dangerously-skip-permissions\n")
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "npx", "args": ["x"]}}}))
    assert sorted((f.rule, f.file) for f in result(tmp_path).findings) == [("AP01", "fixtures/keep.sh")]


def test_form_feed_does_not_shift_inline_ignore(tmp_path):
    write(tmp_path, "ff.sh", "echo hi\x0cthere\nclaude --dangerously-skip-permissions # open-agent-security: ignore\n")
    assert rules(tmp_path) == []


def test_ignore_cache_overflow_does_not_raise(monkeypatch):
    monkeypatch.setattr(ignore, "IGNORE_CACHE_FOLDERS", 10)
    ig = Ignores([parse_pattern(f"nomatch{i}*") for i in range(110)])
    assert not any(ig.match(f"d{i}/f{i}.json") for i in range(200))


def test_plugin_rule_ids_in_ignore_file(tmp_path):
    six_servers(tmp_path)
    write(tmp_path, IGNORE_FILE, "ACME01 .mcp.json\n")
    r = report(tmp_path)
    assert len(r["findings"]) == 6 and any("unknown rule ACME01" in n for n in r["notes"])
    assert load_ignores(tmp_path)[0][0].rule == "ACME01"


def test_patterns_deeper_than_the_cap_are_skipped_with_a_note(tmp_path):
    too_deep = "/".join(["*?*"] * (MAX_SEGMENTS + 1))
    write(tmp_path, IGNORE_FILE, f"{too_deep}\nrun.sh\n")
    entries, notes = load_ignores(tmp_path)
    assert len(entries) == 1
    assert notes and "more than 16 folders" in notes[0]
    write(tmp_path, "a.sh", f"claude -p hi {FLAG}\n")
    assert any("more than 16 folders" in n for n in report(tmp_path)["notes"])
    config(tmp_path, {"include": [too_deep]})
    assert scan(tmp_path)[0] == 2


def test_ignore_matching_still_follows_gitignore_rules(tmp_path):
    from open_agent_security.ignore import Ignores, parse_pattern
    ig = Ignores([parse_pattern(p) for p in ("build/", "**/gen/**", "/top.sh", "*.log", "!keep.log", "a/**/z.sh")])
    assert ig.match("x/build/y.sh") and ig.match("build", is_dir=True) and not ig.match("x/build.sh")
    assert ig.match("p/gen/q/r.sh") and ig.match("top.sh") and not ig.match("sub/top.sh")
    assert ig.match("deep/x.log") and not ig.match("deep/keep.log")
    assert ig.match("a/z.sh") and ig.match("a/b/c/z.sh") and not ig.match("b/z.sh")


def test_plugin_rule_ids_with_dashes_in_the_ignore_file(tmp_path):
    write(tmp_path, IGNORE_FILE, "ACME-01 run.sh\n")
    assert load_ignores(tmp_path)[0][0].rule == "ACME-01"
    write(tmp_path, "run.sh", f"claude -p hi {FLAG}\n")
    r = report(tmp_path)
    assert [f["rule"] for f in r["findings"]] == ["AP01"]
    assert any("unknown rule ACME-01" in n for n in r["notes"])


@pytest.mark.parametrize("pattern,path,ignored", [
    ("X/**", "X", False), ("X/**", "X/a.sh", True), ("X/**", "X/d/a.sh", True), ("*/**", "a.sh", False),
    ("*/**", "d/a.sh", True), ("**", "a.sh", True), ("a/**/b.sh", "a/b.sh", True), ("**/b.sh", "b.sh", True)])
def test_a_trailing_double_star_matches_only_inside_the_folder(pattern, path, ignored):
    assert Ignores([parse_pattern(pattern)]).match(path) is ignored


TREE = ["X", "Y/X", "X2/a.sh", "Xd/a.sh", "a.sh", "d/a.sh", "d/e/a.sh", "d/e/f/b.py", "e/d/a.sh", "a/b.sh",
        "a/x/b.sh", "a/x/y/b.sh", "src/a.ts", "src/lib/b.ts", "docs/a.md", "d.sh/c.sh"]
PATTERNS = ["X/**", "*/**", "**", "/X", "X", "d/", "/d/", "d/**", "**/e", "**/e/**", "a/**/b.sh", "*.sh", "/*.sh",
            "src/*", "src/**/*.ts", "d/*/a.sh", "**/a.sh", "?.sh", "a/x/**", "*/e/*", "d.sh/", "e/d/", "!x"]


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
@pytest.mark.parametrize("pattern", PATTERNS)
def test_globs_match_like_git(tmp_path, pattern):
    for rel in TREE:
        write(tmp_path, rel, "x\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(pattern + "\n", encoding="utf-8")
    out = subprocess.run(["git", "-C", str(tmp_path), "-c", "core.ignorecase=false", "check-ignore", "--no-index", "--stdin"], input="\n".join(TREE),
                         capture_output=True, text=True).stdout.split()
    entry = parse_pattern(pattern)
    ours = {rel for rel in TREE if entry and Ignores([entry]).match(rel)} if not pattern.startswith("!") else set()
    assert ours == set(out), pattern


@pytest.mark.parametrize("make,why", [
    (lambda root: os.symlink(root / "real", root / IGNORE_FILE), "a symlink"),
    (lambda root: (root / IGNORE_FILE).write_text("*\n" * 700_000), "over 1024 KB"),
    (lambda root: (root / IGNORE_FILE).mkdir(), "not a regular file")])
def test_an_ignore_file_that_cannot_be_read_is_not_applied_and_says_so(tmp_path, make, why):
    write(tmp_path, "real", "*.sh\n")
    write(tmp_path, "run.sh", f"claude {FLAG}\n")
    make(tmp_path)
    r = report(tmp_path)
    assert [f["rule"] for f in r["findings"]] == ["AP01"]
    assert f"ignore file: {IGNORE_FILE} is {why}, so it was not applied" in r["notes"]
