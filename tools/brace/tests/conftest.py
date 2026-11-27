import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

TOOL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL_DIR))
sys.path.insert(0, str(TOOL_DIR.parent.parent / "src"))

import brace  # noqa: E402

MAX_WORKERS = 8  # more workers than this only add start-up and scheduling cost on a busy machine


def pytest_xdist_auto_num_workers(config):
    """`-n auto` (pytest.ini): one worker per CPU, at most MAX_WORKERS."""
    return max(1, min(MAX_WORKERS, len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 1))


# The wall-clock budget of the default suite: over the target is reported loudly, over the
# limit fails the run, so a slow test cannot creep in unnoticed.
BUDGET_TARGET, BUDGET_LIMIT = 5 * 60, 10 * 60
_started = time.monotonic()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if hasattr(config, "workerinput"):
        return
    took = time.monotonic() - _started
    if took > BUDGET_LIMIT:
        terminalreporter.section("TEST BUDGET EXCEEDED", red=True, bold=True)
        terminalreporter.line(f"the suite took {took:.0f} s; the limit is {BUDGET_LIMIT} s", red=True)
    elif took > BUDGET_TARGET:
        terminalreporter.section("TEST BUDGET WARNING", yellow=True, bold=True)
        terminalreporter.line(f"the suite took {took:.0f} s; the target is under {BUDGET_TARGET} s", yellow=True)


def pytest_sessionfinish(session, exitstatus):
    if not hasattr(session.config, "workerinput") and time.monotonic() - _started > BUDGET_LIMIT and exitstatus == 0:
        session.exitstatus = 1


ITEMS = json.loads((TOOL_DIR / "brace_items.json").read_text(encoding="utf-8"))
GATE = {i["id"]: i["gate"] for i in ITEMS}


def first(gate: str) -> str:
    return next(i["id"] for i in ITEMS if i["gate"] == gate)


def good_deployment(**overrides) -> dict:
    dep = {
        "brace_checklist": "2026-10-01",
        "deployment": {"name": "support-agent", "environment": "production", "release": "42"},
        "classification": {
            "stakes": "low",
            "autonomy": "low",
            "rationale": "Read-only helper.",
            "approved_by": "@alice",
        },
        "roles": {"agent_team": ["@acme/agent-team"], "governance": ["@acme/ai-governance"]},
        "approvals": {"provider": "github", "approvers": ["@acme/ai-governance", "@carol"]},
    }
    dep.update(overrides)
    return dep


def good_record() -> dict:
    return {
        "items": {
            i["id"]: {
                "outcome": "pass",
                "lead": "@bob",
                "evidence": [{"link": f"https://ci.example/run/{i['id']}", "date": "2026-09-30"}],
            }
            for i in ITEMS
        }
    }


def good_exception(item: str) -> dict:
    return {
        "item": item,
        "threat": "Multi-step abuse goes undetected.",
        "affected_systems": "support-agent production",
        "compensating_controls": [{"control": "Rate quotas (B07).", "evidence": "https://ci.example/run/456"}],
        "accepted_by": "@carol",
        "accepted_on": "2026-10-01",
        "remediation_owner": "@acme/security",
        "tracking": "https://tracker.example/SEC-12",
    }


def good_na(item: str) -> dict:
    return {
        "item": item,
        "reason": "The agent has no memory that lasts between runs.",
        "evidence": ["https://github.com/acme/agent/blob/abc/src/agent.py#L10"],
        "reviewer": "@carol",
        "reviewed_on": "2026-10-01",
    }


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.brace = root / ".brace"
        (self.brace / "exceptions").mkdir(parents=True)
        (self.brace / "na").mkdir(parents=True)
        self.deployment = good_deployment()
        self.record = good_record()
        self.write()

    def write(self):
        (self.brace / "deployment.yaml").write_text(yaml.safe_dump(self.deployment, sort_keys=False))
        (self.brace / "record.yaml").write_text(yaml.safe_dump(self.record, sort_keys=False))

    def add(self, sub: str, stem: str, data) -> Path:
        p = self.brace / sub / f"{stem}.yaml"
        p.write_text(data if isinstance(data, str) else yaml.safe_dump(data, sort_keys=False))
        return p

    def set_item(self, item: str, **fields):
        self.record["items"][item] = fields
        self.write()

    def check(self, *extra: str):
        out = self.root / "result.json"
        code = brace.main(["check", "--dir", str(self.root), "--json", str(out), *extra])
        result = json.loads(out.read_text()) if out.exists() else None
        if out.exists():
            out.unlink()
        return code, result

    # git helpers
    def git(self, *args: str) -> str:
        res = subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false", *args],
            cwd=self.root, capture_output=True, text=True, check=True,
        )
        return res.stdout.strip()

    def git_init(self):
        self.git("init", "-q")
        self.commit_all("initial")

    def commit_all(self, msg: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for var in ("GITHUB_TOKEN", "GITHUB_REPOSITORY", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_API_URL"):
        monkeypatch.delenv(var, raising=False)
    return Repo(tmp_path)


@pytest.fixture(params=["jsonschema", "builtin"])
def validator_kind(request, monkeypatch):
    if request.param == "builtin":
        monkeypatch.setattr(brace, "_JSValidator", None)
    elif brace._JSValidator is None:
        pytest.skip("jsonschema not installed")
    return request.param
