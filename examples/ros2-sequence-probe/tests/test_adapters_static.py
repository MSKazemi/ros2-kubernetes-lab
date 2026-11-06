"""The rclpy adapters must import and reject bad arguments WITHOUT rclpy installed.
They are never run against ROS 2 here (NOT RUN)."""
import contextlib
import importlib.util
import io
import os
import sys
import unittest

ADAPTERS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rclpy_adapters")


def load(name):
    if ADAPTERS not in sys.path:
        sys.path.insert(0, ADAPTERS)
    spec = importlib.util.spec_from_file_location(name, os.path.join(ADAPTERS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AdapterStaticTests(unittest.TestCase):
    def test_import_does_not_pull_in_rclpy(self):
        before = "rclpy" in sys.modules
        pub, sub = load("publisher_node"), load("subscriber_node")
        self.assertEqual("rclpy" in sys.modules, before)
        self.assertTrue(callable(pub.main) and callable(sub.main))

    def test_bad_args_return_2_before_touching_ros(self):
        pub, sub = load("publisher_node"), load("subscriber_node")
        cases = [
            (pub, ["--run-id", "r1", "--count", "0"]),
            (pub, ["--run-id", "r1", "--rate-hz", "-3"]),
            (pub, ["--run-id", "r1", "--payload-bytes", "2"]),
            (pub, ["--run-id", "bad id"]),
            (pub, ["--run-id", "r1", "--depth", "0"]),
            (sub, ["--run-id", "r1", "--expected-count", "0"]),
            (sub, ["--run-id", "r1", "--idle-timeout-s", "0"]),
        ]
        for mod, argv in cases:
            with self.subTest(argv=argv):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(mod.main(argv), 2)
                self.assertIn("error:", err.getvalue())

    def test_unknown_qos_flag_value_is_a_usage_error(self):
        pub = load("publisher_node")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            pub.main(["--run-id", "r1", "--reliability", "sometimes"])
        self.assertEqual(cm.exception.code, 2)

    def test_qos_flags_map_to_spec(self):
        common = load("_common")
        args = load("publisher_node").build_parser().parse_args(
            ["--run-id", "r1", "--reliability", "best-effort", "--depth", "5"])
        spec = common.qos_spec_from_args(args)
        self.assertEqual((spec.reliability, spec.depth, spec.durability), ("best-effort", 5, "volatile"))


if __name__ == "__main__":
    unittest.main()
