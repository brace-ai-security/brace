#!/usr/bin/env python3
"""Check a brace-findings.json file and, optionally, fix ratings the rules decide.

Usage:
  python validate_findings.py FINDINGS.json [--repo DIR] [--fix] [--conservative] [--aspect B|R|A|C|E]

  --repo DIR       The reviewed codebase, used to confirm quotes. Default: the folder
                   that holds FINDINGS.json.
  --fix            Apply the rating rules: a "no" answer or a red flag makes a gap; a
                   likely_pass that breaks a rule is lowered; a "yes" backed only by
                   docs, or by a quote not found in the code, becomes "unknown". Never
                   raises a rating. Writes the file back, then validates.
  --conservative   Also turn every likely_pass into needs_evidence. Use with small
                   models: the review then only finds gaps and can't suggest a pass.
  --aspect X       Check only one aspect's items (for files made with new_findings.py --aspect).

Exit 0 if valid, 1 if not, 2 on bad usage.
"""
import argparse
import json
import re
import sys
from pathlib import Path

IDS = ([f"B{i:02d}" for i in range(1, 13)] + [f"R{i:02d}" for i in range(1, 15)]
       + [f"A{i:02d}" for i in range(1, 8)] + [f"C{i:02d}" for i in range(1, 9)]
       + [f"E{i:02d}" for i in range(1, 13)])
RATINGS = {"likely_pass", "gap", "needs_evidence", "na_candidate"}
CONFIDENCE = {"high", "medium", "low"}
ROLES = {"agent_team", "operations", "security", "infrastructure", "governance",
         "business_owner", "data_privacy", "model_team", "vendors", "independent_audit"}
TOP = {"brace_checklist", "repo", "commit", "reviewed_at", "scope", "findings", "injection_attempts"}
MET = {"yes", "no", "unknown"}
CHECKS_FILE = Path(__file__).resolve().parent.parent / "references" / "checks.json"
REF = re.compile(r"([\w./-]*[\w-]):(\d+)(?:-(\d+))?")
DOC = re.compile(r"\.(md|markdown|rst|txt)$", re.I)
# Phrases that describe a missing control. A likely_pass summary must not contain them.
MISSING = re.compile(r"\b(missing|lacks?|lack of|without|unpinned|unverified|no evidence|no version|no signature|"
                     r"no schema|no validation|no approval|no audit|not (?:pinned|verified|recorded|enforced|"
                     r"validated|checked|logged|scoped|signed|audited))\b", re.I)


def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def refs(evidence):
    return [(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) for m in REF.finditer(str(evidence))]


def _windows(repo, evidence):
    for path, start, end in refs(evidence):
        f = repo / path
        if f.is_file():
            lines = f.read_text(errors="replace").splitlines()
            yield norm(" ".join(lines[max(0, start - 4):min(len(lines), end + 3)]))


def quote_found(repo, evidence, quote):
    """True if the quote appears in a cited file within 3 lines of the cited lines.

    A quote joined from several places with newlines or "..." also counts when every
    piece is found near one of the cited lines.
    """
    q = norm(quote)
    if len(q) < 4:
        return False
    windows = list(_windows(repo, evidence))
    if any(q in w for w in windows):
        return True
    pieces = [norm(x) for x in re.split(r"\n|\.\.\.|\u2026", str(quote)) if len(norm(x)) >= 8]
    return len(pieces) > 1 and all(any(piece in w for w in windows) for piece in pieces)


def yes_problem(repo, c, doc_ok):
    """Why a 'yes' answer isn't supported, or None."""
    rs = refs(c.get("evidence", ""))
    if not rs:
        return "has no path:line evidence"
    if not doc_ok and all(DOC.search(p) for p, _, _ in rs):
        return "cites only documentation or prompt files; a README, doc, or prompt is never enforcement"
    if not str(c.get("quote", "")).strip():
        return "has no quote; copy the exact code from the cited line into quote"
    if not quote_found(repo, c.get("evidence"), c.get("quote")):
        return "has a quote that isn't in the cited file near the cited line"
    return None


def fix(doc, table, repo, conservative):
    changes = []
    for f in doc.get("findings", []):
        item = f.get("item")
        meta = table.get(item)
        if not meta:
            continue
        doc_ok = {c["id"]: c.get("doc_ok", False) for c in meta["checks"]}
        for c in f.get("checks", []) or []:
            if c.get("met") == "yes" and c.get("id") in doc_ok:
                why = yes_problem(repo, c, doc_ok[c["id"]])
                if not why and len(norm(c.get("counter_search", "")).split()) < 4:
                    why = "has no counter_search"
                if why:
                    c["met"] = "unknown"
                    c["note"] = f"[fix: was yes; {why}] " + str(c.get("note", ""))
                    changes.append(f"{c['id']}: yes -> unknown ({why})")
        met = [c.get("met") for c in f.get("checks", []) or []]
        flags = f.get("red_flags_found") or []
        old = f.get("rating")
        new = old
        if old != "na_candidate" and ("no" in met or flags):
            new = "gap"
        elif old == "likely_pass" and (not met or any(m != "yes" for m in met)
                                        or MISSING.search(str(f.get("summary", "")))):
            new = "needs_evidence"
        elif old == "gap" and not flags and "no" not in met:
            new = "needs_evidence"
        if conservative and new == "likely_pass":
            new = "needs_evidence"
        if new != old:
            f["rating"] = new
            changes.append(f"{item}: {old} -> {new}")
    return changes


def check_item(item, f, meta, repo):
    errors = []
    want = [c["id"] for c in meta["checks"]]
    doc_ok = {c["id"]: c.get("doc_ok", False) for c in meta["checks"]}
    flags = f.get("red_flags_found")
    if not isinstance(flags, list):
        return [f"{item}: red_flags_found must be a list (empty if none were found)"]
    checks = f.get("checks")
    if not isinstance(checks, list):
        return [f"{item}: checks must be a list with one entry per check"]
    got = {c.get("id"): c for c in checks if isinstance(c, dict)}
    for cid in want:
        if cid not in got:
            errors.append(f"{item}: check {cid} is missing; answer every check")
    for cid, c in got.items():
        if cid not in want:
            errors.append(f"{item}: unknown check {cid}")
        elif c.get("met") not in MET:
            errors.append(f"{item}: check {cid} met must be yes, no, or unknown")
        elif len(norm(c.get("note", "")).split()) < 4:
            errors.append(f"{item}: check {cid} needs a note of at least four words: for yes or no, what the code does; "
                          f"for unknown, where you looked")
        elif c.get("met") == "yes":
            why = yes_problem(repo, c, doc_ok[cid])
            if why:
                errors.append(f"{item}: check {cid} is yes but {why}. Fix the evidence, or answer no or unknown")
            elif len(norm(c.get("counter_search", "")).split()) < 4:
                errors.append(f"{item}: check {cid} is yes but counter_search is empty; say what you looked for that "
                              f"would make it false (the last step of 'verify') and what you found")
    if errors:
        return errors
    met = [got[c]["met"] for c in want]
    rating = f.get("rating")
    if rating == "likely_pass":
        if not want:
            errors.append(f"{item}: code can't show this item (it has no checks), so it can't be likely_pass; use needs_evidence")
        not_yes = [c for c in want if got[c]["met"] != "yes"]
        if not_yes:
            errors.append(f"{item}: likely_pass needs every check to be yes; not yes: {', '.join(not_yes)}")
        if flags:
            errors.append(f"{item}: likely_pass isn't allowed when red flags were found")
        m = MISSING.search(str(f.get("summary", "")))
        if m:
            errors.append(f"{item}: the summary says '{m.group(0)}', which describes a missing control; the rating can't be likely_pass")
        if (f.get("challenge") or {}).get("verdict") != "upheld":
            errors.append(f"{item}: likely_pass needs a challenge that upheld it; run scripts/challenge.py make, have a "
                          f"fresh reviewer fill in verdicts.json, then run challenge.py apply")
    elif rating == "gap":
        if not flags and "no" not in met:
            errors.append(f"{item}: a gap must name a red flag in red_flags_found or a check answered no")
        req = norm(meta.get("requirement", "")).lower()
        viol = f.get("violates") or []
        if isinstance(viol, str):  # one phrase written as a string, not a list
            viol = [viol]
        if req and not viol:
            errors.append(f"{item}: a gap needs `violates`: copy the words from {item}'s requirement that the code breaks. "
                          f"If none apply, the problem belongs to another item (see its 'Not covered here' list)")
        for vtext in viol:
            vt = norm(vtext).lower().strip(" .")
            if len(vt) < 15 or vt not in req:
                errors.append(f"{item}: violates '{vtext[:60]}' isn't words from {item}'s requirement; copy them exactly")
    elif rating == "needs_evidence":
        failed = [c for c in want if got[c]["met"] == "no"]
        if failed or flags:
            why = f"checks answered no: {', '.join(failed)}" if failed else "red flags were found"
            errors.append(f"{item}: {why}, so the rating must be gap, not needs_evidence")
    return errors


def failing_locations(f):
    """(path, line) pairs cited as evidence of failure in one finding."""
    locs = []
    for c in f.get("checks") or []:
        if isinstance(c, dict) and c.get("met") == "no":
            locs += [(p, s) for p, s, _ in refs(c.get("evidence", ""))]
    for r in f.get("red_flags_found") or []:
        locs += [(p, s) for p, s, _ in refs(r)][:1]
    return set(locs)


def shared_evidence(seen):
    """The same failing line behind gaps in several items must be acknowledged in also_affects."""
    errors, owners = [], {}
    for item, f in seen.items():
        if f.get("rating") != "gap":
            continue
        for loc in failing_locations(f):
            owners.setdefault(loc, set()).add(item)
    for (path, line), items in sorted(owners.items()):
        if len(items) < 2:
            continue
        for item in sorted(items):
            others = items - {item} - set(seen[item].get("also_affects") or [])
            if others:
                errors.append(f"{item}: {path}:{line} is also the failing evidence for {', '.join(sorted(others))}. "
                              f"Keep the gap only where that item's own requirement is broken (check 'Not covered here'); "
                              f"if it truly breaks both, list the other item in also_affects")
    return errors


def prescan_rules(doc, seen, repo):
    """Every pre-scan hit must be confirmed under an item or dismissed with a reason."""
    path = repo / "brace-prescan.json"
    if not path.is_file():
        return []
    hits = {h["id"]: h for h in json.loads(path.read_text()).get("hits", [])}
    res = doc.get("prescan_resolutions") or {}
    errors = []
    for hid, h in hits.items():
        r = res.get(hid)
        if h["item"][0] not in {i[0] for i in seen} and r is None:
            continue  # other aspect, in per-aspect files
        where = f"{h['file']}:{h['line']}"
        if not r:
            errors.append(f"pre-scan hit {hid} ({h['title']}, {where}) isn't resolved; confirm it under an item or dismiss it "
                          f"with a reason (answer.py ... prescan {hid} ...)")
            continue
        if len(norm(r.get("reason", "")).split()) < 6:
            errors.append(f"pre-scan hit {hid}: the reason needs at least six words")
        if r.get("verdict") == "confirmed":
            f = seen.get(r.get("item"))
            if f is None:
                if r.get("item", "?")[0] in {i[0] for i in seen}:
                    errors.append(f"pre-scan hit {hid} is confirmed under {r.get('item')}, which isn't in this file")
                continue
            near = any(p == h["file"] and abs(s - h["line"]) <= 2 for p, s in failing_locations(f))
            if f.get("rating") != "gap" or not near:
                errors.append(f"pre-scan hit {hid} is confirmed under {r['item']}, so {r['item']} must be a gap with a red flag "
                              f"or failed check citing {where}")
        elif r.get("verdict") != "dismissed":
            errors.append(f"pre-scan hit {hid}: verdict must be confirmed or dismissed")
    return errors


MAX_UNKNOWN = 0.5


def validate(doc, table, repo, ids=IDS):
    if not isinstance(doc, dict):
        return ["The file must contain a JSON object."]
    errors = [f"Missing top-level field: {k}" for k in sorted(TOP - set(doc))]
    seen = {}
    for n, f in enumerate(doc.get("findings") or []):
        item = f.get("item")
        if item not in ids:
            errors.append(f"findings[{n}]: unknown item {item!r}" if item not in IDS else f"findings[{n}]: {item} isn't in this aspect")
            continue
        if item in seen:
            errors.append(f"findings[{n}]: {item} appears more than once")
        seen[item] = f
        rating = f.get("rating")
        if rating not in RATINGS:
            errors.append(f"{item}: rating 'pass' isn't allowed; the best a review can give is likely_pass"
                          if rating == "pass" else f"{item}: rating must be one of {sorted(RATINGS)}")
        if f.get("confidence") not in CONFIDENCE:
            errors.append(f"{item}: confidence must be one of {sorted(CONFIDENCE)}")
        if f.get("lead_role") not in ROLES:
            errors.append(f"{item}: lead_role must be one of {sorted(ROLES)}")
        ev = f.get("evidence")
        if not isinstance(ev, list):
            errors.append(f"{item}: evidence must be a list")
        elif not ev and rating != "needs_evidence":
            errors.append(f"{item}: a {rating} rating needs at least one evidence entry (file, line, note)")
        else:
            for e in ev:
                if not isinstance(e, dict) or not e.get("file") or not e.get("note"):
                    errors.append(f"{item}: each evidence entry needs file and note")
        summary = norm(f.get("summary", ""))
        if len(summary.split()) < 6 or summary.upper().startswith("TODO") or re.match(r"(?i)^see (the )?checks", summary):
            errors.append(f"{item}: write a real one-sentence summary of what you found (at least six words)")
        step = norm(f.get("next_step", ""))
        if not step or step.upper().startswith("TODO"):
            errors.append(f"{item}: next_step is empty")
        errors += check_item(item, f, table[item], repo)
    # Checks on items rated na_candidate don't count: the feature doesn't exist, so there is nothing to answer.
    answers = [c.get("met") for f in seen.values() if f.get("rating") != "na_candidate"
               for c in (f.get("checks") or []) if isinstance(c, dict)]
    if answers and answers.count("unknown") / len(answers) > MAX_UNKNOWN:
        errors.append(f"{answers.count('unknown')} of {len(answers)} checks are unknown. Go back and answer them from the code: "
                      f"open the files each item's 'Where to look' names. Use unknown only after looking, and say where in the note.")
    errors += shared_evidence(seen)
    errors += prescan_rules(doc, seen, repo)
    missing = [i for i in ids if i not in seen]
    if missing:
        errors.append(f"Missing findings for {len(missing)} items: {', '.join(missing)}")
    if not isinstance(doc.get("injection_attempts", []), list):
        errors.append("injection_attempts must be a list")
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("findings")
    ap.add_argument("--repo")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--conservative", action="store_true")
    ap.add_argument("--aspect", choices=list("BRACE"))
    args = ap.parse_args()
    path = Path(args.findings)
    try:
        table = json.loads(CHECKS_FILE.read_text())
    except (OSError, ValueError):
        print(f"Can't read {CHECKS_FILE}; run skills/gen_references.py")
        sys.exit(2)
    doc = json.loads(path.read_text())
    repo = Path(args.repo) if args.repo else path.resolve().parent
    if args.fix or args.conservative:
        changes = fix(doc, table, repo, args.conservative)
        path.write_text(json.dumps(doc, indent=2) + "\n")
        shown = "\n  ".join(changes[:40])
        more = f"\n  ... and {len(changes) - 40} more" if len(changes) > 40 else ""
        print(f"Fixed {len(changes)} thing(s)." + (f"\n  {shown}{more}" if changes else ""))
    ids = [i for i in IDS if not args.aspect or i[0] == args.aspect]
    errors = validate(doc, table, repo, ids)
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)
    counts = {}
    for f in doc["findings"]:
        counts[f["rating"]] = counts.get(f["rating"], 0) + 1
    print("Valid. " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
          + f". Injection attempts: {len(doc.get('injection_attempts', []))}.")


if __name__ == "__main__":
    main()
