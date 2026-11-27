"""mappings/*.json: generated from the Markdown mapping tables, current, and consistent with
each page's summary totals."""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "tools/site/gen_mappings_json.py"
PAGES = sorted((ROOT / "mappings").glob("*.md"))
sys.path.insert(0, str(GEN.parent))
import gen_mappings_json as gen  # noqa: E402


def test_generated_files_are_current():
    r = subprocess.run([sys.executable, str(GEN), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("md", PAGES, ids=[p.stem for p in PAGES])
def test_counts_match_the_summary_total(md):
    doc = json.loads(md.with_suffix(".json").read_text(encoding="utf-8"))
    counts = Counter(m["coverage"] for m in doc["mappings"])
    text = md.read_text(encoding="utf-8")
    # The summary's Total row: either "| **Total** | **N** | **d** | **p** | **o** |" or a Coverage/Risks table.
    total = re.search(r"^\| \*\*Total[^*]*\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|$", text, re.M)
    if total:
        n, d, p, o = map(int, total.groups())
        assert (len(doc["mappings"]), counts["Direct"], counts["Partial"], counts["Out of scope"]) == (n, d, p, o)
    else:
        n = int(re.search(r"^\| \*\*Total\*\* \| \*\*(\d+)\*\* \|$", text, re.M).group(1))
        assert len(doc["mappings"]) == n
    assert all(m["id"] and m["coverage"] in gen.COVERAGE for m in doc["mappings"])


def test_rejects_unknown_item_and_coverage(tmp_path):
    bad = tmp_path / "x.md"
    bad.write_text("# X\n\n| ID | Name | Coverage | BRACE items | Why |\n|---|---|---|---|---|\n| X1 | n | Direct | Z99 | w |\n")
    gen.parse(bad)  # Z99 is not an item shape, so nothing is flagged
    bad.write_text("# X\n\n| ID | Name | Coverage | BRACE items | Why |\n|---|---|---|---|---|\n| X1 | n | Direct | B99 | w |\n")
    with pytest.raises(gen.MappingError, match="B99"):
        gen.parse(bad)
    bad.write_text("# X\n\n| ID | Name | Coverage | BRACE items | Why |\n|---|---|---|---|---|\n| X1 | n | Full | B01 | w |\n")
    with pytest.raises(gen.MappingError, match="coverage"):
        gen.parse(bad)
