"""Deterministic ID allocation utilities for Tinkerspace entities.

Implements PREFIX-A01 series progression using a 24-letter base excluding 'I' and 'O'.
"""

from pathlib import Path
import re
from typing import Sequence

# 24-letter alphabet excluding 'I' and 'O' (DA-01 §02)
ID_ALPHABET = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M",
    "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
]
LETTER_TO_VAL = {char: idx for idx, char in enumerate(ID_ALPHABET)}
ID_PATTERN = re.compile(r"^([A-Za-z]{3,4})-([A-HJ-NP-Za-hj-np-z]{1,2})([0-9]{2})$")


def sequence_to_index(seq_str: str) -> int:
    """Convert sequence string (e.g. 'A01', 'Z99', 'AA01') to zero-based integer index."""
    match = re.match(r"^([A-HJ-NP-Za-hj-np-z]{1,2})([0-9]{2})$", seq_str.strip())
    if not match:
        raise ValueError(f"Invalid ID sequence format: {seq_str}")

    letters = match.group(1).upper()
    num = int(match.group(2))
    if num < 1 or num > 99:
        raise ValueError(f"Sequence number must be 01-99, got {num}")

    num_offset = num - 1
    if len(letters) == 1:
        l_idx = LETTER_TO_VAL[letters[0]]
        return l_idx * 99 + num_offset

    l1_idx = LETTER_TO_VAL[letters[0]]
    l2_idx = LETTER_TO_VAL[letters[1]]
    single_series_total = 24 * 99
    return single_series_total + (l1_idx * 24 + l2_idx) * 99 + num_offset


def index_to_sequence(index: int) -> str:
    """Convert zero-based integer index to sequence string (e.g. 0 -> 'A01', 99 -> 'B01')."""
    if index < 0:
        raise ValueError(f"Index must be non-negative, got {index}")

    single_series_total = 24 * 99
    if index < single_series_total:
        l_idx = index // 99
        num = (index % 99) + 1
        return f"{ID_ALPHABET[l_idx]}{num:02d}"

    rem = index - single_series_total
    pair_idx = rem // 99
    l1_idx = pair_idx // 24
    l2_idx = pair_idx % 24
    num = (rem % 99) + 1

    if l1_idx >= 24:
        raise OverflowError("ID sequence space exceeded (max ZZ99)")

    return f"{ID_ALPHABET[l1_idx]}{ID_ALPHABET[l2_idx]}{num:02d}"


def parse_id_components(id_str: str) -> tuple[str, str] | None:
    """Extract (prefix, sequence) from ID string if valid."""
    match = ID_PATTERN.match(id_str.strip())
    if not match:
        return None
    prefix = match.group(1).upper()
    seq = f"{match.group(2).upper()}{match.group(3)}"
    return prefix, seq


def allocate_next_id(prefix: str, existing_ids: Sequence[str]) -> str:
    """Compute the deterministic next ID for a prefix given all existing allocated IDs."""
    target_prefix = prefix.strip().upper()
    matching_indices: list[int] = []

    for item in existing_ids:
        parsed = parse_id_components(item)
        if parsed is not None:
            item_prefix, seq = parsed
            if item_prefix == target_prefix:
                matching_indices.append(sequence_to_index(seq))

    if not matching_indices:
        return f"{target_prefix}-A01"

    next_idx = max(matching_indices) + 1
    return f"{target_prefix}-{index_to_sequence(next_idx)}"
