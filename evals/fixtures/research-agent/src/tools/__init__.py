from src.tools.fetch import fetch_page
from src.tools.search import web_search

TOOLS = {"web_search": web_search, "fetch_page": fetch_page}

TOOL_SCHEMAS = [
    {"name": "web_search", "description": "Search the public web. Returns titles, URLs, and snippets.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string", "maxLength": 300}},
                      "required": ["query"]}},
    {"name": "fetch_page", "description": "Fetch a web page and return its readable text.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string", "format": "uri"}},
                      "required": ["url"]}},
]
