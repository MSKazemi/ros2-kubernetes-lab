"""Observation message: positive and negative tests."""

import base64
import copy
import unittest

import support
from support import ContractCase, c, make_validator, obs1, obs2


class ObservationSchemaTests(ContractCase):
    def test_valid_fixture_accepted(self):
        self.assertAccepted(make_validator().validate_observation(obs1()))

    def test_every_required_field_missing_rejected(self):
        for field in c.OBSERVATION_FIELDS:
            with self.subTest(field=field):
                m = obs1()
                del m[field]
                self.assertRejected(make_validator().validate_observation(m), self.R.MISSING_FIELD, field)

    def test_unknown_field_rejected(self):
        m = obs1()
        m["extra"] = 1
        self.assertRejected(make_validator().validate_observation(m), self.R.MALFORMED_MESSAGE, "extra")

    def test_wrong_types_rejected(self):
        cases = [
            ("sequence_id", True, self.R.WRONG_TYPE),  # bool is not an int
            ("sequence_id", "1", self.R.WRONG_TYPE),
            ("source_timestamp_ns", 1.5, self.R.WRONG_TYPE),
            ("ttl_ms", "500", self.R.WRONG_TYPE),
            ("observation_id", 7, self.R.WRONG_TYPE),
            ("cameras", {}, self.R.WRONG_TYPE),
            ("contract_version", 1, self.R.WRONG_TYPE),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field, value=value):
                m = obs1()
                m[field] = value
                self.assertRejected(make_validator().validate_observation(m), reason, field)

    def test_malformed_messages_rejected_not_raised(self):
        for bad in (None, [], "text", 42, 3.5, True, {}, {"a": 1}, {1: 2}):
            with self.subTest(bad=bad):
                r = make_validator().validate_observation(bad)
                self.assertFalse(r.ok)
                self.assertIsNotNone(r.reason)

    def test_bad_identifier_rejected(self):
        for bad in ("", "has space", "x" * 65, "line\nbreak", "../etc"):
            with self.subTest(bad=bad):
                m = obs1()
                m["observation_id"] = bad
                self.assertRejected(make_validator().validate_observation(m), self.R.MALFORMED_MESSAGE)

    def test_unsupported_version_and_not_simulated(self):
        m = obs1()
        m["contract_version"] = "ros2-obs-action/v2"
        self.assertRejected(make_validator().validate_observation(m), self.R.UNSUPPORTED_VERSION)
        m = obs1()
        m["simulated"] = False
        self.assertRejected(make_validator().validate_observation(m), self.R.NOT_SIMULATED)


class CameraMappingTests(ContractCase):
    def test_camera_name_maps_to_key(self):
        for name, key in c.CAMERA_KEYS.items():
            cam = next(x for x in obs1()["cameras"] if x["name"] == name)
            self.assertEqual(cam["key"], key)
        self.assertAccepted(make_validator().validate_observation(obs1()))

    def test_missing_camera_rejected(self):
        for i, name in enumerate(c.REQUIRED_CAMERAS):
            with self.subTest(missing=name):
                m = obs1()
                m["cameras"] = [x for x in m["cameras"] if x["name"] != name]
                self.assertRejected(make_validator().validate_observation(m), self.R.MISSING_CAMERA)

    def test_no_cameras_rejected(self):
        m = obs1()
        m["cameras"] = []
        self.assertRejected(make_validator().validate_observation(m), self.R.MISSING_CAMERA)

    def test_unknown_camera_rejected(self):
        m = obs1()
        m["cameras"][0]["name"] = "rear_depth"
        self.assertRejected(make_validator().validate_observation(m), self.R.UNKNOWN_CAMERA)

    def test_wrong_key_for_camera_rejected(self):
        m = obs1()
        # swap: front_rgb carrying the wrist key
        m["cameras"][0]["key"] = c.CAMERA_KEYS["wrist_rgb"]
        self.assertRejected(make_validator().validate_observation(m), self.R.CAMERA_KEY_MISMATCH, "cameras[0].key")

    def test_duplicate_camera_rejected(self):
        m = obs1()
        m["cameras"][1] = copy.deepcopy(m["cameras"][0])
        self.assertRejected(make_validator().validate_observation(m), self.R.MALFORMED_MESSAGE)

    def test_wrong_shape_rejected(self):
        m = obs1()
        m["cameras"][0]["width"] = 3  # data is 2x2 rgb8
        self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_SHAPE)
        m = obs1()
        m["cameras"][0]["encoding"] = "mono8"  # 4 bytes expected, 12 present
        self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_SHAPE)
        for dim in (0, -1, 1025):
            m = obs1()
            m["cameras"][0]["height"] = dim
            self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_SHAPE)

    def test_bad_encoding_and_bad_base64_rejected(self):
        m = obs1()
        m["cameras"][0]["encoding"] = "bgr16"
        self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_SHAPE)
        m = obs1()
        m["cameras"][0]["data_b64"] = "!!not base64!!"
        self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_DATA)
        m = obs1()
        m["cameras"][0]["data_b64"] = base64.b64encode(b"x" * 8).decode()  # valid b64, wrong size
        self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_SHAPE)

    def test_oversized_payload_rejected(self):
        m = obs1()
        m["cameras"][0]["data_b64"] = "A" * (2 * 1024 * 1024)
        self.assertRejected(make_validator().validate_observation(m), self.R.BAD_CAMERA_DATA)


class StateUnitsTests(ContractCase):
    def test_state_names_and_order_enforced(self):
        m = obs1()
        m["state"]["names"] = list(reversed(m["state"]["names"]))
        self.assertRejected(make_validator().validate_observation(m), self.R.WRONG_STATE_NAMES)
        m = obs1()
        m["state"]["names"][0] = "base_yaw"
        self.assertRejected(make_validator().validate_observation(m), self.R.WRONG_STATE_NAMES)

    def test_wrong_units_rejected_per_joint(self):
        for i in range(c.ACTION_DIM):
            with self.subTest(joint=c.JOINT_NAMES[i]):
                m = obs1()
                m["state"]["units"][i] = "deg" if c.JOINT_UNITS[i] == "rad" else "mm"
                self.assertRejected(make_validator().validate_observation(m), self.R.WRONG_UNITS)

    def test_gripper_unit_is_metres_not_radians(self):
        m = obs1()
        m["state"]["units"][5] = "rad"
        self.assertRejected(make_validator().validate_observation(m), self.R.WRONG_UNITS, "state.units[5]")

    def test_wrong_dimension_rejected(self):
        for n in (0, 5, 7):
            with self.subTest(n=n):
                m = obs1()
                m["state"]["values"] = [0.0] * n
                self.assertRejected(make_validator().validate_observation(m), self.R.WRONG_DIMENSION)

    def test_nan_and_inf_state_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=bad):
                m = obs1()
                m["state"]["values"][2] = bad
                self.assertRejected(make_validator().validate_observation(m), self.R.NON_FINITE_VALUE, "state.values[2]")

    def test_state_outside_limits_rejected(self):
        m = obs1()
        m["state"]["values"][5] = 0.5  # gripper max is 0.08 m
        self.assertRejected(make_validator().validate_observation(m), self.R.OUT_OF_LIMITS, "state.values[5]")


class ObservationTimestampTests(ContractCase):
    def test_monotonic_sequence_accepted(self):
        val = make_validator()
        self.assertAccepted(val.validate_observation(obs1()))
        self.assertAccepted(val.validate_observation(obs2()))

    def test_duplicate_sequence_rejected(self):
        val = make_validator()
        self.assertAccepted(val.validate_observation(obs1()))
        self.assertRejected(val.validate_observation(obs1()), self.R.DUPLICATE_SEQUENCE)

    def test_out_of_order_sequence_rejected(self):
        val = make_validator()
        self.assertAccepted(val.validate_observation(obs2()))
        self.assertRejected(val.validate_observation(obs1()), self.R.OUT_OF_ORDER_SEQUENCE)

    def test_non_increasing_timestamp_rejected(self):
        val = make_validator()
        self.assertAccepted(val.validate_observation(obs1()))
        m = obs2()
        m["source_timestamp_ns"] = obs1()["source_timestamp_ns"]  # new seq, same time
        self.assertRejected(val.validate_observation(m), self.R.TIMESTAMP_NOT_MONOTONIC)
        m["source_timestamp_ns"] -= 1
        self.assertRejected(val.validate_observation(m), self.R.TIMESTAMP_NOT_MONOTONIC)

    def test_rejected_message_does_not_advance_state(self):
        val = make_validator()
        bad = obs2()
        bad["state"]["values"][0] = float("nan")
        self.assertRejected(val.validate_observation(bad), self.R.NON_FINITE_VALUE)
        self.assertAccepted(val.validate_observation(obs2()))  # still acceptable

    def test_timestamp_bounds(self):
        for bad in (-1, c.MAX_TIMESTAMP_NS + 1, 10**30):
            with self.subTest(bad=bad):
                m = obs1()
                m["source_timestamp_ns"] = bad
                self.assertRejected(make_validator().validate_observation(m), self.R.TIMESTAMP_OUT_OF_BOUNDS)
        m = obs1()
        m["source_timestamp_ns"] = c.MAX_TIMESTAMP_NS  # upper bound is inclusive
        self.assertAccepted(make_validator().validate_observation(m))

    def test_non_finite_timestamp_rejected(self):
        for bad in (float("nan"), float("inf")):
            m = obs1()
            m["source_timestamp_ns"] = bad
            self.assertRejected(make_validator().validate_observation(m), self.R.NON_FINITE_VALUE)

    def test_ttl_bounds(self):
        for bad in (0, -5, c.MAX_TTL_MS + 1):
            m = obs1()
            m["ttl_ms"] = bad
            self.assertRejected(make_validator().validate_observation(m), self.R.MALFORMED_MESSAGE, "ttl_ms")


if __name__ == "__main__":
    unittest.main()
