"""
P15 (see ~/browseterm/p.md's "P15" section, plan section 5.6): snapshot version formatting.

The DB stores the raw integer (container_snapshots.version_sequence / containers.
next_snapshot_sequence) as the source of truth - this module only formats that integer into the
5-part dotted-decimal display form (e.g. 1 -> "0.0.0.0.1", 100 -> "0.0.1.0.0", 99999 ->
"9.9.9.9.9") for the `version` column. Deliberately base-10 digit-group formatting, not real
arithmetic on the formatted string - the plan explicitly says "Do NOT perform version arithmetic
using strings," so nothing here ever parses a `version` string back into a sequence number; the
integer column is always the one arithmetic (allocation, comparison, ordering) is done on.
"""


def format_snapshot_version(sequence: int) -> str:
    """1 -> "0.0.0.0.1", 10 -> "0.0.0.1.0", 99999 -> "9.9.9.9.9"."""
    if sequence < 0:
        raise ValueError(f"version_sequence must be >= 0, got {sequence}")
    digits = str(sequence).zfill(5)
    if len(digits) > 5:
        raise ValueError(f"version_sequence {sequence} does not fit in 5 digits (max 99999)")
    return ".".join(digits)
