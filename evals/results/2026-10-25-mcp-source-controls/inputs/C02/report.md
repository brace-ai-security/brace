Source-only report; nothing was executed.

The GET branch returns store.jobs[handle] directly without calling store.owned, so result reads lack a tenant check.
DELETE calls store.owned and enforces tenant ownership.
