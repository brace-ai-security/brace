"""Reading and writing files safely: regular files only, bounded sizes, no symlinks followed.

A scanned folder can hold FIFOs that block forever, devices, symlinks out of the folder and
huge or binary files. These helpers never open a special file, never follow a symlink unless
asked, never read more than a limit, and decode text without trusting its encoding.
"""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .limits import MB

# Open flags that refuse a symlink at the path and never block on a FIFO. Windows has neither
# flag (both are 0 there), so open_regular() also checks the path with lstat right before
# opening it and the opened file with fstat after: a symlink or special file swapped in between
# is caught by comparing the two (same device and file id, still a regular file).
NOFOLLOW = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)


def open_regular(p: Path) -> int:
    """A read-only descriptor for the regular file at p, never through a symlink; OSError otherwise."""
    before = os.lstat(p)
    if not stat.S_ISREG(before.st_mode):
        raise OSError(f"not a regular file: {p}")
    fd = os.open(p, NOFOLLOW)
    try:
        after = os.fstat(fd)
        if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise OSError(f"changed while opening: {p}")
    except BaseException:
        os.close(fd)
        raise
    return fd


@dataclass
class ReadFailure:
    """Why read() returned no text: "oversized", "symlink", "not a regular file" or "unreadable"
    (with the cause, such as " (binary)", in the display)."""
    reason: str
    display: str


def read(p: Path, follow: bool = False, limit: int = MB, display: str = "") -> str | ReadFailure:
    """Regular files only (no FIFOs or devices; symlinks only with follow=True), up to `limit`
    bytes, decoded by decode(). Line breaks become "\\n"."""
    display = display or str(p)
    try:
        st = os.stat(p) if follow else os.lstat(p)
        if stat.S_ISLNK(st.st_mode):
            return ReadFailure("symlink", display)
        if not stat.S_ISREG(st.st_mode):
            return ReadFailure("not a regular file", display)
        if st.st_size > limit:
            return ReadFailure("oversized", display)
        with (open(p, "rb") if follow else os.fdopen(open_regular(p), "rb")) as fh:
            data = fh.read(limit + 1)
    except OSError:
        return ReadFailure("unreadable", display)
    text = decode(data)
    if text is None:
        cause = "not valid UTF-16" if data.startswith(UTF16_BOMS) else "binary"
        return ReadFailure("unreadable", f"{display} ({cause})")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def contains(p: Path, needles: tuple[bytes, ...], cap: int = 16 * MB) -> bool:
    """Whether the first `cap` bytes of a regular file hold any of the needles, read in chunks
    (for files too large to read as text). Symlinks are not followed."""
    overlap, tail, seen = max(map(len, needles)) - 1, b"", 0
    try:
        with os.fdopen(open_regular(p), "rb") as fh:
            while seen < cap:
                chunk = fh.read(MB)
                if not chunk:
                    return False
                seen += len(chunk)
                window = tail + chunk
                if any(n in window for n in needles):
                    return True
                tail = window[-overlap:]
    except OSError:
        return False
    return False


UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")
SAMPLE = 8192  # bytes looked at to tell text from binary


def decode(data: bytes) -> str | None:
    """UTF-8 (with or without BOM), or UTF-16 with a BOM, or None for binary data.

    UTF-16 is decoded strictly and must contain a NUL byte (every ASCII character has one),
    so bytes that merely start like a BOM are not read as garbage. A NUL byte alone does not
    make a file binary: text that is otherwise printable is read with its NULs removed."""
    if data.startswith(UTF16_BOMS):
        if len(data) > 2 and b"\x00" not in data[2:SAMPLE]:
            return None
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            return None
    text = data.decode("utf-8-sig", errors="replace")
    if "\x00" in text[:SAMPLE]:
        if not mostly_text(text[:SAMPLE].replace("\x00", "")):
            return None
        text = text.replace("\x00", "")
    return text


def mostly_text(sample: str) -> bool:
    """At least 95% printable characters, tabs and line breaks (undecodable bytes count against)."""
    good = sum(1 for ch in sample if ch in "\n\r\t" or (ch.isprintable() and ch != "\ufffd"))
    return good >= 0.95 * len(sample)


def starts_with(p: Path, prefix: bytes) -> bool:
    """Whether a regular file starts with `prefix`. FIFOs, devices and symlinks are never opened,
    so they cannot hang the scan or lead out of the folder."""
    try:
        with os.fdopen(open_regular(p), "rb") as fh:
            return fh.read(len(prefix)) == prefix
    except OSError:
        return False


def write_new(path: str, text: str, append: bool = False) -> None:
    """Write without following a symlink at the target path."""
    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
