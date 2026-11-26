"""The notes that say what hid findings or files from a scan.

Ignore entries, rules turned off or re-rated, inline marks and lowered limits can each make
a scan look cleaner than the folder is, and a pull request can add any of them. So whenever
one is in effect, every output format carries a note saying what it hid; folders skipped by
default are counted in notes too.
"""
from __future__ import annotations

from .ignore import IGNORE_FILE
from .limits import LIMIT_KEYS, Limits
from .model import Tally
from .output import plural, size_label


def lowered(limits: Limits) -> tuple[str, ...]:
    """The limits set below the defaults, as the suppression note shows them."""
    return tuple(f"limits.{key} lowered to {size_label(v) if attr == 'max_file_bytes' else v}"
                 for key, attr in LIMIT_KEYS if (v := getattr(limits, attr)) < getattr(Limits(), attr))


def suppression_note(tally: Tally, config_path: str | None) -> str:
    """'' when no filter was in effect; otherwise what was in effect and what it hid."""
    from_config = [plural(tally.rules_off, "rule") + " off" if tally.rules_off else "",
                   plural(tally.overrides, "severity override") if tally.overrides else "",
                   plural(tally.config_ignores, "ignore entry", "ignore entries") if tally.config_ignores else ""]
    parts = [f"config {config_path}: " + ", ".join(p for p in from_config if p) if any(from_config) else "",
             f"{IGNORE_FILE}: {plural(tally.ignore_file_entries, 'entry', 'entries')}"
             if tally.ignore_file_entries else "",
             f"inline ignore marks: {plural(tally.by_mark, 'finding')}" if tally.by_mark else "",
             *tally.lowered]
    parts = [p for p in parts if p]
    if not parts:
        return ""
    parts.append(f"{plural(tally.suppressed, 'finding')} suppressed")
    if tally.config_ignores or tally.ignore_file_entries:
        folders = f" and {plural(tally.folders, 'folder')}" if tally.folders else ""
        parts.append(f"{plural(tally.files, 'file')}{folders} not scanned because of ignore entries")
    return "; ".join(parts)


def skipped_dirs_notes(tally: Tally) -> list[str]:
    """Folders skipped by default, counted: dependencies in one note, version control and caches
    in another; and symlinks to paths inside the folder, which the walk reads where they point."""
    notes = [f"did not enter {plural(sum(group.values()), what)} ({', '.join(sorted(group))})"
             for group, what in ((tally.dependency_dirs, "dependency folder"),
                                 (tally.other_dirs, "version-control or cache folder")) if group]
    if tally.links_inside:
        more = tally.links_inside - len(tally.link_names)
        notes.append(f"did not follow {plural(tally.links_inside, 'symlink')} to paths inside the folder, scanned "
                     f"where they point: {', '.join(tally.link_names)}" + (f" and {more} more" if more else ""))
    return notes
