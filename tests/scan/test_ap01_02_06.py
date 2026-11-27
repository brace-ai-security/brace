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
    assert [r for r, f in got if f == ".mcp.json" and r == "AP04"] == ["AP04"] * 4  # with docker image `i`
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
    write(tmp_path, "run.sh", f"claude -p 'say \\' #{FLAG}\n")  # single quotes have no escapes, but
    assert rules(tmp_path) == ["AP01"]  # round 12: a trailing comment after an agent command is not stripped
    write(tmp_path, "run.sh", f"echo 'say \\' #{FLAG}\n")
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
    ("guard.py", 'assert "--dangerously-skip-permissions" not in cmd\n'),
    ("guard2.py", 'if "--dangerously-skip-permissions" in cmd:\n    raise SystemExit(1)\n'),
    ("guard.ts", 'if (/--dangerously-skip-permissions/.test(cmd)) { throw new Error("no"); }\n'),
    ("policy.yml", 'blocked:\n  - "--dangerously-skip-permissions"\n  - "--yolo"\n'),
    ("deny.json", '{"deny": ["--dangerously-skip-permissions"]}\n'),
    ("block.js", "/* never use --dangerously-skip-permissions */\nrun();\n"),
])
def test_a_flag_only_mentioned_is_not_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == []


def test_the_mention_rule_is_documented():
    assert "only mentioned" in (TOOL_DIR / "SCAN-DETAILS.md").read_text(encoding="utf-8")


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


@pytest.mark.parametrize("name", ["FORBIDDEN", "blocklist", "deny", "BANNED", "disallowed", "rejected"])
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
    assert rules(tmp_path) == ["AP01", "AP01", "AP02"]  # help text is reported since round 10


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


@pytest.mark.parametrize("rel,text", [
    ("run.sh", "npm install -g @google/gemini-cli && sudo apt-get install -y jq\n"),
    ("Dockerfile", "FROM node:20\nRUN npm install -g @google/gemini-cli@0.9.0 \\\n    && apt-get update \\\n"
                   "    && apt-get install -y jq\n"),
    ("run.sh", "deno run --allow-all x.ts && codex exec 'fix'\n"),
    ("run.sh", "pip install qwen; python train.py --yolo\n"),
    ("run.sh", "npm install -g @github/copilot --allow-all\n"),
])
def test_round9_gated_flags_of_another_command_do_not_count(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert not {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    ("run.sh", "npm install -g @google/gemini-cli && gemini -y -p 'fix'\n"),
    ("run.sh", "sudo timeout 300 gemini --yolo -p fix\n"),
    ("run.sh", "OUT=$(gemini --yolo -p fix)\n"),
    ("agent.py", 'cmd = [\n    "gemini",\n    "--yolo",\n    "-p",\n    prompt,\n]\n'),
    (".github/workflows/w.yml", "jobs:\n  a:\n    steps:\n      - uses: openai/codex-action@v1\n        with:\n"
                                "          codex-args: '[\"--yolo\"]'\n"),
    (".github/workflows/w.yml", "jobs:\n  a:\n    steps:\n      - uses: google-github-actions/run-gemini-cli@v0\n"
                                "        with:\n          gemini_cli_args: --yolo\n"),
    ("agent.yml", "gemini_cli_args: --yolo\n"),
])
def test_round9_gated_flags_of_the_cli_still_count(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) in (["AP01"], ["AP02"])


@pytest.mark.parametrize("rel,text", [
    ("check.sh", f'if grep -q -- "{FLAG}" "$1"; then exit 1; fi\n'),
    ("check.sh", f'case "$arg" in\n  {FLAG}) echo "refused"; exit 1 ;;\nesac\n'),
    ("check.sh", f'case "$arg" in {FLAG}) exit 1 ;; esac\n'),
    ("check.sh", f'if [[ "$*" == *{FLAG}* ]]; then exit 1; fi\n'),
    ("check.sh", f'if [[ "$*" =~ {FLAG} ]]; then exit 1; fi\n'),
    ("check.sh", f'[ "$1" = "{FLAG}" ] && exit 1\n'),
    (".claude/settings.json", json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
        "type": "command", "command": f"jq -r .tool_input.command | grep -q -- '{FLAG}' && exit 2"}]}]}}, indent=2)),
    (".claude/settings.json", json.dumps({"permissions": {"ask": [f"Bash(claude {FLAG}:*)"]}}, indent=2)),
    (".claude/settings.json", json.dumps({"permissions": {"deny": [f"Bash(claude {FLAG}:*)"]}}, indent=2)),
])
def test_round9_guards_that_search_for_or_refuse_the_flag_are_mentions(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert not {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    ("run.sh", f'claude {FLAG} -p "never touch the tests" | grep -v noise\n'),
    ("run.sh", f'OUT=$(claude {FLAG} -p "fix")\n'),
    ("run.py", f'os.system("claude {FLAG} -p \'do not stop\'")\n'),
    ("run.sh", f'[[ -n "$CI" ]] && claude {FLAG} -p fix\n'),
    ("agent.json", json.dumps({"profiles": {"ci": {"permissions": {"defaultMode": "bypassPermissions"}}}}, indent=2)),
    (".devcontainer/devcontainer.json", json.dumps({"postCreateCommand": "echo '{\"permissions\":{\"defaultMode\":"
                                                   "\"bypassPermissions\"}}' > ~/.claude/settings.json"})),
    (".vscode/settings.json", json.dumps({"claudeCode.initialPermissionMode": "bypassPermissions"})),
    ("tox.ini", f"[testenv]\ncommands = sh -c cd repo ; claude {FLAG} -p x\n"),
    ("agent.py", f'const_guard_cmd = 1\nguard_cmd = ["claude", "{FLAG}"]\n'),
    ("agent.yml", f"blocks:\n  - run: claude {FLAG} -p x\n"),
])
def test_round9_passed_flags_are_still_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert {"AP01", "AP02"} & set(rules(tmp_path))


def test_round9_structural_and_inline_default_mode_report_once(tmp_path):
    write(tmp_path, ".claude/settings.json", json.dumps({"permissions": {"defaultMode": "bypassPermissions"}}, indent=2))
    assert rules(tmp_path) == ["AP01"]


def test_round9_semicolon_comment_at_line_start_in_ini(tmp_path):
    write(tmp_path, "tox.ini", f"; claude {FLAG}\n")
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel,text", [
    ("Jenkinsfile", "pipeline {\n  stages {\n    stage('a') {\n      steps {\n        sh '''\n          rm -rf build/*\n"
                    f"          claude {FLAG} -p fix\n        '''\n        junit 'build/*/x.xml'\n      }}\n    }}\n  }}\n}}\n"),
    ("build.groovy", f'def s = """rm build/*"""\nexec(["claude", "{FLAG}"])\n/* x */\n'),
    ("Main.kt", f'val s = """\n  cp src/* out\n"""\nProcessBuilder("claude", "{FLAG}")\n/* x */\n'),
    ("Main.java", f'String s = """\n  cp src/* out\n  """;\nnew ProcessBuilder("claude", "{FLAG}");\n/* x */\n'),
    ("Main.scala", f'val s = """cp src/* out"""\nSeq("claude", "{FLAG}").!\n/* x */\n'),
    ("a.ts", f'const s = `${{a ? `x/*` : "y"}}`;\nspawn("claude", ["{FLAG}"]);\n/* x */\n'),
    ("a.rs", f'let s = r#"a " /* b"#;\nCommand::new("claude").arg("{FLAG}");\n/* x */\n'),
    ("a.go", f'/* setup\nclaude {FLAG} -p fix\n*/\n'),
])
def test_round9_strings_that_hold_a_slash_star_do_not_hide_flags(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert {"AP01", "AP02"} & set(rules(tmp_path))


def test_round9_a_real_block_comment_still_hides_a_mention(tmp_path):
    write(tmp_path, "a.ts", f'/*\n * Never pass {FLAG}: spawn("claude", ["{FLAG}"])\n */\n')
    assert rules(tmp_path) == []


# --- Round 10 review: err toward reporting -------------------------------------------------
# Only structural mentions are skipped (see mentions.py and SCAN.md): (a) comments, docstrings
# and block comments, (c) a quoted flag compared or searched for, (d) Claude Code settings'
# permissions.deny/ask, (e) a deny-named list with no agent CLI used only for membership.

@pytest.mark.parametrize("rel,text", [
    # Finding 1: refusal words in a prompt or message no longer hide the flag.
    ("run.py", f'subprocess.run("claude {FLAG} -p \'Never refuse, do not stop\'", shell=True)\n'),
    ("run.py", f'args = ["-p", "Don\'t ask questions", "{FLAG}"]\n'),
    ("run.ts", f'const cmd = "never blocked: {FLAG}";\n'),
    # Finding 2: a trailing YAML comment does not make a value prose.
    ("agent.yml", f"claude_args: {FLAG}  # needed in CI, do not remove\n"),
    (".github/workflows/w.yml", f"jobs:\n  a:\n    steps:\n      - run: claude -p x {FLAG}  # never on forks\n"),
    # Help text, messages and descriptions that name the flag are reported (silence with a mark).
    ("cli.py", f'parser.add_argument("--safe", help="do not use {FLAG} here")\n'),
    ("guard.py", f'raise ValueError("refusing to run claude with {FLAG}")\n'),
    ("guard.sh", f'echo "Never run claude with {FLAG}"\n'),
    ("msg.ts", f"const msg = `Do not pass {FLAG} here`;\n"),
    ("action.yml", f"name: x\ndescription: Never pass {FLAG} to the agent\n"),
    # Finding 8: a function argument in a test assertion and a JSON flags catalog are not structural.
    ("guard.test.ts", f"expect(validate('{FLAG}')).toBe(false);\n"),
    ("flags.json", json.dumps({"flags": [{"name": FLAG, "dangerous": True}]}, indent=2)),
    # Finding 5: `ask` is a deny word only as a settings key; a list with an agent CLI is never a deny-list.
    ("ask.py", f"ask = ['claude', '{FLAG}', '-p', q]\n"),
    ("ask.ts", f"const ask = ['{FLAG}'];\nspawn('claude', ask);\n"),
    ("deny.py", f'DENY = ["claude", "{FLAG}"]\n'),
    ("blocked.py", f'BLOCKED = ["{FLAG}"]\nsubprocess.run(["claude", *BLOCKED])\n'),
    ("names.py", f'BLOCKED_FLAGS = ["{FLAG}"]\n'),
    ("policy.yml", f'blocked_flags:\n  - "{FLAG}"\n'),
    ("config.json", json.dumps({"permissions": {"deny": [f"Bash(claude {FLAG}:*)"]}}, indent=2)),
])
def test_round10_passed_or_ambiguous_flags_are_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    # (a)
    ("a.sh", f"# claude {FLAG}\n"), ("a.py", f'def f():\n    """Never pass {FLAG}."""\n'),
    ("a.ts", f"/* spawn('claude', ['{FLAG}']) */\n"),
    # (c)
    ("c.py", f'if arg == "{FLAG}":\n    sys.exit(2)\n'), ("c.py", f'if arg != "{FLAG}":\n    pass\n'),
    ("c.py", f'if "{FLAG}" in cmd:\n    sys.exit(2)\n'), ("c.py", f'assert "{FLAG}" not in cmd\n'),
    ("c.js", f'if (cmd.includes("{FLAG}")) process.exit(2);\n'), ("c.kt", f'if (cmd.contains("{FLAG}")) exit()\n'),
    ("c.ts", f"if (arg.startsWith('{FLAG}')) throw new Error('x');\n"),
    ("c.sh", f'grep -q -- "{FLAG}" "$1" && exit 1\n'), ("c.sh", f'case "$a" in\n  {FLAG}) exit 1 ;;\nesac\n'),
    ("c.js", f"switch (arg) {{\n  case '{FLAG}':\n    throw new Error('no');\n}}\n"),
    ("c.sh", f'[[ "$*" == *{FLAG}* ]] && exit 1\n'), ("c.ts", f"if (/{FLAG}/.test(cmd)) throw 1;\n"),
    # (d)
    (".claude/settings.json", json.dumps({"permissions": {"deny": [f"Bash(claude {FLAG}:*)"]}}, indent=2)),
    (".claude/settings.local.json", json.dumps({"permissions": {"ask": [f"Bash(claude {FLAG}:*)"]}})),
    ("settings.yaml", f'permissions:\n  deny:\n    - "Bash(claude {FLAG}:*)"\n'),
    # (e)
    ("e.py", f'BLOCKED = ["{FLAG}", "--yolo"]\nif any(f in cmd for f in BLOCKED):\n    sys.exit(2)\n'),
    ("e.py", f'FORBIDDEN = frozenset({{"{FLAG}"}})\nif arg in FORBIDDEN:\n    sys.exit(2)\n'),
    ("e.ts", f'const DENY = new Set(["{FLAG}"]);\nif (DENY.has(arg)) throw 1;\n'),
    ("e.js", f'const blocklist = ["{FLAG}"];\nif (blocklist.includes(arg)) throw 1;\n'),
    ("BAD.py", f'BANNED = ["{FLAG}"]\n'),
    ("e.json", json.dumps({"deny": [FLAG]})), ("e.yml", f"blocked:\n  - {FLAG}\n"),
])
def test_round10_structural_mentions_are_not_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert not {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    ("Dockerfile", "FROM node:20\nENTRYPOINT gemini --yolo\n"),
    ("Dockerfile", "FROM node:20\nCMD gemini --yolo -p fix\n"),
    ("Dockerfile", 'FROM node:20\nENTRYPOINT ["gemini", "--yolo"]\n'),
    ("run.sh", "op run -- gemini --yolo -p fix\n"), ("run.sh", "doppler run -- gemini --yolo\n"),
    ("run.sh", "dotenv -- gemini --yolo\n"), ("run.sh", "docker run --rm img gemini --yolo\n"),
    ("run.sh", "ssh box gemini --yolo\n"), ("run.sh", "find . -name '*.md' -exec gemini --yolo {} \;\n"),
    ("run.sh", "parallel gemini --yolo ::: a b\n"), ("run.sh", "xvfb-run gemini --yolo\n"),
    ("run.sh", "stdbuf -oL gemini --yolo\n"), ("run.sh", "script -q /dev/null gemini --yolo\n"),
    ("run.sh", "retry 3 gemini --yolo\n"), ("run.sh", 'gy() { gemini --yolo "$@"; }\n'),
    ("run.sh", "crush -y\n"), ("run.sh", "copilot -p fix --allow-all-tools 2>&1 | tee log\n"),
    ("agent.js", 'spawn("gemini", [\n  "--yolo",\n  "-p",\n  prompt,\n]);\n'),
    ("agent.js", "const args = ['-p', prompt];\nargs.push('--yolo');\nspawn('gemini', args);\n"),
    ("agent.py", 'args = ["-p", prompt]\nargs.append("--yolo")\nsubprocess.run(["qwen", *args])\n'),
    ("agent.json", json.dumps({"command": "gemini", "args": ["--yolo"]}, indent=2)),
    (".zed/settings.json", json.dumps({"agent_servers": {"g": {"command": "gemini", "args": ["--experimental-acp",
                                                                                           "--yolo"]}}}, indent=2)),
    ("agent.yml", "command: gemini\nargs: [--yolo]\n"),
    ("compose.yaml", "services:\n  agent:\n    image: x\n    command: gemini --yolo\n"),
    ("pod.yaml", "spec:\n  containers:\n    - name: a\n      image: x\n      command: [\"gemini\"]\n"
                 "      args:\n        - --yolo\n"),
    ("pod2.yaml", "spec:\n  containers:\n    - name: a\n      command:\n        - gemini\n      args: [\"-y\"]\n"),
    ("mcp.json", '{"x": ["npx","-y","@google/gemini-cli",\n "--yolo"]}\n'),
])
def test_round10_gated_flags_of_the_cli_are_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    ("run.sh", "npm install -g @google/gemini-cli && apt-get install -y jq\n"),
    ("Dockerfile", "FROM node:20\nRUN npm install -g @google/gemini-cli \\\n    && apt-get install -y --no-install-recommends jq\n"),
    ("package.json", json.dumps({"scripts": {"setup": "npm i -g @google/gemini-cli", "train": "python yolo.py --yolo"}})),
    ("run.sh", "brew install gemini-cli --yolo-mode\n"),
    ("pod.yaml", "spec:\n  containers:\n    - name: a\n      command: [\"gemini\"]\n    - name: b\n      command: [\"train\"]\n"
                 "      args: [\"--yolo\"]\n"),
])
def test_round10_gated_flags_of_another_command_are_not_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert not {"AP01", "AP02"} & set(rules(tmp_path))


def test_round10_the_reporting_bias_is_documented():
    doc = (TOOL_DIR / "SCAN-DETAILS.md").read_text(encoding="utf-8")
    assert "errs toward reporting" in doc and "open-agent-security: ignore" in doc


# --- Round 11 ---------------------------------------------------------------------------------
STEP = "jobs:\n  a:\n    runs-on: x\n    steps:\n"


@pytest.mark.parametrize("rel,text", [
    # 4: -y in an agent action's step belongs to npx or apt-get, not to the agent.
    (".github/workflows/w.yml", STEP + "      - uses: anthropics/claude-code-action@v1\n        with:\n          mcp_config: |\n"
     '            {"mcpServers":{"g":{"command":"npx","args":["-y","@modelcontextprotocol/server-github@1.2.3"]}}}\n'),
    (".github/workflows/w.yml", STEP + "      - uses: anthropics/claude-code-action@v1\n        with:\n"
     "          prompt: run apt-get install -y jq first\n"),
    (".github/workflows/w.yml", STEP + "      - uses: google-github-actions/run-gemini-cli@v0\n        with:\n          settings: |\n"
     '            {"mcpServers":{"g":{"command":"npx","args":["-y","x@1.0.0"]}}}\n'),
    (".github/workflows/w.yml", STEP + "      - uses: google-github-actions/run-gemini-cli@v0\n        with:\n"
     "          prompt: never pass --yolo here\n"),
    # 8: a path, file or flag value that equals a CLI name.
    ("run.sh", "deno run --allow-all examples/gemini.ts\n"),
    ("package.json", json.dumps({"scripts": {"gen": "deno run --allow-all scripts/copilot.ts"}})),
    ("run.sh", "python train.py --yolo --out codex/\n"),
    ("run.sh", "mytool --provider gemini -y\n"),
    ("run.sh", "mytool --provider=gemini --yolo\n"),
])
def test_round11_gated_flags_of_another_command_are_not_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert not {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    (".github/workflows/w.yml", STEP + "      - uses: google-github-actions/run-gemini-cli@v0\n        with:\n"
     "          gemini_cli_args: |\n            --yolo\n"),
    (".github/workflows/w.yml", STEP + "      - uses: openai/codex-action@v1\n        with:\n          args: --yolo\n"),
    ("run.sh", "/usr/local/bin/gemini --yolo -p fix\n"),
    ("run.sh", "gemini.exe --yolo\n"),
    ("run.sh", "npx -y @google/gemini-cli -y -p fix\n"),
])
def test_round11_gated_flags_of_the_agent_still_count(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert {"AP01", "AP02"} & set(rules(tmp_path))


@pytest.mark.parametrize("rel,text", [
    ("check.sh", f'case "$arg" in\n  {FLAG}) echo "refused"; exit 1 ;;\nesac\n'),
    ("check.sh", f'case "$a" in -h) usage ;; {FLAG}) exit 1 ;; esac\n'),
    (".github/workflows/w.yml", STEP + f'      - run: |\n          case "$ARGS" in\n            *{FLAG}*) exit 1 ;;\n'
                                       f'          esac\n'),
    ("check.sh", f'if grep -q -- "{FLAG}" "$1"; then exit 1; fi\n'),
    ("check.sh", f'x=$(grep -c -- {FLAG} run.log)\n'),
    ("check.sh", f'if [ "$1" = "{FLAG}" ]; then exit 1; fi\n'),
    ("Makefile", f'check:\n\ttest "$$FLAGS" != {FLAG}\n'),
])
def test_round11_structural_mentions_in_shell_are_still_mentions(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel,text", [
    # (c) shell forms only in shell: a case arm or test shape in another language counts.
    ("a.py", f'x = [\n"{FLAG}")\n'),
    # no `case ... in` open: a line-starting `--flag)` is not an arm
    ("run.sh", f'run_agent \\\n  {FLAG})\n'),
    ("run.sh", f'esac\n{FLAG})\n'),
    # the overriding rule: an agent CLI in the same call
    ("a.py", f'subprocess.run(["claude", "-p", q, "--", "grep", "{FLAG}"])\n'),
])
def test_round11_shell_shapes_elsewhere_are_reported(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert {"AP01", "AP02"} & set(rules(tmp_path))


def test_round11_an_agent_on_the_line_overrides_every_mention_form(tmp_path):
    write(tmp_path, "run.sh", f'case "$a" in\n  {FLAG}) claude -p hi ;;\nesac\ngrep -q -- {FLAG} log && claude -p fix\n')
    assert [f.line for f in result(tmp_path).findings] == [2, 4]


def test_round11_ansible_block_is_not_a_deny_list_but_blocked_still_is(tmp_path):
    write(tmp_path, "play.yml", f"- block:\n    - {FLAG}\n")
    assert rules(tmp_path) == ["AP01"]
    write(tmp_path, "play.yml", f"blocked:\n  - {FLAG}\nblocklist:\n  - {FLAG}\n")
    assert rules(tmp_path) == []
    write(tmp_path, "play.yml", f'blocked:\n  - shell: "x {FLAG}"\n')
    assert rules(tmp_path) == ["AP01"]


def test_round11_codex_full_access_is_read_from_the_parsed_toml(tmp_path):
    write(tmp_path, ".codex/config.toml", 'approval_policy = "never"\nsandbox_mode = """danger-full-access"""\n'
                                          '[profiles.ci]\nsandbox_mode = "danger-\\u0066ull-access"\n')
    found_ = result(tmp_path).findings
    assert [(f.rule, f.line, f.detail) for f in found_] == [
        ("AP01", 2, 'sandbox_mode = "danger-full-access" + approval_policy = "never"'),
        ("AP01", 4, 'profiles.ci.sandbox_mode = "danger-full-access"')]


@pytest.mark.parametrize("rel,text", [
    (".env", "CLAUDE_PERMISSION_MODE=bypassPermissions\n"),
    ("a.ts", 'const o = { claudePermissionMode: "bypassPermissions" };\n'),
    ("a.py", 'run(default_permission_mode="bypassPermissions")\n'),
    ("a.yml", "with:\n  permission-mode: bypassPermissions\n"),
    ("a.ts", 'q.setPermissionMode("bypassPermissions");\n'),
    ("a.py", 'MODE = "bypassPermissions"\nopts = Options(permission_mode=MODE)\n'),
    ("a.yml", 'env:\n  MODE: bypassPermissions\nrun: claude --permission-mode "$MODE" -p hi\n'),
    (".qwen/settings.json", json.dumps({"tools": {"approvalMode": "yolo"}})),
    ("a.py", 'approval_mode = "yolo"\n'),
    ("a.ts", 'const sandbox = "danger-full-access";\n'),
])
def test_round12_a_bypass_value_is_reported_whatever_its_key(tmp_path, rel, text):
    """Finding 2: a bypassPermissions or danger-full-access value, or approval mode yolo, on its own."""
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]


def test_round12_a_bypass_value_is_reported_once_per_flag(tmp_path):
    write(tmp_path, "a.py", '["claude", "--permission-mode", "bypassPermissions"]\nx = 1  # bypassPermissions\n')
    assert found(tmp_path) == [("AP01", '--permission-mode", "bypassPermissions')]
    write(tmp_path, ".claude/settings.json", json.dumps({"permissions": {"defaultMode": "bypassPermissions"}}))
    assert [f for f in found(tmp_path) if f[1] == "defaultMode: bypassPermissions"] == \
        [("AP01", "defaultMode: bypassPermissions")]


@pytest.mark.parametrize("rel,text", [
    ("a.py", f"subprocess.run('claude -p \\'fix #12\\' {FLAG}', shell=True)\n"),
    ("run.sh", f"ssh box 'claude -p '\\''fix #1'\\'' {FLAG}'\n"),
    ("a.js", f'execSync(`claude -p "x" // {FLAG}`)\n'),
    ("a.go", f'exec.Command("sh", "-c", `claude -p x // {FLAG}`)\n'),
    ("run.sh", f"claude -p hi # {FLAG}\n"),  # the safety rule: an agent command's trailing comment is kept
])
def test_round12_quotes_and_escapes_do_not_open_a_comment(tmp_path, rel, text):
    """Finding 3: escapes by file kind, backticks as quotes, and the agent-command safety rule."""
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("rel,text", [
    ("run.sh", f"# claude {FLAG}\n"),
    ("run.sh", f"echo hi # claude {FLAG}\n"),
    ("a.js", f"// claude {FLAG}\n"),
])
def test_round12_real_comments_still_hide_a_mention(tmp_path, rel, text):
    write(tmp_path, rel, text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel,text", [
    ("run.sh", 'npx https://github.com/google-gemini/gemini-cli --yolo -p "fix it"\n'),
    ("run.sh", 'GEMINI_FLAGS="--yolo"\ngemini $GEMINI_FLAGS -p go\n'),
    ("Makefile", "GEMINI_ARGS := --yolo\nfix:\n\tgemini $(GEMINI_ARGS)\n"),
    ("run.sh", "docker run --rm gemini-cli/sandbox:0.1.1 --yolo\n"),
    ("a.yml", "env:\n  QWEN_FLAGS: --yolo\n"),
    ("run.sh", "qwen-code --yolo -p hi\n"),
])
def test_round12_gemini_cli_forms_and_named_variables_gate_yolo(tmp_path, rel, text):
    """Finding 5."""
    write(tmp_path, rel, text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("text", ['FLAGS="--yolo"\n', "brew install gemini-cli && yolo --yolo\n",
                                  "python detect.py --yolo\n"])
def test_round12_yolo_without_a_gated_cli_stays_quiet(tmp_path, text):
    write(tmp_path, "run.sh", text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("text,detail", [
    ("amp --dangerously-allow-all -x hi\n", "--dangerously-allow-all"),
    ("cursor-agent -p --force 'fix'\n", "--force"),
    ("cursor-agent -p -f 'fix'\n", "-f"),
    ("aider --yes-always --message hi\n", "--yes-always"),
    ("copilot --allow-all-paths -p hi\n", "--allow-all-paths"),
    ("copilot --allow-all-tools -p hi\n", "--allow-all-tools"),
])
def test_round12_other_clis_bypass_flags(tmp_path, text, detail):
    """Finding 9: each flag beside its own CLI."""
    write(tmp_path, "run.sh", text)
    assert found(tmp_path) == [("AP01", detail)]


@pytest.mark.parametrize("text", ["cursor-agent --force\n", "git push --force\n", "rm -f x\n", "pip --yes-always\n"])
def test_round12_other_clis_flags_need_their_cli(tmp_path, text):
    write(tmp_path, "run.sh", text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("rel", [".claude/agents/deployer.md", ".claude/commands/ship.md", ".claude/skills/x/SKILL.md",
                                 ".gemini/commands/x.md"])
def test_round12_agent_markdown_frontmatter_is_config(tmp_path, rel):
    """Finding 6: the frontmatter of agent Markdown files is read; the body stays prose."""
    write(tmp_path, rel, "---\nname: x\npermissionMode: bypassPermissions\n---\nbypassPermissions in prose\n")
    assert found(tmp_path) == [("AP01", "permissionMode: bypassPermissions")]


def test_round12_agent_markdown_allowed_tools_is_ap06(tmp_path):
    write(tmp_path, ".claude/commands/a.md", "---\nallowed-tools: Bash(git add:*), Bash(*)\n---\nDo it\n")
    write(tmp_path, ".claude/commands/b.md", "---\nallowed-tools:\n  - Read\n  - Bash\n---\n")
    write(tmp_path, "docs/c.md", "---\nallowed-tools: Bash(*)\npermissionMode: bypassPermissions\n---\n")
    assert sorted(found(tmp_path)) == [("AP06", 'allowed-tools "Bash"'), ("AP06", 'allowed-tools "Bash(*)"')]
