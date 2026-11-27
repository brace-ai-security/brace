"""Every bound the scanner keeps, in one place, each with why it exists.

The scanned folder is untrusted, so every size, count and length the scanner reads, keeps or
prints has a fixed bound: scans stay linear in time and bounded in memory, and output stays
readable whatever the input. Limits are the two a config file may change (lower freely, raise
only up to CEILINGS); the rest are fixed. Look-around windows that define what a heuristic
means (such as how far before a list its name is searched for) stay next to that heuristic.
"""
from __future__ import annotations

from dataclasses import dataclass

KB, MB = 1024, 1024 * 1024


@dataclass(frozen=True)
class Limits:
    """The bounds a config file may set."""
    max_file_bytes: int = 1 * MB      # larger files are listed in a note, not read
    max_files: int = 200_000         # the walk stops here and the scan is incomplete


# Config keys of the Limits fields, in the order notes list them.
LIMIT_KEYS = (("max-file-bytes", "max_file_bytes"), ("max-files", "max_files"))
CEILINGS = Limits(max_file_bytes=16 * MB, max_files=1_000_000)  # a config file cannot raise limits past these

# Reading
HOST_FILE_BYTES = 5 * MB             # host settings such as ~/.claude.json grow larger than repository files
CONFIG_FILE_BYTES = 256 * KB         # a config file is hand-written; anything larger is a mistake or an attack
MAX_VALUE = 4096                     # characters of one string matched against secret patterns, shown, or kept
                                     # from a server's name, arguments and keys (redaction sees a secret whole)
TOML_KEY_PARTS = 64                  # dotted parts in one TOML key: tomllib (3.11-3.13) is quadratic in them
TOML_LINE = 64 * KB                  # characters in one TOML line
TOML_NESTING = 100                   # inline tables and arrays nested in one TOML file
BASELINE_BYTES = 8 * MB              # a baseline file (--baseline): about 100 bytes per finding
BASELINE_IDS = 50_000                # findings listed in one baseline
MERGE_FILE_BYTES = 32 * MB           # one JSON report read by `merge`
MERGE_FILES = 1000                   # reports one `merge` combines
MERGE_FINDINGS = 200_000             # findings of all reports one `merge` keeps
EXPIRY_WARNING_DAYS = 30             # an ignore entry or exception expiring this soon gets a note

# Findings
MAX_PER_FILE = 100                   # findings per file and check (and images kept per file); more is incomplete
MAX_INVENTORY = 5000                 # agent config files and MCP servers listed in a CycloneDX inventory
MAX_SUPPRESSED = 5000                # suppressed findings kept for SARIF and JSON; past it they are only counted
MAX_PER_LINE = 20                    # bypass matches examined on one line; one line says enough
MAX_LINE = 2000                      # characters of a workflow line the line heuristics read
WORD_PART_CHARS = 200                # characters of each name, package, image or host AP09 reads words from
WRAPPER_DEPTH = 6                    # wrappers looked through to find a server's program (env exec sh -c ...)
MAX_OPEN_BRACKETS = 1000             # brackets tracked when deciding whether a flag sits in a deny-list
MAX_NAMES = 200                      # distinct names whose uses are followed in one file (deny-lists, pushed
                                     # argument lists); past it a flag is reported, not judged a mention
MAX_PER_COMMAND = 200                # gated flags examined in one logical command (a line and its continuations)
JSON_INDEX_KEYS = 200_000            # object keys indexed for line numbers in one JSON file
WALK_DEPTH = 32                      # nesting followed when every value of an agent config is checked for secrets
WALK_VALUES = 20_000                 # values of one agent config checked for secrets
JSON_INDEX_DEPTH = 8                 # findings point at most 6 keys deep (projects.<p>.mcpServers.<n>.env.<k>)

# Ignore entries and config globs: matching cost grows with these, so they are capped
MAX_IGNORES = 200                    # entries read from the ignore file, and in the config's ignore list
MAX_PATTERN = 200                    # characters in one pattern
MAX_SEGMENTS = 16                    # folders in one pattern; deeper ones are skipped (ignore file) or refused (config)
MAX_FLEX = 400                       # segments after `**`, summed over one list: each can be live in every folder
IGNORE_CACHE_FOLDERS = 4096          # folders whose pattern states are cached during the walk
MAX_GLOBS = 200                      # include and agent-config entries
MAX_IGNORE_RULES = 1000              # ignore path-and-rule pairs after expanding each entry's rule list
MAX_TOKENS = 50                      # custom token formats
TOKEN_MIN, TOKEN_MAX = 8, 400        # length bounds a custom token may declare

# Output: lengths of strings as shown, and how many items a summary lists
DETAIL_CHARS = 160                   # a finding's detail
FILE_CHARS = 300                     # a finding's file path
NOTE_CHARS = 300                     # a note or an error message
NOTE_PATH_CHARS = 120                # a file path inside a note
LISTED_PATH_CHARS = 80               # each file in a list of skipped files
LISTED_FILES = 5                     # skipped files named per note; the rest are counted
MAX_PLACES = 8                       # places listed per rule in the text output (--json lists all)
MAX_ROWS = 200                       # Markdown rows: GitHub caps a job summary at 1 MiB and a row is about 2 KB
MAX_NOTES = 50                       # notes in the Markdown summary
MAX_RESULTS = 5000                   # SARIF results in one file, as consumers cap uploads (the JSON lists all)
