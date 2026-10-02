"""Entry points: HTTP service, single run, nightly dunning sweep."""
from __future__ import annotations

import argparse
import json
import logging
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

from .agent import Deps, run
from .control import ControlFlag, KubeConfigMaps
from .identity import ROOT, compute_agent_type_id, context_from_token, scheduler_context
from .mcp_client import AccountingMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("billing_agent")

CFG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
AGENT_TYPE_ID = compute_agent_type_id(CFG["agent"]["model"])


def _deps() -> Deps:
    cms = KubeConfigMaps(CFG["control"]["namespace"])
    control = ControlFlag(cms, CFG["control"]["configmap"])
    mcp = AccountingMCP(CFG["accounting"]["server"], CFG)
    mcp.connect()
    return Deps(CFG, control, mcp)


class Handler(BaseHTTPRequestHandler):
    deps: Deps

    def do_POST(self) -> None:
        if self.path != "/v1/runs":
            self.send_error(404)
            return
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self.send_error(401)
            return
        length = min(int(self.headers.get("Content-Length", 0)), 64_000)
        body = json.loads(self.rfile.read(length) or b"{}")
        trace_id = self.headers.get("traceparent", "").split("-")[1] if self.headers.get("traceparent") else uuid.uuid4().hex
        try:
            ctx = context_from_token(auth[7:], CFG, AGENT_TYPE_ID, trace_id)
        except Exception:
            self.send_error(401)
            return
        result = run(ctx, str(body.get("task", ""))[:4000], str(body.get("tenant_name", ctx.tenant_id)), self.deps)
        payload = json.dumps({**result, "trace_id": ctx.trace_id, "agent_instance_id": ctx.agent_instance_id}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


def sweep(deps: Deps) -> None:
    cms = KubeConfigMaps(CFG["control"]["namespace"])
    tenants = [r[0] for r in deps.invoices._conn().execute(
        "SELECT DISTINCT tenant_id FROM invoices WHERE status = 'open' ORDER BY tenant_id").fetchall()]
    start = cms.get("billing-agent-sweep-cursor").get("last_tenant", "")
    for tenant in tenants:
        if tenant <= start:
            continue
        ctx = scheduler_context(tenant, CFG, AGENT_TYPE_ID)
        result = run(ctx, "Send first reminders for invoices 7-30 days overdue.", tenant, deps)
        log.info("sweep tenant=%s status=%s trace=%s", tenant, result["status"], ctx.trace_id)
        cms.patch("billing-agent-sweep-cursor", {"last_tenant": tenant})
        if result["status"] == "halted":
            break
    cms.patch("billing-agent-sweep-cursor", {"last_tenant": ""})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["serve", "run", "sweep"])
    p.add_argument("--task")
    p.add_argument("--token")
    args = p.parse_args()
    log.info("agent_type_id=%s", AGENT_TYPE_ID)
    deps = _deps()
    if args.cmd == "serve":
        Handler.deps = deps
        ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
    elif args.cmd == "run":
        ctx = context_from_token(args.token, CFG, AGENT_TYPE_ID, uuid.uuid4().hex)
        print(json.dumps(run(ctx, args.task, ctx.tenant_id, deps), indent=2))
    else:
        sweep(deps)


if __name__ == "__main__":
    main()
