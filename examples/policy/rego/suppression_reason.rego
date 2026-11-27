# Fail when a finding is suppressed without a written reason.
#
# The scanner fills in a justification for every suppression. Only a config [[ignore]]
# entry with `reason = "..."` carries a reason someone wrote; an inline mark, an ignore-file
# entry and a config entry without a reason get a generated one, which this policy refuses.
# A rule turned off in the config is allowed: that decision is visible in the config file.
# Suppressions have no expiry date today, so no date is checked.
package main

import rego.v1

generated := ["inline '", ".open-agent-security-ignore entry '", "config ignore entry '"]

deny contains msg if {
	some f in object.get(input, "suppressed_findings", [])
	some prefix in generated
	startswith(f.suppression.justification, prefix)
	msg := sprintf("%s at %s:%d is suppressed without a written reason (%s)", [f.rule, f.file, f.line, f.suppression.justification])
}
