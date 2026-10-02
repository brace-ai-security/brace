"""Slack entry point: `/ops <request>` starts a run; workers start with `--worker`."""
import argparse
import json
import os
import sys

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.agent import run
from src.checkpoint import resume_pending_runs

app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.command("/ops")
def handle_ops(ack, command, respond):
    ack("On it.")
    summary = run(goal=command["text"], requester=command["user_id"])
    respond(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--goal")
    parser.add_argument("--run-id")
    args = parser.parse_args()

    if args.worker:
        print(json.dumps({"summary": run(goal=args.goal, requester="parent", run_id=args.run_id)}))
        sys.exit(0)

    resume_pending_runs()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()


if __name__ == "__main__":
    main()
