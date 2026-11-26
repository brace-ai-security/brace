"""Text the scanner prints: made printable, short, redacted, and inert in every place it lands.

Everything shown comes from files the scanner does not trust. clean() strips control
characters, redacts secrets and cuts to length (in that order, so a cut can never leave half
a secret behind); the escapers keep names from becoming workflow commands in a GitHub Actions
log or links and markup in Markdown.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .limits import DETAIL_CHARS, FILE_CHARS, MAX_VALUE, NOTE_CHARS
from .secrets import DEFAULT, Secrets

# A GitHub Actions workflow command (`::error ...::`, `::add-mask::`, `::stop-commands::`) at
# the start of a line, after spaces or colour codes, or a `##[error]` log command anywhere.
WORKFLOW_COMMAND = re.compile(r"^((?:[ \t]|\x1b\[[0-9;]*m)*)::", re.M)


def defuse(text: str) -> str:
    """Text the Actions log shows as written instead of running it as a command."""
    return WORKFLOW_COMMAND.sub(r"\1: :", text).replace("##[", "# #[")


def clean(s, n: int = DETAIL_CHARS, redact: bool = True, secrets: Secrets = DEFAULT) -> str:
    """Printable, (by default) secret-redacted, then cut to n characters.

    Redaction runs before the cut, on the first n + MAX_VALUE characters: every secret pattern
    is shorter than MAX_VALUE, so a secret that starts in the part shown is redacted whole and
    a cut can never leave a recognisable prefix of it, while redaction time stays bounded."""
    s = "".join(ch for ch in str(s) if ch.isprintable())
    if redact:
        s = secrets.redact(s[:n + MAX_VALUE])
    return s if len(s) <= n else s[: n - 1] + "…"


def path_bytes(path: str) -> bytes:
    """A path (or text holding one) as its bytes on disk. os.walk keeps bytes that are not UTF-8
    as lone surrogates; they go back to those bytes instead of failing to encode."""
    return path.encode("utf-8", "surrogateescape")


def safe_path(path: str) -> str:
    """A path exactly, as valid text for JSON and XML: bytes that are not UTF-8 written as \\xNN."""
    return path_bytes(path).decode("utf-8", "backslashreplace")


def path_uri(path: str) -> str:
    """A relative URI of the path's exact bytes, for SARIF."""
    return quote(path_bytes(path), safe="/")


def shown_path(path: str) -> str:
    """A finding's path for people (text and Markdown): printable and cut to FILE_CHARS."""
    return clean(path, FILE_CHARS, redact=False)


def inert(text: str, media: str) -> str:
    """Output for a GitHub Actions log, which runs workflow commands it finds: text is defused;
    JSON writes `#` as \\u0023 (the same character inside a JSON string, and `#` occurs only
    inside strings), so `##[error]` cannot appear, and a string never starts a line, so `::` cannot."""
    return text.replace("#", "\\u0023") if media == "json" else defuse(text)


MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|<>~])")
MD_SPECIAL_DOTS = re.compile(r"([\\`*_{}\[\]()#+!|<>~@.])")


def md_escape(t, dots: bool = False) -> str:
    """Text shown as written: no emphasis, links or HTML. With dots (for names and notes from the
    scanned folder), `.` and `@` are escaped too, so `www.evil.example` is not turned into a
    link and `@octocat.sh` does not mention anyone."""
    return (MD_SPECIAL_DOTS if dots else MD_SPECIAL).sub(r"\\\1", clean(t, NOTE_CHARS))


def size_label(n: int) -> str:
    """A byte count for people: bytes under 1 KB, else whole KB."""
    return f"{n} bytes" if n < 1024 else f"{n // 1024} KB"


def plural(n: int, one: str, many: str = "") -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"
