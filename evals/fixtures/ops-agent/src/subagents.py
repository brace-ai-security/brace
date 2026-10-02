"""Starts worker sub-agents as separate processes."""
import os
import subprocess
import sys
import uuid


def spawn_worker(goal: str, run_id: str) -> str:
    worker_id = str(uuid.uuid4())
    env = os.environ.copy()  # workers need the same cluster and GitHub access
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.main", "--worker", "--goal", goal, "--run-id", worker_id],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return f"Started worker {worker_id} (pid {proc.pid})."
