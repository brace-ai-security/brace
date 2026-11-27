"""Reading and writing files for the BRACE tools.

Reads go through the scanner's fsio.read: regular files only, bounded, explicit decoding.
Files found inside a reviewed repository are read without following symlinks; a file the user
names on the command line may be a symlink (follow=True). Writes are atomic: a temporary file
in the same folder, then os.replace.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from open_agent_security.fsio import ReadFailure, read

MB = 1024 * 1024
LIMIT = 16 * MB  # the CycloneDX schema is 0.3 MB; topologies and findings are far smaller


class ReadError(ValueError):
    """A file could not be read or parsed; the message names the file."""


def read_text(path: Path, follow: bool = False, limit: int = LIMIT) -> str:
    text = read(Path(path), follow=follow, limit=limit)
    if isinstance(text, ReadFailure):
        why = {"oversized": f"larger than {limit // MB} MB"}.get(text.reason, text.reason)
        raise ReadError(f"can't read {text.display}: {why}")
    return text


def read_json(path: Path, follow: bool = False, limit: int = LIMIT) -> Any:
    try:
        return json.loads(read_text(path, follow, limit))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ReadError(f"{path} is not valid JSON ({str(exc)[:120]})") from None


def read_json_object(path: Path, follow: bool = False, limit: int = LIMIT) -> dict:
    data = read_json(path, follow, limit)
    if not isinstance(data, dict):
        raise ReadError(f"{path} must hold a JSON object, not {type(data).__name__}")
    return data


def read_yaml(path: Path, follow: bool = False, limit: int = LIMIT) -> Any:
    """The one place the tools parse YAML (safe_load). Needs the [record] extra."""
    import yaml
    try:
        return yaml.safe_load(read_text(path, follow, limit))
    except (yaml.YAMLError, RecursionError) as exc:
        raise ReadError(f"{path} is not valid YAML ({str(exc)[:120]})") from None


def write_atomic(path: Path, text: str, newline: str | None = None) -> None:
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
