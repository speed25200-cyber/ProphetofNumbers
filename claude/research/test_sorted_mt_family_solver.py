import random
import unittest

import sorted_mt_family_solver as solver


class SortedMTFamilySolverTests(unittest.TestCase):
    def test_reference_mt19937_vector(self):
        stream = solver.MT19937Stream.from_seed(5489)
        expected = [
            3499211612,
            581869302,
            3890346734,
            3586334585,
            545404204,
            4161255391,
            3922919429,
            949333985,
            2715962298,
            1323567403,
        ]
        self.assertEqual([stream.next_u32() for _ in expected], expected)

    def test_reference_twist_matches_cpython_across_in_place_boundaries(self):
        initial = solver.mt_init(0xD15EA5E)
        oracle = random.Random()
        oracle.setstate((3, tuple(initial) + (624,), None))
        expected = [oracle.getrandbits(32) for _ in range(626)]
        stream = solver.MT19937Stream(solver.mt_twist(initial))
        actual = [stream.next_u32() for _ in range(626)]
        for index in (0, 226, 227, 396, 622, 623, 624, 625):
            self.assertEqual(actual[index], expected[index], f"output {index}")
        self.assertEqual(actual, expected)

    def test_twist_is_gf2_linear(self):
        left = solver.mt_init(1)
        right = solver.mt_init(2)
        combined = tuple(a ^ b for a, b in zip(left, right, strict=True))
        self.assertEqual(
            solver.mt_twist(combined),
            tuple(
                a ^ b
                for a, b in zip(
                    solver.mt_twist(left), solver.mt_twist(right), strict=True
                )
            ),
        )

    def test_affine_output_enumeration_matches_direct_mt(self):
        family = solver.make_affine_family(6)
        constants, coefficients = solver.affine_first_output_forms(family, 4, 20)
        for draw_index in range(4):
            enumerated = solver.enumerate_affine_u32(
                constants[draw_index], coefficients[draw_index]
            )
            for assignment in range(family.candidate_count):
                direct = solver.sampled_first_outputs(
                    family.state(assignment), 4, 20
                )[draw_index]
                self.assertEqual(int(enumerated[assignment]), direct)

    def test_affine_forms_remain_exact_after_next_twist(self):
        family = solver.make_affine_family(4)
        constants, coefficients = solver.affine_first_output_forms(family, 34, 20)
        for draw_index in (31, 33):
            enumerated = solver.enumerate_affine_u32(
                constants[draw_index], coefficients[draw_index]
            )
            for assignment in range(family.candidate_count):
                direct = solver.sampled_first_outputs(
                    family.state(assignment), 34, 20
                )[draw_index]
                self.assertEqual(int(enumerated[assignment]), direct)

    def test_support_bitset_equals_brute_force_membership(self):
        family = solver.make_affine_family(6)
        truth = 37
        draws = solver.generate_sorted_draws(family.state(truth), 4)
        constants, coefficients = solver.affine_first_output_forms(family, 4, 20)
        for draw_index, draw in enumerate(draws):
            support, count = solver.exact_membership_support(
                constants[draw_index], coefficients[draw_index], draw
            )
            brute = 0
            for assignment in range(family.candidate_count):
                output = solver.sampled_first_outputs(
                    family.state(assignment), draw_index + 1, 20
                )[-1]
                first_ball = solver.mulhi(output, 80) + 1
                if first_ball in draw:
                    brute |= 1 << assignment
            self.assertEqual(support, brute)
            self.assertEqual(count, brute.bit_count())
            self.assertTrue((support >> truth) & 1)

    def test_solver_recovers_and_replays_across_twist_boundary(self):
        report = solver.run_experiment(
            10, train_draws=14, holdout_draws=20, stride=20
        )
        self.assertTrue(report["recovered_true_assignment"])
        self.assertTrue(report["exact_full_set_training_replay"])
        self.assertTrue(report["exact_full_set_holdout_replay"])
        self.assertTrue(report["crosses_624_word_twist_boundary"])
        self.assertEqual(report["solution"]["survivor_count"], 1)

    def test_sorted_observation_validation_is_strict(self):
        with self.assertRaises(ValueError):
            solver.validate_sorted_draw(range(20))
        with self.assertRaises(ValueError):
            solver.validate_sorted_draw([1] * 20)
        with self.assertRaises(ValueError):
            solver.validate_sorted_draw(list(range(2, 21)) + [True])
        with self.assertRaises(ValueError):
            solver.validate_sorted_draw(list(range(1, 20)) + [80, 20])
        with self.assertRaises(ValueError):
            solver.make_affine_family(25)


if __name__ == "__main__":
    unittest.main()
