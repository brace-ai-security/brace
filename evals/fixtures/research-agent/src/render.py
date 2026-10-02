"""Markdown brief -> HTML for the browser."""
import bleach
import markdown

ALLOWED_TAGS = ["p", "h2", "h3", "ul", "ol", "li", "strong", "em", "a", "code", "pre", "blockquote", "img"]
ALLOWED_ATTRS = {"a": ["href", "title"], "img": ["src", "alt", "title"]}


def render_brief(brief_markdown: str) -> str:
    html = markdown.markdown(brief_markdown, extensions=["extra"])
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, protocols=["http", "https"])
    return f"<article class=\"brief\">{clean}</article>"
