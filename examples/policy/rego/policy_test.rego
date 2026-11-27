# Unit tests: opa test examples/policy/rego
package main_test

import rego.v1

import data.main

finding(rule, severity, detail) := {"rule": rule, "severity": severity, "detail": detail, "file": ".mcp.json", "line": 3, "title": "t"}

report(findings, suppressed, incomplete) := {
	"scanner": "open-agent-security", "incomplete": incomplete, "truncated": false,
	"findings": findings, "suppressed_findings": suppressed,
}

test_clean_report_passes if {
	count(main.deny) == 0 with input as report([], [], false)
}

test_critical_fails if {
	denied := main.deny with input as report([finding("AP03", "critical", "x")], [], false)
	some msg in denied
	startswith(msg, "critical finding AP03")
}

test_incomplete_fails if {
	count(main.deny) == 1 with input as report([], [], true)
}

test_unpinned_fails_unless_approved if {
	r := report([finding("AP04", "high", "dev: npx dev-mcp")], [], false)
	count(main.deny) == 1 with input as r
	count(main.deny) == 0 with input as r with data.approved_unpinned_mcp as ["dev"]
}

test_suppression_needs_written_reason if {
	mark := object.union(finding("AP01", "high", "x"), {"suppression": {"kind": "inSource", "justification": "inline 'open-agent-security: ignore' mark on line 1"}})
	written := object.union(finding("AP01", "high", "x"), {"suppression": {"kind": "external", "justification": "test fixture, not run"}})
	count(main.deny) == 1 with input as report([], [mark], false)
	count(main.deny) == 0 with input as report([], [written], false)
}
