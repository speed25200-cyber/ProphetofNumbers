#!/usr/bin/env python3
"""Measure exact MT-prefix constraints available from sorted 20-of-80 sets.

For a forward Fisher-Yates sampler with multiply-high mapping, the first selected
ball is ``1 + ((u * 80) >> 32)``.  Even when the draw order is lost, that ball must
belong to the published set.  This program measures the resulting disjunction on
the top ``b`` output bits and checks whether it contains any affine GF(2) equality.

It is a feasibility audit, not a state-recovery claim: information counts alone do
not establish that a SAT instance is computationally tractable.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable


def number_mask(numbers: Iterable[int]) -> int:
    mask = 0
    values = list(numbers)
    if len(values) != 20 or len(set(values)) != 20:
        raise ValueError("each draw must contain exactly 20 unique numbers")
    for value in values:
        if type(value) is not int or not 1 <= value <= 80:
            raise ValueError("draw number outside 1..80")
        mask |= 1 << (value - 1)
    return mask


def prefix_number_masks(bits: int) -> list[int]:
    if not 1 <= bits <= 20:
        raise ValueError("prefix width must be in 1..20")
    shift = 32 - bits
    masks = []
    for prefix in range(1 << bits):
        low = prefix << shift
        high = ((prefix + 1) << shift) - 1
        first_index = (low * 80) >> 32
        last_index = (high * 80) >> 32
        mask = 0
        for index in range(first_index, last_index + 1):
            mask |= 1 << index
        masks.append(mask)
    return masks


def allowed_prefixes(draw_mask: int, prefix_masks: list[int]) -> list[int]:
    return [prefix for prefix, possible in enumerate(prefix_masks) if draw_mask & possible]


def gf2_rank(rows: Iterable[int]) -> int:
    pivots: dict[int, int] = {}
    rank = 0
    for row in rows:
        value = row
        while value:
            pivot = value.bit_length() - 1
            if pivot in pivots:
                value ^= pivots[pivot]
            else:
                pivots[pivot] = value
                rank += 1
                break
    return rank


def affine_rank(points: list[int]) -> int:
    if not points:
        return 0
    origin = points[0]
    return gf2_rank(point ^ origin for point in points[1:])


def load_archive(draw_directory: Path) -> list[int]:
    paths = sorted(draw_directory.glob("draws-*.csv"))
    if not paths:
        raise ValueError(f"no draws-*.csv files in {draw_directory}")
    masks: list[int] = []
    previous_id: int | None = None
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for line_number, row in enumerate(reader, 2):
                try:
                    draw_id = int(row["id"])
                    values = [int(row[f"n{i}"]) for i in range(1, 21)]
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"{path}:{line_number}: invalid archive row") from exc
                if values != sorted(values):
                    raise ValueError(f"{path}:{line_number}: archive set is not sorted")
                if previous_id is not None and draw_id != previous_id + 1:
                    raise ValueError(f"{path}:{line_number}: non-contiguous draw id")
                previous_id = draw_id
                masks.append(number_mask(values))
    return masks


def audit_width(draw_masks: list[int], bits: int, state_bits: int, margin_bits: int) -> dict:
    prefix_masks = prefix_number_masks(bits)
    counts: Counter[int] = Counter()
    affine_ranks: Counter[int] = Counter()
    information = []
    for draw_mask in draw_masks:
        allowed = allowed_prefixes(draw_mask, prefix_masks)
        count = len(allowed)
        counts[count] += 1
        affine_ranks[affine_rank(allowed)] += 1
        information.append(bits - math.log2(count))
    mean_information = sum(information) / len(information)
    required = math.ceil((state_bits + margin_bits) / mean_information)
    return {
        "prefix_bits": bits,
        "draws": len(draw_masks),
        "mean_allowed_prefixes": round(
            sum(count * frequency for count, frequency in counts.items()) / len(draw_masks), 9
        ),
        "min_allowed_prefixes": min(counts),
        "max_allowed_prefixes": max(counts),
        "mean_information_bits": round(mean_information, 9),
        "min_information_bits": round(min(information), 9),
        "max_information_bits": round(max(information), 9),
        "affine_rank_histogram": {str(rank): affine_ranks[rank] for rank in sorted(affine_ranks)},
        "draws_with_no_affine_equality": affine_ranks.get(bits, 0),
        "heuristic_draws_for_state_plus_margin": required,
        "state_bits": state_bits,
        "margin_bits": margin_bits,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument(
        "--draw-directory",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "draws",
    )
    root.add_argument("--prefix-bits", type=int, nargs="+", default=[7, 8])
    root.add_argument("--state-bits", type=int, default=19_937)
    root.add_argument("--margin-bits", type=int, default=64)
    return root


def main() -> int:
    args = parser().parse_args()
    masks = load_archive(args.draw_directory)
    report = {
        "model": "first Fisher-Yates/mulhi output belongs to published sorted set",
        "warning": "information heuristic only; no MT19937 state recovery is claimed",
        "widths": [
            audit_width(masks, bits, args.state_bits, args.margin_bits)
            for bits in args.prefix_bits
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
