"""Robust JSONL reader that skips bad lines and counts them."""

from __future__ import annotations

import json
from typing import List, Tuple

ParsedEntry = dict


def read_jsonl(filepath: str) -> Tuple[List[ParsedEntry], int]:
    """Read a JSONL file, parsing each line and skipping invalid ones.

    Returns:
        (entries, bad_line_count) - valid parsed entries and count of lines
        that could not be parsed as JSON.
    """
    entries: List[ParsedEntry] = []
    bad_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                # Skip empty lines but don't count as bad
                continue
            try:
                entry = json.loads(stripped)
                entries.append(entry)
            except json.JSONDecodeError:
                bad_count += 1

    return entries, bad_count