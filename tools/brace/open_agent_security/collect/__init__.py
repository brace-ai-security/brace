"""Collectors: where source files come from (the scanned folder, this machine)."""
from .host import HostCollector
from .repo import RepoCollector

BUILTIN = (RepoCollector(), HostCollector())
