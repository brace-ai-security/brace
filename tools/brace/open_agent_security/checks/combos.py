"""AP09: one config file gives an agent untrusted input, private data and a way out.

The capability classes are a heuristic on whole words in the server name, the package it
runs and the URL host, so the finding says "likely", never "proven".
"""
from __future__ import annotations

import re
from typing import Iterator
from urllib.parse import urlsplit

from ..limits import WORD_PART_CHARS
from ..model import CheckContext, Document, Finding, Server
from ..parse.mcp_json import CONTAINERS
from .mcp_servers import fetched

UNTRUSTED = {"fetch", "browser", "puppeteer", "playwright", "web", "websearch", "search", "brave", "tavily", "exa",
             "firecrawl", "scrape", "scraper", "crawl", "crawler", "gmail", "email", "mail", "imap", "outlook", "slack",
             "discord", "telegram", "github", "gitlab", "jira", "linear", "notion", "rss", "youtube", "reddit", "twitter"}
PRIVATE = {"filesystem", "fs", "files", "postgres", "postgresql", "mysql", "sqlite", "mongo", "mongodb", "redis",
           "database", "db", "supabase", "drive", "gdrive", "gmail", "email", "outlook", "notion", "github", "gitlab",
           "jira", "linear", "slack", "secrets", "vault", "1password", "bitwarden", "aws", "gcp", "azure", "stripe",
           "snowflake", "bigquery", "salesforce", "hubspot"}
SENDS = {"fetch", "browser", "puppeteer", "playwright", "slack", "discord", "telegram", "gmail", "email", "mail", "smtp",
         "outlook", "github", "gitlab", "jira", "linear", "notion", "twitter", "webhook", "stripe", "aws", "shell",
         "exec", "terminal", "commander", "http-client", "requests"}
LEGS = (("untrusted input", UNTRUSTED), ("private data", PRIVATE), ("a way out", SENDS))


NOT_WORD = re.compile(r"[^a-z0-9-]+")
VERSION = re.compile(r"@[^/]{0,200}$")  # a package's @version or @tag


def words(*parts: str) -> set[str]:
    """Whole words of the parts, each cut to WORD_PART_CHARS: every hyphenated token
    (`desktop-commander`) and each of its pieces. One linear split, whatever the input."""
    out: set[str] = set()
    for token in NOT_WORD.split(" ".join(p[:WORD_PART_CHARS] for p in parts if p).lower()):
        token = token.strip("-")
        if token:
            out.add(token)
            out.update(piece for piece in token.split("-") if piece)
    return out


def classify(s: Server) -> set[str]:
    pkgs = fetched(s.command, s.args)[1]
    image = next((a for a in reversed(s.args) if not a.startswith("-") and "/" in a), "") \
        if s.command in CONTAINERS else ""
    try:
        host = urlsplit(s.url).hostname or "" if s.url else ""
    except ValueError:
        host = ""
    w = words(s.name, *(VERSION.sub("", p[:WORD_PART_CHARS]) for p in pkgs), image, host)
    return {leg for leg, vocab in LEGS if w & vocab}


class LethalCombination:
    name = "lethal-combination"
    emits = ("AP09",)
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        legs: dict[str, list[str]] = {}
        paths: dict[str, tuple] = {}
        for s in doc.servers:
            paths.setdefault(s.name, s.path)
            for leg in classify(s):
                legs.setdefault(leg, []).append(s.name)
        need = [leg for leg, _ in LEGS]
        if not all(legs.get(leg) for leg in need):
            return
        detail = "; ".join(f"{leg}: {', '.join(sorted(set(legs[leg]))[:4])}" for leg in need)
        first = legs["untrusted input"][0]
        yield Finding("AP09", doc.source.display, doc.line_of(paths[first]), f"likely, from server names — {detail}")
