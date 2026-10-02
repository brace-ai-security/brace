"""Run state in S3 so a crashed pod can pick up where it left off."""
import pickle

import boto3
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())["checkpoints"]
_s3 = boto3.client("s3")


def save_checkpoint(run_id: str, requester: str, goal: str, messages: list) -> None:
    state = {"run_id": run_id, "requester": requester, "goal": goal, "messages": messages}
    _s3.put_object(Bucket=CFG["bucket"], Key=f"{CFG['prefix']}{run_id}.pkl", Body=pickle.dumps(state))


def resume_pending_runs() -> None:
    """On startup, finish every run that was interrupted."""
    from src.agent import run
    from src.tools.registry import dispatch

    listing = _s3.list_objects_v2(Bucket=CFG["bucket"], Prefix=CFG["prefix"])
    for obj in listing.get("Contents", []):
        body = _s3.get_object(Bucket=CFG["bucket"], Key=obj["Key"])["Body"].read()
        state = pickle.loads(body)
        last = state["messages"][-1]
        # If the crash happened after the model asked for tools, run those tool calls again.
        if last["role"] == "assistant":
            results = []
            for block in last["content"]:
                if getattr(block, "type", None) == "tool_use":
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": dispatch(block.name, block.input, run_id=state["run_id"])})
            state["messages"].append({"role": "user", "content": results})
        run(state["goal"], state["requester"], run_id=state["run_id"], messages=state["messages"])
        _s3.delete_object(Bucket=CFG["bucket"], Key=obj["Key"])
