"""Nothing loads from the scanned folder: isolated mode and the launchers."""
import subprocess
import sys

from support import TOOL_DIR, write


def test_isolated_mode_does_not_import_from_scanned_repo(tmp_path):
    write(tmp_path, "json.py", "raise SystemExit('PWNED')\n")
    write(tmp_path, "open_agent_security/__init__.py", "raise SystemExit('PWNED')\n")
    p = subprocess.run([sys.executable, "-I", str(TOOL_DIR / "scan.py"), ".", "--fail-on", "none"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert p.returncode == 0 and "PWNED" not in p.stdout + p.stderr


def test_brace_py_scan_under_isolated_mode(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    p = subprocess.run([sys.executable, "-I", str(TOOL_DIR / "brace.py"), "scan", str(tmp_path), "--fail-on", "none"],
                       capture_output=True, text=True)
    assert p.returncode == 0 and "AP01" in p.stdout, p.stderr
