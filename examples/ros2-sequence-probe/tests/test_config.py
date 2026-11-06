import unittest

from seqprobe.config import GeneratorConfig, PublisherConfig, SubscriberConfig
from seqprobe.errors import ConfigError
from seqprobe.generator import plan
from seqprobe.qos import QosSpec


class GeneratorConfigTests(unittest.TestCase):
    def test_defaults_valid(self):
        g = GeneratorConfig(run_id="r1")
        self.assertEqual(g.period_ns, 100_000_000)

    def test_zero_and_negative_count(self):
        for c in (0, -1):
            with self.assertRaises(ConfigError):
                GeneratorConfig(run_id="r1", count=c)

    def test_bad_count_types(self):
        for c in (True, 1.5, "10", None):
            with self.assertRaises(ConfigError):
                GeneratorConfig(run_id="r1", count=c)

    def test_bad_rates(self):
        for r in (0, -1.0, float("nan"), float("inf"), 1e9, "fast", True):
            with self.subTest(rate=r):
                with self.assertRaises(ConfigError):
                    GeneratorConfig(run_id="r1", rate_hz=r)

    def test_bad_payload_sizes(self):
        for n in (0, -4, 5, 2 ** 21, 64.0, True):
            with self.subTest(n=n):
                with self.assertRaises(ConfigError):
                    GeneratorConfig(run_id="r1", payload_bytes=n)

    def test_bad_run_id_clock_seed(self):
        for kw in ({"run_id": ""}, {"run_id": "a b"}, {"run_id": "x" * 33}, {"run_id": "a;b"},
                   {"run_id": "r1", "clock": "utc"}, {"run_id": "r1", "seed": 1.5}):
            with self.subTest(kw=kw):
                with self.assertRaises(ConfigError):
                    GeneratorConfig(**kw)

    def test_plan_is_deterministic_and_complete(self):
        g = GeneratorConfig(run_id="r1", count=5, rate_hz=4.0)
        a, b = list(plan(g)), list(plan(g))
        self.assertEqual(a, b)
        self.assertEqual([m.seq for m in a], [0, 1, 2, 3, 4])
        self.assertEqual([m.offset_ns for m in a], [0, 250_000_000, 500_000_000, 750_000_000, 1_000_000_000])


class OtherConfigTests(unittest.TestCase):
    def test_publisher_config_validation(self):
        g = GeneratorConfig(run_id="r1")
        for kw in ({"node": ""}, {"topic": "a b"}, {"start_delay_s": -1}, {"start_delay_s": float("nan")}):
            with self.subTest(kw=kw):
                with self.assertRaises(ConfigError):
                    PublisherConfig(generator=g, **kw)

    def test_subscriber_config_validation(self):
        for kw in ({"expected_count": 0}, {"expected_count": True}, {"idle_timeout_s": 0},
                   {"first_message_timeout_s": -1}, {"overall_timeout_s": float("inf")},
                   {"clock": "x"}):
            with self.subTest(kw=kw):
                with self.assertRaises(ConfigError):
                    SubscriberConfig(run_id="r1", **kw)
        self.assertIsNone(SubscriberConfig(run_id="r1").expected_count)

    def test_qos_validation(self):
        QosSpec("best-effort", 1, "transient-local")
        for kw in ({"reliability": "maybe"}, {"depth": 0}, {"depth": 10 ** 6}, {"durability": "x"},
                   {"depth": True}):
            with self.subTest(kw=kw):
                with self.assertRaises(ConfigError):
                    QosSpec(**kw)


if __name__ == "__main__":
    unittest.main()
