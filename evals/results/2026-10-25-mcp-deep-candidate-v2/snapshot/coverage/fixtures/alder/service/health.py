def describe(registry):
    return {
        "ready": bool(registry.handlers),
        "transport": "in-process-mcp",
        "tools": registry.describe(),
    }

def liveness():
    return {"status": "alive"}
