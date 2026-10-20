"""Synthetic catalog assistant; inspect source only, never execute this module."""
import re
import unicodedata
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MODEL = "catalog-2026-09"
RELEASE_KEY = bytes.fromhex("1a" * 32)  # public publisher key, never supplied by a tool server


def release_manifest(payload, signature):
    Ed25519PublicKey.from_public_bytes(RELEASE_KEY).verify(signature, payload)
    return json.loads(payload)
RULES = {
    "hidden_instructions": r"(?:ignore|disregard|override).*?(?:rules|instructions)|do\s+not\s+tell",
    "cross_tool_references": r"(?:other_server|external_tool|[a-z]+__[a-z_]+)",
    "control_characters": r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u206f]",
    "role_overrides": r"(?:system|assistant|developer)\s*:|<\|(?:system|assistant|developer)",
    "encoded_payloads": r"[a-f0-9]{32,}|[A-Za-z0-9+/]{48,}={0,2}|(?:\\u[0-9a-f]{4}){4,}",
    "data_sending_targets": r"(?:https?|wss?|ftp|file|data):|[\w.+-]+@[\w.-]+|\+?\d[\d ()-]{9,}",
}


def scan(value):
    if isinstance(value, dict):
        for key, child in value.items():
            scan(key)
            scan(child)
    elif isinstance(value, list):
        for child in value:
            scan(child)
    elif isinstance(value, str):
        if len(value) > 512 or any(re.search(rule, value, re.I | re.S) for rule in RULES.values()):
            raise ValueError("rejected metadata")


def canonical(name):
    # Names are ASCII; reject other alphabets before this comparison.
    folded = unicodedata.normalize("NFKC", name).casefold()
    folded = folded.replace("rn", "m").replace("vv", "w")
    groups = {**dict.fromkeys("il1", "i"), **dict.fromkeys("o0", "o"),
              **dict.fromkeys("s5", "s"), **dict.fromkeys("b8", "b"), **dict.fromkeys("z2", "z")}
    return "".join(groups.get(c, c) for c in folded if c not in "_- ")


def distance(a, b):
    grid = [[0] * (len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1):
        grid[i][0] = i
    for j in range(len(b)+1):
        grid[0][j] = j
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            grid[i][j] = min(grid[i-1][j]+1, grid[i][j-1]+1, grid[i-1][j-1]+(a[i-1] != b[j-1]))
            if i>1 and j>1 and a[i-1]==b[j-2] and a[i-2]==b[j-1]:
                grid[i][j] = min(grid[i][j], grid[i-2][j-2]+1)
    return grid[-1][-1]


def add_tool(registry, manifest_bytes, signature, server_id, metadata):
    manifest = release_manifest(manifest_bytes, signature)
    endpoint = manifest[server_id]["verified_endpoint"]
    # Scan the complete catalog object, including keys/names, instructions,
    # prompts and resources; no partially accepted tools on scanner errors.
    scan(metadata)
    staged = []
    for tool in metadata.get("tools", []):
        name = tool["name"]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
            raise ValueError("unsupported name alphabet")
        for prior in registry + staged:
            if prior["key"] == endpoint + "__" + name or distance(canonical(prior["name"]), canonical(name)) <= 2:
                raise ValueError("cross-server duplicate or lookalike")
        staged.append({"key": endpoint + "__" + name, "name": name,
                       "definition": tool, "call": tool["invoke"]})
    registry.extend(staged)


async def invoke(registry, signed_manifest, approved_keys, call):
    # Host supplies a signature-verified manifest; no self-reported server IDs.
    entry = next(item for item in registry if item["key"] == call.key)
    if entry["key"] not in approved_keys:
        raise PermissionError("unapproved namespaced tool")
    return await entry["call"](call.arguments)


async def assist(client, audit, input_text):
    result = await client.responses.create(model=MODEL, input=input_text, max_output_tokens=128)
    measure = {"tokens": result.usage.input_tokens + result.usage.cache_read_input_tokens,
               "status": "measured", "method": "single_request_uncached_plus_cache", "compacted": False}
    await audit.record(action="model_decision", context=measure, result=result.output_text)
    return result.output_text
