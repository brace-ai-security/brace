"""Rule metadata, declared once. Every reporter, the SARIF rule list and --list-rules derive from it.

Keep titles in step with the `### APnn: Title` headings in ANTI-PATTERNS.md and the table in
SCAN.md; tests check both.

Taxonomy references (refs) let code-scanning tools group findings by OWASP and MITRE ATLAS
entries. They are derived, not chosen per rule: an OWASP risk or ATLAS technique relates to a
rule when its most relevant BRACE item (listed first in mappings/*.md) is one of the rule's
checklist items, and the mapping rates it Direct or Partial (Direct only for ATLAS, whose
techniques are finer grained). A test re-derives them from the mapping files. CWE entries are
added only where the weakness is the finding itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DOCS = "https://braceframework.org/anti-patterns/"
NOT_ALNUM = re.compile(r"[^A-Za-z0-9]+")
NOT_ANCHOR = re.compile(r"[^\w\- ]")  # characters a Markdown heading anchor drops
RULE_ID_PATTERN = r"[A-Z][A-Z0-9_\-]{1,31}"  # a rule ID, built-in (AP04) or from a plugin (ACME-01)


@dataclass(frozen=True)
class Taxonomy:
    name: str
    version: str | None      # None when no single edition applies
    uri: str
    organization: str


# The taxonomies refs point into, by ref prefix; the one place their editions are named.
TAXONOMIES = {
    "owasp-asi": Taxonomy("OWASP Top 10 for Agentic Applications", "2026",
                          "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/", "OWASP"),
    "owasp-mcp": Taxonomy("OWASP MCP Top 10", "2025", "https://owasp.org/www-project-mcp-top-10/", "OWASP"),
    "atlas": Taxonomy("MITRE ATLAS", "2026.10", "https://atlas.mitre.org/", "MITRE"),
    "cwe": Taxonomy("CWE", None, "https://cwe.mitre.org/", "MITRE"),
}
# The name of every entry a built-in rule refers to.
TAXA = {
    "owasp-asi:ASI01": "Agent Goal Hijack",
    "owasp-asi:ASI02": "Tool Misuse and Exploitation",
    "owasp-asi:ASI04": "Agentic Supply Chain Vulnerabilities",
    "owasp-asi:ASI05": "Unexpected Code Execution (RCE)",
    "owasp-mcp:MCP01": "Token Mismanagement & Secret Exposure",
    "owasp-mcp:MCP02": "Privilege Escalation via Scope Creep",
    "owasp-mcp:MCP04": "Software Supply Chain Attacks & Dependency Tampering",
    "owasp-mcp:MCP06": "Intent Flow Subversion",
    "owasp-mcp:MCP07": "Insufficient Authentication & Authorization",
    "owasp-mcp:MCP09": "Shadow MCP Servers",
    "atlas:AML.T0010.004": "Supply Chain Compromise: Container Registry",
    "atlas:AML.T0050": "Command and Scripting Interpreter",
    "atlas:AML.T0051": "LLM Prompt Injection",
    "atlas:AML.T0051.002": "LLM Prompt Injection: Triggered",
    "atlas:AML.T0053": "AI Agent Tool Invocation",
    "atlas:AML.T0055": "Unsecured Credentials",
    "atlas:AML.T0077": "LLM Response Rendering",
    "atlas:AML.T0083": "Credentials from AI Agent Configuration",
    "atlas:AML.T0085.001": "Data from AI Services: AI Agent Tools",
    "atlas:AML.T0086": "Exfiltration via AI Agent Tool Invocation",
    "atlas:AML.T0100": "AI Agent Clickbait",
    "atlas:AML.T0101": "Data Destruction via AI Agent Tool Invocation",
    "atlas:AML.T0110.000": "AI Agent Tool Poisoning: Definition and Instructions",
    "atlas:AML.T0125": "Create Account",
    "atlas:AML.T0132": "Misconfigured or Publicly Exposed AI Services",
    "cwe:250": "Execution with Unnecessary Privileges",
    "cwe:319": "Cleartext Transmission of Sensitive Information",
    "cwe:798": "Use of Hard-coded Credentials",
    "cwe:829": "Inclusion of Functionality from Untrusted Control Sphere",
}


@dataclass(frozen=True)
class RuleMeta:
    id: str
    title: str
    severity: str
    why: str
    fix: str
    checklist: tuple[str, ...] = ()
    url: str = ""  # a plugin rule's own documentation; built-in rules link to ANTI-PATTERNS
    refs: tuple[str, ...] = ()  # taxonomy entries, "prefix:id" with a prefix from TAXONOMIES

    @property
    def name(self) -> str:
        """The title as one PascalCase word, the readable rule name SARIF consumers show."""
        return "".join(w[:1].upper() + w[1:] for w in NOT_ALNUM.split(self.title) if w)

    @property
    def anchor(self) -> str:
        """Heading anchor of the rule in ANTI-PATTERNS.md ('### AP01: Title')."""
        return NOT_ANCHOR.sub("", f"{self.id}: {self.title}".lower()).replace(" ", "-")

    @property
    def help_uri(self) -> str:
        return self.url or f"{DOCS}#{self.anchor}"


RULES: tuple[RuleMeta, ...] = (
    RuleMeta("AP01", "Agent runs with all permission checks turned off", "high",
             "Every tool call, including shell commands and file deletes, runs without approval. One prompt "
             "injection in a file, issue or web page the agent reads can run any command as you.",
             "Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway "
             "sandbox with no secrets and no network beyond what the task needs.",
             ("B05", "B01", "B08"),
             refs=("owasp-asi:ASI02", "atlas:AML.T0053", "atlas:AML.T0086", "atlas:AML.T0100", "atlas:AML.T0101")),
    RuleMeta("AP02", "Unattended agent in CI with permission checks turned off", "critical",
             "A CI agent with no approvals and the job's token can be steered by anyone who can write an issue, "
             "PR, commit message or file it reads, and then push code, read secrets or publish packages.",
             "Keep approvals on, give the job read-only permissions, and run untrusted-input jobs without "
             "repository secrets.",
             ("B05", "B02", "B03", "B09"),
             refs=("owasp-mcp:MCP01", "owasp-mcp:MCP02", "atlas:AML.T0055", "atlas:AML.T0083", "atlas:AML.T0085.001",
                   "atlas:AML.T0086", "atlas:AML.T0100", "atlas:AML.T0101", "atlas:AML.T0125")),
    RuleMeta("AP03", "Agent workflow triggered by pull_request_target", "critical",
             "pull_request_target runs with the base repository's secrets and write token on events from "
             "forks. An agent that reads the fork's PR text or code can be told to leak or misuse them.",
             "Use pull_request for agent jobs, or split the job so the agent never sees secrets or a "
             "write token while it reads outside content.",
             ("B02", "B05", "R02"),
             refs=("owasp-asi:ASI01", "owasp-mcp:MCP02", "owasp-mcp:MCP06", "atlas:AML.T0051", "atlas:AML.T0051.002",
                   "atlas:AML.T0085.001", "atlas:AML.T0086", "atlas:AML.T0100", "atlas:AML.T0101", "atlas:AML.T0125")),
    RuleMeta("AP04", "MCP server installed from an unpinned package", "high",
             "npx/uvx/bunx fetch the newest version at every start. A hijacked or malicious update "
             "becomes code running with your agent's access, with no review.",
             "Pin an exact version (for example pkg@1.4.2), or install it once from a reviewed lockfile.",
             ("E02", "E03", "C05"),
             refs=("owasp-asi:ASI04", "owasp-mcp:MCP04", "atlas:AML.T0110.000", "cwe:829")),
    RuleMeta("AP05", "Secret written directly in agent configuration", "high",
             "Config files get committed, copied and read by the agent itself. A literal token is "
             "long-lived, shared and easy to leak through the agent's output.",
             "Load the secret from the environment or a secret manager, use a short-lived scoped "
             "token, and rotate the exposed one.",
             ("B03", "R03"),
             refs=("owasp-mcp:MCP01", "atlas:AML.T0055", "atlas:AML.T0077", "atlas:AML.T0083", "cwe:798")),
    RuleMeta("AP06", "Agent allowed to run any shell command", "high",
             "An allow-rule like Bash(*) or a bare Bash lets the agent run any command without asking. "
             "That includes curl to send your files out, rm -rf and git push --force.",
             "Allow only the specific commands the task needs, such as Bash(npm test), and keep deny "
             "rules for network and destructive commands.",
             ("B01", "B05"),
             refs=("owasp-asi:ASI02", "atlas:AML.T0053", "atlas:AML.T0086", "atlas:AML.T0100", "atlas:AML.T0101")),
    RuleMeta("AP07", "Remote MCP server reached over plain HTTP", "medium",
             "Tool calls, results and credentials cross the network unencrypted and can be read or "
             "changed in transit, including the tool descriptions the model trusts.",
             "Use https, and authenticate the server.",
             ("E05", "E06"),
             refs=("owasp-mcp:MCP07", "owasp-mcp:MCP09", "atlas:AML.T0132", "cwe:319")),
    RuleMeta("AP08", "Agent tool container can take over the host", "high",
             "--privileged, a mounted Docker socket, host networking or a mounted root filesystem "
             "remove the container boundary. A compromised tool then controls the machine.",
             "Drop these flags. Mount only the folders the tool needs, read-only where possible.",
             ("B08", "B11", "B09"),
             refs=("owasp-asi:ASI05", "atlas:AML.T0050", "cwe:250")),
    RuleMeta("AP09", "Lethal combination: untrusted input, private data and a way out", "medium",
             "The same agent can read content an attacker controls, reach private data and send data "
             "or act outside. Prompt injection then becomes data theft; no system prompt reliably stops it.",
             "Split the capabilities across agents, remove one leg, or require a person to approve "
             "every outbound or consequential action.",
             ("B05", "B01", "R02"),
             refs=("owasp-asi:ASI01", "owasp-asi:ASI02", "owasp-mcp:MCP06", "atlas:AML.T0051", "atlas:AML.T0051.002",
                   "atlas:AML.T0053", "atlas:AML.T0086", "atlas:AML.T0100", "atlas:AML.T0101")),
    RuleMeta("AP10", "Agent image not pinned to a digest", "low",
             "A mutable tag such as :latest can change under you, so what you tested is not what runs.",
             "Pin the base image by digest (image@sha256:...) and update it on purpose.",
             ("B10", "C01"),
             refs=("atlas:AML.T0010.004", "cwe:829")),
)
