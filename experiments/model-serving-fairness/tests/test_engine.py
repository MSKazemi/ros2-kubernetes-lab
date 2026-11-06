import json
import unittest

from servesim import parse_config, simulate, summarize
from servesim.report import run_matrix, to_json
from servesim.workload import generate_requests
from tests.helpers import fixed, make_raw, run

def default_raw():
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "default_fleet.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class DeterminismTests(unittest.TestCase):
    def test_same_seed_identical_json(self):
        raw = default_raw()
        a = to_json(run_matrix(raw, [3], ["fifo", "drr"], ["first_idle"]))
        b = to_json(run_matrix(raw, [3], ["fifo", "drr"], ["first_idle"]))
        self.assertEqual(a, b)

    def test_different_seed_changes_workload(self):
        raw = default_raw()
        r1 = generate_requests(parse_config({**raw, "seed": 1}))
        r2 = generate_requests(parse_config({**raw, "seed": 2}))
        self.assertNotEqual([r.arrival for r in r1], [r.arrival for r in r2])

    def test_workload_identical_across_schedulers(self):
        raw = default_raw()
        w = [[(r.client, r.model, r.arrival, r.service)
              for r in generate_requests(parse_config({**raw, "scheduler": s}))]
             for s in ("fifo", "edf", "drr")]
        self.assertEqual(w[0], w[1])
        self.assertEqual(w[0], w[2])

    def test_seed_recorded_in_output(self):
        rep = run_matrix(default_raw(), [7, 8], ["fifo"], ["first_idle"])
        self.assertEqual(rep["seeds"], [7, 8])
        self.assertEqual([r["seed"] for r in rep["runs"]], [7, 8])
        self.assertTrue(all(r["label"] == "SIMULATED" for r in rep["runs"]))
        self.assertEqual(rep["label"], "SIMULATED")

    def test_workload_requests_never_mutated_by_summary(self):
        cfg = parse_config(default_raw())
        res = simulate(cfg)
        self.assertEqual(summarize(res), summarize(res))


class InvariantTests(unittest.TestCase):
    def test_conservation_all_combinations_with_failure(self):
        raw = default_raw()
        raw["duration"] = 30.0
        raw["failures"] = [{"worker": 1, "start": 5.0, "end": 12.0}]
        for sched in ("fifo", "edf", "drr"):
            for place in ("first_idle", "cache_aware"):
                for drop in (False, True):
                    with self.subTest(sched=sched, place=place, drop=drop):
                        s = summarize(simulate(parse_config(
                            {**raw, "scheduler": sched, "placement": place, "drop_expired": drop})))
                        t = s["totals"]
                        self.assertEqual(
                            t["arrivals"],
                            t["rejected"] + t["dropped"] + t["completed"] + t["unfinished"])
                        self.assertEqual(t["completed"], t["on_time"] + t["late"])
                        self.assertEqual(t["unfinished"], 0)      # drain=True
                        for c in s["clients"].values():
                            self.assertEqual(
                                c["arrivals"],
                                c["rejected"] + c["dropped"] + c["completed"] + c["unfinished"])

    def test_default_fleet_runs_fast_enough(self):
        import time
        t0 = time.perf_counter()
        simulate(parse_config(default_raw()))
        self.assertLess(time.perf_counter() - t0, 10.0)


class OverloadTests(unittest.TestCase):
    ARR = [0.0, 0.1, 0.2, 0.3, 0.4]

    def test_queue_capacity_rejects_hand_computed(self):
        # service 1.0, queue_capacity 2: r0 runs at once, r1,r2 queue, r3,r4 rejected.
        # finishes 1,2,3 vs deadlines 2.5, 2.6, 2.7 -> only r2 late -> 1 of 3 admitted.
        s = summarize(run(make_raw([fixed("c", self.ARR, 2.5)]), queue_capacity=2))
        t = s["totals"]
        self.assertEqual((t["arrivals"], t["admitted"], t["rejected"], t["completed"]), (5, 3, 2, 3))
        self.assertEqual((t["on_time"], t["late"]), (2, 1))
        self.assertAlmostEqual(s["deadline_miss_rate"], 1 / 3, places=5)
        self.assertAlmostEqual(s["goodput_rate"], 2 / 5, places=5)

    def test_drop_expired_hand_computed(self):
        # deadlines 1.5,1.6,1.7,1.8,1.9. r0 done at 1.0 ok; r1 done at 2.0 late;
        # r2 popped at 2.0 > 1.7 dropped, r3 and r4 dropped as well.
        s = summarize(run(make_raw([fixed("c", self.ARR, 1.5)]), drop_expired=True))
        t = s["totals"]
        self.assertEqual((t["completed"], t["on_time"], t["late"], t["dropped"]), (2, 1, 1, 3))
        self.assertAlmostEqual(s["deadline_miss_rate"], 4 / 5)

    def test_no_drop_serves_everything_late(self):
        s = summarize(run(make_raw([fixed("c", self.ARR, 1.5)])))
        self.assertEqual((s["totals"]["completed"], s["totals"]["on_time"]), (5, 1))
        self.assertEqual(s["end_time_s"], 100.0)           # horizon = duration

    def test_no_drain_leaves_unfinished(self):
        # duration 1.5, service 1.0, arrivals 0, 0.5, 1.0: only r0 finishes (t=1.0);
        # r1 starts at 1.0 (would end 2.0 > 1.5) and r2 is queued; both deadlines (1.5+) -> r1 not expired.
        raw = make_raw([fixed("c", [0.0, 0.5, 1.0], 10.0)], duration=1.5, drain=False)
        s = summarize(run(raw))
        self.assertEqual((s["totals"]["completed"], s["totals"]["unfinished"]), (1, 2))
        self.assertEqual(s["end_time_s"], 1.5)
        self.assertEqual(s["deadline_miss_rate"], 0.0)     # unfinished but deadlines not yet passed

    def test_no_drain_unfinished_past_deadline_counts_as_miss(self):
        raw = make_raw([fixed("c", [0.0, 0.5, 1.0], 0.6)], duration=1.5, drain=False)
        s = summarize(run(raw))
        # r0 finishes at 1.0 > deadline 0.6 -> late; r1 (deadline 1.1 < 1.5) is unfinished and
        # expired -> miss; r2 (deadline 1.6 >= 1.5) is unfinished but not yet expired.
        self.assertEqual(s["totals"]["late"], 1)
        self.assertAlmostEqual(s["deadline_miss_rate"], 2 / 3, places=5)   # r0 late + r1 unfinished-expired


class StarvationAndFairnessTests(unittest.TestCase):
    def test_wait_and_starved_requests(self):
        # waits: r0 0, r1 0.9, r2 1.8 ; threshold 1.5 -> 1 starved, max wait 1.8
        s = summarize(run(make_raw([fixed("c", [0.0, 0.1, 0.2], 100)], starvation_wait=1.5)))
        c = s["clients"]["c"]
        self.assertEqual(c["starved_requests"], 1)
        self.assertAlmostEqual(c["max_queue_wait_s"], 1.8, places=5)
        self.assertEqual(s["starved_requests"], 1)

    def test_no_service_client_and_jain_half(self):
        # queue_capacity 1: A's r0 runs, A's r1 queues, B's only request is rejected.
        clients = [fixed("A", [0.0, 0.1], 100), fixed("B", [0.3], 100)]
        s = summarize(run(make_raw(clients), queue_capacity=1))
        self.assertEqual(s["clients_with_no_service"], ["B"])
        self.assertEqual(s["clients"]["A"]["goodput_ratio"], 1.0)
        self.assertEqual(s["clients"]["B"]["goodput_ratio"], 0.0)
        self.assertAlmostEqual(s["jain_goodput_index"], 0.5)           # (1+0)^2 / (2*1)
        self.assertEqual(s["totals"]["rejected"], 1)

    def test_quiet_client_aggregate_excludes_noisy(self):
        # noisy N submits first and hogs the worker; quiet Q is late under fifo.
        clients = [fixed("N", [0.0, 0.0, 0.0], 100, noisy=True), fixed("Q", [0.1], 1.0)]
        s = summarize(run(make_raw(clients), scheduler="fifo"))
        self.assertEqual(s["clients"]["Q"]["deadline_miss_rate"], 1.0)  # Q finishes at 4.0
        self.assertEqual(s["quiet_clients_deadline_miss_rate"], 1.0)
        self.assertEqual(s["deadline_miss_rate"], 0.25)


class WorkerFailureTests(unittest.TestCase):
    FAIL = [{"worker": 0, "start": 0.5, "end": 2.0}]

    def test_inflight_request_restarts_after_recovery(self):
        res = run(make_raw([fixed("c", [0.0], 100)]), failures=self.FAIL)
        r = res.requests[0]
        self.assertEqual((r.first_start, r.finish, r.attempts), (0.0, 3.0, 2))   # restarts at 2.0
        self.assertEqual(res.retried, 1)
        # busy: 0.5 s aborted attempt + 1.0 s second attempt
        self.assertAlmostEqual(res.busy_time, 1.5)

    def test_failure_clears_cache(self):
        models = {"m": {"service_time": 1.0, "load_cost": 0.5, "size": 1.0}}
        res = run(make_raw([fixed("c", [0.0], 100)], models), failures=[
            {"worker": 0, "start": 1.0, "end": 2.0}])
        # first attempt: miss, would end 1.5, aborted at 1.0; restart at 2.0: miss again, ends 3.5
        self.assertEqual((res.hits, res.misses), (0, 2))
        self.assertEqual(res.requests[0].finish, 3.5)

    def test_other_worker_takes_over_immediately(self):
        res = run(make_raw([fixed("c", [0.0], 100)], workers=2), failures=self.FAIL)
        r = res.requests[0]
        self.assertEqual(r.finish, 1.5)                  # aborted at 0.5, restarted at 0.5 on worker 1
        self.assertEqual([w for (_t, _i, w, _h) in res.dispatch_log], [0, 1])

    def test_request_waits_while_all_workers_down(self):
        res = run(make_raw([fixed("c", [1.0], 100)]), failures=[
            {"worker": 0, "start": 0.0, "end": 5.0}])
        r = res.requests[0]
        self.assertEqual((r.first_start, r.finish), (5.0, 6.0))

    def test_stale_completion_ignored(self):
        # completion at 1.0 is scheduled for the aborted attempt; it must not complete the request early.
        res = run(make_raw([fixed("c", [0.0], 100)]), failures=self.FAIL)
        self.assertEqual(res.requests[0].finish, 3.0)


if __name__ == "__main__":
    unittest.main()
