import unittest

from servesim.cache import ModelCache
from tests.helpers import fixed, make_raw, run


class LruCacheTests(unittest.TestCase):
    def test_lru_eviction_order(self):
        c = ModelCache(2)
        self.assertFalse(c.access("a", 1))
        self.assertFalse(c.access("b", 1))
        self.assertTrue(c.access("a", 1))           # a becomes most recent
        self.assertEqual(c.resident(), ["b", "a"])
        self.assertFalse(c.access("c", 1))          # evicts b (least recent)
        self.assertEqual(c.resident(), ["a", "c"])
        self.assertEqual(c.evictions, 1)
        self.assertNotIn("b", c)

    def test_size_aware_eviction_evicts_several(self):
        c = ModelCache(4)
        c.access("s1", 1)
        c.access("s2", 1)
        c.access("s3", 1)
        self.assertFalse(c.access("big", 3))        # needs 3 free: evicts s1, s2 (free 1 -> 2 -> 3)
        self.assertEqual(c.resident(), ["s3", "big"])
        self.assertEqual(c.evictions, 2)
        self.assertAlmostEqual(c.used, 4)

    def test_oversize_and_bad_capacity(self):
        with self.assertRaises(ValueError):
            ModelCache(0)
        with self.assertRaises(ValueError):
            ModelCache(1).access("x", 2)

    def test_clear(self):
        c = ModelCache(2)
        c.access("a", 1)
        c.clear()
        self.assertEqual(c.resident(), [])
        self.assertAlmostEqual(c.free(), 2)


class EngineCacheTests(unittest.TestCase):
    models = {k: {"service_time": 1.0, "load_cost": 0.5, "size": 1.0} for k in ("m1", "m2", "m3")}

    def test_lru_sequence_hand_computed(self):
        # capacity 2, requests spaced 10 s apart so nothing queues.
        # m1 miss [m1] | m2 miss [m1,m2] | m1 hit [m2,m1] | m3 miss evict m2 [m1,m3]
        # m2 miss evict m1 [m3,m2] | m1 miss evict m3 [m2,m1]  -> 1 hit, 5 misses, 3 evictions
        clients = [fixed("c1", [0, 20, 50], 100, "m1"), fixed("c2", [10, 40], 100, "m2"),
                   fixed("c3", [30], 100, "m3")]
        res = run(make_raw(clients, self.models, cache_capacity=2.0))
        self.assertEqual((res.hits, res.misses, res.evictions), (1, 5, 3))
        lat = {r.arrival: round(r.finish - r.arrival, 9) for r in res.requests}
        self.assertEqual(lat[20], 1.0)                       # the single hit: no load cost
        for t in (0, 10, 30, 40, 50):
            self.assertEqual(lat[t], 1.5)                    # misses pay 0.5 s load

    def test_cache_aware_placement_hand_computed(self):
        # 2 workers, 1 slot each, requests 10 s apart (both workers always idle).
        # first_idle: always worker 0 -> m1 miss, m2 miss, m1 miss, m2 miss = 0 hits.
        # cache_aware: m1->w0, m2->w1 (free slot), m1->w0 hit, m2->w1 hit = 2 hits.
        models = {k: {"service_time": 1.0, "load_cost": 0.5, "size": 1.0} for k in ("m1", "m2")}
        clients = [fixed("c1", [0, 20], 100, "m1"), fixed("c2", [10, 30], 100, "m2")]
        base = make_raw(clients, models, cache_capacity=1.0, workers=2)
        naive = run(base, placement="first_idle")
        aware = run(base, placement="cache_aware")
        self.assertEqual((naive.hits, naive.misses), (0, 4))
        self.assertEqual((aware.hits, aware.misses), (2, 2))
        self.assertEqual([w for (_t, _id, w, _h) in naive.dispatch_log], [0, 0, 0, 0])
        self.assertEqual([w for (_t, _id, w, _h) in aware.dispatch_log], [0, 1, 0, 1])


if __name__ == "__main__":
    unittest.main()
