"""Old location of brace_tools.record.export, kept so `import record_export` keeps working.

The module object is aliased, so patching this module's globals patches the real module.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from brace_tools.record import export as _real  # noqa: E402

if __name__ != "__main__":
    sys.modules[__name__] = _real
