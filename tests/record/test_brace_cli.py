"""The unified `brace` command line (src/brace_tools/cli.py)."""
import json
import subprocess
import sys
from pathlib import Path

from conftest import TOOL_DIR

from brace_tools import cli

SRC = TOOL_DIR.parent.parent / "src"
BILL = TOOL_DIR / "examples" / "billing-agent"
NO_YAML = "import sys; sys.modules['yaml'] = None; sys.path.insert(0, sys.argv[1]); from brace_tools.cli import main; sys.exit(main(sys.argv[2:]))"


def test_version_help_and_unknown(capsys):
    assert cli.main(["--version"]) == 0 and capsys.readouterr().out.startswith("brace 3.")
    assert cli.main(["--help"]) == 0 and "import-results" in capsys.readouterr().out
    assert cli.main([]) == 2
    assert cli.main(["nosuch"]) == 2 and "unknown command" in capsys.readouterr().err


def test_scan_delegates_to_the_scanner(tmp_path, capsys):
    assert cli.main(["scan", str(tmp_path), "--fail-on", "none"]) == 0


def test_record_commands(repo, capsys):
    assert cli.main(["items", "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)) > 10
    assert cli.main(["check", "--dir", str(repo.root), "--approvals", "off"]) in (0, 1)


def test_map_and_plan(tmp_path, capsys):
    assert cli.main(["map", "validate", str(BILL / "topology.cdx.json")]) == 0
    out = tmp_path / "gh.txt"
    code = cli.main(["plan", str(BILL / "sample-findings.json"), str(BILL / "topology.cdx.json"), "-o",
                     str(tmp_path / "p.md"), "--html", str(tmp_path / "p.html"), "--github-output", str(out)])
    assert code == 0 and (tmp_path / "p.html").exists()
    lines = dict(x.split("=") for x in out.read_text().splitlines())
    assert set(lines) == {"actions", "gaps", "blocker_gaps", "notes", "failing"} and all(v.isdigit() for v in lines.values())


def test_missing_extra_names_it():
    p = subprocess.run([sys.executable, "-I", "-c", NO_YAML, str(SRC), "check"], capture_output=True, text=True)
    assert p.returncode == 2 and 'open-agent-security[record]' in p.stderr and "yaml" in p.stderr
    p = subprocess.run([sys.executable, "-I", "-c", NO_YAML, str(SRC), "--version"], capture_output=True, text=True)
    assert p.returncode == 0


def test_old_launcher_without_pyyaml_still_scans_and_hints(tmp_path):
    shim = str(TOOL_DIR / "brace.py")
    code = "import runpy, sys; sys.modules['yaml'] = None; sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"
    p = subprocess.run([sys.executable, "-I", "-c", code, shim, "check"], capture_output=True, text=True)
    assert p.returncode == 2 and "pip install" in p.stderr
    p = subprocess.run([sys.executable, "-I", "-c", code, shim, "scan", str(tmp_path), "--fail-on", "none"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
