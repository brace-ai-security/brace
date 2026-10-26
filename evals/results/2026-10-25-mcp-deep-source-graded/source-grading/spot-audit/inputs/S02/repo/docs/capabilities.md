# Capability catalog

The capability adapter is used by clients which discover operations by capability
name rather than by a dedicated tool. It shares the same identity and Store with
the dedicated routes. Metadata supplies the dispatch operation, required scope
and owner-only policy. Adding catalog entries requires a matching dispatch arm.

`document.preview` returns a complete document, including its body. It is a
convenience name for read access, not a public redacted summary. `account.archive`
returns all account rows for one tenant, equivalent to account.export. The optional
tenant parameter supports clients that always include their active workspace.
It is a selector, not a delegation mechanism. Omitting it selects the caller's
own tenant. Capability jobs are created anew on every request and are not cached.

Missing capability names are invalid requests. Missing preview keys are invalid
requests. Unknown storage keys are NotFound. No route permits tenant discovery,
bulk scope changes, session creation, or attaching arbitrary Permit objects.
