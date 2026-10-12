

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

ParsedEntry = dict


def read_jsonl(filepath: str | Path) -> Tuple[List[ParsedEntry], int]:
    """Read JSONL entries, skipping invalid lines and counting them."""

    entries: List[ParsedEntry] = []
    bad_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if not stripped:
                continue

            try:
                entry = json.loads(stripped)

                # The analyzer requires each entry to be a dictionary.
                if not isinstance(entry, dict):
                    bad_count += 1
                    continue

                entries.append(entry)

            except json.JSONDecodeError:
                bad_count += 1

    return entries, bad_count