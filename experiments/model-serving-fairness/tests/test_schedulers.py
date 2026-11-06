import unittest

from servesim.schedulers import DrrScheduler, EdfScheduler, FifoScheduler
from servesim.workload import Request
from tests.helpers import finish_order, fixed, make_raw, run

MODELS = {"blk": {"service_time": 1.0}, "q": {"service_time": 0.5}, "big": {"service_time": 1.0}}


def req(i, client, arrival, deadline, service=1.0):
    return Request(id=i, client=client, model="m", arrival=arrival, deadline=deadline, service=service)


class UnitOrderTests(unittest.TestCase):
    def test_fifo_orders_by_arrival_then_id(self):
        s = FifoScheduler()
        for r in (req(2, "a", 0.5, 9), req(0, "a", 0.1, 9), req(1, "b", 0.1, 1)):
            s.push(r)
        self.assertEqual([s.pop(0).id for _ in range(3)], [0, 1, 2])
        self.assertIsNone(s.pop(0))

    def test_edf_orders_by_deadline_then_arrival_then_id(self):
        s = EdfScheduler()
        for r in (req(0, "a", 0.0, 5), req(1, "b", 0.1, 2), req(2, "c", 0.05, 2)):
            s.push(r)
        self.assertEqual([s.pop(0).id for _ in range(3)], [2, 1, 0])   # tie on 2: earlier arrival

    def test_drr_hand_computed_unit_costs(self):
        s = DrrScheduler(quantum=1.0, weights={"a": 1.0, "b": 1.0})
        for i in range(3):
            s.push(req(i, "a", 0.0 + i * 0.01, 9))
        s.push(req(10, "b", 0.5, 9))
        # ring [a, b]: a, b, a, a
        self.assertEqual([s.pop(0).client for _ in range(4)], ["a", "b", "a", "a"])
        self.assertEqual(len(s), 0)
        self.assertIsNone(s.pop(0))

    def test_drr_deficit_accumulates_for_expensive_request(self):
        # head cost 2.5 with quantum 1.0 needs three visits; the cheap client is served meanwhile.
        s = DrrScheduler(quantum=1.0, weights={"x": 1.0, "y": 1.0})
        s.push(req(0, "x", 0.0, 9, service=2.5))
        for i in range(1, 4):
            s.push(req(i, "y", 0.1, 9, service=1.0))
        # x: +1 (1<2.5) | y: +1 serve y1 | x: +1 (2<2.5) | y: +1 serve y2 | x: +1 (3>=2.5) serve x
        self.assertEqual([s.pop(0).client for _ in range(4)], ["y", "y", "x", "y"])


class EngineOrderTests(unittest.TestCase):
    """Hand-computed orders on one worker. Z occupies the worker over [0, 1)."""

    def clients(self, a_weight=1.0):
        return [
            fixed("Z", [0.0], 100, "blk"),
            fixed("A", [0.1] * 4, 100, "q", weight=a_weight),
            fixed("B", [0.2], 0.3, "q"),            # absolute deadline 0.5: earliest
        ]

    def test_fifo(self):
        res = run(make_raw(self.clients(), MODELS, scheduler="fifo"))
        self.assertEqual(finish_order(res), ["Z", "A", "A", "A", "A", "B"])

    def test_edf(self):
        res = run(make_raw(self.clients(), MODELS, scheduler="edf"))
        self.assertEqual(finish_order(res), ["Z", "B", "A", "A", "A", "A"])

    def test_drr_equal_weights(self):
        res = run(make_raw(self.clients(), MODELS, scheduler="drr", drr_quantum=0.5))
        self.assertEqual(finish_order(res), ["Z", "A", "B", "A", "A", "A"])

    def test_drr_weight_two_gets_two_per_turn(self):
        res = run(make_raw(self.clients(a_weight=2.0), MODELS, scheduler="drr", drr_quantum=0.5))
        self.assertEqual(finish_order(res), ["Z", "A", "A", "B", "A", "A"])

    def test_drr_is_cost_aware(self):
        # X: three 1.0 s requests, Y: four 0.5 s requests, quantum 1.0 -> X one per turn, Y two.
        clients = [fixed("Z", [0.0], 100, "blk"), fixed("X", [0.1] * 3, 100, "big"),
                   fixed("Y", [0.2] * 4, 100, "q")]
        res = run(make_raw(clients, MODELS, scheduler="drr", drr_quantum=1.0))
        self.assertEqual(finish_order(res), ["Z", "X", "Y", "Y", "X", "Y", "Y", "X"])

    def test_fifo_vs_edf_deadline_misses(self):
        # service 1.0. A: arrivals 0, 0.1 (loose deadline); B: arrival 0.2, absolute deadline 2.5.
        # FIFO: A0 [0,1] A1 [1,2] B [2,3] -> B late.  EDF: A0 [0,1] B [1,2] A1 [2,3] -> none late.
        clients = [fixed("A", [0.0, 0.1], 100), fixed("B", [0.2], 2.3)]
        fifo = run(make_raw(clients, scheduler="fifo"))
        edf = run(make_raw(clients, scheduler="edf"))
        from servesim.metrics import summarize
        sf, se = summarize(fifo), summarize(edf)
        self.assertEqual((sf["totals"]["late"], se["totals"]["late"]), (1, 0))
        self.assertAlmostEqual(sf["deadline_miss_rate"], 1 / 3, places=5)
        self.assertEqual(se["deadline_miss_rate"], 0.0)
        # latencies: FIFO 1.0, 1.9, 2.8 ; EDF 1.0, 1.8, 2.9
        self.assertEqual(sf["latency_s"]["p50"], 1.9)
        self.assertEqual(se["latency_s"]["p50"], 1.8)
        self.assertEqual(sf["latency_s"]["max"], 2.8)
        self.assertEqual(se["latency_s"]["max"], 2.9)


if __name__ == "__main__":
    unittest.main()
