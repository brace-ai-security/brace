"""`brace.py export`: the .brace/ evidence record as one row per checklist item, for auditors,
security questionnaires and GRC tools.

Each row: ID, title, gate, outcome, the check's status and problems, lead, evidence (link, date,
note), the latest evidence date, and for a risk acceptance or N/A decision its file, approver,
dates and (when the file has one) expiry. The deployment's metadata and the check's decision
head the export.

Formats:
- json: {"export": ..., "deployment": ..., "check": ..., "items": [...]}.
- csv: one row per item; lists are joined with " | ". A cell that a spreadsheet would read as a
  formula (starting with = + - or a control character, or @ unless it is a plain handle such as
  @acme/team) is prefixed with a quote.
- html: one self-contained, print-friendly page: inline CSS, no scripts, no external resources;
  every value is HTML-escaped and only http(s) links become anchors.

Every value comes from the record files, which a pull request can change, so each is cut to
MAX_TEXT characters and lists to MAX_LIST entries.
"""
from __future__ import annotations

import csv
import datetime as _dt
import html
import io
import json
import re
from urllib.parse import urlsplit

MAX_TEXT = 2000
MAX_LIST = 50
FORMULA = re.compile(r"^[=+\-\t\r\n]|^@(?![\w./-]*$)")  # @team/handle alone is not a formula
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
FORMATS = ("json", "csv", "html")
CSV_FIELDS = ["id", "title", "gate", "outcome", "status", "lead", "evidence_links", "evidence_dates",
              "latest_evidence_date", "decision_type", "decision_file", "approver", "decision_date", "expires",
              "tracking", "reason", "problems"]


def text(v) -> str:
    """A bounded, printable string ('' for None)."""
    if v is None:
        return ""
    s = CONTROL.sub("", str(v))
    return s if len(s) <= MAX_TEXT else s[:MAX_TEXT] + "..."


def rows(checker, res: dict) -> list[dict]:
    """One dict per catalog item, in catalog order, from a Checker that has run."""
    records = checker.record["items"]
    out = []
    for item_id, meta in checker.catalog.items():
        rec = records.get(item_id) or {}
        item = res["items"][item_id]
        evidence = [{"link": text(e.get("link")), "date": text(e.get("date")), "note": text(e.get("note"))}
                    for e in (rec.get("evidence") or [])[:MAX_LIST]]
        dates = sorted(e["date"] for e in evidence if e["date"])
        decision = None
        if item["outcome"] == "gap" and rec.get("exception"):
            data = checker.exceptions.get(rec["exception"]) or {}
            decision = {"type": "risk_acceptance", "file": f".brace/exceptions/{text(rec['exception'])}.yaml",
                        "approver": text(data.get("accepted_by")), "date": text(data.get("accepted_on")),
                        "expires": text(data.get("expires")), "tracking": text(data.get("tracking")),
                        "remediation_owner": text(data.get("remediation_owner")), "reason": text(data.get("threat")),
                        "compensating_controls": [{"control": text(c.get("control")), "evidence": text(c.get("evidence"))}
                                                  for c in (data.get("compensating_controls") or [])[:MAX_LIST]
                                                  if isinstance(c, dict)]}
        elif item["outcome"] == "na" and rec.get("na"):
            data = checker.na_files.get(rec["na"]) or {}
            decision = {"type": "not_applicable", "file": f".brace/na/{text(rec['na'])}.yaml",
                        "approver": text(data.get("reviewer")), "date": text(data.get("reviewed_on")),
                        "expires": text(data.get("expires")), "tracking": "", "reason": text(data.get("reason")),
                        "evidence": [text(e) for e in (data.get("evidence") or [])[:MAX_LIST]]}
        out.append({"id": item_id, "title": text(meta["title"]), "gate": meta["gate"], "outcome": item["outcome"],
                    "status": item["status"], "lead": text(rec.get("lead")), "verified_by": text(rec.get("verified_by")),
                    "evidence": evidence, "latest_evidence_date": dates[-1] if dates else "",
                    "decision": decision, "notes": text(rec.get("notes")),
                    "problems": [text(p) for p in item["problems"][:MAX_LIST]]})
    return out


def document(checker, res: dict, today: str | None = None) -> dict:
    dep = checker.deployment
    meta = dep.get("deployment") or {}
    cls = dep.get("classification") or {}
    return {
        "export": {"format": "brace-record-export", "version": 1,
                   "generated": today or _dt.date.today().isoformat(),
                   "note": "Exported from .brace/ by brace.py. Outcomes are the record's; status is brace.py check's."},
        "deployment": {"name": text(meta.get("name")), "environment": text(meta.get("environment")),
                       "release": text(meta.get("release")), "task": text(meta.get("task")),
                       "brace_checklist": text(dep.get("brace_checklist")),
                       "classification": {k: text(cls.get(k)) for k in ("stakes", "autonomy", "rationale", "approved_by")},
                       "agent_type_id": text((dep.get("agent_type_id") or {}).get("value"))},
        "check": {"decision": res["decision"], "notice": res["notice"], "approvals": res["approvals"],
                  "strict": res["strict"], "reasons": [text(r) for r in res["reasons"]],
                  "warnings": [text(w) for w in res["warnings"]], "counts": res["counts"]},
        "items": rows(checker, res),
    }


def render_json(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def cell(v) -> str:
    s = text(v).replace("\r", " ").replace("\n", " ")
    return "'" + s if FORMULA.match(s) else s


def render_csv(doc: dict) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\r\n")
    w.writeheader()
    for r in doc["items"]:
        d = r["decision"] or {}
        w.writerow({k: cell(v) for k, v in {
            "id": r["id"], "title": r["title"], "gate": r["gate"], "outcome": r["outcome"], "status": r["status"],
            "lead": r["lead"], "evidence_links": " | ".join(e["link"] for e in r["evidence"]),
            "evidence_dates": " | ".join(e["date"] for e in r["evidence"]),
            "latest_evidence_date": r["latest_evidence_date"], "decision_type": d.get("type", ""),
            "decision_file": d.get("file", ""), "approver": d.get("approver", ""), "decision_date": d.get("date", ""),
            "expires": d.get("expires", ""), "tracking": d.get("tracking", ""), "reason": d.get("reason", ""),
            "problems": " | ".join(r["problems"])}.items()})
    return buf.getvalue()


def e(v) -> str:
    return html.escape(text(v), quote=True)


def link(v) -> str:
    """An anchor for an http(s) URL, escaped text for anything else (a path, a javascript: URL)."""
    s = text(v)
    try:
        scheme = urlsplit(s).scheme.lower()
    except ValueError:
        scheme = ""
    if scheme in ("http", "https"):
        return f'<a href="{e(s)}" rel="noopener noreferrer">{e(s)}</a>'
    return e(s)


CSS = """
:root{--fg:#1a1a1a;--muted:#555;--line:#ccc;--bg:#fff;--head:#f2f2f2;--bad:#a40000;--ok:#1d6b2f}
@media (prefers-color-scheme:dark){:root{--fg:#e8e8e8;--muted:#aaa;--line:#444;--bg:#151515;--head:#222;--bad:#ff8a80;--ok:#8fd19e}}
body{font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--fg);background:var(--bg);margin:0;padding:16px;max-width:1200px}
h1{font-size:1.4em;margin:0 0 .3em}h2{font-size:1.1em;margin:1.4em 0 .4em}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.2em 1em;margin:0}dt{color:var(--muted)}dd{margin:0}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{border:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:left;overflow-wrap:anywhere}
th{background:var(--head)}td.id{white-space:nowrap;font-weight:600}
.blocked{color:var(--bad);font-weight:600}.ok{color:var(--ok)}small{color:var(--muted)}ul{margin:0;padding-left:1.1em}
a{color:inherit}
@media print{body{max-width:none;padding:0;font-size:10pt}:root{--fg:#000;--bg:#fff;--head:#eee;--line:#999}
tr{break-inside:avoid}thead{display:table-header-group}a{text-decoration:none}}
"""


def render_html(doc: dict) -> str:
    dep, chk = doc["deployment"], doc["check"]
    cls = dep["classification"]
    meta = [("Deployment", dep["name"]), ("Environment", dep["environment"]), ("Release", dep["release"]),
            ("Task", dep["task"]), ("BRACE checklist", dep["brace_checklist"]),
            ("Classification", f"stakes {cls['stakes'] or '-'}, autonomy {cls['autonomy'] or '-'}"),
            ("Rated by", cls["approved_by"]), ("Agent-type-id", dep["agent_type_id"]),
            ("Check result", chk["decision"]), ("Approvals verified", chk["approvals"] + (" (strict)" if chk["strict"] else "")),
            ("Exported", doc["export"]["generated"])]
    out = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">',
           f"<title>BRACE record: {e(dep['name'])}</title><style>{CSS}</style></head><body>",
           f"<h1>BRACE evidence record: {e(dep['name'])}</h1>",
           f"<p><small>{e(chk['notice'])}</small></p>", "<dl>"]
    out += [f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in meta if v]
    out.append("</dl>")
    if chk["reasons"]:
        out.append(f"<h2>Unresolved ({len(chk['reasons'])})</h2><ul>")
        out += [f"<li>{e(r)}</li>" for r in chk["reasons"]]
        out.append("</ul>")
    out.append('<h2>Items</h2><div class="wrap"><table><thead><tr><th>ID</th><th>Item</th><th>Gate</th>'
               "<th>Outcome</th><th>Evidence</th><th>Exception or N/A</th></tr></thead><tbody>")
    for r in doc["items"]:
        ev = "".join(f"<li>{link(x['link'])}{' <small>' + e(x['date']) + '</small>' if x['date'] else ''}"
                     f"{' <small>' + e(x['note']) + '</small>' if x['note'] else ''}</li>" for x in r["evidence"])
        d = r["decision"]
        dec = ""
        if d:
            label = "Risk acceptance" if d["type"] == "risk_acceptance" else "N/A"
            dec = (f"{label}: {e(d['file'])}<br><small>approver</small> {e(d['approver']) or '-'}"
                   f" <small>on</small> {e(d['date']) or '-'}"
                   + (f"<br><small>expires</small> {e(d['expires'])}" if d["expires"] else "")
                   + (f"<br><small>tracking</small> {link(d['tracking'])}" if d["tracking"] else "")
                   + (f"<br>{e(d['reason'])}" if d["reason"] else ""))
        status = r["outcome"] + ("" if r["status"] == "ok" else f" ({r['status']})")
        problems = "".join(f"<br><small>{e(p)}</small>" for p in r["problems"])
        out.append(f'<tr><td class="id">{e(r["id"])}</td><td>{e(r["title"])}'
                   f"{'<br><small>lead ' + e(r['lead']) + '</small>' if r['lead'] else ''}</td>"
                   f"<td>{e(r['gate'])}</td><td class=\"{'ok' if r['status'] == 'ok' else 'blocked'}\">{e(status)}{problems}</td>"
                   f"<td>{'<ul>' + ev + '</ul>' if ev else ''}</td><td>{dec}</td></tr>")
    out.append("</tbody></table></div></body></html>\n")
    return "\n".join(out)


RENDER = {"json": render_json, "csv": render_csv, "html": render_html}
