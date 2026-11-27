# Example policies for the scanner's JSON report

Small [Open Policy Agent](https://www.openpolicyagent.org/docs/policy-language) (Rego) policies
that gate a build on an `open-agent-security` JSON report
([report-1.schema.json](../../src/open_agent_security/report/schema/report-1.schema.json)).
They are examples to copy and adapt. They are not part of BRACE's requirements.

| Policy | Fails when |
|---|---|
| [`rego/no_critical.rego`](rego/no_critical.rego) | any finding is `critical` |
| [`rego/unpinned_mcp.rego`](rego/unpinned_mcp.rego) | an MCP server package or image is unpinned (AP04) and the server is not in `approved_unpinned_mcp` (data) |
| [`rego/suppression_reason.rego`](rego/suppression_reason.rego) | a finding is suppressed without a written reason (only a config `[[ignore]]` entry with `reason` has one; rules turned off in the config are allowed). Suppressions have no expiry date, so none is checked. |
| [`rego/complete_scan.rego`](rego/complete_scan.rego) | the scan is incomplete or stopped at the file limit, or the input is not a scanner report |

All four put their messages in `deny` in `package main`, the namespace Conftest reads by default.
[`rego/policy_test.rego`](rego/policy_test.rego) holds unit tests. [`inputs/`](inputs/) holds two
real reports (`pass.json`, `fail.json`) and an approved list (`approved.json`).

## Run them

```bash
python3 -I tools/brace/scan.py . --json --fail-on none > report.json

# Conftest: exit 1 when any policy denies
conftest test report.json -p examples/policy/rego --data examples/policy/inputs/approved.json

# OPA: print the denials (an empty set passes)
opa eval --format pretty -d examples/policy/rego -d examples/policy/inputs/approved.json \
  -i report.json 'data.main.deny'

# OPA: fail the step on any denial
opa eval --fail-defined -d examples/policy/rego -i report.json 'data.main.deny[_]'

# Unit tests
opa test examples/policy/rego
```

`tools/brace/tests/test_rego_policies.py` runs the unit tests and both example inputs when
`opa` or `conftest` is installed, and skips otherwise.

## Gateway policy languages for B01, B05 and E06

These checklist items are enforced at run time, in an MCP gateway or proxy, not in the scan
report. The table points to the policy languages gateways commonly use. It is a set of pointers,
not a BRACE requirement or an endorsement, and it does not show that any product meets an item.

| Item | What the gateway policy decides | Cedar | CEL | Rego |
|---|---|---|---|---|
| **B01** Minimal tool surface | Which principal (agent role) may call which tool; unlisted tools are denied | `permit (principal in Role::"…", action == Action::"call", resource in Tool::"…")`, default deny ([Cedar docs](https://docs.cedarpolicy.com/)) | A boolean expression over the request (tool name in an allowlist) evaluated per call ([cel.dev](https://cel.dev/)) | `allow if input.tool in data.roles[input.role].tools` with `default allow := false` ([OPA](https://www.openpolicyagent.org/docs/policy-language)) |
| **B05** Destructive-action interception | Block high-impact operations unless an approval for that specific action is present; authorize operation, target and arguments | `forbid` for destructive actions `unless { context.approval.action == … }` | Conditions over arguments and approval attributes | `deny` rules over `input.arguments` and an approval record in `data` |
| **E06** Enforced gateway boundary | Authenticate the caller, keep agent and delegated-subject identity, authorize tool, operation, resource, tenant and arguments on every call, fail closed | Entities for agent, user and tenant; policies per action and resource | Per-request checks in proxies that embed CEL (for example Envoy's RBAC filter) | Per-request decisions through an external authorization hook (for example Envoy `ext_authz` with OPA) |

Whatever the language, the item's evidence is the same: the policy, a test that an unlisted
or unapproved call is refused, and a test that the gateway fails closed when the policy
engine is unavailable (see [CHECKLIST.md](../../CHECKLIST.md)).
