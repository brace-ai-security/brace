# Fail when the scan is incomplete or stopped at the file limit: an incomplete scan
# cannot say a folder is clean, so a gate must not pass on it.
package main

import rego.v1

deny contains "the scan is incomplete (see its notes), so it cannot say this folder is clean" if {
	input.incomplete == true
}

deny contains "the scan stopped at the file limit" if {
	input.truncated == true
}

deny contains "the input is not an open-agent-security JSON report" if {
	input.scanner != "open-agent-security"
}
