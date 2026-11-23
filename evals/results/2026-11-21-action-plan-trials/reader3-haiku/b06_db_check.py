import asyncio, asyncpg, sys
sys.path.insert(0, ".")
from src.approvals import ApprovalStore, ApprovalInvalid
from src.audit import RunContext
import inspect
async def main():
    pool = await asyncpg.create_pool("postgresql://postgres@127.0.0.1:54329/hr")
    fields = list(inspect.signature(RunContext).parameters)
    import uuid; ctx = RunContext(**{f: (str(uuid.uuid4()) if f.endswith("_id") else f"v-{f}") for f in fields})
    store = ApprovalStore(pool, 600) if len(inspect.signature(ApprovalStore).parameters) == 2 else ApprovalStore(pool)
    args = {"leave_type": "annual", "start_date": "2026-12-01", "end_date": "2026-12-02"}
    results = {}
    for label, used_scope in (("mismatch", "hris.admin"), ("match", "hris.leave.request")):
        aid, _ = await store.request(ctx, "hris/file_leave_request", "emp-1", args, f"tu-{label}", "hris.leave.request")
        await store.confirm(aid, ctx.subject)
        try:
            await store.consume(ctx, aid, "hris/file_leave_request", "emp-1", args, used_scope)
            results[label] = "accepted"
        except ApprovalInvalid:
            results[label] = "refused"
    print(results)
    assert results == {"mismatch": "refused", "match": "accepted"}
asyncio.run(main())
