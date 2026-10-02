"""The only tools the model can call. Unknown tool names are refused."""
from src.subagents import spawn_worker
from src.tools.git import git
from src.tools.shell import kubectl, helm

TOOLS = {
    "kubectl": kubectl,          # inspect and fix workloads
    "helm": helm,                # roll back releases
    "git": git,                  # open fix-up branches in infra repos
    "spawn_worker": spawn_worker,  # split multi-cluster work
}

TOOL_SCHEMAS = [
    {"name": "kubectl", "description": "Run a kubectl command. Pass the arguments after `kubectl`.",
     "input_schema": {"type": "object", "properties": {"args": {"type": "string"}, "context": {"type": "string"}},
                      "required": ["args", "context"]}},
    {"name": "helm", "description": "Run a helm command. Pass the arguments after `helm`.",
     "input_schema": {"type": "object", "properties": {"args": {"type": "string"}, "context": {"type": "string"}},
                      "required": ["args", "context"]}},
    {"name": "git", "description": "Run a git command in /work/<repo>.",
     "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}, "args": {"type": "string"}},
                      "required": ["repo", "args"]}},
    {"name": "spawn_worker", "description": "Start a worker agent with its own goal.",
     "input_schema": {"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]}},
]


def dispatch(name: str, arguments: dict, run_id: str) -> str:
    if name not in TOOLS:
        return f"Unknown tool {name!r}."
    if name == "spawn_worker":
        return spawn_worker(arguments["goal"], run_id=run_id)
    try:
        return TOOLS[name](**arguments)
    except Exception as exc:  # report errors back to the model
        return f"Error: {exc}"
