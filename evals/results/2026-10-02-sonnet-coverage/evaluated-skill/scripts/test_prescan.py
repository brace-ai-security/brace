"""Self-test for prescan.py. Run: pytest skills/brace-review/scripts/test_prescan.py

Each sample file holds lines that must hit a pattern and near-miss lines that must not.
A line marked `# HIT P..` / `// HIT P..` must be reported for that pattern; every other
line in the file must not be reported for the patterns under test.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prescan  # noqa: E402

SAMPLES = {
    "agent/tools.py": '''
import subprocess, os, pickle
subprocess.run(cmd, shell=True)  # HIT P01
subprocess.run(["ls", path], shell=False)
os.system("ls " + user_dir)  # HIT P01
prog = cmd.split()[0]  # HIT P04
if path.startswith(SANDBOX_ROOT):  # HIT P06
if name.endswith(".py"):
env = os.environ.copy()  # HIT P11
env = {"PATH": os.environ["PATH"]}
data = pickle.load(fh)  # HIT P45
data = json.load(fh)
cur.execute(f"SELECT * FROM t WHERE id = {item_id}")  # HIT P46
cur.execute("SELECT * FROM t WHERE id = %s", (item_id,))
r = requests.get(url, verify=False)  # HIT P22
r = requests.get(url, verify=True)
''',
    "agent/policy.py": '''
def check(action):
    try:
        return engine.decide(action)
    except Exception:  # HIT P07
        log.warning("policy engine failed")
        return True

def check_strict(action):
    try:
        return engine.decide(action)
    except Exception:
        return False
''',
    "agent/hash.py": '''
for name in files:
    if name.startswith("_"):  # HIT P09
        continue
    if name.endswith(".pyc"):
        continue
''',
    "agent/mail.py": '''
internal = address.lower().endswith(FIRM_DOMAIN)  # HIT P51
internal2 = address.lower().endswith("example.com")  # HIT P51
internal3 = address.lower().endswith("@example.com")
ok = host.endswith(".example.com")
''',
    "src/server.ts": '''
import { execFile } from "child_process";
import { exec } from "child_process"; // HIT P02
const child = spawn(bin, args, { env: { ...process.env } }); // HIT P11
const child2 = spawn(bin, args, { env: { PATH: process.env.PATH } });
if (resolved.startsWith(workspaceRoot)) { // HIT P06
const tenant = req.body.tenantId; // HIT P38
const tenant2 = session.tenantId;
await page.click(args.selector); // HIT P52
await page.goto(url);
await page.locator(selector).first().click({ timeout: 10_000 }); // HIT P52
button.click();
''',
    "deploy/Dockerfile": '''
FROM python:3.12-slim  # HIT P13
FROM python:3.12-slim@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
RUN pip install requests  # HIT P16
RUN pip install -r requirements.txt
# RUN pip install requests
RUN apt-get install -y curl \\
    --privileged  # HIT P23
''',
    "deploy/pod.yaml": '''
spec:
  containers:
    - name: agent
      image: ghcr.io/acme/agent:latest  # HIT P14
      image: ghcr.io/acme/agent@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
      securityContext:
        privileged: true  # HIT P23
        privileged: false
''',
    "cmd/run.go": '''
out := exec.Command("sh", "-c", userCmd)  // HIT P03
out2 := exec.Command("ls", "-la", dir)
q := fmt.Sprintf("SELECT * FROM users WHERE id = %s", id)  // HIT P46
msg := fmt.Sprintf("Select %q from: %s", text, where)
// key := "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  HIT P33
''',
    "infra/sg.tf": '''
  cidr_blocks = ["0.0.0.0/0"]  # HIT P20
  cidr_blocks = ["10.0.0.0/8"]
''',
    ".mcp.json": '''
{"mcpServers": {"gh": {
  "command": "npx",  # HIT P15
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "command": "node",
  "args": ["@modelcontextprotocol/server-github@1.2.3"],
  "env": {"GITHUB_TOKEN": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"}  # HIT P33
}}}
''',
}

# Patterns whose hits and non-hits are fully specified by the samples above.
UNDER_TEST = {"P01", "P02", "P03", "P04", "P06", "P07", "P09", "P11", "P13", "P14", "P15",
              "P16", "P20", "P22", "P23", "P33", "P38", "P45", "P46", "P51", "P52"}


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    repo = tmp_path_factory.mktemp("repo")
    for rel, body in SAMPLES.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body.lstrip("\n"))
    # Directories the scanner must skip.
    (repo / "node_modules" / "x").mkdir(parents=True)
    (repo / "node_modules" / "x" / "a.py").write_text("subprocess.run(c, shell=True)\n")
    (repo / "brace-findings.json").write_text('{"x": "0.0.0.0/0"}\n')
    out = repo / "brace-prescan.json"
    proc = subprocess.run([sys.executable, str(HERE / "prescan.py"), str(repo), "--out", str(out)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return repo, json.loads(out.read_text()), proc.stdout


def expected_hits(repo):
    exp = set()
    for rel, body in SAMPLES.items():
        for n, line in enumerate(body.lstrip("\n").splitlines(), 1):
            for pid in re.findall(r"HIT (P\d\d)", line):
                exp.add((pid, rel, n))
    return exp


def test_patterns_file_is_valid():
    patterns = prescan.load_patterns()
    assert 35 <= len(patterns) <= 60
    assert {p["id"] for p in patterns} >= UNDER_TEST


def test_expected_hits_and_no_near_misses(result):
    repo, data, _ = result
    got = {(h["pattern"], h["file"], h["line"]) for h in data["hits"] if h["pattern"] in UNDER_TEST}
    exp = expected_hits(repo)
    assert exp - got == set(), f"missed: {sorted(exp - got)}"
    assert got - exp == set(), f"unexpected: {sorted(got - exp)}"


def test_hit_shape_and_skips(result):
    _, data, stdout = result
    for h in data["hits"]:
        assert set(h) == {"id", "pattern", "item", "title", "file", "line", "text", "ask"}
        assert len(h["text"]) <= 200
        assert not h["file"].startswith(("node_modules/", "brace-findings"))
    assert [h["id"] for h in data["hits"]] == [f"H{i:03d}" for i in range(1, len(data["hits"]) + 1)]
    assert "B01:" in stdout


def test_cap(tmp_path):
    (tmp_path / "many.py").write_text("subprocess.run(c, shell=True)\n" * 30)
    data = prescan.scan(tmp_path, prescan.load_patterns())
    p01 = [h for h in data["hits"] if h["pattern"] == "P01"]
    assert len(p01) == 25
    assert {"pattern": "P01", "item": "B01", "found": 30, "kept": 25} in data["capped"]
