import unittest

from seqprobe.errors import ConfigError
from seqprobe.tracker import SequenceTracker


def feed(expected, seqs, timed_out=False):
    t = SequenceTracker(expected)
    kinds = [t.observe(s) for s in seqs]
    return kinds, t.verdict(timed_out=timed_out)


class TrackerTests(unittest.TestCase):
    def test_clean_run_is_ok(self):
        kinds, v = feed(5, range(5))
        self.assertEqual(set(kinds), {"in_order"})
        self.assertTrue(v.ok)
        self.assertEqual((v.completion, v.missing, v.duplicates, v.reordered, v.gap_events), ("complete", 0, 0, 0, 0))

    def test_gap_in_the_middle(self):
        kinds, v = feed(6, [0, 1, 3, 4, 5])
        self.assertEqual(kinds[2], "gap")
        self.assertEqual((v.missing, v.missing_ranges, v.gap_events), (1, ((2, 2),), 1))
        self.assertEqual(v.completion, "incomplete")
        self.assertFalse(v.ok)

    def test_head_loss(self):
        _, v = feed(4, [2, 3])
        self.assertEqual(v.missing_ranges, ((0, 1),))

    def test_tail_loss_needs_known_count(self):
        _, known = feed(5, [0, 1, 2])
        self.assertEqual(known.missing_ranges, ((3, 4),))
        self.assertTrue(known.tail_loss_detectable)
        _, unknown = feed(None, [0, 1, 2])
        self.assertEqual(unknown.missing, 0)           # cannot see the tail
        self.assertFalse(unknown.tail_loss_detectable)
        self.assertEqual(unknown.completion, "unknown")
        self.assertFalse(unknown.ok)                   # never "ok" without a known count

    def test_duplicate(self):
        kinds, v = feed(3, [0, 1, 1, 2])
        self.assertEqual(kinds[2], "duplicate")
        self.assertEqual((v.duplicates, v.received_total, v.unique, v.completion), (1, 4, 3, "complete"))
        self.assertFalse(v.ok)

    def test_out_of_order_fill(self):
        kinds, v = feed(4, [0, 2, 1, 3])
        self.assertEqual(kinds, ["in_order", "gap", "reordered", "in_order"])
        self.assertEqual((v.reordered, v.missing, v.completion), (1, 0, "complete"))
        self.assertFalse(v.ok)

    def test_timeout_verdict(self):
        _, v = feed(5, [0, 1], timed_out=True)
        self.assertEqual((v.completion, v.missing_ranges), ("timeout", ((2, 4),)))
        self.assertFalse(v.ok)
        _, none = feed(5, [], timed_out=True)
        self.assertEqual((none.completion, none.unique, none.missing), ("timeout", 0, 5))

    def test_complete_wins_over_late_timeout_flag(self):
        _, v = feed(2, [0, 1], timed_out=True)
        self.assertEqual(v.completion, "complete")

    def test_unexpected_seq_not_stored(self):
        kinds, v = feed(3, [0, 1, 2, 3, -1])
        self.assertEqual(kinds[3:], ["unexpected", "unexpected"])
        self.assertEqual(v.unexpected, 2)
        self.assertFalse(v.ok)

    def test_bad_arguments(self):
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ConfigError):
                SequenceTracker(bad)
        with self.assertRaises(ConfigError):
            SequenceTracker(3).observe("1")
        with self.assertRaises(ConfigError):
            SequenceTracker(3).observe(True)

    def test_verdict_dict_is_json_serialisable(self):
        import json
        _, v = feed(4, [0, 3])
        d = json.loads(json.dumps(v.to_dict()))
        self.assertEqual(d["missing_ranges"], [[1, 2]])


if __name__ == "__main__":
    unittest.main()
