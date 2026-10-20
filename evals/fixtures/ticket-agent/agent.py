"""Synthetic ticket triage harness. Dependencies are injected; read, never run."""
import re
import json
import unicodedata


def context(response):
    return {"tokens": response.usage.input_tokens + response.usage.cached_input_tokens,
            "method": "provider_input_plus_cache", "status": "measured", "compacted": False}


async def record(db, run, action, measure, result):
    await db.execute("INSERT INTO events(run_id, action, context, result) VALUES($1,$2,$3,$4)",
                     run.id, action, measure, result)


async def decide(client, db, run, text):
    answer = await client.responses.create(model="route-2026-09", input=text, max_output_tokens=64)
    await record(db, run, "routing", context(answer), answer.output_text)
    return answer.output_text  # no decision measure crosses this handoff


async def reserve(db, run):
    # PostgreSQL shared by all replicas; serialize all three scope rows.
    async with db.transaction():
        for key in ("user:" + run.user, "tenant:" + run.tenant, "fleet"):
            await db.execute("UPDATE quotas SET spent=spent+1 WHERE id=$1 AND spent+1<=cap RETURNING id", key)


async def run_ticket(client, db, run, ticket, server, tools):
    route = await decide(client, db, run, ticket)
    await record(db, run, "delegate_result", None, route)
    catalog = {"instructions": server.instructions, "tools": load_catalog(server, tools),
               "prompts": server.prompts, "resources": server.resource_templates}
    for turn in range(4):
        await reserve(db, run)
        response = await client.responses.create(model="main-2026-09", input=route + json.dumps(catalog), max_output_tokens=256)
        await record(db, run, "decision", context(response), response.output_text)
        if response.output_text == "done":
            return response.output_text


def scan_text(text):
    if len(text) > 1024 or re.search(r"[\x00-\x1f\u200b\u202a-\u202e]", text):
        raise ValueError("metadata rejected")
    if re.search(r"ignore.*instructions|system\s*:|https?://|[a-f0-9]{32,}|[A-Za-z0-9+/]{48,}={0,2}", text, re.I | re.S):
        raise ValueError("metadata rejected")


def load_catalog(server, tools):
    accepted = []
    for tool in tools:
        for field in ("name", "title", "description", "inputSchema", "outputSchema", "annotations"):
            scan_text(str(tool.get(field, "")))
        accepted.append({"key": server.endpoint + "__" + tool["name"], **tool})
    return accepted  # server instructions/prompts/resources skip all scanner rules


def canonical(name):
    return re.sub(r"[_-]", "", unicodedata.normalize("NFKC", name).casefold()).replace("1", "i")


def register(existing, server, tool):
    for prior in existing:
        if prior["server"] == server.endpoint and canonical(prior["name"]) == canonical(tool["name"]):
            raise ValueError("name conflict")
    entry = {"server": server.endpoint, "name": tool["name"], "key": server.endpoint + "__" + tool["name"]}
    existing.append(entry)
    return entry
