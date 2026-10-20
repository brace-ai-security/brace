#!/usr/bin/env python3
"""Challenge every likely_pass and G1/G2 N/A claim with a fresh look at the code.

  python challenge.py make  FINDINGS.json [--repo DIR] [--out DIR] [--hunt]
      Writes one sheet per likely_pass item to DIR (default: <repo>/brace-challenges/),
      plus every G1/G2 na_candidate, and with --hunt every G1/G2 needs_evidence,
      plus a verdicts.json to fill in. Each sheet shows the item's checks, how to
      verify them, and the quoted code with surrounding lines.

  python challenge.py apply FINDINGS.json [--repo DIR] [--out DIR]
      Reads verdicts.json and updates the findings:
        upheld   -> the item keeps likely_pass and records the challenge;
        failed   -> each failed check becomes "no" with the quoted counter-evidence,
                    a red flag is added, and the item becomes a gap;
        unclear  -> the named checks become "unknown"; the item becomes needs_evidence.
      A failed hunt turns a needs_evidence item into a gap. Nothing is ever raised.

Give each sheet to a reviewer who hasn't seen the original answers: a sub-agent,
or a fresh pass that reads only that sheet and the repo. Parallel sub-agents should
each write their answer to <ITEM>.verdict.json next to the sheet; apply reads those
files as well as verdicts.json.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CHECKS_FILE = Path(__file__).resolve().parent.parent / "references" / "checks.json"
REF = re.compile(r"([\w./-]*[\w-]):(\d+)(?:-(\d+))?")
CONTEXT = 12

DISCOVERY_INTRO = """# Independent coverage discovery: {item} — {title}

Establish your own findings from the code before comparing with any earlier
review. You are not told the earlier rating, answers, citations or exceptions.
**Requirement:** {requirement}
**N/A condition:** {na_when}

Inventory all relevant paths/fields, including indirect paths, helpers and both directions of
handoffs. For each check, record coverage rows (subject, status enforced/missing/
unclear/not_applicable, evidence, exact quote, note), deviations (required-control
omissions; empty only if none), and concrete falsification attempts (category,
input, trace, outcome blocked/accepted/unclear/not_applicable, evidence, quote).
Small or residual omissions are still omissions. A missing row or unresolved
coverage cannot support holds. Do not run repository code; derive counterexamples
by tracing it. A bounded_after budget claim needs a finite overshoot bound, not
just a shared counter. Exemptions need quoted scope evidence.

Set applicability absent/present/unclear, with top-level evidence, quote and a
search explanation. Absent must satisfy the exact N/A condition. When present,
verdict is failed if any required check fails, unclear if any is unresolved,
otherwise upheld. Copy broken words from the requirement into violates.
"""

NA_INTRO = """# N/A challenge: {item} — {title}

The reviewer says this item's feature or exposure is absent. **Try to disprove that
claim.** Trace the harness, tools, integrations, peer messages, and indirect paths;
names and README claims are not enough. Explain what you searched and found.

**The requirement:** {requirement}
**N/A when:** {na_when}
**Reviewer's claim:** {summary}
**Reviewer's evidence:** {evidence}

Set `applicability` to **absent** only when the N/A condition holds, **present**
when you find the feature or exposure, or **unclear** when you cannot establish
absence. Include `evidence` (path:line), `quote` (exact code), and `note` (paths
searched and why the condition holds or fails) at the top level of your verdict.
If present, evaluate the checks below: a failed control makes this a gap; if you
cannot show a failed control, it becomes needs_evidence. Never turn it into a pass.
If absent, use verdict upheld; if unclear, use verdict unclear.
"""

HUNT_INTRO = """# Gap hunt: {item} — {title}

A reviewer couldn't decide whether this item is met. **Your job is to find out whether any
check below is false in this codebase.** The reviewer's partial answers and the code they
looked at are shown. Read the code, and open the repo files the checks point to.

For each check, decide:
- **fails**: you found the line that makes it false (a missing control, a bypass, a
  value never used, an exception that continues, a filter that lets something through).
  Quote that line;
- **holds**: you found the code that makes it true in every case;
- **unclear**: you can't tell from this repo.

**The requirement for {item}:** {requirement}

If a check fails, also copy the words from this requirement that the code breaks into
`violates`. Then write your answer (format at the end).
"""

SHEET_INTRO = """# Challenge: {item} — {title}

You are checking someone else's review. They said every check below is true for this
codebase. **Your job is to find a reason one is false.** Read the code shown, and open the
repo files if you need more. Assume the reviewer may have misread the code.

For each check, decide:
- **holds**: the code shown makes it true in every case you can find;
- **fails**: you found code that makes it false: a skipped file, a second path, an
  exception that continues, a value never used, a credential that can undo it, a
  filter that lets something through. Quote that line;
- **unclear**: you can't tell from this repo.

Then write your answer for this item in verdicts.json (format at the end).
"""


def excerpt(repo, evidence):
    out = []
    for m in REF.finditer(str(evidence)):
        path, start = m.group(1), int(m.group(2))
        end = int(m.group(3) or start)
        f = repo / path
        if not f.is_file():
            out.append(f"(file not found: {path})")
            continue
        lines = f.read_text(errors="replace").splitlines()
        lo, hi = max(1, start - CONTEXT), min(len(lines), end + CONTEXT)
        body = "\n".join(f"{n:4d}{'>' if start <= n <= end else ' '} {lines[n - 1]}" for n in range(lo, hi + 1))
        out.append(f"`{path}` lines {lo}–{hi} (cited lines marked >):\n```\n{body}\n```")
    return "\n\n".join(out) or "(no evidence cited)"


def make(doc, table, repo, out, hunt=False):
    out.mkdir(parents=True, exist_ok=True)
    verdicts = {}
    for f in doc["findings"]:
        item = f["item"]
        meta = table[item]
        is_na = f.get("rating") == "na_candidate" and meta["gate"] in ("G1", "G2")
        is_hunt = (hunt and f.get("rating") == "needs_evidence" and meta["gate"] in ("G1", "G2")
                   and meta["checks"])
        if f.get("rating") != "likely_pass" and not is_hunt and not is_na:
            continue
        intro = DISCOVERY_INTRO
        parts = [intro.format(item=item, title=meta["title"], requirement=meta.get("requirement", ""),
                              na_when=meta.get("na_when", ""), summary=f.get("summary", ""),
                              evidence=json.dumps(f.get("evidence", [])))]
        verify = {c["id"]: c.get("verify", "") for c in meta["checks"]}
        claim = {'item': item, 'rating': f.get('rating'), 'summary': f.get('summary'),
                 'checks': f.get('checks'), 'evidence': f.get('evidence')}
        (out / f'{item}.claim.json').write_text(json.dumps(claim, indent=2) + '\n')
        from review_coverage import inventory
        sites = inventory(repo)['sites']
        for canonical in meta["checks"]:
            parts.append(f"## {canonical['id']}\n\n**Check:** {canonical.get('check') or ''}\n\n"
                         f"**How to verify:** {verify.get(canonical['id']) or '(none)'}\n\n"
                         '**Coverage policy:** ' + json.dumps({k: canonical[k] for k in
                          ('inventory_kinds', 'fields', 'rules', 'attempt_categories') if k in canonical}) + '\n\n'
                         '**Candidate sites (trace aliases and missed paths manually):** ' + json.dumps([
                          s for s in sites if s['kind'] in canonical.get('inventory_kinds', [])]))
        parts.append("## Your answer\n\nWrite this JSON to " + item + ".verdict.json in this folder (or put it in verdicts.json under \"" + item + "\"):\n"
                     "```json\n{\"verdict\": \"upheld | failed | unclear\",\n"
                     " \"checks\": [{\"id\": \"" + (meta["checks"][0]["id"] if meta.get("checks") else item + ".1") +
                     "\", \"result\": \"holds | fails | unclear\", \"evidence\": \"path:line\", "
                     "\"quote\": \"exact code\", \"note\": \"why\", \"coverage\": [], \"deviations\": [], \"attempts\": []}],\n"
                     " \"applicability\": \"absent | present | unclear\", \"evidence\": \"path:line\", \"quote\": \"exact code\",\n \"note\": \"one sentence\"}\n```\n"
                     "Verdict is **failed** if any check fails, **unclear** if none fails but any is unclear, "
                     "otherwise **upheld**. A failed check needs the quoted line that makes it false: `evidence` is "
                     "path:line, and `quote` is the exact text of that line. To cite two places, list both refs in "
                     "`evidence` (`a.py:12, b.yaml:40`) and put each line's text on its own line in `quote`. If the check "
                     "fails, add `\"violates\": [\"words copied exactly from the requirement\"]`.")
        (out / f"{item}.md").write_text("\n\n".join(parts) + "\n")
        verdicts[item] = {"verdict": "TODO", "checks": [], "note": "", "hunt": is_hunt}
        if is_na:
            verdicts[item].update(applicability="TODO", evidence="", quote="")
    (out / "verdicts.json").write_text(json.dumps(verdicts, indent=2) + "\n")
    print(f"Wrote {len(verdicts)} challenge sheet(s) to {out}. Fill in {out / 'verdicts.json'}.")


def apply(doc, verdicts, repo):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_findings import quote_found  # same quote check as the validator
    from review_coverage import inventory, ledger_problems, failure_rows, ADMISSION
    table = json.loads(CHECKS_FILE.read_text())
    sites = inventory(repo)['sites']
    changes, problems = [], []
    by_item = {f["item"]: f for f in doc["findings"]}
    def record(v):
        result = {k: v.get(k) for k in ('verdict', 'note', 'applicability', 'evidence', 'quote') if k in v}
        if doc.get('review_protocol') == 'coverage-first-v1':
            discovery = json.loads(json.dumps(v))
            result.update(protocol='coverage-first-v1', discovery=discovery,
                          discovery_sha256=hashlib.sha256(json.dumps(discovery, sort_keys=True).encode()).hexdigest())
        return result
    for item, v in verdicts.items():
        f = by_item.get(item)
        hunting = bool(v.get("hunt")) or (f is not None and f.get("rating") == "needs_evidence")
        if not f or f.get("rating") not in ("likely_pass", "needs_evidence", "na_candidate"):
            continue
        was_na = f.get("rating") == "na_candidate"
        verdict = v.get("verdict")
        results = {c.get("id"): c for c in v.get("checks", [])}
        checks = {c["id"]: c for c in f.get("checks", [])}
        if verdict not in ("failed", "unclear", "upheld"):
            problems.append(f"{item}: verdict must be upheld, failed, or unclear")
            continue
        # An independent discovery cannot uphold an admitted omission, even when
        # its label says holds. Invalid positives lower confidence, never pass.
        if doc.get('review_protocol') == 'coverage-first-v1' and v.get('applicability') == 'absent' and not was_na:
            verdict = 'unclear'
            for r in results.values():
                r['result'] = 'unclear'
            v = {**v, 'verdict': verdict}
        if doc.get('review_protocol') == 'coverage-first-v1' and v.get('applicability') != 'absent':
            for canonical in table[item]['checks']:
                r = results.get(canonical['id'])
                if r is None:
                    if verdict != 'failed':
                        verdict = 'unclear'
                    continue
                failures = failure_rows(r)
                demonstrated = next((x for x in failures if quote_found(repo, x.get('evidence'), x.get('quote'))
                                     and x.get('status') != 'unclear' and x.get('outcome') != 'unclear'), None)
                if demonstrated:
                    r.update(result='fails', evidence=demonstrated['evidence'], quote=demonstrated['quote'],
                             note=demonstrated.get('note') or demonstrated.get('trace'))
                    v.setdefault('violates', [table[item]['requirement']])
                    verdict = 'failed'
                elif r.get('result') == 'holds' and ledger_problems(r, canonical, repo, sites):
                    r['result'] = 'unclear'
                    if verdict != 'failed':
                        verdict = 'unclear'
            if ADMISSION.search(str(v.get('note', ''))) and verdict == 'upheld':
                verdict = 'unclear'
            if verdict == 'upheld' and v.get('applicability') != 'present':
                verdict = 'unclear'
                for r in results.values():
                    r['result'] = 'unclear'
            v = {**v, 'verdict': verdict}
        if was_na:
            applicability = v.get("applicability")
            if applicability not in ("absent", "present", "unclear"):
                problems.append(f"{item}: N/A challenge needs applicability absent, present, or unclear")
                continue
            if applicability == "absent":
                if (verdict != "upheld" or any(r.get("result") in ("fails", "unclear") for r in results.values())
                        or not quote_found(repo, v.get("evidence"), v.get("quote"))
                        or len(str(v.get("note", "")).split()) < 6):
                    problems.append(f"{item}: upholding N/A needs an upheld verdict, quoted code and a search explanation")
                    continue
                if table[item].get('na_when') == 'never':
                    problems.append(f'{item}: canonical N/A condition is never; absence cannot uphold')
                    continue
                f["challenge"] = record(v)
                changes.append(f"{item}: N/A challenge upheld")
                continue
            # An unproven absence must not hide a potentially applicable control.
            f["rating"] = "needs_evidence"
        if not was_na and verdict == "upheld" and not any(r.get("result") in ("fails", "unclear") for r in results.values()):
            if f.get("rating") == "likely_pass":
                for cid, r in results.items():
                    if cid in checks:
                        for field in ('coverage', 'deviations', 'attempts'):
                            if field in r:
                                checks[cid][field] = r[field]
                f["challenge"] = record(v)
            changes.append(f"{item}: {'hunt found nothing' if hunting else 'challenge upheld'}")
            continue
        for cid, r in results.items():
            c = checks.get(cid)
            if not c:
                continue
            if r.get("result") == "fails":
                if not quote_found(repo, r.get("evidence"), r.get("quote")):
                    problems.append(f"{item}: challenge says {cid} fails, but its quote isn't in the cited file; "
                                    f"fix evidence/quote in verdicts.json")
                    continue
                c.update(met="no", evidence=r.get("evidence"), quote=r.get("quote"),
                         note=f"[challenge] {r.get('note', '')}")
                f.setdefault("red_flags_found", []).append(f"{r.get('evidence')} {r.get('note', '')}".strip())
            elif r.get("result") == "unclear":
                c.update(met="unknown", note=f"[challenge: unclear] {r.get('note', '')}")
            for field in ('coverage', 'deviations', 'attempts'):
                if field in r:
                    c[field] = r[field]
        met = [c.get("met") for c in checks.values()]
        if "no" in met and v.get("violates"):
            # A challenger may write one phrase as a string; list("...") would split it into letters.
            new = [v["violates"]] if isinstance(v["violates"], str) else list(v["violates"])
            old = f.get("violates") or []
            old = [old] if isinstance(old, str) else old
            f["violates"] = list(dict.fromkeys(old + new))
        f["rating"] = "gap" if ("no" in met or f.get("red_flags_found")) else "needs_evidence"
        f["challenge"] = record(v)
        if was_na:
            f["challenge"]["applicability"] = v["applicability"]
            f["summary"] = f"N/A claim was not upheld: {v.get('note') or 'feature absence could not be established from the code'}"
            f["next_step"] = "Resolve the challenged feature or exposure and verify the applicable controls."
        changes.append(f"{item}: challenge {verdict} -> {f['rating']}")
    return changes, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["make", "apply"])
    ap.add_argument("findings")
    ap.add_argument("--repo")
    ap.add_argument("--out")
    ap.add_argument("--hunt", action="store_true")
    args = ap.parse_args()
    path = Path(args.findings)
    repo = Path(args.repo) if args.repo else path.resolve().parent
    out = Path(args.out) if args.out else repo / "brace-challenges"
    doc = json.loads(path.read_text())
    table = json.loads(CHECKS_FILE.read_text())
    if args.mode == "make":
        make(doc, table, repo, out, args.hunt)
        return
    verdicts = json.loads((out / "verdicts.json").read_text())
    # Parallel challengers can each write <ITEM>.verdict.json instead of editing verdicts.json.
    for vf in sorted(out.glob("*.verdict.json")):
        verdicts[vf.name.split(".")[0]] = json.loads(vf.read_text())
    todo = [k for k, v in verdicts.items() if v.get("verdict") == "TODO"]
    if todo:
        sys.exit(f"Fill in verdicts for: {', '.join(todo)}")
    changes, problems = apply(doc, verdicts, repo)
    path.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"Applied {len(changes)} verdict(s)." + ("\n  " + "\n  ".join(changes) if changes else ""))
    if problems:
        print(f"{len(problems)} problem(s):\n- " + "\n- ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
