"""Action message: positive and negative tests (fail-closed behaviour)."""

import unittest

from support import ALLOWED, ContractCase, act1, act2, c, make_validator, now_for, obs1, obs2


def primed(**kw):
    """Validator that has already accepted observation 1."""
    val = make_validator(**kw)
    assert val.validate_observation(obs1()).ok
    return val


class ActionAcceptTests(ContractCase):
    def test_valid_action_accepted(self):
        a = act1()
        self.assertAccepted(primed().validate_action(a, now_for(a)))

    def test_increasing_sequence_accepted(self):
        val = primed()
        a1, a2 = act1(), act2()
        self.assertAccepted(val.validate_observation(obs2()))
        self.assertAccepted(val.validate_action(a1, now_for(a1)))
        self.assertAccepted(val.validate_action(a2, now_for(a2)))


class StaleActionTests(ContractCase):
    def test_fresh_action_accepted_and_boundary_inclusive(self):
        a = act1()
        val = primed(max_action_age_ms=50)
        # age exactly equal to the maximum is still accepted
        self.assertAccepted(val.validate_action(a, now_for(a, 50)))

    def test_stale_action_rejected(self):
        a = act1()
        r = primed(max_action_age_ms=50).validate_action(a, now_for(a, 51))
        self.assertRejected(r, self.R.STALE_ACTION, "created_timestamp_ns")

    def test_max_age_is_configurable(self):
        a = act1()
        a["ttl_ms"] = 1000  # make sure ttl is not the limiting factor
        now = now_for(a, 150)
        self.assertAccepted(primed(max_action_age_ms=200).validate_action(a, now))
        self.assertRejected(primed(max_action_age_ms=100).validate_action(a, now), self.R.STALE_ACTION)

    def test_default_max_age_rejects_old_action(self):
        a = act1()
        a["ttl_ms"] = 10_000
        self.assertRejected(primed().validate_action(a, now_for(a, 100_000)), self.R.STALE_ACTION)

    def test_action_expired_by_own_ttl_rejected(self):
        a = act1()
        a["ttl_ms"] = 10
        self.assertRejected(primed(max_action_age_ms=200).validate_action(a, now_for(a, 50)), self.R.EXPIRED_TTL)

    def test_future_action_rejected(self):
        a = act1()
        self.assertRejected(primed().validate_action(a, now_for(a, -100)), self.R.FUTURE_TIMESTAMP)

    def test_small_clock_skew_tolerated(self):
        a = act1()
        self.assertAccepted(primed(max_future_skew_ms=5).validate_action(a, now_for(a, -3)))

    def test_stale_source_observation_rejected(self):
        a = act1()
        a["created_timestamp_ns"] = 1_600_000_000  # keep the action itself fresh
        now = now_for(a, 1)
        # observation 1 has ttl 500 ms and timestamp 1.1e9, so 1.601e9 is past it
        self.assertRejected(primed().validate_action(a, now), self.R.STALE_OBSERVATION)

    def test_bad_now_rejected(self):
        a = act1()
        for bad in (None, "1", -1, float("nan"), True):
            with self.subTest(bad=bad):
                self.assertFalse(primed().validate_action(a, bad).ok)


class AuthorizationTests(ContractCase):
    def test_allowed_source_accepted(self):
        a = act1()
        self.assertEqual(a["source_id"], ALLOWED)
        self.assertAccepted(primed().validate_action(a, now_for(a)))

    def test_unknown_source_rejected(self):
        a = act1()
        a["source_id"] = "attacker-01"
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.UNAUTHORIZED_SOURCE, "source_id")

    def test_empty_allow_list_rejects_everything(self):
        a = act1()
        val = make_validator(allowed_sources=frozenset())
        self.assertAccepted(val.validate_observation(obs1()))
        self.assertRejected(val.validate_action(a, now_for(a)), self.R.UNAUTHORIZED_SOURCE)

    def test_default_config_is_fail_closed(self):
        import validate

        a = act1()
        val = validate.ContractValidator()
        self.assertAccepted(val.validate_observation(obs1()))
        self.assertRejected(val.validate_action(a, now_for(a)), self.R.UNAUTHORIZED_SOURCE)

    def test_source_id_is_exact_match(self):
        for bad in (ALLOWED.lower(), ALLOWED + "x", ALLOWED[:-1]):
            with self.subTest(bad=bad):
                a = act1()
                a["source_id"] = bad
                self.assertRejected(primed().validate_action(a, now_for(a)), self.R.UNAUTHORIZED_SOURCE)

    def test_unauthorized_command_rejected(self):
        for bad in ("cmd_vel", "shell", "raw_motor", "SET_JOINT_TARGETS", ""):
            with self.subTest(bad=bad):
                a = act1()
                a["command"] = bad
                self.assertRejected(primed().validate_action(a, now_for(a)), self.R.UNAUTHORIZED_COMMAND, "command")

    def test_unsupported_action_space_rejected(self):
        a = act1()
        a["action_space"] = "velocity"
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.UNAUTHORIZED_COMMAND, "action_space")


class VectorTests(ContractCase):
    def test_wrong_dimension_rejected(self):
        for n in (0, 1, 5, 7, 100):
            with self.subTest(n=n):
                a = act1()
                a["values"] = [0.0] * n
                self.assertRejected(primed().validate_action(a, now_for(a)), self.R.WRONG_DIMENSION, "values")

    def test_wrong_unit_dimension_rejected(self):
        a = act1()
        a["units"] = a["units"][:-1]
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.WRONG_DIMENSION, "units")

    def test_wrong_units_rejected_per_joint(self):
        for i in range(c.ACTION_DIM):
            with self.subTest(joint=c.JOINT_NAMES[i]):
                a = act1()
                a["units"][i] = "deg" if c.JOINT_UNITS[i] == "rad" else "mm"
                self.assertRejected(primed().validate_action(a, now_for(a)), self.R.WRONG_UNITS, f"units[{i}]")

    def test_each_joint_limit_enforced_both_sides(self):
        for i, (lo, hi) in enumerate(c.JOINT_LIMITS):
            for label, value in (("below", lo - 0.001), ("above", hi + 0.001)):
                with self.subTest(joint=c.JOINT_NAMES[i], side=label):
                    a = act1()
                    a["values"][i] = value
                    self.assertRejected(
                        primed().validate_action(a, now_for(a)), self.R.OUT_OF_LIMITS, f"values[{i}]"
                    )
            with self.subTest(joint=c.JOINT_NAMES[i], side="exactly-at-limit"):
                a = act1()
                a["values"][i] = hi
                self.assertAccepted(primed().validate_action(a, now_for(a)))

    def test_nan_and_inf_rejected_at_every_position(self):
        for i in range(c.ACTION_DIM):
            for bad in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(index=i, bad=bad):
                    a = act1()
                    a["values"][i] = bad
                    self.assertRejected(
                        primed().validate_action(a, now_for(a)), self.R.NON_FINITE_VALUE, f"values[{i}]"
                    )

    def test_non_numeric_values_rejected(self):
        for bad in ("NaN", "0.1", None, True, [0.1], {"x": 1}):
            with self.subTest(bad=bad):
                a = act1()
                a["values"][0] = bad
                self.assertRejected(primed().validate_action(a, now_for(a)), self.R.WRONG_TYPE)

    def test_huge_integer_is_out_of_limits_not_a_crash(self):
        a = act1()
        a["values"][0] = 10**400
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.OUT_OF_LIMITS)


class MalformedAndReplayTests(ContractCase):
    def test_malformed_action_rejected_not_raised(self):
        for bad in (None, [], "text", 7, 1.5, True, {}, {"values": []}):
            with self.subTest(bad=bad):
                r = primed().validate_action(bad, 1_200_000_000)
                self.assertFalse(r.ok)
                self.assertIsNotNone(r.reason)

    def test_every_required_field_missing_rejected(self):
        for field in c.ACTION_FIELDS:
            with self.subTest(field=field):
                a = act1()
                now = now_for(a)
                del a[field]
                self.assertRejected(primed().validate_action(a, now), self.R.MISSING_FIELD, field)

    def test_unknown_field_rejected(self):
        a = act1()
        a["shell"] = "rm -rf /"
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.MALFORMED_MESSAGE, "shell")

    def test_not_simulated_and_wrong_version_rejected(self):
        a = act1()
        a["simulated"] = False
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.NOT_SIMULATED)
        a = act1()
        a["contract_version"] = "other/v9"
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.UNSUPPORTED_VERSION)

    def test_replayed_action_rejected(self):
        val = primed()
        a = act1()
        self.assertAccepted(val.validate_action(a, now_for(a)))
        self.assertRejected(val.validate_action(a, now_for(a)), self.R.DUPLICATE_SEQUENCE)

    def test_out_of_order_action_rejected(self):
        val = primed()
        self.assertAccepted(val.validate_observation(obs2()))
        a1, a2 = act1(), act2()
        self.assertAccepted(val.validate_action(a2, now_for(a2)))
        self.assertRejected(val.validate_action(a1, now_for(a1)), self.R.OUT_OF_ORDER_SEQUENCE)

    def test_action_for_unknown_observation_rejected(self):
        a = act1()
        a["observation_id"] = "obs-9999"
        self.assertRejected(primed().validate_action(a, now_for(a)), self.R.UNKNOWN_OBSERVATION)

    def test_action_before_any_observation_rejected(self):
        a = act1()
        self.assertRejected(make_validator().validate_action(a, now_for(a)), self.R.UNKNOWN_OBSERVATION)

    def test_rejected_action_does_not_advance_sequence(self):
        val = primed()
        bad = act1()
        bad["values"][0] = float("nan")
        self.assertRejected(val.validate_action(bad, now_for(bad)), self.R.NON_FINITE_VALUE)
        good = act1()
        self.assertAccepted(val.validate_action(good, now_for(good)))


if __name__ == "__main__":
    unittest.main()
