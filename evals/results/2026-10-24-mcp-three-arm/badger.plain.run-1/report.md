**Review of the job-status API (`api.py`, `store.py`)**

**High: GET has no tenant check, so any tenant can read another tenant's results** (`repo/api.py:7-9`)

The GET branch reads `store.jobs[handle]` directly and returns `job.result`. It never compares `job.tenant` to `identity.tenant`. The README says handles can appear in shared support URLs and that possession grants no authority. So anyone with a leaked or shared handle can read another tenant's data. DELETE already does this correctly through `store.owned(...)`.

Fix:
```python
if request.method == 'GET':
    job = store.owned(identity.tenant, handle)
    return {'result': job.result}
```

**Medium: handle existence leaks, and unknown handles cause unhandled errors** (`repo/store.py:16`, `repo/api.py:8`)
- `self.jobs[handle]` raises `KeyError` for an unknown handle. A handle that exists under another tenant raises `Forbidden`. A caller can tell "exists but isn't mine" from "doesn't exist", which confirms that a leaked or guessed handle is real.
- The `KeyError` is probably an unhandled 500, unless the host maps it.
- Make `owned` raise the same not-found error for both cases:
  ```python
  job = self.jobs.get(handle)
  if job is None or job.tenant != tenant:
      raise NotFound()
  ```
- The host would need to map `Forbidden` and `NotFound` to 403 and 404. That mapping is outside the code I can see.

**Low / hardening**
- **`create` stores the request body as `result`** (`repo/store.py:11-13`, `repo/api.py:5`). The caller controls what is later returned as the job result. The worker is external, so this may be a placeholder. If not, results should come only from the worker, and the body should be validated or stored as job input. Body validation is said to happen at ingress, which I can't see.
- **No lifecycle management.** `Store.jobs` is an unbounded in-memory dict with no TTL, eviction or per-tenant quota. That risks memory exhaustion and keeps results for as long as the process runs. It is also not shared across workers or processes.
- **A cancelled job still returns its result on GET.** `cancelled` is set but never checked on read. Confirm that's intended.
- **Unused import:** `Forbidden` in `api.py:1`.
- **Unsupported methods raise a bare `ValueError`** (`repo/api.py:14`), which likely becomes a 500. Return a 405 instead. The same applies to POST on any path other than `/jobs`, which falls through to `path_params['job_id']` and can raise `KeyError`.

**Good**
- Handles come from `secrets.token_urlsafe(24)`, which is unguessable.
- Tenant comes from the host-injected `verified_identity`, not from the request body.
- DELETE enforces ownership.

I did not review `research/`. I read only the `repo/` files and ran nothing.
