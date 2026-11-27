"""The scanner never imports PyYAML, jsonschema or the BRACE tools package (dependency rule)."""
import subprocess
import sys

from support import ROOT

PROBE = r"""
import pkgutil, sys
sys.path.insert(0, sys.argv[1])
import open_agent_security
for info in pkgutil.walk_packages(open_agent_security.__path__, "open_agent_security."):
    if not info.name.endswith("__main__"):
        __import__(info.name)
bad = sorted(m for m in sys.modules if m.split(".")[0] in {"yaml", "jsonschema", "brace_tools", "brace"})
print(" ".join(bad))
sys.exit(1 if bad else 0)
"""


def test_importing_every_scanner_module_imports_no_optional_dependency():
    p = subprocess.run([sys.executable, "-I", "-c", PROBE, str(ROOT / "src")], capture_output=True, text=True)
    assert p.returncode == 0, (p.stdout, p.stderr)


def test_no_scanner_module_mentions_the_tools_package():
    for f in (ROOT / "src" / "open_agent_security").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "brace_tools" not in text and "import yaml" not in text and "jsonschema" not in text, f


def test_published_report_schema_matches_the_packaged_one():
    """The schema's $id URL is served from tools/brace/open_agent_security/ by the website."""
    rel = "open_agent_security/report/schema/report-1.schema.json"
    assert (ROOT / "tools/brace" / rel).read_bytes() == (ROOT / "src" / rel).read_bytes()
    assert not list((ROOT / "tools/brace/open_agent_security").rglob("*.py"))
