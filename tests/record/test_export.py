"""brace.py export: the record as JSON, CSV and a self-contained HTML page."""
import csv
import io
import json
import re
from html.parser import HTMLParser

import pytest

from conftest import ITEMS, brace, good_exception, good_na

EXC, NA = "R01", "A03"


@pytest.fixture
def full(repo):
    repo.add("exceptions", f"{EXC}-quota", good_exception(EXC))
    repo.set_item(EXC, outcome="gap", lead="@bob", exception=f"{EXC}-quota")
    repo.add("na", f"{NA}-nomem", good_na(NA))
    repo.set_item(NA, outcome="na", lead="@bob", na=f"{NA}-nomem")
    return repo


def export(repo, fmt, capsys):
    out = repo.root / f"out.{fmt}"
    code = brace.main(["export", "--format", fmt, "--dir", str(repo.root), "--output", str(out)])
    assert code == 0, capsys.readouterr().err
    return out.read_text(encoding="utf-8")


def test_json_one_row_per_item(full, capsys):
    doc = json.loads(export(full, "json", capsys))
    assert [r["id"] for r in doc["items"]] == [i["id"] for i in ITEMS]
    assert doc["deployment"]["name"] == "support-agent" and doc["deployment"]["release"] == "42"
    assert doc["check"]["approvals"] == "off"
    rows = {r["id"]: r for r in doc["items"]}
    b01 = rows["B01"]
    assert b01["outcome"] == "pass" and b01["evidence"][0]["link"] == "https://ci.example/run/B01"
    assert b01["latest_evidence_date"] == "2026-09-30" and b01["gate"] == "Blocker"
    exc = rows[EXC]["decision"]
    assert exc["type"] == "risk_acceptance" and exc["approver"] == "@carol" and exc["date"] == "2026-10-01"
    assert exc["file"] == f".brace/exceptions/{EXC}-quota.yaml" and exc["expires"] == ""
    na = rows[NA]["decision"]
    assert na["type"] == "not_applicable" and na["approver"] == "@carol"


def test_csv(full, capsys):
    rows = list(csv.DictReader(io.StringIO(export(full, "csv", capsys))))
    assert len(rows) == len(ITEMS)
    by = {r["id"]: r for r in rows}
    assert by[EXC]["decision_type"] == "risk_acceptance" and by[EXC]["approver"] == "@carol"
    assert by["B01"]["evidence_links"] == "https://ci.example/run/B01"


def test_csv_defuses_formulas(repo, capsys):
    repo.set_item("B01", outcome="pass", lead="=HYPERLINK(\"http://x\")",
                  evidence=[{"link": "@SUM(1)", "date": "2026-09-30"}])
    rows = {r["id"]: r for r in csv.DictReader(io.StringIO(export(repo, "csv", capsys)))}
    assert rows["B01"]["lead"].startswith("'=") and rows["B01"]["evidence_links"].startswith("'@")


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.attrs = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs += attrs


def test_html_is_self_contained_and_escaped(full, capsys):
    full.set_item("B02", outcome="pass", lead="<script>alert(1)</script>",
                  evidence=[{"link": "javascript:alert(1)", "date": "2026-09-30", "note": "\"><img src=x onerror=1>"}])
    page = export(full, "html", capsys)
    p = Collect()
    p.feed(page)
    assert "script" not in p.tags and "img" not in p.tags and "link" not in p.tags
    hrefs = [v for k, v in p.attrs if k in ("href", "src")]
    assert hrefs and all(h.startswith("https://") for h in hrefs)
    assert not re.search(r"(?:src|href)=\"(?!https://)", page)
    assert "&lt;script&gt;" in page and "javascript:alert(1)" in page  # shown as text, not a link
    assert "@media print" in page and "Content-Security-Policy" in page
    assert page.count('<td class="id">') == len(ITEMS)


def test_stdout_and_bounded_values(repo, capsys):
    repo.set_item("B01", outcome="pass", notes="x" * 10_000,
                  evidence=[{"link": "https://e.example/" + "a" * 10_000, "date": "2026-09-30"}])
    assert brace.main(["export", "--format", "json", "--dir", str(repo.root)]) == 0
    doc = json.loads(capsys.readouterr().out)
    b01 = next(r for r in doc["items"] if r["id"] == "B01")
    assert len(b01["notes"]) < 2100 and len(b01["evidence"][0]["link"]) < 2100


def test_invalid_record_exits_2(repo, capsys):
    (repo.brace / "record.yaml").unlink()
    assert brace.main(["export", "--format", "csv", "--dir", str(repo.root)]) == 2
