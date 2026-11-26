"""Permission bypasses written as text (AP01, AP02), mentions that are not passed, and Claude settings (AP06, AP01)."""
import json

import pytest
from support import FLAG, TOOL_DIR, found, report, result, rules, write


def test_skip_permissions_local_vs_ci(tmp_path):
    write(tmp_path, "run.sh", "claude -p 'fix' --dangerously-skip-permissions\n")
    write(tmp_path, ".github/workflows/agent.yml", "steps:\n  - run: claude -p x --dangerously-skip-permissions\n")
    write(tmp_path, ".gitlab-ci.yml", "job:\n  script: codex exec --dangerously-bypass-approvals-and-sandbox\n")
    assert rules(tmp_path) == ["AP01", "AP02", "AP02"]


def test_bypass_cli_forms_and_comments(tmp_path):
    write(tmp_path, ".github/workflows/a.yml",
          "# We deliberately do NOT pass --dangerously-skip-permissions here.\n"
          "  - run: claude -p review --permission-mode bypassPermissions\n"
          "  - run: codex exec --sandbox danger-full-access\n"
          "  - run: gemini --approval-mode yolo\n")
    found = result(tmp_path).findings
    assert [f.line for f in found] == [2, 3, 4]
    assert {f.rule for f in found} == {"AP02"}


def test_codex_approval_never_alone_is_not_flagged(tmp_path):
    write(tmp_path, ".codex/config.toml", 'approval_policy = "never"\nsandbox_mode = "read-only"\n')
    assert rules(tmp_path) == []
    write(tmp_path, ".codex/config.toml", 'sandbox_mode = "danger-full-access"\n')
    assert rules(tmp_path) == ["AP01"]
    assert result(tmp_path).findings[0].detail == 'sandbox_mode = "danger-full-access"'


def test_broad_shell_allow(tmp_path):
    write(tmp_path, ".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(*)", "Bash(npm test)"]}}))
    assert rules(tmp_path) == ["AP06"]


def test_settings_default_mode_bypass(tmp_path):
    write(tmp_path, ".claude/settings.json", json.dumps({"permissions": {"defaultMode": "bypassPermissions"}}))
    assert rules(tmp_path) == ["AP01"]


def test_docs_do_not_trigger_permission_rule(tmp_path):
    write(tmp_path, "README.md", "Never use --dangerously-skip-permissions.\n")
    assert rules(tmp_path) == []


def test_yolo_prefixed_flags_are_not_bypasses(tmp_path):
    write(tmp_path, "train.sh", "python detect.py --yolo-weights yolov8n.pt\npython export.py --yolo-version 8\n")
    assert rules(tmp_path) == []


def test_round3_missed_patterns(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", "on: [issues]\njobs:\n  a:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n"
          "        with:\n          settings: '{\"permissions\":{\"defaultMode\":\"bypassPermissions\"}}'\n")
    write(tmp_path, "scripts/agent", "#!/bin/sh\nclaude --dangerously-skip-permissions\n")
    write(tmp_path, ".env", "X=1\nAGENT_FLAGS=--dangerously-skip-permissions\n")
    write(tmp_path, ".claude/settings.json", json.dumps({"env": {"ANTHROPIC_API_KEY": "sk-ant-api03-" + "Ab1" * 30}}))
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {
        "a": {"command": "bash", "args": ["-c", "npx -y pkg"]},
        "b": {"command": "bun", "args": ["x", "pkg2"]},
        "c": {"command": "uvx", "args": ["--from", "git+https://github.com/o/r@main", "tool"]},
        "d": {"command": "docker", "args": ["run", "--privileged=true", "i"]}}}))
    write(tmp_path, ".github/workflows/p.yml", '"on": pull_request_target\njobs:\n  a:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n')
    write(tmp_path, ".github/workflows/q.yml", 'on:\n  [pull_request_target, issues]\njobs:\n  a:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n')
    got = sorted((f.rule, f.file) for f in result(tmp_path).findings)
    assert ("AP02", ".github/workflows/w.yml") in got
    assert ("AP01", "scripts/agent") in got and ("AP01", ".env") in got
    assert ("AP05", ".claude/settings.json") in got
    assert [r for r, f in got if f == ".mcp.json" and r == "AP04"] == ["AP04", "AP04", "AP04"]
    assert ("AP08", ".mcp.json") in got
    assert ("AP03", ".github/workflows/p.yml") in got and ("AP03", ".github/workflows/q.yml") in got


def test_trailing_comment_mentioning_a_flag(tmp_path):
    write(tmp_path, "c.yml", "x: 1  # never pass --dangerously-skip-permissions here\ny: 'gemini # --yolo'\n")
    write(tmp_path, "d.ts", "run('x') // do not add --dangerously-skip-permissions\n")
    assert [(f.file, f.line) for f in result(tmp_path).findings] == [("c.yml", 2)]


def test_bare_yolo_needs_an_agent_cli(tmp_path):
    write(tmp_path, "detect.sh", "python detect.py --yolo\n")
    write(tmp_path, "agent.sh", "gemini --yolo -p fix\nnpx @qwen-code/qwen-code --yolo\n")
    assert found(tmp_path) == [("AP01", "--yolo"), ("AP01", "--yolo")]
    assert {f["file"] for f in report(tmp_path)["findings"]} == {"agent.sh"}


def test_escaped_double_quote_does_not_close_the_string(tmp_path):
    write(tmp_path, "run.sh", f'claude -p "say \\" #hi" {FLAG}\n')
    assert rules(tmp_path) == ["AP01"]
    write(tmp_path, "run.sh", f"claude -p 'say \\' #{FLAG}\n")  # single quotes have no escapes
    assert rules(tmp_path) == []


@pytest.mark.parametrize("text", [
    f'BLOCKED = ["{FLAG}"]\n',
    f'BLOCKED = {{\n    "--yolo",\n    "{FLAG}",\n}}\n',
    f'if arg == "{FLAG}":\n    sys.exit(2)\n',
    f'if arg in ("--x", "{FLAG}"):\n    sys.exit(2)\n',
])
def test_guard_lists_are_not_reported(tmp_path, text):
    write(tmp_path, "hooks/guard.py", text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel,text", [
    ("run.py", f'subprocess.run(["claude", "-p", x, "{FLAG}"])\n'),
    ("run.py", f'cmd = [\n    "claude",\n    "-p",\n    prompt,\n    "{FLAG}",\n]\n'),
    ("run.ts", f'spawn("claude", ["-p", prompt, "{FLAG}"]);\n'),
    ("run.py", f'os.system("claude -p hi {FLAG}")\n'),
    ("run.sh", f'ARGS=("{FLAG}")\n'),
])
def test_agent_argument_lists_are_still_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("rel,text", [
    ("agent.py", 'args = [CLAUDE_BIN, "--print", "--dangerously-skip-permissions", "--output-format", "json", prompt]\n'),
    ("run.ts", 'const args = ["--dangerously-skip-permissions", "--output-format", "stream-json"];\n'),
    ("codex.ts", "export const codexArgs = ['exec', '--dangerously-bypass-approvals-and-sandbox'];\n"),
    ("agent.go", 'func args(prompt string) []string {\n\treturn []string{"-p", prompt, "--dangerously-skip-permissions"}\n}\n'),
    ("bin.py", 'subprocess.run(["/usr/local/bin/claude", "--dangerously-skip-permissions"])\n'),
    ("ci.yml", 'steps:\n  - run: claude -p "fix it" --dangerously-skip-permissions\n'),
    ("plain.py", 'FLAGS = ["--dangerously-skip-permissions"]\n'),
])
def test_a_flag_passed_in_source_is_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("rel,text", [
    ("doc.py", 'def run():\n    """Never pass --dangerously-skip-permissions to the agent."""\n'),
    ("doc2.py", 'def run():\n    """Run the agent.\n\n    Never pass --dangerously-skip-permissions; it turns off every check.\n    """\n'),
    ("cli.py", 'parser.add_argument("--safe", help="do not use --dangerously-skip-permissions here")\n'),
    ("guard.py", 'assert "--dangerously-skip-permissions" not in cmd\n'),
    ("guard2.py", 'if "--dangerously-skip-permissions" in cmd:\n'
                  '    raise SystemExit("refusing to run with --dangerously-skip-permissions")\n'),
    ("guard.ts", 'if (/--dangerously-skip-permissions/.test(cmd)) { throw new Error("no"); }\n'),
    ("msg.ts", "const msg = `Do not pass --dangerously-skip-permissions here`;\n"),
    ("policy.yml", 'blocked_flags:\n  - "--dangerously-skip-permissions"\n  - "--yolo"\n'),
    ("action.yml", "name: x\ndescription: Never pass --dangerously-skip-permissions to the agent\n"),
    ("deny.json", '{"deny": ["--dangerously-skip-permissions"]}\n'),
    ("block.js", "/* never use --dangerously-skip-permissions */\nrun();\n"),
])
def test_a_flag_only_mentioned_is_not_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == []


def test_the_mention_rule_is_documented():
    assert "only mentioned" in (TOOL_DIR / "SCAN.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("line,expected", [("copilot -p hi --allow-all-tools\n", ["AP01"]),
                                           ("copilot -p hi --allow-all\n", ["AP01"]),
                                           ("deno run --allow-all main.ts\n", [])])
def test_copilot_allow_all_is_a_bypass(tmp_path, line, expected):
    write(tmp_path, "run.sh", line)
    assert rules(tmp_path) == expected


@pytest.mark.parametrize("name,text", [("agent.bat", f"REM claude -p hi {FLAG}\n"), ("agent.cmd", f":: claude {FLAG}\n"),
                                       ("agent.fish", f"# claude {FLAG}\n"), ("x.mk", f"# claude {FLAG}\n"),
                                       ("agent.mts", f"// claude {FLAG}\n")])
def test_comment_markers_of_the_new_file_types(tmp_path, name, text):
    write(tmp_path, name, text)
    assert rules(tmp_path) == []


def test_permission_mode_in_a_folded_scalar(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", "jobs:\n  a:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n"
                                               "        with:\n          claude_args: >-\n            --permission-mode\n"
                                               "            bypassPermissions\n")
    assert found(tmp_path) == [("AP02", "--permission-mode bypassPermissions")]


@pytest.mark.parametrize("rel,before", [
    ("a.ts", 'const files = glob("src/*.ts");'), ("a.js", 'const routes = ["/api/*"];'),
    ("a.go", 'h := map[string]string{"Accept": "*/*"}'), ("a.ts", "const t = `/*${x}`;"),
    ("a.go", "re := `a/*b`"), ("a.rs", 'let p = "/tmp/*";'), ("A.java", "String g = 'a/*';"),
    ("a.kt", 'val g = "a/*"'), ("a.jsonc", '{"glob": "src/*.ts",'), ("a.js", "// see /* below\nx();"),
    ("a.js", 'const u = "http://x/*";')])
def test_a_block_comment_opener_inside_a_string_hides_nothing(tmp_path, rel, before):
    write(tmp_path, rel, f'{before}\nspawn("claude", ["{FLAG}"]);\n')
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("rel,text", [
    ("a.ts", f'const s = "x"; /* old: spawn("claude", ["{FLAG}"]) */\n'),
    ("a.go", f'/*\nexec.Command("claude", "{FLAG}")\n*/\n'),
    ("a.js", f'/**\n * spawn("claude", ["{FLAG}"])\n */\n'),
    ("a.py", f'def run():\n    """Never pass {FLAG} here."""\n'),
    ("a.py", f'"""Module docs: claude -p x {FLAG}."""\n'),
    ("a.py", f'class A:\n    """claude {FLAG}"""\n'),
    ("a.py", f'def run(\n    x: int,\n) -> None:\n    """claude {FLAG}"""\n')])
def test_real_block_comments_and_docstrings_still_hide_a_flag(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel,text", [
    ("agent.py", f'subprocess.run([\n    *base, "{FLAG}"\n])\n'),
    ("agent.py", f'subprocess.run(\n    """\n    claude -p "x" {FLAG}\n    """, shell=True)\n'),
    ("agent.py", f'CMD = """\nclaude -p x {FLAG}\n"""\n'),
    ("run.sh", f"; claude {FLAG}\n"), ("run.sh", f"claude {FLAG} ;# done\n"),
    ("a.js", f'const args = [\n  *rest, "{FLAG}"];\n')])
def test_a_star_line_or_triple_quoted_argument_is_not_a_comment(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("rel,text", [("a.ini", f"; claude {FLAG}\n"), ("a.cfg", f"; claude {FLAG}\n"),
                                      ("a.bat", f"REM claude {FLAG}\n"), ("a.cmd", f":: claude {FLAG}\n")])
def test_comment_markers_still_apply_to_their_own_file_types(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel,text", [
    (".github/workflows/a.yml", f'on: push\njobs:\n  a:\n    steps:\n      - run: npx @anthropic-ai/claude-code {FLAG} "fix the tests"\n'),
    (".github/workflows/a.yml", 'on: push\njobs:\n  a:\n    steps:\n      - run: npx @google/gemini-cli --yolo "explain the code"\n'),
    ("package.json", json.dumps({"scripts": {"fix": f'npx @anthropic-ai/claude-code {FLAG} "fix the tests"'}})),
    ("package.json", json.dumps({"scripts": {"fix": f'claude-code {FLAG} "fix the tests"'}}))])
def test_an_agent_command_with_a_quoted_prompt_is_not_prose(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert len(rules(tmp_path)) == 1


@pytest.mark.parametrize("rel,text", [
    ("a.py", '["claude", "-p", "x", "--permission-mode", "bypassPermissions"]\n'),
    ("a.py", '["exec", "--sandbox", "danger-full-access"]\n'),
    ("a.ts", "['--permission-mode',\n  'bypassPermissions']\n"),
    ("a.yml", "args:\n  - --permission-mode\n  - bypassPermissions\n"),
    ("a.yml", "permission_mode: bypassPermissions\n"),
    ("a.toml", "sandbox_mode = danger-full-access\n"),
    ("run.sh", "codex exec -s danger-full-access 'fix'\n")])
def test_flag_and_value_split_across_list_items(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]
    assert "<" not in result(tmp_path).findings[0].detail


# --- Round 8 review -------------------------------------------------------------------------

def test_a_js_regex_literal_does_not_open_a_comment(tmp_path):
    """Finding 4: `/\\/*$/` is a regex, not the start of a block comment hiding what follows."""
    write(tmp_path, "agent.js", 'const base = url.replace(/\\/*$/, "");\n'
                                f'spawn("claude", ["{FLAG}", "-p", "x"]);\n')
    write(tmp_path, "agent.ts", 'const re = /a\\/*b/g; const n = x / 2;\n'
                                f'spawn("claude", ["{FLAG}"]);\n')
    assert rules(tmp_path) == ["AP01", "AP01"]


def test_an_unclosed_or_escaped_block_comment_hides_nothing(tmp_path):
    """Finding 4: an unterminated `/*` and a `\\/*` are not comments; nor is an unclosed docstring."""
    write(tmp_path, "a.go", f'cmd := exec.Command("claude", "{FLAG}")\nx := 1 /* never closed\n')
    write(tmp_path, "b.go", f'/* never closed\ncmd := exec.Command("claude", "{FLAG}")\n')
    write(tmp_path, "c.java", f'String p = a + \\/* x */ b;\nrun("claude", "{FLAG}");\n')
    write(tmp_path, "d.py", f'"""never closed\nimport os\nos.system("claude {FLAG} -p x")\n')
    assert rules(tmp_path) == ["AP01"] * 4


def test_a_block_comment_and_a_regex_still_hide_a_mention(tmp_path):
    write(tmp_path, "a.js", f'/* do not use {FLAG} */\nif (/{FLAG}/.test(arg)) refuse();\n')
    assert rules(tmp_path) == []


@pytest.mark.parametrize("name", ["UNSAFE_ARGS", "dangerousFlags", "DANGER_ARGS", "unguarded_args"])
def test_a_list_named_for_what_it_passes_is_not_a_deny_list(tmp_path, name):
    """Finding 5: `danger`/`unsafe` name the flags passed, not refused."""
    write(tmp_path, "agent.py", f'{name} = ["{FLAG}"]\nsubprocess.run(["claude", *{name}])\n')
    write(tmp_path, "agent.yml", f"danger_args:\n  - {FLAG}\n")
    assert rules(tmp_path) == ["AP01", "AP01"]


@pytest.mark.parametrize("name", ["BLOCKED_FLAGS", "denyList", "disallowed_args", "FORBIDDEN", "GUARDS",
                                  "blocklist", "rejected_flags"])
def test_a_list_named_as_blocked_is_a_deny_list(tmp_path, name):
    write(tmp_path, "agent.py", f'{name} = ["{FLAG}"]\n')
    write(tmp_path, "agent.yml", f"{name}:\n  - {FLAG}\n")
    assert rules(tmp_path) == []


def test_a_for_loop_list_is_passed_not_tested(tmp_path):
    """Skip-path audit: `for f in [...]` is not a membership test."""
    write(tmp_path, "agent.py", f'for f in ["{FLAG}", "-p"]:\n    args.append(f)\n')
    write(tmp_path, "check.py", f'if arg in ("--x", "{FLAG}"):\n    refuse()\n')
    assert rules(tmp_path) == ["AP01"]


def test_a_string_with_an_expansion_is_a_command_not_prose(tmp_path):
    """Skip-path audit: `$AGENT <flag> on the repo` reads like prose but runs an agent."""
    write(tmp_path, "run.sh", f'sh -c "$AGENT {FLAG} on the repo"\n')
    write(tmp_path, ".github/workflows/w.yml", f"jobs:\n  a:\n    steps:\n      - run: $AGENT {FLAG} on the repo\n")
    write(tmp_path, "cli.py", f'parser.add_argument("--x", help="never pass {FLAG} to the agent")\n')
    assert rules(tmp_path) == ["AP01", "AP02"]


def test_a_yaml_deny_list_is_recognised_past_two_hundred_lines(tmp_path):
    """Finding 18: the parent key is tracked with a stack, not a 200-line look-back."""
    items = "".join(f"  - --flag-{i}\n" for i in range(300))
    write(tmp_path, "policy.yml", f"blocked:\n{items}  - {FLAG}\nallowed:\n  - -p\n")
    write(tmp_path, "run.yml", f"blocked:\n  - --x\nargs:\n  - {FLAG}\n")
    assert [(f["file"], f["line"]) for f in report(tmp_path)["findings"]] == [("run.yml", 4)]


@pytest.mark.parametrize("name", ["Dockerfile.dev", "app.dockerfile", ".env.example", "Jenkinsfile", "Makefile",
                                  "justfile"])
def test_comments_follow_the_file_kind(tmp_path, name):
    """Finding 10: markers by file kind, not by Path.suffix."""
    marker = "//" if name == "Jenkinsfile" else "#"
    write(tmp_path, name, f"{marker} RUN claude {FLAG} -p x\n")
    assert rules(tmp_path) == []


def test_a_jenkinsfile_block_comment_and_hash_are_not_confused(tmp_path):
    write(tmp_path, "Jenkinsfile", f"/* sh 'claude {FLAG}' */\nsh 'claude -p x' # {FLAG}\n")
    assert [(f["rule"], f["line"]) for f in report(tmp_path)["findings"]] == [("AP02", 2)]


@pytest.mark.parametrize("text", [
    "with:\n  sandbox: danger-full-access\n",
    'const t = codex.startThread({ sandboxMode: "danger-full-access" });\n',
    "gemini -y -p 'fix the tests'\n",
    "npx @google/gemini-cli -y -p hi\n",
    "qwen -p hi -y\n",
])
def test_more_codex_and_gemini_full_access_spellings(tmp_path, text):
    """Finding 7."""
    write(tmp_path, "agent.yml" if text.startswith("with") else "agent.ts" if "const" in text else "run.sh", text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("text", ["npx -y @google/gemini-cli -p hi\n", "apt-get install -y curl\n",
                                  "npx -y some-tool && echo gemini\n"])
def test_a_short_y_that_is_not_gemini_s_does_not_count(tmp_path, text):
    write(tmp_path, "run.sh", text)
    assert rules(tmp_path) == []


def test_a_gated_flag_on_a_continued_line_counts(tmp_path):
    """Skip-path audit: `gemini -p x \\` then `--yolo` on the next line is one command."""
    write(tmp_path, "run.sh", "gemini -p 'fix' \\\n  --yolo\n")
    write(tmp_path, "other.sh", "echo hi\n  --yolo\n")
    assert [f["file"] for f in report(tmp_path)["findings"]] == ["run.sh"]
