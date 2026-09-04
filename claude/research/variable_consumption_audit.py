#!/usr/bin/env python3
"""Exact audit of variable RNG consumption for plausible bounded samplers.

The cardinalities in this report are mathematical facts about the named
algorithms.  Probabilities and expectations are conditional on independent,
uniform raw words; the program does not infer which algorithm the production
backend uses.  In particular, a small rejection probability is not permission
to silently treat a variable-consumption stream as fixed-stride.
"""

from __future__ import annotations

import argparse
import json
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import reduce
from operator import mul
from typing import Iterable, Sequence


FISHER_YATES_BOUNDS = tuple(range(80, 60, -1))


def _strict_nonnegative_int(value: int, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _validate_calls(
    bounds: Sequence[int], domains: Sequence[int], accepted_counts: Sequence[int]
) -> None:
    if not bounds or len(bounds) != len(domains) or len(bounds) != len(accepted_counts):
        raise ValueError("bounds, domains, and accepted counts must have equal non-zero length")
    for position, (bound, domain, accepted) in enumerate(
        zip(bounds, domains, accepted_counts)
    ):
        if type(bound) is not int or bound <= 0:
            raise ValueError(f"invalid bound at position {position}")
        if type(domain) is not int or domain <= 0:
            raise ValueError(f"invalid raw domain at position {position}")
        if type(accepted) is not int or not 0 < accepted <= domain:
            raise ValueError(f"invalid accepted count at position {position}")


def _product(values: Iterable[Fraction]) -> Fraction:
    return reduce(mul, values, Fraction(1, 1))


def _fraction_json(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _decimal(value: Fraction, precision: int = 80) -> Decimal:
    with localcontext() as context:
        context.prec = precision
        return Decimal(value.numerator) / Decimal(value.denominator)


def _scientific(value: Decimal) -> str:
    return format(value, ".18E")


def _one_minus_scientific(complement: Decimal) -> str:
    """Render ``1-complement`` without rounding a tiny complement out of sight."""

    with localcontext() as context:
        context.prec = 80
        difference = Decimal(1) - complement
    if difference == 1 and complement:
        return f"1 - {_scientific(complement)}"
    return _scientific(difference)


def call_sequence_statistics(
    *,
    name: str,
    mechanism: str,
    bounds: Sequence[int],
    domains: Sequence[int],
    accepted_counts: Sequence[int],
    campaign_draws: int,
    semantic_coverage: str,
) -> dict:
    """Return exact one-sequence facts and conditional campaign probabilities.

    Each logical bounded call repeats independent raw draws until one of
    ``accepted_counts[i]`` values in a domain of size ``domains[i]`` occurs.
    """

    _strict_nonnegative_int(campaign_draws, "campaign_draws")
    _validate_calls(bounds, domains, accepted_counts)

    acceptance = [Fraction(accepted, domain) for accepted, domain in zip(accepted_counts, domains)]
    zero_rejection = _product(acceptance)
    expected_words = sum(
        (Fraction(domain, accepted) for domain, accepted in zip(domains, accepted_counts)),
        Fraction(0, 1),
    )
    expected_extra = expected_words - len(bounds)

    with localcontext() as context:
        context.prec = 80
        p0_decimal = _decimal(zero_rejection)
        campaign_p0 = p0_decimal**campaign_draws
        expected_extra_campaign = _decimal(expected_extra) * campaign_draws

    per_call = []
    for bound, domain, accepted in zip(bounds, domains, accepted_counts):
        rejected = domain - accepted
        per_call.append(
            {
                "bound": bound,
                "raw_domain": domain,
                "accepted_raw_values": accepted,
                "rejected_raw_values": rejected,
                "rejection_probability_exact": _fraction_json(Fraction(rejected, domain)),
            }
        )

    log10_p0 = sum(math.log10(accepted / domain) for accepted, domain in zip(accepted_counts, domains))
    return {
        "model": name,
        "mechanism": mechanism,
        "claim_status": {
            "accepted_and_rejected_cardinalities": "PROVED_FOR_THE_DEFINED_ALGORITHM",
            "probabilities_and_expectations": "CONDITIONAL_ON_IID_UNIFORM_RAW_WORDS",
            "production_backend_uses_this_model": "NOT_ESTABLISHED",
        },
        "semantic_coverage_by_keno_break": semantic_coverage,
        "logical_calls_per_draw": len(bounds),
        "one_draw": {
            "zero_rejection_probability_exact": _fraction_json(zero_rejection),
            "zero_rejection_probability_decimal": _scientific(_decimal(zero_rejection)),
            "any_rejection_probability_exact": _fraction_json(1 - zero_rejection),
            "any_rejection_probability_decimal": _one_minus_scientific(
                _decimal(zero_rejection)
            ),
            "expected_raw_words_exact": _fraction_json(expected_words),
            "expected_raw_words_decimal": _scientific(_decimal(expected_words)),
            "expected_extra_words_exact": _fraction_json(expected_extra),
            "expected_extra_words_decimal": _scientific(_decimal(expected_extra)),
        },
        "campaign": {
            "draws": campaign_draws,
            "zero_rejection_probability_expression": (
                f"({zero_rejection.numerator}/{zero_rejection.denominator})^{campaign_draws}"
            ),
            "zero_rejection_probability_decimal": _scientific(campaign_p0),
            "log10_zero_rejection_probability": round(log10_p0 * campaign_draws, 12),
            "any_rejection_probability_expression": (
                f"1 - ({zero_rejection.numerator}/{zero_rejection.denominator})^{campaign_draws}"
            ),
            "any_rejection_probability_decimal": _one_minus_scientific(campaign_p0),
            "expected_extra_words_expression": (
                f"{campaign_draws}*({expected_extra.numerator}/{expected_extra.denominator})"
            ),
            "expected_extra_words_decimal": _scientific(expected_extra_campaign),
        },
        "calls": per_call,
    }


def threshold_model(
    *, name: str, word_space: int, campaign_draws: int, semantic_coverage: str
) -> dict:
    """Audit threshold-modulo/Lemire rejection cardinalities for 80..61.

    Both canonical threshold-modulo and Lemire's multiply-high construction
    reject exactly ``word_space % bound`` raw values.  Their returned indices
    differ, so ``semantic_coverage`` must state which fixed mapping matches the
    no-rejection path.
    """

    if (
        type(word_space) is not int
        or word_space <= 0
        or word_space & (word_space - 1)
    ):
        raise ValueError("word_space must be a positive power of two")
    accepted = [word_space - (word_space % bound) for bound in FISHER_YATES_BOUNDS]
    return call_sequence_statistics(
        name=name,
        mechanism="unbiased bounded integer by redraw outside a complete range",
        bounds=FISHER_YATES_BOUNDS,
        domains=[word_space] * len(FISHER_YATES_BOUNDS),
        accepted_counts=accepted,
        campaign_draws=campaign_draws,
        semantic_coverage=semantic_coverage,
    )


def python_getrandbits_model(campaign_draws: int) -> dict:
    """Audit CPython-style ``r=getrandbits(n.bit_length()); r<n`` calls."""

    domains = [1 << bound.bit_length() for bound in FISHER_YATES_BOUNDS]
    return call_sequence_statistics(
        name="python_getrandbits_randbelow",
        mechanism="draw k=bound.bit_length() bits and redraw while r >= bound",
        bounds=FISHER_YATES_BOUNDS,
        domains=domains,
        accepted_counts=list(FISHER_YATES_BOUNDS),
        campaign_draws=campaign_draws,
        semantic_coverage="NOT_COVERED (variable bit widths and redraws)",
    )


def duplicate_rejection_model(campaign_draws: int) -> dict:
    """Audit drawing uniform 1..80 candidates until 20 are distinct."""

    selected = tuple(range(20))
    return call_sequence_statistics(
        name="twenty_unique_by_duplicate_redraw",
        mechanism="uniform 1..80 candidate; redraw a duplicate until 20 values are unique",
        bounds=(80,) * 20,
        domains=(80,) * 20,
        accepted_counts=tuple(80 - count for count in selected),
        campaign_draws=campaign_draws,
        semantic_coverage="NOT_COVERED (draw stride is intrinsically variable)",
    )


def build_report(training_draws: int, holdout_draws: int) -> dict:
    training_draws = _strict_nonnegative_int(training_draws, "training_draws")
    holdout_draws = _strict_nonnegative_int(holdout_draws, "holdout_draws")
    campaign_draws = training_draws + holdout_draws
    if campaign_draws == 0:
        raise ValueError("the campaign must contain at least one draw")

    return {
        "scope": "variable RNG word consumption for one 20-of-80 draw and a full campaign",
        "campaign": {
            "training_draws": training_draws,
            "holdout_draws": holdout_draws,
            "total_draws": campaign_draws,
        },
        "proof_boundary": {
            "algorithmic_counts": "exact for each explicitly defined algorithm",
            "probabilities": "require IID uniform raw words",
            "production_algorithm": "unknown until identified and prospectively replayed",
        },
        "fixed_consumption_models_already_implemented": [
            {
                "mapping": "mulhi (u*k)>>32",
                "raw_words_per_index": 1,
                "variable_consumption": False,
                "status": "PROVED_FROM_KENO_BREAK_IMPLEMENTATION",
            },
            {
                "mapping": "u%k",
                "raw_words_per_index": 1,
                "variable_consumption": False,
                "status": "PROVED_FROM_KENO_BREAK_IMPLEMENTATION",
            },
            {
                "mapping": "(u>>16)%k",
                "raw_words_per_index": 1,
                "variable_consumption": False,
                "status": "PROVED_FROM_KENO_BREAK_IMPLEMENTATION",
            },
        ],
        "variable_consumption_models": [
            threshold_model(
                name="u32_threshold_or_lemire",
                word_space=1 << 32,
                campaign_draws=campaign_draws,
                semantic_coverage=(
                    "NO-REJECTION PATH ONLY: threshold-modulo matches mapping 1; "
                    "Lemire multiply-high matches mapping 0"
                ),
            ),
            threshold_model(
                name="classic_java_util_Random_nextInt",
                word_space=1 << 31,
                campaign_draws=campaign_draws,
                semantic_coverage=(
                    "NOT_COVERED (31-bit input, power-of-two branch, and redraw semantics differ)"
                ),
            ),
            python_getrandbits_model(campaign_draws),
            duplicate_rejection_model(campaign_draws),
        ],
        "operational_conclusion": [
            "A single redraw changes every later MT word alignment; fixed-stride recovery must reject or explicitly model that branch.",
            "The u32 and classic Java rejection risks can be numerically small, but that is only an IID-model error bound, not proof of backend behavior.",
            "CPython-style randbelow and duplicate-redraw sampling are materially variable and cannot be approximated as stride 20.",
        ],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--training-draws", type=int, default=500)
    root.add_argument("--holdout-draws", type=int, default=50)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        report = build_report(args.training_draws, args.holdout_draws)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
