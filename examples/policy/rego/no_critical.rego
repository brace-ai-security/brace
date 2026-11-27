# Fail when the scan reports any critical finding.
# Input: an open-agent-security JSON report (report-1.schema.json).
package main

import rego.v1

deny contains msg if {
	some f in input.findings
	f.severity == "critical"
	msg := sprintf("critical finding %s at %s:%d: %s", [f.rule, f.file, f.line, f.title])
}
