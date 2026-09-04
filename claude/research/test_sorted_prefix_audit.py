import math
import unittest

import sorted_prefix_audit as audit


class SortedPrefixAuditTests(unittest.TestCase):
    def test_prefix_domains_cover_every_first_ball(self):
        masks = audit.prefix_number_masks(8)
        covered = 0
        for mask in masks:
            covered |= mask
        self.assertEqual(covered, (1 << 80) - 1)

    def test_all_numbers_allow_every_prefix(self):
        masks = audit.prefix_number_masks(7)
        allowed = audit.allowed_prefixes((1 << 80) - 1, masks)
        self.assertEqual(allowed, list(range(128)))
        self.assertEqual(audit.affine_rank(allowed), 7)

    def test_affine_rank_detects_a_fixed_bit(self):
        points = [value for value in range(16) if value & 1]
        self.assertEqual(audit.affine_rank(points), 3)

    def test_information_report_is_self_consistent(self):
        draw = audit.number_mask(list(range(1, 21)))
        report = audit.audit_width([draw], 7, state_bits=32, margin_bits=0)
        count = report["mean_allowed_prefixes"]
        self.assertAlmostEqual(report["mean_information_bits"], 7 - math.log2(count))
        self.assertGreater(report["heuristic_draws_for_state_plus_margin"], 0)

    def test_number_mask_rejects_duplicates_and_boolean(self):
        with self.assertRaises(ValueError):
            audit.number_mask([1] * 20)
        values = list(range(1, 21))
        values[0] = True
        with self.assertRaises(ValueError):
            audit.number_mask(values)


if __name__ == "__main__":
    unittest.main()
