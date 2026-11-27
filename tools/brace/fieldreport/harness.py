#!/usr/bin/env python3
"""Field-report harness for the open-agent-security scanner (standard library only).

Usage:
  python3 harness.py clone LIST DIR             # shallow-clone each owner/name in LIST into DIR/<index>
  python3 harness.py scan DIR OUT --scanner PATH  # run the scanner on each clone, write OUT (JSON)
  python3 harness.py label OUT CSV [--sample N --seed S]  # reviewer CSV: all critical/high + N sampled others
  python3 harness.py stats OUT CSV              # Markdown prevalence/count tables and FP rate per rule

Clone contents are untrusted: nothing from a clone is imported or executed.
Git hooks and symlinks are disabled; the scanner runs as `python3 -I` with --no-config
from a neutral temp directory, so a repo's own config cannot suppress findings (the repo's
.open-agent-security-ignore and inline suppressions still apply; scan records them).
"""
import argparse
import collections
import csv
import json
import os
import random
import subprocess
import sys
import tempfile
import time

CLONE_TIMEOUT = 120
SCAN_TIMEOUT = 900
SEVERITIES = ["critical", "high", "medium", "low", "info"]


def _git_env():
    env = dict(os.environ)
    env.update(GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="true", GIT_LFS_SKIP_SMUDGE="1",
               GIT_CONFIG_NOSYSTEM="1")
    return env


def _filter_supported():
    out = subprocess.run(["git", "clone", "-h"], capture_output=True, text=True)
    return "--filter" in (out.stdout + out.stderr)


def cmd_clone(args):
    repos = [l.strip() for l in open(args.list) if l.strip() and not l.startswith("#")]
    os.makedirs(args.dir, exist_ok=True)
    mpath = os.path.join(args.dir, "manifest.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    filt = ["--filter=blob:limit=2m"] if _filter_supported() else []
    env = _git_env()
    for i, repo in enumerate(repos):
        key = str(i)
        dest = os.path.join(args.dir, key)
        if manifest.get(key, {}).get("status") == "ok" and os.path.isdir(dest):
            continue
        if os.path.exists(dest):
            subprocess.run(["rm", "-rf", dest])
        cmd = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.symlinks=false",
               "-c", "protocol.file.allow=never", "clone", "--depth", "1", "--single-branch",
               "--no-tags", "--quiet", *filt, f"https://github.com/{repo}.git", dest]
        t0 = time.time()
        entry = {"repo": repo}
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True,
                               timeout=CLONE_TIMEOUT, stdin=subprocess.DEVNULL)
            if r.returncode == 0:
                sha = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                                     capture_output=True, text=True, env=env).stdout.strip()
                entry.update(status="ok", sha=sha)
            else:
                entry.update(status="failed", error=r.stderr.strip()[-300:])
        except subprocess.TimeoutExpired:
            entry.update(status="timeout")
        entry["seconds"] = round(time.time() - t0, 1)
        if entry["status"] != "ok":
            subprocess.run(["rm", "-rf", dest])
        manifest[key] = entry
        print(f"[{i}] {entry['status']} {entry['seconds']}s", file=sys.stderr)
        with open(mpath, "w") as f:
            json.dump(manifest, f, indent=1)
    ok = sum(1 for e in manifest.values() if e.get("status") == "ok")
    print(f"cloned {ok}/{len(repos)}")


def _findings(data):
    if isinstance(data, dict):
        for k in ("findings", "results"):
            if isinstance(data.get(k), list):
                return data[k]
    return data if isinstance(data, list) else []


def _f(f, *keys):
    for k in keys:
        v = f.get(k)
        if v not in (None, ""):
            return v
    loc = f.get("location") or {}
    for k in keys:
        if isinstance(loc, dict) and loc.get(k) not in (None, ""):
            return loc[k]
    return ""


def cmd_scan(args):
    scanner = os.path.abspath(args.scanner)
    manifest = json.load(open(os.path.join(args.dir, "manifest.json")))
    out = {}
    neutral = tempfile.mkdtemp(prefix="oas-scan-")
    keys = [k for k in sorted(manifest, key=int) if manifest[k].get("status") == "ok"]

    def one(key):
        target = os.path.abspath(os.path.join(args.dir, key))
        rec = {"sha": manifest[key].get("sha"),
               "had_config": os.path.exists(os.path.join(target, ".open-agent-security.toml")),
               "had_ignore_file": os.path.exists(os.path.join(target, ".open-agent-security-ignore"))}
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, "-I", scanner, target, "--json",
                                "--fail-on", "none", "--no-config"], cwd=neutral,
                               capture_output=True, text=True, timeout=SCAN_TIMEOUT,
                               stdin=subprocess.DEVNULL)
            rec["exit_code"] = r.returncode
            try:
                data = json.loads(r.stdout)
            except ValueError:
                data = None
                rec["error"] = (r.stderr or r.stdout).strip()[-500:]
        except subprocess.TimeoutExpired:
            data, rec["exit_code"], rec["error"] = None, None, "timeout"
        rec["runtime"] = round(time.time() - t0, 2)
        fl = []
        for f in _findings(data):
            fl.append({"rule": _f(f, "rule", "rule_id", "ruleId"),
                       "severity": str(_f(f, "severity", "level")).lower(),
                       "file": _f(f, "file", "path"), "line": _f(f, "line", "start_line"),
                       "detail": _f(f, "detail", "message", "title"), "id": _f(f, "id", "fingerprint")})
        rec["findings"] = fl
        d = data if isinstance(data, dict) else {}
        sev = [f["severity"] for f in fl if f["severity"] in SEVERITIES]
        rec["verdict"] = ("error" if data is None else "incomplete" if d.get("incomplete")
                          else min(sev, key=SEVERITIES.index) if sev else "clean")
        rec["suppressed"] = d.get("suppressed", 0)  # .open-agent-security-ignore / inline; not disabled by --no-config
        rec["suppressed_findings"] = [{"rule": f.get("rule"), "file": f.get("file"), "line": f.get("line"),
                                       "suppression": f.get("suppression")} for f in d.get("suppressed_findings", [])]
        rec["notes"] = data.get("notes", []) if isinstance(data, dict) else []
        rec["by_rule"] = dict(collections.Counter(f["rule"] for f in fl))
        rec["by_severity"] = dict(collections.Counter(f["severity"] for f in fl))
        return key, rec
        print(f"[{key}] {len(fl)} findings exit={rec['exit_code']} {rec['runtime']}s", file=sys.stderr)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for key, rec in pool.map(one, keys):
            out[key] = rec
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"scanned {len(out)} repos -> {args.out}")


COLS = ["repo_index", "rule", "severity", "file", "line", "detail", "id", "label", "reason"]


def cmd_label(args):
    data = json.load(open(args.out))
    top, rest = [], []
    for key in sorted(data, key=int):
        for f in data[key]["findings"]:
            row = {"repo_index": key, **{c: f.get(c, "") for c in COLS[1:7]}, "label": "", "reason": ""}
            (top if f["severity"] in ("critical", "high") else rest).append(row)
    rng = random.Random(args.seed)
    sample = rng.sample(rest, min(args.sample, len(rest)))
    with open(args.csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(top + sample)
    print(f"wrote {len(top)} critical/high + {len(sample)} sampled rows -> {args.csv}")


def cmd_stats(args):
    data = json.load(open(args.out))
    n = len(data)
    errors = sum(1 for r in data.values() if r.get("error"))
    prev, counts = collections.Counter(), collections.defaultdict(collections.Counter)
    for r in data.values():
        for rule in r["by_rule"]:
            prev[rule] += 1
        for f in r["findings"]:
            counts[f["rule"]][f["severity"]] += 1
    print(f"Repos scanned: {n} (scan errors: {errors}); repos with any finding: "
          f"{sum(1 for r in data.values() if r['findings'])}\n")
    print("| Rule | Repos | Prevalence | " + " | ".join(SEVERITIES) + " | Total |")
    print("|---|---|---|" + "---|" * (len(SEVERITIES) + 1))
    for rule in sorted(counts, key=lambda k: -sum(counts[k].values())):
        c = counts[rule]
        print(f"| {rule} | {prev[rule]} | {100 * prev[rule] / max(n, 1):.1f}% | "
              + " | ".join(str(c.get(s, 0)) for s in SEVERITIES) + f" | {sum(c.values())} |")
    if args.csv and os.path.exists(args.csv):
        lab = collections.defaultdict(collections.Counter)
        for row in csv.DictReader(open(args.csv, newline="")):
            v = row.get("label", "").strip().lower()
            if v in ("tp", "fp", "intended"):
                lab[row["rule"]][v] += 1
        print("\n| Rule | Labelled | TP | FP | Intended | FP rate |")
        print("|---|---|---|---|---|---|")
        for rule in sorted(lab):
            c = lab[rule]
            t = sum(c.values())
            print(f"| {rule} | {t} | {c['tp']} | {c['fp']} | {c['intended']} | {100 * c['fp'] / t:.1f}% |")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("clone"); a.add_argument("list"); a.add_argument("dir"); a.set_defaults(fn=cmd_clone)
    a = sp.add_parser("scan"); a.add_argument("dir"); a.add_argument("out")
    a.add_argument("--jobs", type=int, default=1); a.add_argument("--scanner", required=True); a.set_defaults(fn=cmd_scan)
    a = sp.add_parser("label"); a.add_argument("out"); a.add_argument("csv")
    a.add_argument("--sample", type=int, default=100); a.add_argument("--seed", type=int, default=1)
    a.set_defaults(fn=cmd_label)
    a = sp.add_parser("stats"); a.add_argument("out"); a.add_argument("csv", nargs="?")
    a.set_defaults(fn=cmd_stats)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
