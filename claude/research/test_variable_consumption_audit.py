import unittest
from fractions import Fraction

import variable_consumption_audit as audit


class VariableConsumptionAuditTests(unittest.TestCase):
    def test_threshold_cardinality_is_exact(self):
        report = audit.threshold_model(
            name="test", word_space=1 << 32, campaign_draws=1, semantic_coverage="test"
        )
        calls = {call["bound"]: call for call in report["calls"]}
        for bound in audit.FISHER_YATES_BOUNDS:
            self.assertEqual(calls[bound]["rejected_raw_values"], (1 << 32) % bound)
            self.assertEqual(calls[bound]["accepted_raw_values"] % bound, 0)

    def test_java_power_of_two_bound_never_rejects(self):
        report = audit.threshold_model(
            name="java", word_space=1 << 31, campaign_draws=1, semantic_coverage="test"
        )
        bound_64 = next(call for call in report["calls"] if call["bound"] == 64)
        self.assertEqual(bound_64["rejected_raw_values"], 0)

    def test_python_power_of_two_bound_rejects_half(self):
        report = audit.python_getrandbits_model(campaign_draws=1)
        bound_64 = next(call for call in report["calls"] if call["bound"] == 64)
        self.assertEqual(bound_64["raw_domain"], 128)
        self.assertEqual(bound_64["accepted_raw_values"], 64)
        self.assertEqual(bound_64["rejected_raw_values"], 64)

    def test_duplicate_sampler_no_redraw_probability(self):
        report = audit.duplicate_rejection_model(campaign_draws=1)
        exact = report["one_draw"]["zero_rejection_probability_exact"]
        observed = Fraction(int(exact["numerator"]), int(exact["denominator"]))
        expected = Fraction(1, 1)
        for remaining in range(80, 60, -1):
            expected *= Fraction(remaining, 80)
        self.assertEqual(observed, expected)

    def test_campaign_probability_is_per_draw_power(self):
        one = audit.threshold_model(
            name="one", word_space=256, campaign_draws=1, semantic_coverage="test"
        )
        three = audit.threshold_model(
            name="three", word_space=256, campaign_draws=3, semantic_coverage="test"
        )
        fraction = one["one_draw"]["zero_rejection_probability_exact"]
        p0 = Fraction(int(fraction["numerator"]), int(fraction["denominator"]))
        any_fraction = one["one_draw"]["any_rejection_probability_exact"]
        self.assertEqual(
            Fraction(int(any_fraction["numerator"]), int(any_fraction["denominator"])),
            1 - p0,
        )
        self.assertEqual(
            three["campaign"]["zero_rejection_probability_expression"],
            f"({p0.numerator}/{p0.denominator})^3",
        )

    def test_report_marks_proof_boundary_and_coverage(self):
        report = audit.build_report(400, 50)
        self.assertEqual(report["campaign"]["total_draws"], 450)
        self.assertEqual(report["proof_boundary"]["production_algorithm"], "unknown until identified and prospectively replayed")
        models = {model["model"]: model for model in report["variable_consumption_models"]}
        self.assertIn("NOT_COVERED", models["python_getrandbits_randbelow"]["semantic_coverage_by_keno_break"])
        self.assertIn("NOT_COVERED", models["twenty_unique_by_duplicate_redraw"]["semantic_coverage_by_keno_break"])

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            audit.build_report(True, 1)
        with self.assertRaises(ValueError):
            audit.build_report(0, 0)
        with self.assertRaises(ValueError):
            audit.threshold_model(
                name="bad", word_space=100, campaign_draws=1, semantic_coverage="bad"
            )
        with self.assertRaises(ValueError):
            audit.call_sequence_statistics(
                name="bad",
                mechanism="bad",
                bounds=[80],
                domains=[0],
                accepted_counts=[1],
                campaign_draws=1,
                semantic_coverage="bad",
            )


if __name__ == "__main__":
    unittest.main()
