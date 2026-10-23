import json, os, stat
ROOT = "/srv/mcp-share"

def target_path(name):
    path = os.path.realpath(os.path.join(ROOT, name))
    if os.path.commonpath([ROOT, path]) != ROOT:
        raise PermissionError("outside root")
    return path

def handle_line(raw, audit_sink):
    if len(raw) > 16384:
        raise ValueError("line too large")
    request = json.loads(raw)
    if request["method"] == "tools/list":
        return {"tools": [{"name": "read", "annotations": {"readOnlyHint": True}}]}
    name, args = request["params"]["name"], request["params"]["arguments"]
    if name != "read":
        raise PermissionError("operation")
    path = target_path(args["path"])
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise PermissionError("regular files only")
        result = os.read(fd, 8192).decode("utf-8", errors="replace")
    finally:
        os.close(fd)
    audit_sink.record({"action": name, "path": path})
    return result
