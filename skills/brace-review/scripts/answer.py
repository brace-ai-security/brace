#!/usr/bin/env python3
"""Write one answer into a findings file, check it, and show what's next.

Use this instead of editing the JSON by hand.

  Answer a check:
    python answer.py FINDINGS.json check B05.2 --met no --evidence src/x.py:41 \\
        --quote "exact code on that line" --note "what the code does" [--counter "what you searched"]

  Add a red flag:
    python answer.py FINDINGS.json flag B05 --evidence src/x.py:41 --note "what's wrong"

  Finish an item:
    python answer.py FINDINGS.json item B05 --rating gap --confidence high \\
        --summary "one sentence" --next "what to fix" [--violates "exact words from the requirement"] \\
        [--also-affects E06]

  Resolve a pre-scan hit:
    python answer.py FINDINGS.json prescan H003 --verdict confirmed --item R03 --reason "..."

  Show the next unanswered check:
    python answer.py FINDINGS.json next

The quote is checked against the file right away; a "yes" without a matching quote
and a counter-search is refused. Paths are relative to the repo, which defaults to the
folder holding FINDINGS.json (set --repo to change it).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_findings import quote_found, norm, refs  # noqa: E402

CHECKS_FILE = Path(__file__).resolve().parent.parent / "references" / "checks.json"


def load(path):
    return json.loads(Path(path).read_text())


def save(path, doc):
    Path(path).write_text(json.dumps(doc, indent=2) + "\n")


def find_item(doc, item):
    for f in doc["findings"]:
        if f["item"] == item:
            return f
    sys.exit(f"{item} isn't in this findings file.")


def next_open(doc):
    for f in doc["findings"]:
        for c in f.get("checks", []):
            if c.get("met") == "unknown" and not norm(c.get("note", "")):
                return f"Next: {c['id']} — {c.get('check', '')}\n  How to verify: {c.get('verify', '')}"
        if str(f.get("summary", "")).startswith("TODO"):
            return f"Next: finish item {f['item']} with `answer.py ... item {f['item']} --rating ...`"
    return "All checks and items have answers. Run validate_findings.py --fix."


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("findings")
    ap.add_argument("kind", choices=["check", "flag", "item", "prescan", "next"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("--repo")
    ap.add_argument("--met", choices=["yes", "no", "unknown"])
    ap.add_argument("--evidence", default="")
    ap.add_argument("--quote", default="")
    ap.add_argument("--counter", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--rating", choices=["likely_pass", "gap", "needs_evidence", "na_candidate"])
    ap.add_argument("--confidence", choices=["high", "medium", "low"], default="medium")
    ap.add_argument("--summary", default="")
    ap.add_argument("--next", dest="next_step", default="")
    ap.add_argument("--violates", action="append", default=[])
    ap.add_argument("--also-affects", action="append", default=[])
    ap.add_argument("--verdict", choices=["confirmed", "dismissed"])
    ap.add_argument("--item")
    ap.add_argument("--reason", default="")
    a = ap.parse_args()
    path = Path(a.findings)
    repo = Path(a.repo) if a.repo else path.resolve().parent
    doc = load(path)

    if a.kind == "next":
        print(next_open(doc))
        return

    if a.kind == "check":
        item = a.target.split(".")[0]
        f = find_item(doc, item)
        c = next((c for c in f["checks"] if c["id"] == a.target), None)
        if not c:
            sys.exit(f"{a.target} isn't a check of {item}. Checks: {', '.join(c['id'] for c in f['checks'])}")
        if not a.met or len(norm(a.note).split()) < 4:
            sys.exit("Give --met and a --note of at least four words.")
        if a.met in ("yes", "no"):
            if not refs(a.evidence):
                sys.exit("--evidence must be path:line.")
            if not quote_found(repo, a.evidence, a.quote):
                sys.exit(f"The quote isn't in {a.evidence} (within 3 lines). Copy the exact code text.")
        if a.met == "yes" and len(norm(a.counter).split()) < 4:
            sys.exit("A yes needs --counter: what you searched for that would make it false, and what you found.")
        c.update(met=a.met, evidence=a.evidence, quote=a.quote, counter_search=a.counter, note=a.note)
        save(path, doc)
        print(f"Saved {a.target} = {a.met}. " + next_open(doc))
        return

    if a.kind == "flag":
        f = find_item(doc, a.target)
        if not refs(a.evidence) or len(norm(a.note).split()) < 4:
            sys.exit("A red flag needs --evidence path:line and a --note of at least four words.")
        f.setdefault("red_flags_found", []).append(f"{a.evidence} {a.note}")
        save(path, doc)
        print(f"Added red flag to {a.target}.")
        return

    if a.kind == "item":
        f = find_item(doc, a.target)
        if not a.rating or len(norm(a.summary).split()) < 6 or not norm(a.next_step):
            sys.exit("Give --rating, a --summary of at least six words, and --next.")
        if a.rating == "gap":
            req = norm(json.loads(CHECKS_FILE.read_text()).get(a.target, {}).get("requirement", ""))
            bad = [v for v in a.violates if len(norm(v).strip(" .")) < 15
                   or norm(v).lower().strip(" .") not in req.lower()]
            if req and (bad or not a.violates):
                sys.exit(f"A gap needs --violates: words copied exactly from {a.target}'s requirement, one phrase "
                         f"per --violates, at least 15 characters each. "
                         + (f"Not found in it: {bad}. " if bad else "")
                         + f"The requirement is:\n{req}")
        f.update(rating=a.rating, confidence=a.confidence, summary=a.summary, next_step=a.next_step)
        if a.violates:
            f["violates"] = a.violates
        if a.also_affects:
            f["also_affects"] = a.also_affects
        ev = next((c for c in f["checks"] if c.get("met") in ("no", "yes") and refs(c.get("evidence"))), None)
        if ev and not f.get("evidence"):
            p, line, _ = refs(ev["evidence"])[0]
            f["evidence"] = [{"file": p, "line": line, "note": ev.get("note", "")}]
        save(path, doc)
        print(f"Saved item {a.target} = {a.rating}. " + next_open(doc))
        return

    if a.kind == "prescan":
        if not a.verdict or len(norm(a.reason).split()) < 6:
            sys.exit("Give --verdict and a --reason of at least six words.")
        if a.verdict == "confirmed" and not a.item:
            sys.exit("A confirmed hit needs --item: the item whose requirement it breaks.")
        res = doc.setdefault("prescan_resolutions", {})
        res[a.target] = {"verdict": a.verdict, "item": a.item, "reason": a.reason}
        save(path, doc)
        print(f"Saved pre-scan {a.target} = {a.verdict}.")


if __name__ == "__main__":
    main()
