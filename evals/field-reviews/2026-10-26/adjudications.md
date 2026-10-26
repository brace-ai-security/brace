# Source adjudications

Original reports and auditor outputs are unchanged. `audit-selections.json` selects
separate corrected/adjudicated versions. No server code or skill was changed.

- Notion auditor corrected its initial interpretation of Docker `{}`. The report
  says it hides a missing token, not an existing configured token. That sentence
  is a qualified late-failure concern; the separate unconditional non-object JSON
  assertion still contradicts fallback to NOTION_TOKEN.
- Filesystem stop/recovery row explicitly says `needs_evidence`, with host ownership.
  Its within-call wording can mean awaited tool work rather than detached jobs.
  Root qualifies this ambiguity rather than infer a claimed cancellation or
  serialization guarantee. Async implementation is still explicit. The unqualified
  write-TOCTOU likely_pass across Windows remains a substantive false assurance.
- Notion plain advice prioritizes restricting upload paths for an asserted current
  exploit. The shipped fixed specification has no such operations. The original
  auditor called that a conditional future-hardening direction; root marks the
  recommendation unsupported **as stated for this current server**. Conditions
  supplied by an auditor do not retroactively qualify the original urgent advice.
  Future optional upload hardening is a distinct proposal. This recommendation
  overlaps the false finding and must not be counted as another independent flaw.

These are static judgments. Other recommendations rated conditional still need
the recorded applicability, compatibility and runtime checks. No safe production
fix, complete recall, release decision or general model reliability is established.
