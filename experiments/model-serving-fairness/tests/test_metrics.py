import unittest

from servesim.metrics import jain_index, percentile_nearest_rank


class PercentileTests(unittest.TestCase):
    def test_nearest_rank_ten_values(self):
        v = list(range(1, 11))                       # 1..10
        self.assertEqual(percentile_nearest_rank(v, 50), 5)    # ceil(5.0) = 5
        self.assertEqual(percentile_nearest_rank(v, 95), 10)   # ceil(9.5) = 10
        self.assertEqual(percentile_nearest_rank(v, 99), 10)

    def test_nearest_rank_twenty_values_no_float_error(self):
        v = list(range(1, 21))                       # 1..20
        self.assertEqual(percentile_nearest_rank(v, 95), 19)   # ceil(19.0) = 19 exactly
        self.assertEqual(percentile_nearest_rank(v, 50), 10)
        self.assertEqual(percentile_nearest_rank(v, 100), 20)
        self.assertEqual(percentile_nearest_rank(v, 1), 1)

    def test_unsorted_input_and_single_value(self):
        self.assertEqual(percentile_nearest_rank([9, 1, 5], 50), 5)   # ceil(1.5)=2 -> 5
        self.assertEqual(percentile_nearest_rank([7.5], 99), 7.5)

    def test_empty_is_none(self):
        self.assertIsNone(percentile_nearest_rank([], 50))

    def test_invalid_p(self):
        for p in (0, 101, 50.5, True, "50"):
            with self.subTest(p=p), self.assertRaises(ValueError):
                percentile_nearest_rank([1, 2, 3], p)


class JainTests(unittest.TestCase):
    def test_equal_is_one(self):
        self.assertAlmostEqual(jain_index([1, 1, 1, 1]), 1.0)
        self.assertAlmostEqual(jain_index([0.3, 0.3]), 1.0)

    def test_one_takes_all_is_one_over_n(self):
        self.assertAlmostEqual(jain_index([1, 0, 0, 0]), 0.25)
        self.assertAlmostEqual(jain_index([5, 0]), 0.5)

    def test_hand_computed(self):
        # (1+2+3)^2 / (3 * (1+4+9)) = 36 / 42
        self.assertAlmostEqual(jain_index([1, 2, 3]), 36 / 42)

    def test_scale_invariant(self):
        self.assertAlmostEqual(jain_index([1, 2, 3]), jain_index([10, 20, 30]))

    def test_edge_cases(self):
        self.assertIsNone(jain_index([]))
        self.assertEqual(jain_index([0, 0, 0]), 1.0)
        with self.assertRaises(ValueError):
            jain_index([1, -1])


if __name__ == "__main__":
    unittest.main()
