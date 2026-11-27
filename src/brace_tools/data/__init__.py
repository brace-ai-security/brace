"""Package data: the item list, JSON schemas and the .brace/ record templates.

`path("schemas", "record.schema.json")` returns a filesystem path to a file shipped in the
package (setuptools installs package data as plain files).
"""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def path(*parts: str) -> Path:
    return Path(str(files(__name__).joinpath(*parts)))
