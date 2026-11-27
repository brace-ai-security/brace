"""Import red-team and eval results as BRACE evidence.

Reads a results file from garak, PyRIT, promptfoo or UK AISI Inspect, summarizes
it (tool, version, date, pass and fail counts, attack categories) and adds an
evidence entry to chosen items in `.brace/record.yaml`.

Rules this module keeps:

* It never sets an item's outcome to `pass`. A run where any attack got through
  marks a `not_reviewed` item as `gap`; an existing `pass` or `na` is left for a
  person to review, with a warning.
* The results file is untrusted. It is read as JSON only (never executed or
  unpickled), size-limited, and every string copied from it is cleaned and
  shortened before it reaches the record or the terminal.

Formats (checked against each tool's source, November 2026):

* garak  `report.jsonl`: `init` row has `garak_version`, `start_time`;
  `eval` rows have `probe`, `detector`, `passed`, `fails`, `total_evaluated`.
* promptfoo `promptfoo eval -o out.json`: `OutputFile` with `results`
  (`EvaluateSummaryV3`: `version`, `timestamp`, `stats`, `results[]`) and
  `metadata.promptfooVersion`; red-team rows carry `testCase.metadata.pluginId`.
* PyRIT: a JSON list (or JSONL) of `AttackResult.model_dump(mode="json")`
  (`outcome` = success|failure|undetermined) or of `Score` dumps
  (`score_type`, `score_value`, `score_category`).
* Inspect: an eval log in JSON format (`inspect eval --log-format=json` or
  `inspect log convert --to json`): `version`, `status`, `eval.task`,
  `eval.packages`, `eval.created`, `results`, `samples[].scores`.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

TOOLS = ("garak", "pyrit", "promptfoo", "inspect")
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
MAX_ROWS = 2_000_000
MAX_CATEGORIES = 40
IMPORT_TAG = "brace.py import-results"


class ImportProblem(Exception):
    """The results file can't be used. Message is plain language."""


# --------------------------------------------------------------------------
# Attack categories and the BRACE items they bear on
# --------------------------------------------------------------------------

CATEGORY_LABEL = {
    "prompt_injection": "prompt injection",
    "jailbreak": "jailbreak",
    "data_exfiltration": "data exfiltration",
    "excessive_agency": "excessive agency",
    "tool_misuse": "tool misuse",
    "pii_leakage": "personal data leakage",
    "system_prompt_leakage": "system prompt leakage",
    "credential_leakage": "credential leakage",
    "unsafe_output": "unsafe output (code, SQL, markup)",
    "access_control": "access control bypass",
    "memory_poisoning": "memory poisoning",
    "retrieval_poisoning": "retrieval poisoning",
    "supply_chain": "supply chain (hallucinated packages)",
    "resource_abuse": "resource exhaustion",
    "harmful_content": "harmful content",
    "other": "other",
}

# Suggestions only. A person decides which items the run is evidence for.
CATEGORY_ITEMS = {
    "prompt_injection": ["R02", "R01", "B05"],
    "jailbreak": ["R02", "R10"],
    "data_exfiltration": ["R03", "B09"],
    "excessive_agency": ["B01", "B02", "B05", "E08"],
    "tool_misuse": ["B05", "R01", "E04", "E06"],
    "pii_leakage": ["R03", "R05"],
    "system_prompt_leakage": ["R03", "B12"],
    "credential_leakage": ["R03", "B03"],
    "unsafe_output": ["R01", "R03"],
    "access_control": ["B02", "E08"],
    "memory_poisoning": ["R05", "R06"],
    "retrieval_poisoning": ["R04"],
    "supply_chain": ["E02"],
    "resource_abuse": ["B07"],
    "harmful_content": [],
    "other": [],
}

# First match wins. Patterns run on the lower-cased probe, plugin or task name.
_RULES: list[tuple[str, str]] = [
    # garak probe modules
    (r"^(latentinjection|promptinject|web_injection\.(?!markdown)|goodside\.(tag|threat))", "prompt_injection"),
    (r"^web_injection\.markdown|markdown.*exfil|colabaimage|stringassemblydataexfil", "data_exfiltration"),
    (r"^(dan|tap|suffix|grandma|visual_jailbreak|fitd|goat|encoding|smuggling|phrasing|doctor|badchars|"
     r"dra|sata)\b", "jailbreak"),
    (r"^(xss|exploitation|ansiescape)\b", "unsafe_output"),
    (r"^(leakreplay|divergence)\b", "pii_leakage"),
    (r"^apikey\b", "credential_leakage"),
    (r"^sysprompt_extraction\b", "system_prompt_leakage"),
    (r"^packagehallucination\b", "supply_chain"),
    (r"^(malwaregen|lmrc|realtoxicityprompts|continuation|donotanswer|atkgen|misleading|topic|snowball|av_spam_scanning)\b",
     "harmful_content"),
    # promptfoo plugins and strategies; PyRIT and Inspect names
    (r"indirect-prompt-injection|prompt.?injection|system-prompt-override|special-token-injection|"
     r"ascii-smuggling|hijacking|xpia|cross.?domain", "prompt_injection"),
    (r"prompt-extraction|system.?prompt.?(leak|extract)", "system_prompt_leakage"),
    (r"data-exfil|exfiltrat|rag-document-exfiltration|ssrf", "data_exfiltration"),
    (r"excessive-agency|agency|goal-misalignment", "excessive_agency"),
    (r"shell-injection|sql-injection|tool-discovery|mcp|tool.?misuse|debug-access", "tool_misuse"),
    (r"^pii|pii:|harmful:privacy|cross-session-leak|privacy|personal.?data|pii", "pii_leakage"),
    (r"credential|api.?key|secret", "credential_leakage"),
    (r"bola|bfla|rbac|access.?control", "access_control"),
    (r"memory-poisoning|memory.?poison", "memory_poisoning"),
    (r"rag-poisoning|retrieval.?poison", "retrieval_poisoning"),
    (r"reasoning-dos|divergent-repetition|denial.?of.?service", "resource_abuse"),
    (r"jailbreak|crescendo|pair|tree.?of.?attacks|many.?shot|skeleton|flip|roleplay|base64|rot13|leetspeak|"
     r"homoglyph|multilingual|best.?of.?n|composite|pliny|likert|math-prompt|citation|gcg", "jailbreak"),
    (r"harmful|toxic|hate|bias|violence|self-harm|harmbench|beavertails|donotanswer|xstest|aegis|"
     r"misinformation|hallucination|overreliance|politics|religion|competitors|contracts|imitation", "harmful_content"),
]
_RULES_C = [(re.compile(p), c) for p, c in _RULES]


def categorize(name: str) -> str:
    n = name.lower()
    for rx, cat in _RULES_C:
        if rx.search(n):
            return cat
    return "other"


# --------------------------------------------------------------------------
# Untrusted text
# --------------------------------------------------------------------------

_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f​-‏‪-‮⁦-⁩]")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.:/@+ -]")


def clean(value, limit: int = 80) -> str:
    """Make an untrusted value safe to print and store: no control or bidi
    characters, no newlines, bounded length."""
    s = _CTRL.sub("", str(value)).strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def clean_name(value, limit: int = 80) -> str:
    """Names (probes, plugins, versions) keep a narrow character set."""
    return _SAFE_NAME.sub("", clean(value, limit * 2))[:limit]


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

@dataclass
class Summary:
    tool: str
    version: str = "unknown"
    run_date: str | None = None
    passed: int = 0
    failed: int = 0
    other: int = 0  # errors, undetermined, unscored
    categories: dict = field(default_factory=dict)  # category -> {"passed": n, "failed": n, "names": set}
    notes: list = field(default_factory=list)
    other_label: str = "not scored"

    def add(self, name: str, passed: int = 0, failed: int = 0, other: int = 0) -> None:
        self.passed += passed
        self.failed += failed
        self.other += other
        cat = categorize(name) if name else "other"
        slot = self.categories.setdefault(cat, {"passed": 0, "failed": 0, "other": 0, "names": set()})
        slot["other"] += other
        slot["passed"] += passed
        slot["failed"] += failed
        if name and len(slot["names"]) < MAX_CATEGORIES:
            slot["names"].add(clean_name(name))

    @property
    def total(self) -> int:
        return self.passed + self.failed

    def suggested_items(self, known: set[str]) -> list[str]:
        out: list[str] = []
        for cat in self.categories:
            for item in CATEGORY_ITEMS.get(cat, []):
                if item in known and item not in out:
                    out.append(item)
        return out

    def category_text(self) -> str:
        parts = []
        for cat, s in sorted(self.categories.items(), key=lambda kv: (-kv[1]["failed"], kv[0])):
            text = f"{s['failed']} failed of {s['passed'] + s['failed']}"
            if s.get("other"):
                text += f", {s['other']} {self.other_label}"
            parts.append(f"{CATEGORY_LABEL.get(cat, cat)} ({text})")
        return "; ".join(parts) or "none found"


def _iso_date(value) -> str | None:
    if not value:
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", str(value))
    if not m:
        return None
    try:
        _dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None
    return m.group(1)


def _int(v) -> int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int) and v >= 0:
        return v
    if isinstance(v, float) and v >= 0 and v == v:
        return int(v)
    return 0


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------

def read_bytes(path: Path, max_bytes: int) -> bytes:
    try:
        st = path.stat()
    except OSError as exc:
        raise ImportProblem(f"Can't open {path}: {exc.strerror or exc}.")
    if not path.is_file():
        raise ImportProblem(f"{path} is not a regular file.")
    if st.st_size > max_bytes:
        raise ImportProblem(f"{path} is {st.st_size:,} bytes, over the {max_bytes:,}-byte limit. "
                            "Use --max-bytes to raise the limit if you trust this file.")
    with open(path, "rb") as fh:
        data = fh.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ImportProblem(f"{path} grew past the size limit while it was being read.")
    if data[:2] == b"PK":
        raise ImportProblem(f"{path} is a zip archive (for example an Inspect .eval log). "
                            "Convert it to JSON first, for example: inspect log convert --to json")
    return data


def _loads(text: str, where: str):
    try:
        return json.loads(text)
    except RecursionError:
        raise ImportProblem(f"{where} is nested too deeply to read safely.")
    except ValueError as exc:
        raise ImportProblem(f"{where} is not valid JSON ({clean(exc, 120)}).")


def parse_json(data: bytes, label: str):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportProblem(f"{label} is not UTF-8 text.")
    return _loads(text, label)


def parse_jsonl(data: bytes, label: str) -> list:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportProblem(f"{label} is not UTF-8 text.")
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if len(rows) >= MAX_ROWS:
            raise ImportProblem(f"{label} has more than {MAX_ROWS:,} rows.")
        rows.append(_loads(line, f"{label} line {n}"))
    return rows


# --------------------------------------------------------------------------
# Per-tool parsers
# --------------------------------------------------------------------------

def parse_garak(data: bytes, label: str) -> Summary:
    s = Summary("garak", other_label="unscoreable")
    evals = 0
    try:
        rows = parse_jsonl(data, label)
    except ImportProblem as exc:
        raise ImportProblem(f"{exc.args[0]} A garak report.jsonl has one JSON object per line.")
    for row in rows:
        if not isinstance(row, dict):
            continue
        kind = row.get("entry_type")
        if kind == "init":
            s.version = clean_name(row.get("garak_version") or "unknown", 40) or "unknown"
            s.run_date = _iso_date(row.get("start_time")) or s.run_date
        elif kind == "eval":
            evals += 1
            passed = _int(row.get("passed"))
            if "fails" in row:
                failed = _int(row.get("fails"))
            else:  # older reports: total_evaluated (or total) minus passed
                failed = max(_int(row.get("total_evaluated", row.get("total"))) - passed, 0)
            s.add(str(row.get("probe") or ""), passed, failed, _int(row.get("nones")))
        elif kind == "completion" and not s.run_date:
            s.run_date = _iso_date(row.get("end_time"))
    if not evals:
        raise ImportProblem(f"{label} has no garak 'eval' rows. Is it a finished garak report.jsonl "
                            "(not the hitlog or the HTML report)?")
    s.notes.append("garak counts each probe and detector pair; 'failed' means the detector found a hit.")
    return s


def parse_promptfoo(data: bytes, label: str) -> Summary:
    doc = parse_json(data, label)
    if not isinstance(doc, dict) or not isinstance(doc.get("results"), dict):
        raise ImportProblem(f"{label} doesn't look like promptfoo output. Save it with: promptfoo eval -o results.json")
    summary = doc["results"]
    rows = summary.get("results")
    if not isinstance(rows, list):
        raise ImportProblem(f"{label} has no results list. Use promptfoo's JSON output (-o results.json).")
    s = Summary("promptfoo", other_label="errored")
    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    s.version = clean_name(meta.get("promptfooVersion") or "unknown", 40) or "unknown"
    s.run_date = _iso_date(summary.get("timestamp")) or _iso_date(meta.get("evaluationCreatedAt"))
    for row in rows[:MAX_ROWS]:
        if not isinstance(row, dict):
            continue
        tc = row.get("testCase") if isinstance(row.get("testCase"), dict) else {}
        tmeta = tc.get("metadata") if isinstance(tc.get("metadata"), dict) else {}
        rmeta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        plugin = str(tmeta.get("pluginId") or rmeta.get("pluginId") or "")
        strategy = str(tmeta.get("strategyId") or rmeta.get("strategyId") or "")
        name = plugin or strategy or "unlabelled test"
        # failureReason 2 = error in promptfoo's ResultFailureReason enum
        if row.get("error") or row.get("failureReason") == 2:
            s.add(name, other=1)
        elif row.get("success") is True:
            s.add(name, passed=1)
        else:
            s.add(name, failed=1)
    stats = summary.get("stats") if isinstance(summary.get("stats"), dict) else {}
    if stats and (_int(stats.get("successes")), _int(stats.get("failures"))) != (s.passed, s.failed):
        s.notes.append(f"promptfoo's own totals ({_int(stats.get('successes'))} passed, "
                       f"{_int(stats.get('failures'))} failed) differ from the rows read.")
    return s


def _pyrit_rows(doc) -> list:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("attack_results", "results", "scores"):
            if isinstance(doc.get(key), list):
                return doc[key]
        return [doc]
    return []


def parse_pyrit(data: bytes, label: str) -> Summary:
    stripped = data.lstrip()
    if stripped[:1] in (b"[", b"{") and not (stripped[:1] == b"{" and b"\n{" in stripped.strip()):
        doc = parse_json(data, label)
    else:
        doc = parse_jsonl(data, label)
    s = Summary("pyrit", other_label="undetermined")
    if isinstance(doc, dict):
        s.version = clean_name(doc.get("pyrit_version") or "unknown", 40) or "unknown"
    rows = _pyrit_rows(doc)
    seen = 0
    for row in rows[:MAX_ROWS]:
        if not isinstance(row, dict):
            continue
        if "outcome" in row:  # AttackResult
            seen += 1
            ident = row.get("atomic_attack_identifier") or row.get("attack_identifier") or {}
            name = ""
            if isinstance(ident, dict):
                name = str(ident.get("class_name") or ident.get("__type__") or ident.get("name") or "")
            meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            name = str(meta.get("category") or meta.get("harm_category") or name or "attack")
            outcome = str(row.get("outcome")).lower()
            if outcome == "success":  # the attack reached its objective
                s.add(name, failed=1)
            elif outcome == "failure":
                s.add(name, passed=1)
            else:
                s.add(name, other=1)
            s.run_date = max(filter(None, [s.run_date, _iso_date(row.get("timestamp"))]), default=None)
        elif "score_value" in row and "score_type" in row:  # Score
            seen += 1
            cats = row.get("score_category")
            name = str(cats[0]) if isinstance(cats, list) and cats else ""
            if not name:
                sci = row.get("scorer_class_identifier")
                name = str(sci.get("class_name") or "") if isinstance(sci, dict) else ""
            if row.get("score_type") == "true_false":
                v = str(row.get("score_value")).strip().lower()
                if v == "true":  # PyRIT true/false scorers answer "was the objective met?"
                    s.add(name, failed=1)
                elif v == "false":
                    s.add(name, passed=1)
                else:
                    s.add(name, other=1)
            else:
                s.add(name, other=1)
            s.run_date = max(filter(None, [s.run_date, _iso_date(row.get("timestamp"))]), default=None)
    if not seen:
        raise ImportProblem(f"{label} has no PyRIT attack results or scores. Export them as JSON, for example "
                            "[r.model_dump(mode='json') for r in memory.get_attack_results()].")
    s.notes.append("PyRIT: an attack with outcome 'success' (or a true/false score of 'true') counts as failed.")
    return s


def _inspect_sample_value(v, invert: bool):
    """Return True (held), False (attack got through) or None (unknown)."""
    if isinstance(v, str):
        u = v.strip().upper()
        good = {"C": True, "I": False, "P": None, "N": None}.get(u)
    elif isinstance(v, bool):
        good = v
    elif isinstance(v, (int, float)):
        good = True if v >= 1 else (False if v <= 0 else None)
    else:
        good = None
    if good is None:
        return None
    return (not good) if invert else good


def parse_inspect(data: bytes, label: str, invert: bool = False) -> Summary:
    doc = parse_json(data, label)
    if not isinstance(doc, dict) or not isinstance(doc.get("eval"), dict):
        raise ImportProblem(f"{label} doesn't look like an Inspect eval log in JSON format.")
    ev = doc["eval"]
    s = Summary("inspect", other_label="unscored or partial")
    pk = ev.get("packages") if isinstance(ev.get("packages"), dict) else {}
    s.version = clean_name(pk.get("inspect_ai") or "unknown", 40) or "unknown"
    s.run_date = _iso_date(ev.get("created"))
    task = str(ev.get("task") or "")
    tags = [str(t) for t in (ev.get("tags") or []) if isinstance(t, str)][:20]
    names = [task] + tags
    name = next((n for n in names if categorize(n) != "other"), task or "inspect task")
    status = str(doc.get("status") or "unknown")
    if status != "success":
        s.notes.append(f"The Inspect run status is '{clean_name(status, 20)}', not 'success'; results may be partial.")
    samples = doc.get("samples")
    if isinstance(samples, list) and samples:
        for smp in samples[:MAX_ROWS]:
            if not isinstance(smp, dict) or not isinstance(smp.get("scores"), dict) or not smp["scores"]:
                s.add(name, other=1)
                continue
            first = next(iter(smp["scores"].values()))
            val = first.get("value") if isinstance(first, dict) else None
            held = _inspect_sample_value(val, invert)
            if held is True:
                s.add(name, passed=1)
            elif held is False:
                s.add(name, failed=1)
            else:
                s.add(name, other=1)
    else:
        res = doc.get("results") if isinstance(doc.get("results"), dict) else {}
        total = _int(res.get("completed_samples") or res.get("total_samples"))
        s.add(name, other=total)
        s.notes.append("The log has no samples, so pass and fail counts are unknown; only metrics were read.")
    res = doc.get("results") if isinstance(doc.get("results"), dict) else {}
    for sc in (res.get("scores") or [])[:10]:
        if isinstance(sc, dict) and isinstance(sc.get("metrics"), dict):
            for mname, m in list(sc["metrics"].items())[:5]:
                if isinstance(m, dict) and isinstance(m.get("value"), (int, float)):
                    s.notes.append(f"Inspect metric {clean_name(sc.get('name'), 30)}/{clean_name(mname, 30)} = "
                                   f"{round(float(m['value']), 4)}")
    s.notes.append("Inspect: score polarity is set by the task. By default a correct (C, 1) score counts as "
                   "the defence holding" + (" (inverted with --invert)." if invert else "; use --invert if not."))
    return s


def summarize(tool: str, path: Path, max_bytes: int = DEFAULT_MAX_BYTES, invert: bool = False) -> tuple[Summary, str]:
    if tool not in TOOLS:
        raise ImportProblem(f"Unknown tool '{clean(tool, 20)}'. Choose one of: {', '.join(TOOLS)}.")
    data = read_bytes(path, max_bytes)
    digest = hashlib.sha256(data).hexdigest()
    label = path.name
    if tool == "garak":
        s = parse_garak(data, label)
    elif tool == "promptfoo":
        s = parse_promptfoo(data, label)
    elif tool == "pyrit":
        s = parse_pyrit(data, label)
    else:
        s = parse_inspect(data, label, invert)
    return s, digest


# --------------------------------------------------------------------------
# Writing evidence into record.yaml
# --------------------------------------------------------------------------

def evidence_note(s: Summary, digest: str) -> str:
    verdict = (f"{s.failed} attack(s) got through: evidence of a gap" if s.failed
               else "no attack got through in this run; a person must still judge whether it covers the item")
    other = f", {s.other} {s.other_label}" if s.other else ""
    return clean(
        f"{IMPORT_TAG}: {s.tool} {s.version}. {s.passed} passed, {s.failed} failed{other}. {verdict}. "
        f"Categories: {s.category_text()}. sha256:{digest}", 2000)


_ITEM_LINE = re.compile(r"^  ([BRACE]\d{2}):\s*(#.*)?$")


def _yaml_str(v: str) -> str:
    return json.dumps(v, ensure_ascii=True)  # a JSON string is a valid YAML double-quoted scalar


def _patch_text(text: str, item: str, entry: dict, new_outcome: str | None) -> str | None:
    """Add `entry` to `item` keeping comments. Returns None if the layout isn't
    one this simple patcher understands (caller falls back to a full rewrite)."""
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if _ITEM_LINE.match(ln) and _ITEM_LINE.match(ln).group(1) == item), None)
    if start is None:
        return None
    end = start + 1
    while end < len(lines) and (lines[end].startswith("    ") or not lines[end].strip()):
        end += 1
    # trailing blank lines belong to the gap between items
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    block = lines[start + 1:end]
    if new_outcome:
        for i, ln in enumerate(block):
            if re.match(r"^    outcome:\s*\S", ln):
                block[i] = f"    outcome: {new_outcome}"
                break
        else:
            return None
    ev = next((i for i, ln in enumerate(block) if re.match(r"^    evidence:", ln)), None)

    def entry_lines(dash: int) -> list[str]:
        pad = " " * dash
        keys = list(entry)
        out = [f"{pad}- {keys[0]}: {_yaml_str(entry[keys[0]])}"]
        out += [f"{pad}  {k}: {_yaml_str(entry[k])}" for k in keys[1:]]
        return out

    if ev is None:
        block += ["    evidence:"] + entry_lines(6)
    else:
        rest = re.sub(r"\s+#.*$", "", block[ev][len("    evidence:"):]).strip()
        if rest.startswith("#"):
            rest = ""
        if rest == "[]":
            block[ev] = "    evidence:"
            block[ev + 1:ev + 1] = entry_lines(6)
        elif rest == "":
            j = ev + 1
            dash = None
            while j < len(block) and (block[j].startswith("     ") or block[j].startswith("    -") or not block[j].strip()):
                if dash is None and block[j].lstrip().startswith("- "):
                    dash = len(block[j]) - len(block[j].lstrip())
                j += 1
            while j > ev + 1 and not block[j - 1].strip():
                j -= 1
            block[j:j] = entry_lines(dash if dash is not None else 6)
        else:
            return None  # flow-style list or something unusual
    lines[start + 1:end] = block
    return "\n".join(lines)


@dataclass
class ItemResult:
    item: str
    action: str  # "added" | "skipped"
    outcome_before: str
    outcome_after: str
    message: str = ""


def apply_to_record(record_path: Path, items: list[str], entry: dict, digest: str, failed: int,
                    dry_run: bool = False, validate=None) -> tuple[list[ItemResult], list[str]]:
    """Add the evidence entry to each item. Returns per-item results and warnings."""
    import yaml  # brace.py already requires PyYAML

    text = record_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        raise ImportProblem(f"{record_path} has no 'items' map. Run brace.py init first.")
    results: list[ItemResult] = []
    warnings: list[str] = []
    new_text = text
    rewrite = False
    for item in items:
        rec = data["items"].get(item)
        if not isinstance(rec, dict):
            raise ImportProblem(f"{item} is not in {record_path}.")
        before = str(rec.get("outcome") or "not_reviewed")
        evid = rec.get("evidence") if isinstance(rec.get("evidence"), list) else []
        if any(isinstance(e, dict) and digest in str(e.get("note", "")) for e in evid):
            results.append(ItemResult(item, "skipped", before, before, "this results file is already recorded"))
            continue
        after = before
        if failed and before == "not_reviewed":
            after = "gap"
        elif failed and before == "pass":
            warnings.append(f"{item} is marked pass, but this run shows {failed} failure(s). "
                            "Review it; the outcome was not changed.")
        elif failed and before == "na":
            warnings.append(f"{item} is marked N/A, but you linked a run with failures to it. Review it.")
        rec["outcome"] = after
        rec["evidence"] = list(evid) + [dict(entry)]
        results.append(ItemResult(item, "added", before, after))
        if not rewrite:
            patched = _patch_text(new_text, item, entry, after if after != before else None)
            if patched is None:
                rewrite = True
            else:
                new_text = patched

    if not rewrite:
        try:
            check = yaml.safe_load(new_text)
        except yaml.YAMLError:
            check = None
        if _norm(check) != _norm(data):
            rewrite = True
    if rewrite:
        new_text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False, width=100)
        warnings.append(f"Could not keep the comments in {record_path.name}; it was rewritten in plain YAML.")
    if validate is not None:
        errs = validate(_norm(yaml.safe_load(new_text)))
        if errs:
            raise ImportProblem(["The updated record would not match its schema, so nothing was written:"] + errs)
    if not dry_run and any(r.action == "added" for r in results):
        tmp = record_path.with_name(record_path.name + ".tmp")
        tmp.write_text(new_text, encoding="utf-8")
        os.replace(tmp, record_path)
    return results, warnings


def _norm(v):
    if isinstance(v, dict):
        return {str(k): _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, (_dt.date, _dt.datetime)):
        return v.isoformat()[:10]
    return v
