#!/usr/bin/env python3
"""Challenge every likely_pass with a fresh look at the code.

  python challenge.py make  FINDINGS.json [--repo DIR] [--out DIR] [--hunt]
      Writes one sheet per likely_pass item to DIR (default: <repo>/brace-challenges/),
      and with --hunt also one per G1 or G2 item rated needs_evidence (a gap hunt),
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
import json
import re
import sys
from pathlib import Path

CHECKS_FILE = Path(__file__).resolve().parent.parent / "references" / "checks.json"
REF = re.compile(r"([\w./-]*[\w-]):(\d+)(?:-(\d+))?")
CONTEXT = 12

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
        is_hunt = (hunt and f.get("rating") == "needs_evidence" and meta["gate"] in ("G1", "G2")
                   and meta["checks"])
        if f.get("rating") != "likely_pass" and not is_hunt:
            continue
        intro = HUNT_INTRO if is_hunt else SHEET_INTRO
        parts = [intro.format(item=item, title=meta["title"], requirement=meta.get("requirement", ""))]
        verify = {c["id"]: c.get("verify", "") for c in meta["checks"]}
        for c in f.get("checks", []):
            parts.append(f"## {c['id']}\n\n**Check:** {c.get('check') or ''}\n\n"
                         f"**How to verify:** {verify.get(c['id']) or '(none)'}\n\n"
                         f"**Reviewer's evidence:** {c.get('evidence')} — \"{c.get('quote')}\"\n\n"
                         f"**Reviewer's note:** {c.get('note')}\n\n" + excerpt(repo, c.get("evidence")))
        parts.append("## Your answer\n\nWrite this JSON to " + item + ".verdict.json in this folder (or put it in verdicts.json under \"" + item + "\"):\n"
                     "```json\n{\"verdict\": \"upheld | failed | unclear\",\n"
                     " \"checks\": [{\"id\": \"" + (f["checks"][0]["id"] if f.get("checks") else item + ".1") +
                     "\", \"result\": \"holds | fails | unclear\", \"evidence\": \"path:line\", "
                     "\"quote\": \"exact code\", \"note\": \"why\"}],\n \"note\": \"one sentence\"}\n```\n"
                     "Verdict is **failed** if any check fails, **unclear** if none fails but any is unclear, "
                     "otherwise **upheld**. A failed check needs the quoted line that makes it false.")
        (out / f"{item}.md").write_text("\n\n".join(parts) + "\n")
        verdicts[item] = {"verdict": "TODO", "checks": [], "note": "", "hunt": is_hunt}
    (out / "verdicts.json").write_text(json.dumps(verdicts, indent=2) + "\n")
    print(f"Wrote {len(verdicts)} challenge sheet(s) to {out}. Fill in {out / 'verdicts.json'}.")


def apply(doc, verdicts, repo):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_findings import quote_found  # same quote check as the validator
    changes, problems = [], []
    by_item = {f["item"]: f for f in doc["findings"]}
    for item, v in verdicts.items():
        f = by_item.get(item)
        hunting = bool(v.get("hunt")) or (f is not None and f.get("rating") == "needs_evidence")
        if not f or f.get("rating") not in ("likely_pass", "needs_evidence"):
            continue
        verdict = v.get("verdict")
        results = {c.get("id"): c for c in v.get("checks", [])}
        checks = {c["id"]: c for c in f.get("checks", [])}
        if verdict == "upheld" and not any(r.get("result") in ("fails", "unclear") for r in results.values()):
            if f.get("rating") == "likely_pass":
                f["challenge"] = {"verdict": "upheld", "note": v.get("note", "")}
            changes.append(f"{item}: {'hunt found nothing' if hunting else 'challenge upheld'}")
            continue
        if verdict not in ("failed", "unclear", "upheld"):
            problems.append(f"{item}: verdict must be upheld, failed, or unclear")
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
        met = [c.get("met") for c in checks.values()]
        if "no" in met and v.get("violates"):
            # A challenger may write one phrase as a string; list("...") would split it into letters.
            new = [v["violates"]] if isinstance(v["violates"], str) else list(v["violates"])
            old = f.get("violates") or []
            old = [old] if isinstance(old, str) else old
            f["violates"] = list(dict.fromkeys(old + new))
        f["rating"] = "gap" if ("no" in met or f.get("red_flags_found")) else "needs_evidence"
        f["challenge"] = {"verdict": verdict, "note": v.get("note", "")}
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
