# Fail on an unpinned MCP server package or image (rule AP04) unless the server is on an
# approved list, supplied as data (see ../inputs/approved.json):
#   {"approved_unpinned_mcp": ["local-dev-server"]}
# AP04 details start with the server's name: "<server>: npx some-package".
package main

import rego.v1

approved := object.get(data, "approved_unpinned_mcp", [])

deny contains msg if {
	some f in input.findings
	f.rule == "AP04"
	server := split(f.detail, ": ")[0]
	not server in approved
	msg := sprintf("unpinned MCP server %q at %s:%d; pin it or add it to approved_unpinned_mcp", [server, f.file, f.line])
}
