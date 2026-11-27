"""Old location of brace_tools.report.map_html, kept so `import topology_report` keeps working.

The module object is aliased, so patching this module's globals patches the real module.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from brace_tools.report import map_html as _real  # noqa: E402

if __name__ != "__main__":
    sys.modules[__name__] = _real
