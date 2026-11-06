import unittest

from seqprobe.errors import ConfigError, PayloadError
from seqprobe.payload import (build_payload, decode_payload, coerce_bytes, min_payload_bytes,
                              pad_for)


class PayloadTests(unittest.TestCase):
    def test_roundtrip_exact_size(self):
        for size in (min_payload_bytes("r1", "wall"), 64, 1000):
            p = build_payload("r1", 7, 123456789, "wall", size, seed=3)
            self.assertEqual(len(p), size)
            d = decode_payload(p)
            self.assertEqual((d.run_id, d.seq, d.sent_ts_ns, d.sent_clock, d.payload_bytes),
                             ("r1", 7, 123456789, "wall", size))

    def test_deterministic_and_seed_sensitive(self):
        a = build_payload("r1", 1, 5, "wall", 128, seed=1)
        self.assertEqual(a, build_payload("r1", 1, 5, "wall", 128, seed=1))
        self.assertNotEqual(a, build_payload("r1", 1, 5, "wall", 128, seed=2))
        self.assertNotEqual(pad_for(1, 1, 40), pad_for(1, 2, 40))

    def test_too_small_payload_rejected(self):
        with self.assertRaises(ConfigError):
            build_payload("r1", 0, 0, "wall", min_payload_bytes("r1", "wall") - 1, seed=0)

    def test_decode_bytes_and_byte_lists(self):
        p = build_payload("r1", 2, 9, "monotonic", 80, seed=0)
        self.assertEqual(decode_payload(p.encode()).seq, 2)
        self.assertEqual(decode_payload([bytes([c]) for c in p.encode()]).seq, 2)
        self.assertEqual(decode_payload(list(p.encode())).seq, 2)

    def test_malformed_payloads(self):
        good = build_payload("r1", 2, 9, "wall", 80, seed=0)
        bad = [
            "", "hello", good.replace("SQP1", "XXXX"), good.replace(";r1;", ";r 1;"),
            good.replace("0000000002", "2"), good.replace(";wall;", ";sundial;"),
            good.replace("0000000002", "000000000x"), "SQP1;r1;0000000002;" + "9" * 20,
            good.encode() + "\xff".encode("latin-1"),
        ]
        for text in bad:
            with self.subTest(text=text[:40]):
                with self.assertRaises(PayloadError):
                    decode_payload(text)

    def test_coerce_rejects_junk(self):
        for junk in (42, None, [b"ab"], [300], [True], [object()]):
            with self.subTest(junk=junk):
                with self.assertRaises(PayloadError):
                    coerce_bytes(junk)

    def test_out_of_range_inputs(self):
        with self.assertRaises(ConfigError):
            build_payload("r1", -1, 0, "wall", 80, seed=0)
        with self.assertRaises(ConfigError):
            build_payload("r1", 0, -5, "wall", 80, seed=0)
        with self.assertRaises(ConfigError):
            build_payload("r1", 0, 0, "utc", 80, seed=0)


if __name__ == "__main__":
    unittest.main()
