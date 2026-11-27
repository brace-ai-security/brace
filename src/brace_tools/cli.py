"""The `brace` command line: one entry point for every BRACE tool.

Subcommands import their module only when run, so `brace scan` needs nothing beyond the
standard library and a missing optional dependency names the extra to install.

Exit codes (unchanged from the tools each subcommand runs):

  command            0              1                         2                 3
  scan               no finding     findings at --fail-on     usage / error     -
  init items hash
  check export
  import-results     conditions met unresolved findings       invalid input     -
  map ...            done / valid   invalid or rejected       usage             record differs (no --apply)
  plan               written        --strict input notes      usage / invalid   --fail-on matched
"""
from __future__ import annotations

import sys

EXTRA_HINT = 'pip install "open-agent-security[record]"'

RECORD = ("init", "items", "hash", "check", "export", "import-results")
MAP = ("build", "validate", "mermaid", "add-node", "add-edge", "set-zone", "add-tag", "record", "report")

USAGE = f"""usage: brace <command> [args]

Find dangerous agent setups (standard library only):
  scan [path] [options]        the open-agent-security scanner (same options)

Keep a BRACE record (needs the [record] extra: {EXTRA_HINT}):
  init                         create .brace/ from the templates
  items                        list the checklist items
  hash                         hash the files the manifest names
  check                        check the record; findings for high-risk deployments
  export                       the record as HTML, CSV or JSON for an auditor
  import-results               attach garak, PyRIT, promptfoo or Inspect results

Map and plan:
  map {{{','.join(MAP)}}}
                               the CycloneDX topology map
  plan FINDINGS TOPOLOGY -o FILE
                               the action plan (Markdown, CSV, JSON, SARIF, HTML)

Run `brace <command> --help` for a command's options. `brace --version` prints the version.
"""


def _missing(command: str, exc: ModuleNotFoundError) -> int:
    sys.stderr.write(f"brace {command} needs {exc.name}, which comes with the [record] extra.\n"
                     f"Install it with: {EXTRA_HINT}\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        (sys.stdout if argv else sys.stderr).write(USAGE)
        return 0 if argv else 2
    command, rest = argv[0], argv[1:]
    if command in ("--version", "-V"):
        from brace_tools import __version__
        print(f"brace {__version__}")
        return 0
    if command == "scan":
        from open_agent_security.cli import main as scan_main
        return scan_main(rest)
    try:
        if command in RECORD:
            from brace_tools.record import core
            return core.main([command, *rest], prog="brace")
        if command == "map":
            from brace_tools.topology import core
            return core.main(rest, prog="brace map")
        if command == "plan":
            from brace_tools.plan import core
            return core.main(rest, prog="brace plan")
    except ModuleNotFoundError as exc:
        if exc.name in ("yaml", "jsonschema"):
            return _missing(command, exc)
        raise
    sys.stderr.write(f"brace: unknown command {command!r}\n\n{USAGE}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
