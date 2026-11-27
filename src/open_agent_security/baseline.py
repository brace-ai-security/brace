"""Baselines: the findings a team has already triaged, so a scan reports only new ones.

`--write-baseline FILE` writes the fingerprints (finding ids, the same as SARIF's
`openAgentSecurity/v1` partial fingerprints) of the findings a scan reported. `--baseline FILE`
(or `baseline = "path"` in the config) then reports only findings whose id is not in it; the
others become suppressed findings of kind "external", counted in the suppression note, and
never affect the verdict or exit code. An incomplete scan stays incomplete: a baseline hides
findings, never gaps.

A baseline file may come from a pull request, so it is untrusted input: bounded in size, read as
strict JSON with an exact shape, and anything else is an error (exit code 2), never "no baseline".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .fsio import ReadFailure, read
from .limits import BASELINE_BYTES, BASELINE_IDS
from .model import Report

FORMAT = "open-agent-security-baseline"
ID = re.compile(r"^[0-9a-f]{32}$")
ENTRY_KEYS = {"id", "rule", "file"}
TEXT_MAX = 4096  # characters of an entry's rule or file, kept for people reading the file


class BaselineError(Exception):
    """A baseline file that cannot be used as written. Exit code 2."""


def render(report: Report) -> str:
    """The baseline of a report: its reported findings' ids, with rule and file for people, and the
    findings an applied baseline suppressed, so rewriting a baseline keeps what it held and is still found."""
    kept = [f for f in report.suppressed if f.suppression and f.suppression.justification.startswith("in baseline ")]
    rows = sorted({(f.id, f.rule, f.file) for f in report.findings + kept})
    return json.dumps({"format": FORMAT, "version": 1,
                       "findings": [{"id": i, "rule": r, "file": p} for i, r, p in rows]}, indent=2) + "\n"


def load(path: Path, shown: str, follow: bool = True) -> frozenset[str]:
    """The ids in a baseline file. Raises BaselineError for anything but a well-formed baseline."""
    text = read(path, follow=follow, limit=BASELINE_BYTES)
    if isinstance(text, ReadFailure):
        raise BaselineError(f"baseline {shown}: not a readable regular file of at most {BASELINE_BYTES // (1024 * 1024)} MB"
                            + (" (symlinks are not followed)" if text.reason == "symlink" else ""))
    try:
        data = json.loads(text, parse_constant=_reject)
    except (ValueError, RecursionError):
        raise BaselineError(f"baseline {shown}: not valid JSON") from None
    if not isinstance(data, dict) or set(data) != {"format", "version", "findings"} or data["format"] != FORMAT:
        raise BaselineError(f"baseline {shown}: expected an object with format {FORMAT!r}, version and findings")
    if type(data["version"]) is not int or data["version"] != 1:
        raise BaselineError(f"baseline {shown}: version must be 1")
    rows = data["findings"]
    if not isinstance(rows, list) or len(rows) > BASELINE_IDS:
        raise BaselineError(f"baseline {shown}: findings must be a list of at most {BASELINE_IDS} entries")
    ids = set()
    for row in rows:
        if not isinstance(row, dict) or "id" not in row or set(row) - ENTRY_KEYS \
                or not isinstance(row["id"], str) or not ID.match(row["id"]) \
                or any(not isinstance(row.get(k, ""), str) or len(row.get(k, "")) > TEXT_MAX for k in ("rule", "file")):
            raise BaselineError(f"baseline {shown}: each finding is an object with a 32-character hex id, "
                                "and optionally rule and file")
        ids.add(row["id"])
    return frozenset(ids)


def _reject(name: str):
    raise ValueError(name)  # NaN and Infinity are not JSON
