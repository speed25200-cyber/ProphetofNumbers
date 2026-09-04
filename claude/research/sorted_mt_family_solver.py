#!/usr/bin/env python3
"""Exact sorted-draw constraints on a bounded affine family of MT19937 states.

This is a deliberately bounded research prototype.  It uses the real MT19937
transition and tempering functions, and it generates real forward Fisher-Yates
20-of-80 draws with multiply-high index mapping.  The solver sees only each
sorted 20-number set.  For every draw it applies the exact disjunction

    first generated ball is a member of the published set.

The disjunction is evaluated for *every* state in an explicitly constructed
``B``-dimensional affine family.  Constraint supports are represented as Python
integer bitsets and intersected exactly; there are no probabilistic exclusions
and no prefix relaxation.

The important limitation is equally explicit: the cost is Theta(2**B), so this
does not solve MT19937's full 19,937-bit state.  The prototype exists to validate
the modelling, quantify pruning on honest MT19937 streams, and expose the
exponential wall before investing in a full SAT/BDD implementation.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


WORD_MASK = 0xFFFFFFFF
MT_N = 624
MT_M = 397
MATRIX_A = 0x9908B0DF
UPPER_MASK = 0x80000000
LOWER_MASK = 0x7FFFFFFF


def mt_init(seed: int) -> tuple[int, ...]:
    """Return the 624-word state made by the reference ``init_genrand``."""

    if type(seed) is not int or not 0 <= seed <= WORD_MASK:
        raise ValueError("MT seed must be an unsigned 32-bit integer")
    state = [0] * MT_N
    state[0] = seed
    for index in range(1, MT_N):
        previous = state[index - 1]
        state[index] = (
            1812433253 * (previous ^ (previous >> 30)) + index
        ) & WORD_MASK
    return tuple(state)


def mt_twist(state: Sequence[int]) -> tuple[int, ...]:
    """Apply the reference in-place MT19937 twist to one state array.

    The second reference loop deliberately reads words already renewed by the
    first loop.  A tempting modulo-indexed computation into a separate array is
    *not* equivalent after word 226.
    """

    if len(state) != MT_N:
        raise ValueError("an MT19937 state must contain exactly 624 words")
    result = [int(word) & WORD_MASK for word in state]
    for index in range(MT_N - MT_M):
        joined = (result[index] & UPPER_MASK) | (result[index + 1] & LOWER_MASK)
        result[index] = (
            result[index + MT_M]
            ^ (joined >> 1)
            ^ (MATRIX_A if joined & 1 else 0)
        ) & WORD_MASK
    for index in range(MT_N - MT_M, MT_N - 1):
        joined = (result[index] & UPPER_MASK) | (result[index + 1] & LOWER_MASK)
        result[index] = (
            result[index + (MT_M - MT_N)]
            ^ (joined >> 1)
            ^ (MATRIX_A if joined & 1 else 0)
        ) & WORD_MASK
    joined = (result[MT_N - 1] & UPPER_MASK) | (result[0] & LOWER_MASK)
    result[MT_N - 1] = (
        result[MT_M - 1]
        ^ (joined >> 1)
        ^ (MATRIX_A if joined & 1 else 0)
    ) & WORD_MASK
    return tuple(result)


def mt_temper(word: int) -> int:
    """Temper one MT19937 state word exactly as in the reference code."""

    value = int(word) & WORD_MASK
    value ^= value >> 11
    value ^= (value << 7) & 0x9D2C5680
    value ^= (value << 15) & 0xEFC60000
    value ^= value >> 18
    return value & WORD_MASK


class MT19937Stream:
    """MT19937 stream starting at word zero of an already-twisted state."""

    def __init__(self, post_twist_state: Sequence[int]):
        if len(post_twist_state) != MT_N:
            raise ValueError("an MT19937 state must contain exactly 624 words")
        self.state = tuple(int(word) & WORD_MASK for word in post_twist_state)
        self.index = 0

    @classmethod
    def from_seed(cls, seed: int) -> "MT19937Stream":
        return cls(mt_twist(mt_init(seed)))

    def next_u32(self) -> int:
        if self.index == MT_N:
            self.state = mt_twist(self.state)
            self.index = 0
        value = mt_temper(self.state[self.index])
        self.index += 1
        return value


def mulhi(value: int, bound: int) -> int:
    """Map a uint32 uniformly-ish to ``0..bound-1`` using multiply-high."""

    if type(value) is not int or not 0 <= value <= WORD_MASK:
        raise ValueError("value must be an unsigned 32-bit integer")
    if type(bound) is not int or not 1 <= bound <= WORD_MASK:
        raise ValueError("bound must be a positive 32-bit integer")
    return (value * bound) >> 32


def validate_sorted_draw(draw: Iterable[int]) -> tuple[int, ...]:
    values = tuple(draw)
    if len(values) != 20 or len(set(values)) != 20:
        raise ValueError("a draw must contain exactly 20 unique numbers")
    if any(type(value) is not int or not 1 <= value <= 80 for value in values):
        raise ValueError("draw numbers must be plain integers in 1..80")
    if values != tuple(sorted(values)):
        raise ValueError("the observation must be a sorted set")
    return values


def generate_sorted_draws(
    post_twist_state: Sequence[int], draw_count: int, stride: int = 20
) -> list[tuple[int, ...]]:
    """Generate sorted observations using the exact 20-step shuffle prefix."""

    if type(draw_count) is not int or draw_count < 0:
        raise ValueError("draw_count must be a non-negative integer")
    if type(stride) is not int or stride < 20:
        raise ValueError("stride must be an integer of at least 20")
    stream = MT19937Stream(post_twist_state)
    observations: list[tuple[int, ...]] = []
    for _ in range(draw_count):
        population = list(range(1, 81))
        selected: list[int] = []
        for index in range(20):
            target = index + mulhi(stream.next_u32(), 80 - index)
            population[index], population[target] = population[target], population[index]
            selected.append(population[index])
        for _ in range(stride - 20):
            stream.next_u32()
        observations.append(tuple(sorted(selected)))
    return observations


def _xor_states(left: Sequence[int], right: Sequence[int]) -> tuple[int, ...]:
    return tuple((int(a) ^ int(b)) & WORD_MASK for a, b in zip(left, right, strict=True))


def _flatten_state(state: Sequence[int]) -> int:
    flattened = 0
    for index, word in enumerate(state):
        flattened |= (int(word) & WORD_MASK) << (32 * index)
    return flattened


def _insert_independent(vector: int, pivots: dict[int, int]) -> bool:
    value = vector
    while value:
        pivot = value.bit_length() - 1
        if pivot in pivots:
            value ^= pivots[pivot]
        else:
            pivots[pivot] = value
            return True
    return False


@dataclass(frozen=True)
class AffineFamily:
    """A bounded affine subspace inside the image of one MT twist."""

    base_state: tuple[int, ...]
    deltas: tuple[tuple[int, ...], ...]
    basis_ids: tuple[int, ...]

    @property
    def dimension(self) -> int:
        return len(self.deltas)

    @property
    def candidate_count(self) -> int:
        return 1 << self.dimension

    def state(self, assignment: int) -> tuple[int, ...]:
        if type(assignment) is not int or not 0 <= assignment < self.candidate_count:
            raise ValueError("assignment outside the affine family")
        result = list(self.base_state)
        remaining = assignment
        while remaining:
            least = remaining & -remaining
            basis_index = least.bit_length() - 1
            delta = self.deltas[basis_index]
            for word_index in range(MT_N):
                result[word_index] ^= delta[word_index]
            remaining ^= least
        return tuple(result)


def make_affine_family(
    dimension: int,
    *,
    state_seed: int = 0x12345678,
    basis_seed: int = 0x5A17B1,
) -> AffineFamily:
    """Construct independent dense variations before one MT twist.

    Both the base and every variation are in the image of the MT twist.  The
    family is therefore an honest affine slice of MT's recurrence state space,
    although it is intentionally much smaller than its 19,937 dimensions.  Dense
    basis vectors are used so a small synthetic slice exercises many successive
    output words; isolated unit columns would leave almost every early output
    constant in a low-dimensional benchmark.
    """

    if type(dimension) is not int or not 1 <= dimension <= 24:
        raise ValueError("dimension must be in 1..24 for bounded enumeration")
    pre_twist = mt_init(state_seed)
    base = mt_twist(pre_twist)
    generator = random.Random(basis_seed)
    pivots: dict[int, int] = {}
    deltas: list[tuple[int, ...]] = []
    basis_ids: list[int] = []
    attempts = 0
    while len(deltas) < dimension and attempts < dimension + 128:
        pre_delta = tuple(generator.getrandbits(32) for _ in range(MT_N))
        delta = mt_twist(pre_delta)
        if _insert_independent(_flatten_state(delta), pivots):
            deltas.append(delta)
            basis_ids.append(attempts)
        attempts += 1
    if len(deltas) != dimension:
        raise RuntimeError("could not construct the requested independent MT slice")
    return AffineFamily(base, tuple(deltas), tuple(basis_ids))


def sampled_first_outputs(
    post_twist_state: Sequence[int], draw_count: int, stride: int
) -> tuple[int, ...]:
    stream = MT19937Stream(post_twist_state)
    outputs: list[int] = []
    for _ in range(draw_count):
        outputs.append(stream.next_u32())
        for _ in range(stride - 1):
            stream.next_u32()
    return tuple(outputs)


def affine_first_output_forms(
    family: AffineFamily, draw_count: int, stride: int
) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    """Return ``constant[d]`` and one uint32 coefficient per family bit."""

    constants = sampled_first_outputs(family.base_state, draw_count, stride)
    by_basis = [sampled_first_outputs(delta, draw_count, stride) for delta in family.deltas]
    coefficients = tuple(
        tuple(by_basis[basis][draw] for basis in range(family.dimension))
        for draw in range(draw_count)
    )
    return constants, coefficients


def enumerate_affine_u32(constant: int, coefficients: Sequence[int]) -> np.ndarray:
    """Enumerate an affine uint32 form in ordinary binary assignment order."""

    values = np.array([constant], dtype=np.uint32)
    for coefficient in coefficients:
        values = np.concatenate((values, values ^ np.uint32(coefficient)))
    return values


def exact_membership_support(
    constant: int, coefficients: Sequence[int], sorted_draw: Iterable[int]
) -> tuple[int, int]:
    """Return a bitset of assignments satisfying first-ball membership."""

    draw = validate_sorted_draw(sorted_draw)
    outputs = enumerate_affine_u32(constant, coefficients)
    balls = ((outputs.astype(np.uint64) * np.uint64(80)) >> np.uint64(32)) + 1
    lookup = np.zeros(81, dtype=np.bool_)
    lookup[np.asarray(draw, dtype=np.intp)] = True
    allowed = lookup[balls.astype(np.intp)]
    packed = np.packbits(allowed, bitorder="little")
    support = int.from_bytes(packed.tobytes(), "little")
    return support, int(np.count_nonzero(allowed))


def bitset_assignments(bitset: int, limit: int | None = None) -> list[int]:
    assignments: list[int] = []
    remaining = bitset
    while remaining and (limit is None or len(assignments) < limit):
        least = remaining & -remaining
        assignments.append(least.bit_length() - 1)
        remaining ^= least
    return assignments


def solve_first_membership(
    family: AffineFamily,
    observed_draws: Sequence[Iterable[int]],
    *,
    stride: int = 20,
    stop_at_unique: bool = True,
) -> dict:
    """Intersect exact disjunctive supports over the bounded family."""

    if type(stride) is not int or stride < 20:
        raise ValueError("stride must be an integer of at least 20")
    draws = tuple(validate_sorted_draw(draw) for draw in observed_draws)
    constants, coefficients = affine_first_output_forms(family, len(draws), stride)
    domain_size = family.candidate_count
    survivors = (1 << domain_size) - 1
    trace: list[dict] = []
    started = time.perf_counter()
    for draw_index, draw in enumerate(draws):
        constraint_started = time.perf_counter()
        support, allowed_in_domain = exact_membership_support(
            constants[draw_index], coefficients[draw_index], draw
        )
        before = survivors.bit_count()
        survivors &= support
        after = survivors.bit_count()
        trace.append(
            {
                "draw_index": draw_index,
                "allowed_in_full_family": allowed_in_domain,
                "survivors_before": before,
                "survivors_after": after,
                "conditional_information_bits": (
                    round(math.log2(before / after), 9) if after else None
                ),
                "constraint_seconds": round(time.perf_counter() - constraint_started, 6),
            }
        )
        if after == 0 or (stop_at_unique and after == 1):
            break
    elapsed = time.perf_counter() - started
    survivor_count = survivors.bit_count()
    assignments = bitset_assignments(survivors, limit=32)
    return {
        "dimension": family.dimension,
        "domain_candidates": domain_size,
        "constraints_used": len(trace),
        "survivor_count": survivor_count,
        "survivor_assignments": assignments if survivor_count <= 32 else None,
        "survivor_assignments_truncated": survivor_count > 32,
        "trace": trace,
        "solve_seconds": round(elapsed, 6),
        "support_semantics": "exact uint32 mulhi(u,80)+1 membership; no prefix relaxation",
    }


def run_experiment(
    dimension: int,
    *,
    train_draws: int = 24,
    holdout_draws: int = 12,
    stride: int = 20,
    state_seed: int = 0x12345678,
    basis_seed: int = 0x5A17B1,
    truth_seed: int = 0xC0FFEE,
) -> dict:
    """Run one deterministic synthetic experiment and report its full scope."""

    if type(train_draws) is not int or train_draws <= 0:
        raise ValueError("train_draws must be positive")
    if type(holdout_draws) is not int or holdout_draws < 0:
        raise ValueError("holdout_draws must be non-negative")
    if type(stride) is not int or stride < 20:
        raise ValueError("stride must be at least 20")

    total_started = time.perf_counter()
    family_started = time.perf_counter()
    family = make_affine_family(
        dimension, state_seed=state_seed, basis_seed=basis_seed
    )
    family_seconds = time.perf_counter() - family_started
    truth = random.Random(truth_seed + dimension).getrandbits(dimension)
    true_state = family.state(truth)
    observations = generate_sorted_draws(
        true_state, train_draws + holdout_draws, stride=stride
    )
    training = observations[:train_draws]
    holdout = observations[train_draws:]
    solution = solve_first_membership(family, training, stride=stride)

    unique_assignment: int | None = None
    if solution["survivor_count"] == 1:
        unique_assignment = solution["survivor_assignments"][0]
    recovered_truth = unique_assignment == truth
    replay_training = False
    replay_holdout = False
    if unique_assignment is not None:
        replay = generate_sorted_draws(
            family.state(unique_assignment), train_draws + holdout_draws, stride=stride
        )
        replay_training = replay[:train_draws] == training
        replay_holdout = replay[train_draws:] == holdout

    enumerated = 1 << dimension
    report = {
        "model": "reference MT19937 + forward Fisher-Yates 20-of-80 + uint32 multiply-high",
        "observation": "sorted sets only; solver uses exact first-ball membership",
        "scope": (
            f"complete enumeration of a {dimension}-dimensional affine MT19937 state slice; "
            "not the full 19,937-bit state"
        ),
        "family_dimension": dimension,
        "domain_candidates": enumerated,
        "true_assignment": truth,
        "train_draws": train_draws,
        "holdout_draws": holdout_draws,
        "stride": stride,
        "outputs_replayed": (train_draws + holdout_draws) * stride,
        "crosses_624_word_twist_boundary": (
            (train_draws + holdout_draws) * stride > MT_N
        ),
        "solution": solution,
        "unique_assignment": unique_assignment,
        "recovered_true_assignment": recovered_truth,
        "exact_full_set_training_replay": replay_training,
        "exact_full_set_holdout_replay": replay_holdout,
        "timing": {
            "family_construction_seconds": round(family_seconds, 6),
            "total_seconds": round(time.perf_counter() - total_started, 6),
        },
        "complexity": {
            "enumeration": f"Theta(2^{dimension})",
            "support_bitset_bytes": (enumerated + 7) // 8,
            "approx_numpy_peak_bytes": enumerated * 22,
            "full_mt19937_domain": "2^19937 (not enumerated)",
        },
        "warning": (
            "Synthetic recovery in this bounded family is a model/solver check, "
            "not evidence that any real lottery uses MT19937."
        ),
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dimensions",
        type=int,
        nargs="+",
        default=[20],
        help="bounded affine dimensions to benchmark (1..24; default: 20)",
    )
    parser.add_argument("--train-draws", type=int, default=24)
    parser.add_argument("--holdout-draws", type=int, default=12)
    parser.add_argument("--stride", type=int, default=20)
    parser.add_argument("--state-seed", type=lambda value: int(value, 0), default=0x12345678)
    parser.add_argument("--basis-seed", type=lambda value: int(value, 0), default=0x5A17B1)
    parser.add_argument("--truth-seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    reports = [
        run_experiment(
            dimension,
            train_draws=args.train_draws,
            holdout_draws=args.holdout_draws,
            stride=args.stride,
            state_seed=args.state_seed,
            basis_seed=args.basis_seed,
            truth_seed=args.truth_seed,
        )
        for dimension in args.dimensions
    ]
    print(json.dumps({"experiments": reports}, indent=2, sort_keys=True))
    return 0 if all(report["recovered_true_assignment"] for report in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
