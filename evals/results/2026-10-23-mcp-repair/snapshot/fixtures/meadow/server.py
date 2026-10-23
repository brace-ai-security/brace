import json, os
ROOT = "/srv/mcp-share"

def target_path(name):
    path = os.path.normpath(os.path.join(ROOT, name))
    if not path.startswith(ROOT):
        raise PermissionError("outside root")
    return path

def handle_line(raw, audit_sink):
    if len(raw) > 16384:
        raise ValueError("line too large")
    request = json.loads(raw)
    if request["method"] == "tools/list":
        return {"tools": [{"name": "read", "annotations": {"readOnlyHint": True}}]}
    name, args = request["params"]["name"], request["params"]["arguments"]
    if name not in ("read", "write"):
        raise PermissionError("unknown tool")
    path = target_path(args["path"])
    if name == "write":
        with open(path, "w") as stream:
            stream.write(args["content"])
        result = "stored"
    else:
        with open(path) as stream:
            result = stream.read(8192)
    audit_sink.record({"action": name, "path": path})
    return result
