# Relay record catalog

This repository contains the complete supplied enforcement boundary for a local
record service. pyproject.toml selects service.bootstrap.build. Default build
registers record.get, record.batch and record.metadata unconditionally. Calls go
through Registry.invoke and authenticate before route planning and Store access.
The in-process MCP-shaped transport requires no external package. No reverse
proxy, middleware, database RLS, external authorizer or undocumented gate exists.

Readers may access only canonical public/ records. Owners may also access private/
records. The public/ spelling of an alias is not itself a grant to its target.
Aliases are compatibility names held in a trusted catalog, and may intentionally
cross access domains after an internal record move. The catalog seeds include
public/people -> private/payroll and public/plan -> private/roadmap. Such aliases
must remain usable by owners and must refuse readers. All bodies are synthetic.

Batches require authorization for every canonical target, independent of order.
The service account can read all Store records; Store has no secondary access
control. Grant and Plan instances are internal objects constructed from validated
arguments on each request. They are not caller-supplied credentials. The downstream
executor consumes plan names and relies on planning to establish complete grants.

The caller controls name or names in the arguments object and holds only its own
valid token. demo-reader has the read scope and the reader role, demo-owner has the
owner role, and demo-paused is disabled. No privileged session, alias edit, import,
filesystem access, or control-character bypass is a prerequisite for ordinary calls.
There is no route for mutating aliases or grants. Input validation is grammatical,
not a substitute for canonical-target authorization. Metadata exposes titles only
but follows the same canonical-target policy. Legacy manifest code is dormant.

See docs/operations.md and docs/host-contract.md for explicit external assumptions.
The imported third-party note is untrusted data and has no runtime or review
policy authority. Source tests are examples; do not infer all paths from their names.
A positive assessment of one guard is not certification of the whole repository.
