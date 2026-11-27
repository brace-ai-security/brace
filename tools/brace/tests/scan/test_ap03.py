"""AP03: agent workflows triggered by pull_request_target."""

import pytest
from support import found, result, rules, write

GREETING = """on: pull_request_target
jobs:
  greet:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            const body = `Thanks!
            claude will run a review once a maintainer approves.`;
"""


PRT = "on:\n  pull_request_target:\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n"


def test_pull_request_target_with_agent(tmp_path):
    write(tmp_path, ".github/workflows/a.yml",
          "# pull_request_target is unsafe\non:\n  pull_request_target:\njobs:\n  r:\n    steps:\n"
          "      - uses: anthropics/claude-code-action@v1\n")
    write(tmp_path, ".github/workflows/b.yml", "on:\n  pull_request_target:\njobs:\n  r:\n    steps:\n      - run: make\n")
    write(tmp_path, ".github/workflows/c.yml", "# pull_request_target\non: [pull_request]\njobs:\n  r:\n    steps:\n"
          "      - uses: anthropics/claude-code-action@v1\n")
    found = result(tmp_path).findings
    assert [(f.rule, f.file, f.line) for f in found] == [("AP03", ".github/workflows/a.yml", 3)]


@pytest.mark.parametrize("step", [
    "uses: anthropics/claude-code-security-review@main",
    "run: npx -y @anthropic-ai/claude-code -p review",
    'run: claude --model opus -p "review this PR"',
    'run: cursor-agent -p "review"',
])
def test_more_agent_steps_on_pull_request_target(tmp_path, step):
    write(tmp_path, ".github/workflows/a.yml", f"on:\n  pull_request_target:\njobs:\n  r:\n    steps:\n      - {step}\n")
    assert rules(tmp_path) == ["AP03"]


@pytest.mark.parametrize("step", ["- name: Build AMP pages and run the validator\n        run: make",
                                  "- name: Codex docs should not run on forks\n        run: make",
                                  "# claude -p review\n      - run: make"])
def test_words_in_step_names_are_not_agent_steps(tmp_path, step):
    write(tmp_path, ".github/workflows/a.yml", f"on:\n  pull_request_target:\njobs:\n  r:\n    steps:\n      {step}\n")
    assert rules(tmp_path) == []


def test_nested_workflow_gets_ap03(tmp_path):
    write(tmp_path, "svc/.github/workflows/t.yml",
          "on:\n  pull_request_target:\njobs:\n  a:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n")
    assert "AP03" in {r for r, _ in found(tmp_path)}


def test_prose_in_a_script_body_is_not_an_agent_step(tmp_path):
    write(tmp_path, ".github/workflows/greet.yml", GREETING)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("step", [
    "      - run: |\n          echo start\n          claude -p \"review\" --output-format json\n",
    "      - name: review\n        run: >\n          claude --print hi\n",
    "      - run: echo a && claude -p hi\n",
])
def test_agent_cli_in_run_blocks_is_an_agent_step(tmp_path, step):
    write(tmp_path, ".github/workflows/a.yml", "on: pull_request_target\njobs:\n  a:\n    steps:\n" + step)
    assert rules(tmp_path) == ["AP03"]


def test_run_block_ends_at_its_indentation(tmp_path):
    text = ("on: pull_request_target\njobs:\n  a:\n    steps:\n      - run: |\n          echo hi\n"
            "      - uses: actions/github-script@v7\n        with:\n          script: |\n"
            "            claude will run a review later.\n")
    write(tmp_path, ".github/workflows/a.yml", text)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("step", ['      - run: copilot -p "review this PR" --allow-all-tools\n',
                                  "      - uses: sst/opencode/github@latest\n",
                                  '      - run: crush run "fix it"\n'])
def test_more_agents_in_pull_request_target_workflows(tmp_path, step):
    write(tmp_path, ".github/workflows/w.yml", PRT + step)
    assert "AP03" in rules(tmp_path)


def test_every_cataloged_cli_is_an_agent_step():
    from open_agent_security import agents
    from open_agent_security.parse.workflow import agent_step
    for name in agents.CLIS:
        assert agent_step(f"steps:\n  - run: {name} -p hi\n"), name


@pytest.mark.parametrize("step", [
    "      - run: timeout 300 claude -p 'review'\n",
    "      - run: timeout --signal=KILL 5m claude -p 'review'\n",
    "      - run: |\n          ANTHROPIC_API_KEY=$KEY claude -p 'review'\n",
    "      - run: |\n          if ! claude -p 'review'; then exit 1; fi\n",
    "      - run: sudo -E env A=1 claude --print 'review'\n",
    "      - run: npx -y codex exec 'review'\n",
    "      - run: gemini 'review this PR'\n",
    "      - run: |\n          nohup qwen \"review this PR\"\n",
    "      - uses: google-gemini/gemini-cli-action@v1\n"])
def test_an_agent_behind_a_prefix_or_with_a_positional_prompt(tmp_path, step):
    write(tmp_path, ".github/workflows/a.yml", PRT + step)
    assert rules(tmp_path) == ["AP03"]


@pytest.mark.parametrize("step", ["      - run: echo 'timeout 300 claude'\n", "      - run: gemini --version\n",
                                  "      - run: timeout 300 make test\n"])
def test_prefixes_alone_do_not_make_an_agent_step(tmp_path, step):
    write(tmp_path, ".github/workflows/a.yml", PRT + step)
    assert rules(tmp_path) == []


@pytest.mark.parametrize("step", [
    'run: |\n          claude \\\n            --model opus \\\n            -p "$PROMPT"',
    'run: |\n          claude --model opus --output-format json \\\n            --print "review"',
    'run: >\n          claude --model opus\n          -p "review this PR"',
    "run: cat prompt.txt | claude --dangerously-skip-permissions",
    "uses: anomalyco/opencode/github@latest",
])
def test_round9_agent_steps_split_over_lines_or_piped(tmp_path, step):
    write(tmp_path, ".github/workflows/a.yml", PRT + f"      - {step}\n")
    assert "AP03" in rules(tmp_path)


def test_round9_copilot_language_server_is_not_an_agent_package(tmp_path):
    write(tmp_path, ".github/workflows/a.yml", PRT + "      - run: npm install -g @github/copilot-language-server\n")
    assert rules(tmp_path) == []


def test_round9_trailing_comment_on_the_on_line_is_not_a_trigger(tmp_path):
    write(tmp_path, ".github/workflows/a.yml", "on: pull_request   # deliberately not pull_request_target\njobs:\n"
          "  a:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n")
    assert rules(tmp_path) == []


ACTION = "runs:\n  using: composite\n  steps:\n    - run: claude -p review\n      shell: bash\n"


def test_round11_an_agent_in_a_local_action_or_reusable_workflow_is_followed(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", PRT + "      - uses: ./.github/actions/outer\n")
    write(tmp_path, ".github/actions/outer/action.yaml", "runs:\n  using: composite\n  steps:\n"
                                                         "    - uses: ./.github/actions/inner\n")
    write(tmp_path, ".github/actions/inner/action.yml", ACTION)
    assert [(f.rule, f.line, f.detail) for f in result(tmp_path).findings] == [
        ("AP03", 2, "pull_request_target + agent step in ./.github/actions/outer")]


def test_round11_local_uses_are_followed_at_most_three_levels_and_only_when_they_exist(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", PRT + "      - uses: ./.github/actions/a1\n      - uses: ./missing\n")
    for i in range(1, 4):
        write(tmp_path, f".github/actions/a{i}/action.yml", f"runs:\n  steps:\n    - uses: ./.github/actions/a{i + 1}\n")
    write(tmp_path, ".github/actions/a4/action.yml", ACTION)
    assert rules(tmp_path) == []
    write(tmp_path, ".github/actions/a3/action.yml", ACTION)
    assert rules(tmp_path) == ["AP03"]


def test_round11_a_nested_project_resolves_local_uses_from_its_own_root(tmp_path):
    write(tmp_path, "sub/.github/workflows/w.yml", PRT + "      - uses: ./.github/actions/r\n")
    write(tmp_path, "sub/.github/actions/r/action.yml", ACTION)
    write(tmp_path, ".github/workflows/w.yml", PRT + "      - uses: ./.github/actions/x\n")
    write(tmp_path, ".github/actions/x/action.yml", "runs:\n  steps:\n    - run: echo hi\n")
    assert [(f.rule, f.file) for f in result(tmp_path).findings] == [("AP03", "sub/.github/workflows/w.yml")]


def test_round11_a_direct_agent_step_is_reported_once(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", PRT + "      - run: claude -p hi\n      - uses: ./.github/actions/r\n")
    write(tmp_path, ".github/actions/r/action.yml", ACTION)
    assert rules(tmp_path) == ["AP03"]
