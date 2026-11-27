"""Linear time and bounded memory on adversarial input."""
import importlib
import json
import pkgutil
import re
import time
import tracemalloc
from pathlib import Path

import pytest
from support import AGENT, FLAG as FLAG_TEXT, PLAIN, TUNED, config, fast, found, report, result, rules, write

import open_agent_security
from open_agent_security.catalog import RULES
from open_agent_security.ignore import IGNORE_FILE, load_ignores
from open_agent_security.jsonc import JsonLines
from open_agent_security.secrets import DEFAULT


def module_patterns():
    pkg = Path(open_agent_security.__file__).parent
    for info in pkgutil.walk_packages([str(pkg)], "open_agent_security."):
        if info.name.endswith("__main__"):
            continue
        mod = importlib.import_module(info.name)
        for name, val in vars(mod).items():
            if isinstance(val, re.Pattern):
                yield f"{info.name}.{name}", val
    yield "secrets.DEFAULT.any", DEFAULT.any


ADVERSARIAL = [" " * 20_000, "\t" * 20_000, " \t" * 10_000, "a" * 20_000, "0" * 20_000, "-" * 20_000,
               ":" * 20_000, "#" * 20_000, "<" * 20_000, "\"'" * 10_000, "/" * 20_000, "@" * 20_000,
               *(tok * (20_000 // len(tok)) for tok in (
                   "run: ", "run:| ", "claude ", "claude -p", "gemini --yolo ", "-p ", "--yolo ", "a://", "a:b@",
                   "pull_request_target ", "pull_request_target: ", "on: ", "- ", "\"pull_request_target\" ",
                   "sk-", "ghp_", "Bearer ", "eyJa", "FROM ", "<<EOF ", "<<-'", "--permission-mode ",
                   "permission_mode: ", "\\\"", "AP01 ", "mcp", "${", "x" * 9 + " "))]


def test_large_dockerfile_is_fast_and_line_is_right(tmp_path):
    write(tmp_path, ".mcp.json", AGENT)
    write(tmp_path, "Dockerfile", "\n" * 200000 + "FROM python:3.12\n")
    start = time.process_time()
    found = result(tmp_path).findings
    assert time.process_time() - start < 5
    assert [(f.rule, f.line) for f in found] == [("AP10", 200001)]


@pytest.mark.parametrize("make", [
    lambda: ("w.yml", "on: x\n" + " " * 900_000 + "\nrun: claude -p hi\n"),
    lambda: (".mcp.json", json.dumps({"mcpServers": {"s": {"command": "node", "env": {"K": "eyJ" * 300_000}}}})),
    lambda: (".mcp.json", json.dumps({"mcpServers": {"s": {"command": "docker", "args": ["--mount=" * 120_000]}}})),
    lambda: (".mcp.json", json.dumps({"mcpServers": {f"s{i}": {"command": "npx", "args": [f"p{i}"]} for i in range(20000)}})),
])
def test_adversarial_files_scan_fast(tmp_path, make):
    rel, text = make()
    rel = ".github/workflows/" + rel if rel.endswith(".yml") else rel
    write(tmp_path, rel, text)
    start = time.process_time()
    result(tmp_path)
    assert time.process_time() - start < 10


def test_adversarial_ignore_pattern_is_fast(tmp_path):
    write(tmp_path, "a" * 60 + ".sh", "claude --dangerously-skip-permissions\n")
    write(tmp_path, IGNORE_FILE, "*a" * 14 + "*b\n")
    start = time.process_time()
    assert rules(tmp_path) == ["AP01"]
    assert time.process_time() - start < 2


@pytest.mark.parametrize("make", [
    lambda: ("snap.json", json.dumps({"snapshot": json.dumps({f"k{i}": "v" * 20 for i in range(30000)})})),
    lambda: ("q.json", json.dumps({"x": '"' * 500_000})),
    lambda: ("many.sh", "gemini --yolo\n" * 150_000),
])
def test_round3_adversarial_files_are_fast(tmp_path, make):
    rel, text = make()
    write(tmp_path, rel, text)
    start = time.process_time()
    result(tmp_path)
    assert time.process_time() - start < 10


def test_large_ignore_file_and_deep_tree_are_fast(tmp_path):
    for i in range(300):
        write(tmp_path, f"a/b/c/d/e/f/g/h/{i}.sh", "echo\n")
    write(tmp_path, IGNORE_FILE, "\n".join(f"*x{i}*y*" for i in range(1000)) + "\n")
    start = time.process_time()
    result(tmp_path)
    assert time.process_time() - start < 10


def test_many_flags_after_a_long_line_are_linear(tmp_path):
    line = "echo " + "a" * 50_000 + " # " + "--dangerously-skip-permissions " * 1500
    write(tmp_path, "x.sh", line + "\n")
    assert fast(lambda: found(tmp_path)) == []


@pytest.mark.parametrize("line", ["- run:" + " " * 40_000 + "x", "pull_request_target" + " " * 40_000 + "x",
                                  "- run: |" + " \t" * 20_000 + "x"])
def test_long_workflow_lines_are_linear(tmp_path, line):
    write(tmp_path, ".github/workflows/w.yml", "on: push\njobs:\n  a:\n    steps:\n    " + line + "\n")
    fast(lambda: found(tmp_path))


def grows_linearly(rx: re.Pattern, texts: list[str], reps: int = 3) -> bool:
    """Whether searching inputs four times longer takes well under sixteen times as long.

    CPU time (process_time) ignores other processes, the two sizes are timed in turn and the
    best of `reps` runs kept, so a loaded machine slows both alike. A linear pattern grows about
    fourfold and a quadratic one sixteenfold; the ratio allowed is ten, plus an absolute floor so
    timer noise on fast patterns cannot fail it."""
    def seconds(inputs):
        start = time.process_time()
        for text in inputs:
            for s in (text, text + "!", "x" + text + "\n" + text):
                rx.search(s)
        return time.process_time() - start
    quarter = [text[:len(text) // 4] for text in texts]
    small = large = float("inf")
    for _ in range(reps):
        small, large = min(small, seconds(quarter)), min(large, seconds(texts))
    return large < 10 * small + 0.05


@pytest.mark.parametrize("name,rx", list(module_patterns()), ids=lambda v: v if isinstance(v, str) else "")
def test_every_module_regex_is_linear(name, rx):
    assert grows_linearly(rx, ADVERSARIAL), name


def test_the_linearity_check_catches_a_quadratic_regex():
    """The negative control: a pattern that rescans the rest of the input from every position."""
    # 24,000 characters so the quarter-size run is well above the 0.05 s floor: at 12,000 the
    # floor nearly absorbed the quadratic growth and the control flaked on a CI runner.
    assert not grows_linearly(re.compile(r"[ \t]*!x"), [" " * 24_000], reps=3)


LITERAL_WORD = re.compile(r"[A-Za-z_][\w-]{1,30}")
BUDGET_PER_KB = 0.5 / 64  # seconds of CPU per KB of adversarial input: 0.5 s for a 64 KB line


def own_alphabet(rx: re.Pattern, size: int) -> list[str]:
    """Adversarial lines built from a pattern's own literal words (`env`, `claude`, `run`) and
    flag-like fragments (`--a --b --c`), after each separator the pattern names (`;`, `|`, `:`),
    so a pattern that tries many ways to match the same text inside a repeat is driven to it."""
    src = rx.pattern.replace("\\", " ")
    words = sorted({w for w in LITERAL_WORD.findall(src)})
    heads = [""] + [c + " " for c in ";&|:=(\"'/<@#$" if c in src]
    bodies = [w + " --a --b --c " for w in words] + [" ".join(words) + " ", "--a --b --c ", "-a=b -c "]
    return [h + b * (size // len(b)) + "\x00" for h in heads for b in bodies]


TEXTS_PER_SHARD = 8  # own_alphabet lines per test, so a pattern with a large alphabet spreads over workers


def constant_cases():
    for name, rx in module_patterns():
        if isinstance(rx.pattern, str):
            count = len(own_alphabet(rx, 1))
            shards = -(-count // TEXTS_PER_SHARD)
            for shard in range(shards):
                yield pytest.param(name, rx, shard, shards, id=name if shards == 1 else f"{name}-{shard + 1}of{shards}")


@pytest.mark.parametrize("name,rx,shard,shards", list(constant_cases()))
def test_every_module_regex_has_a_small_constant(name, rx, shard, shards):
    """Linear is not enough: a pattern can be linear with a huge constant (8**6 ways to match a
    workflow prefix per failed attempt took 93 s on 40 KB). Each adversarial line from the
    pattern's own alphabet must be searched within BUDGET_PER_KB, first at 4 KB (so a bad
    pattern fails in seconds, not hours) and then at 64 KB. A pattern with many lines is split
    into shards (every `shards`-th line from `shard`), which together cover every line."""
    for kb in (4, 64):
        for text in own_alphabet(rx, kb * 1024)[shard::shards]:
            start = time.process_time()
            rx.search(text)
            assert time.process_time() - start < kb * BUDGET_PER_KB + 0.02, (name, text[:60])


def test_the_constant_check_catches_a_slow_linear_regex():
    """The negative control: round 8's workflow prefix, `-{1,2}[\\w=-]{1,30}` matching `--a` two ways."""
    slow = re.compile(r";[ \t]{0,20}(?:(?:env)(?:[ \t]{1,20}-{1,2}[\w=-]{1,30}){0,3}[ \t]{1,20}){0,6}claude")
    text = own_alphabet(slow, 4 * 1024)
    start = time.process_time()
    for t in text:
        slow.search(t)
    assert time.process_time() - start > 4 * BUDGET_PER_KB


INLINE_REGEX = re.compile(r"\bre\.(?:search|match|findall|finditer|split|sub|fullmatch)\(\s*[rbuf]{0,2}[\"']")


def test_no_regex_is_written_inline():
    """Every pattern is a module-level constant, so test_every_module_regex_is_linear sees it."""
    pkg = Path(open_agent_security.__file__).parent
    inline = [f"{p.relative_to(pkg)}:{n}" for p in sorted(pkg.rglob("*.py"))
              for n, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1) if INLINE_REGEX.search(line)]
    assert inline == []


@pytest.mark.parametrize("server", [{"name": "x" * 40_000, "command": "node"},
                                    {"name": "s", "command": "npx", "args": ["-y", "a" * 40_000]},
                                    {"name": "s", "command": "docker", "args": ["run", "a/" + "b" * 40_000]}])
def test_lethal_combination_words_are_linear_on_long_names(tmp_path, server):
    entry = {k: v for k, v in server.items() if k != "name"}
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {server["name"]: entry, "fetch": {"command": "node"}}}))
    fast(lambda: result(tmp_path), 3.0)


def test_hostile_ignore_patterns_are_fast(tmp_path):
    for i in range(40):
        write(tmp_path, f"d/{'a' * 236}{i:03d}.sh", "echo\n")
    write(tmp_path, IGNORE_FILE, "\n".join(f"*{'a' * 100}b{i}" for i in range(1000)) + "\n")
    fast(lambda: found(tmp_path), 5.0)
    assert len(load_ignores(tmp_path)[0]) == 200


def test_deep_json_index_memory_is_bounded():
    depth, keys = 400, 80_000
    text = '{"a":' * depth + "{" + ",".join(f'"k{i}":1' for i in range(keys)) + "}" + "}" * depth
    tracemalloc.start()
    JsonLines(text).at(("a",) * 3)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert peak < 50 * 1024 * 1024


def test_worst_case_globs_on_a_deep_tree_are_fast(tmp_path):
    for i in range(2000):
        write(tmp_path, f"a{i % 5}/b{i % 7}/c{i % 3}/d{i % 4}/e{i % 10}/f{i}.sh", "echo\n")
    lines = [f"{TUNED}/*{i}x" for i in range(100)] + [f"{PLAIN}/*{i}x" for i in range(100)]
    write(tmp_path, IGNORE_FILE, "\n".join(lines) + "\n")
    every = [r.id for r in RULES][:5]
    config(tmp_path, {
        "ignore": [{"path": f"{PLAIN}/*{i}y", "rules": every} for i in range(200)],
        "include": [f"{PLAIN}/*{i}z" for i in range(200)],
        "agent-config": [f"{PLAIN}/*{i}w" for i in range(200)]})
    start = time.process_time()
    r = report(tmp_path)
    assert time.process_time() - start < 6.0
    assert r["findings"] == [] and any("past the limit of 400 segments" in n for n in r["notes"])


def traced_peak(fn):
    """(fn's result, the peak bytes Python allocated while it ran)."""
    tracemalloc.start()
    try:
        out = fn()
        return out, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def peak_growth(tmp_path, rel: str, body: str, few: int, many: int, scan=report, also: dict = {}):
    """Scans of `few` and then `many` copies of a file: (both results, the extra peak memory
    the extra copies cost). A scan that keeps each file (or anything as large) until the end
    grows by at least the size of the extra copies; one that lets each file go stays flat."""
    out = []
    for n in (few, many):
        root = tmp_path / f"n{n}"
        for i in range(n):
            write(root, f"d{i}/{rel}", body)
        for other, text in also.items():
            write(root, other, text)
        out.append(traced_peak(lambda: scan(root)))
    (r_few, peak_few), (r_many, peak_many) = out
    return r_few, r_many, peak_many - peak_few


def retain_parsed_files(monkeypatch):
    """The negative control for the memory tests: each parsed file kept to the end of the scan,
    as the scanner did before round 6."""
    from open_agent_security import engine
    kept, real = [], engine.parse_file
    monkeypatch.setattr(engine, "parse_file", lambda *a: kept.append(real(*a)) or kept[-1])


DOCKERFILE = "FROM a\n" * 60_000  # 420 KB and more than 100 unpinned images


@pytest.mark.parametrize("control", [False, True], ids=["scanner", "negative-control"])
def test_many_large_dockerfiles_stay_within_memory(tmp_path, monkeypatch, control):
    """Peak memory does not grow with the number of files: four Dockerfiles cost no more than
    one. The negative control keeps each parsed file and must fail the same bound."""
    if control:
        retain_parsed_files(monkeypatch)
    start = time.process_time()
    few, many, growth = peak_growth(tmp_path, "Dockerfile", DOCKERFILE, 1, 4, also={".mcp.json": "{}\n"})
    assert time.process_time() - start < 10
    assert (growth < 3 * len(DOCKERFILE) // 2) is not control, growth
    for r, n in ((few, 1), (many, 4)):
        assert r["incomplete"] is True  # each file has more than 100 unpinned images
        assert sum(f["rule"] == "AP10" for f in r["findings"]) == n * 100


MCP_BODY = json.dumps({"mcpServers": {"big": {"command": "node", "args": [f"a{i:05}" for i in range(8_000)]}}})


@pytest.mark.parametrize("control", [False, True], ids=["scanner", "negative-control"])
def test_many_large_mcp_configs_stay_within_memory(tmp_path, monkeypatch, control):
    """Each file's parsed arguments used to stay in memory to the end of the scan (12 files of
    800 KB peaked at about 72 MB). Now four files cost no more than one; the negative control
    keeps each parsed file and must fail the same bound."""
    if control:
        retain_parsed_files(monkeypatch)
    few, many, growth = peak_growth(tmp_path, "mcp.json", MCP_BODY, 1, 4)
    # Measured: the scanner grows about 0.6x one file (up to ~1.5x with garbage-collection timing
    # on Python 3.14); the control grows about 24x. A 6x bound keeps a 4x margin on both sides.
    assert (growth < 6 * len(MCP_BODY)) is not control, growth
    assert few["incomplete"] is False and many["incomplete"] is False


def huge_name_body(name_length: int) -> str:
    env = {f"T{i}": "ghp_" + f"{i:04d}" + "a" * 32 for i in range(100)}
    return json.dumps({"mcpServers": {"n" * name_length: {"command": "node", "env": env}}}, indent=0)  # a line per key


@pytest.mark.parametrize("control", [False, True], ids=["scanner", "negative-control"])
def test_files_with_huge_server_names_and_many_secrets_stay_within_memory(tmp_path, monkeypatch, control):
    """One 1 MB file used to peak at about 650 MB: every finding kept the whole server name to
    the end of the scan. Findings are now finalized as they are accepted and names cut at
    parse, so four files with 100 KB names and 100 secrets each stay under 4 MB. The negative
    control undoes both (no cut, and every finding kept as found until the end of the scan) and
    must fail the same bound."""
    from open_agent_security import engine
    from open_agent_security.parse import mcp_json
    if control:
        monkeypatch.setattr(mcp_json, "MAX_VALUE", 10 ** 9)
        kept, real = [], engine.finalize
        monkeypatch.setattr(engine, "finalize", lambda f, *a: kept.append(f) or real(f, *a))
    body = huge_name_body(100_000)
    for i in range(4):
        write(tmp_path, f"d{i}/.mcp.json", body)
    r, peak = traced_peak(lambda: result(tmp_path))
    assert sum(f.rule == "AP05" for f in r.findings) >= 4 * 90  # details match after the cut, so lines tell them apart
    assert (peak < 4 * 1024 * 1024) is not control, peak


# The original, full-size runs of the three memory tests above: minutes under tracemalloc, so
# they run nightly (-m slow); the fast versions above prove the same bounds by growth.
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_slow_many_large_dockerfiles_stay_within_memory(tmp_path):
    body = "FROM a\n" * (1024 * 1024 // 7 - 1)
    for i in range(8):
        write(tmp_path, f"d{i}/Dockerfile", body)
    write(tmp_path, ".mcp.json", "{}\n")
    r, peak = traced_peak(lambda: report(tmp_path))
    assert peak < 60 * 1024 * 1024
    assert r["incomplete"] is True
    assert sum(f["rule"] == "AP10" for f in r["findings"]) == 8 * 100


@pytest.mark.slow
@pytest.mark.timeout(600)
def test_slow_many_large_mcp_configs_stay_within_memory(tmp_path):
    body = json.dumps({"mcpServers": {"big": {"command": "node", "args": [f"a{i:05}" for i in range(95_000)]}}})
    assert len(body) > 800_000
    for i in range(12):
        write(tmp_path, f"d{i}/mcp.json", body)
    r, peak = traced_peak(lambda: report(tmp_path))
    assert r["incomplete"] is False
    assert peak < 30 * 1024 * 1024


@pytest.mark.slow
@pytest.mark.timeout(600)
def test_slow_files_with_huge_server_names_and_many_secrets_stay_within_memory(tmp_path):
    body = huge_name_body(990_000)
    assert len(body) < 1024 * 1024
    for i in range(10):
        write(tmp_path, f"d{i}/.mcp.json", body)
    r, peak = traced_peak(lambda: result(tmp_path))
    assert sum(f.rule == "AP05" for f in r.findings) >= 900
    assert peak < 40 * 1024 * 1024


def test_inline_marks_are_kept_only_for_files_with_project_facts(tmp_path):
    from open_agent_security import engine
    kept = {}
    real = engine.run_project_checks
    write(tmp_path, "a.sh", "echo x  # open-agent-security: ignore\n")
    write(tmp_path, "Dockerfile", "FROM node:20  # open-agent-security: ignore\n")
    write(tmp_path, ".mcp.json", AGENT)

    def spy(ctx):
        kept.update(ctx.marks)
        return real(ctx)
    engine.run_project_checks = spy
    try:
        r = result(tmp_path)
    finally:
        engine.run_project_checks = real
    assert set(kept) == {"Dockerfile"} and r.findings == [] and r.tally.by_mark == 1


@pytest.mark.parametrize("text", ['run("claude ' + FLAG_TEXT + '")\n' + '"' * 300_000 + '\n',
                                  FLAG_TEXT + "\n" + ('"""' + " " * 300 + '"""') * 1500 + "\n"])
def test_long_lines_of_triple_quotes_are_linear(tmp_path, text):
    """Finding 3: each triple quote rescanned its line from the start (400 KB took 29 s)."""
    write(tmp_path, "a.py", text)
    fast(lambda: found(tmp_path))


DOTTED_KEY = ".".join(["a"] * 40_000) + " = 1\n"  # 80 KB: tomllib (3.11-3.13) took 14 s CPU on it


def test_round9_long_dotted_toml_key_in_codex_config_is_fast_and_incomplete(tmp_path):
    write(tmp_path, ".codex/config.toml", DOTTED_KEY)
    r = fast(lambda: report(tmp_path))
    assert r["incomplete"] is True


def test_round9_long_dotted_toml_key_in_config_file_is_fast_and_refused(tmp_path):
    from support import cli_run
    config(tmp_path, DOTTED_KEY)
    code, _, err = fast(lambda: cli_run(tmp_path))
    assert code == 2 and "not valid TOML" in err


@pytest.mark.parametrize("text", [".".join(["a"] * 65) + " = 1\n", "x = " + "[" * 200 + "]" * 200 + "\n", "x = \"" + "a" * 70_000 + "\"\n"])
def test_round9_deep_or_long_toml_is_refused(tmp_path, text):
    write(tmp_path, ".codex/config.toml", text)
    assert fast(lambda: report(tmp_path))["incomplete"] is True


@pytest.mark.parametrize("unit", ["--yolo " * 20 + "\\\n", "gemini " + "--yolo " * 20 + "\\\n", "gemini " + "-y " * 20 + "\\\n"])
def test_round10_dense_gated_flags_over_continued_lines_are_linear(tmp_path, unit):
    """Finding 4: each gated flag rescanned up to 4,000 characters of its command (388 KB took
    40 s). Separators and CLI positions are now computed once per file; four times the input
    must take well under sixteen times the CPU time."""
    def seconds(reps):
        root = tmp_path / str(reps)
        write(root, "run.sh", unit * reps)
        start = time.process_time()
        found(root)
        return time.process_time() - start
    small = min(seconds(300), seconds(300))
    assert seconds(1200) < 10 * small + 0.2


def scan_cpu(tmp_path, rel: str, text: str) -> float:
    write(tmp_path, rel, text)
    start = time.process_time()
    result(tmp_path)
    return time.process_time() - start


@pytest.mark.parametrize("rel,unit", [
    # case arms, `case ... in` lines and continued lines: open_cases, case_arm and logical commands
    ("a.sh", f'case "$a" in\n  {FLAG_TEXT}) x ;;\n  y \\\n  {FLAG_TEXT})\n'),
    # flags in one unclosed call: the overriding rule searches each bracket once
    ("a.py", f'run(\n  "{FLAG_TEXT}",\n  [ "x" ], "{FLAG_TEXT}",\n'),
    # block scalars and run keys: yaml_blocks
    ("w.yml", f'- run: |\n    case $x in\n      {FLAG_TEXT}) exit ;;\n    esac\n  env:\n    A: [ "{FLAG_TEXT}" ]\n'),
    # every value of an agent config is walked for secrets
    (".mcp.json", '{"a": {"b": ["x", {"apiKey": "not-a-key"}]}},\n'),
])
def test_round11_new_passes_grow_linearly(tmp_path, rel, unit):
    """CPU time for an input four times larger stays well under sixteen times as long."""
    n = 400
    if rel == ".mcp.json":
        small, large = ("[" + unit * k + "{}]" for k in (n, 4 * n))
    else:
        small, large = unit * n, unit * 4 * n
    t_small = min(scan_cpu(tmp_path, rel, small) for _ in range(2))
    t_large = min(scan_cpu(tmp_path, rel, large) for _ in range(2))
    assert t_large < 10 * t_small + 0.1, (t_small, t_large)


@pytest.mark.parametrize("rel,unit", [
    # deny-list names: each followed its uses with a whole-file search (1 MB took 35 s, clean)
    ("a.py", lambda i: f'n{i}_deny = ["{FLAG_TEXT}"]\n'),
    # pushed-to argument lists: each name searched the rest of the file (1 MB took 40 s)
    ("a.js", lambda i: f"a{i}.push('--yolo')\n"),
])
def test_round12_distinct_names_grow_linearly_and_are_reported(tmp_path, rel, unit):
    """Finding 1: one identifier index per file, and at most MAX_NAMES names followed; past the
    cap a flag is reported, not judged a mention."""
    n = 3000
    small, large = ("".join(unit(i) for i in range(k)) for k in (n, 4 * n))
    t_small = min(scan_cpu(tmp_path, rel, small) for _ in range(2))
    t_large = min(scan_cpu(tmp_path, rel, large) for _ in range(2))
    assert t_large < 10 * t_small + 0.1, (t_small, t_large)
    if rel == "a.py":
        assert "AP01" in rules(tmp_path)  # names past the cap are not deny-lists


def test_round12_a_deny_list_within_the_name_cap_is_still_a_mention(tmp_path):
    write(tmp_path, "a.py", f'BLOCKED = ["{FLAG_TEXT}"]\nif arg in BLOCKED:\n    exit(2)\n')
    assert rules(tmp_path) == []
