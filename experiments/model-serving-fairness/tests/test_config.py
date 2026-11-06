import copy
import unittest

from servesim import ConfigError, parse_config
from tests.helpers import fixed, make_raw


def base():
    return make_raw([fixed("c", [0.0], 1.0)])


class ValidConfigTests(unittest.TestCase):
    def test_minimal_valid(self):
        cfg = parse_config(base())
        self.assertEqual((cfg.workers, cfg.scheduler, cfg.placement), (1, "fifo", "first_idle"))

    def test_all_arrival_kinds_accepted(self):
        for arr in ({"kind": "periodic", "period": 1.0}, {"kind": "poisson", "rate": 2.0},
                    {"kind": "bursty", "burst_interval": 5.0, "burst_size": 3}):
            raw = make_raw([{"id": "c", "arrival": arr, "models": ["m"], "deadline": 1.0}])
            parse_config(raw)


class InvalidConfigTests(unittest.TestCase):
    def mutate(self, fn):
        raw = copy.deepcopy(base())
        fn(raw)
        return raw

    def test_invalid_variants_raise(self):
        cases = {
            "not a dict": lambda r: None,
            "zero workers": lambda r: r.update(workers=0),
            "fractional workers": lambda r: r.update(workers=1.5),
            "bool workers": lambda r: r.update(workers=True),
            "negative duration": lambda r: r.update(duration=-1),
            "nan duration": lambda r: r.update(duration=float("nan")),
            "inf duration": lambda r: r.update(duration=float("inf")),
            "zero cache": lambda r: r.update(cache_capacity=0),
            "unknown scheduler": lambda r: r.update(scheduler="lifo"),
            "unknown placement": lambda r: r.update(placement="random"),
            "zero quantum": lambda r: r.update(drr_quantum=0),
            "zero queue capacity": lambda r: r.update(queue_capacity=0),
            "non-bool drain": lambda r: r.update(drain="yes"),
            "unknown top-level key": lambda r: r.update(wokers=2),
            "missing clients": lambda r: r.pop("clients"),
            "empty clients": lambda r: r.update(clients=[]),
            "empty models": lambda r: r.update(models={}),
            "negative service time": lambda r: r["models"]["m"].update(service_time=-1),
            "zero service time": lambda r: r["models"]["m"].update(service_time=0),
            "negative load cost": lambda r: r["models"]["m"].update(load_cost=-0.1),
            "model larger than cache": lambda r: r["models"]["m"].update(size=11),
            "jitter >= 1": lambda r: r["models"]["m"].update(service_jitter=1.0),
            "unknown model ref": lambda r: r["clients"][0].update(models=["nope"]),
            "empty model list": lambda r: r["clients"][0].update(models=[]),
            "zero deadline": lambda r: r["clients"][0].update(deadline=0),
            "zero weight": lambda r: r["clients"][0].update(weight=0),
            "duplicate client ids": lambda r: r["clients"].append(copy.deepcopy(r["clients"][0])),
            "unknown arrival kind": lambda r: r["clients"][0].update(arrival={"kind": "zipf"}),
            "fixed time past duration": lambda r: r["clients"][0]["arrival"].update(times=[100.0]),
            "negative fixed time": lambda r: r["clients"][0]["arrival"].update(times=[-1.0]),
            "periodic zero period": lambda r: r["clients"][0].update(
                arrival={"kind": "periodic", "period": 0}),
            "poisson zero rate": lambda r: r["clients"][0].update(
                arrival={"kind": "poisson", "rate": 0}),
            "bursty fractional size": lambda r: r["clients"][0].update(
                arrival={"kind": "bursty", "burst_interval": 1.0, "burst_size": 1.5}),
            "arrival extra key": lambda r: r["clients"][0]["arrival"].update(bogus=1),
            "failure worker out of range": lambda r: r.update(
                failures=[{"worker": 1, "start": 0, "end": 1}]),
            "failure end before start": lambda r: r.update(
                failures=[{"worker": 0, "start": 2, "end": 1}]),
            "overlapping failures": lambda r: r.update(failures=[
                {"worker": 0, "start": 0, "end": 5}, {"worker": 0, "start": 4, "end": 6}]),
        }
        for label, fn in cases.items():
            with self.subTest(label):
                raw = self.mutate(fn)
                if label == "not a dict":
                    raw = []
                with self.assertRaises(ConfigError):
                    parse_config(raw)

    def test_config_error_is_value_error(self):
        self.assertTrue(issubclass(ConfigError, ValueError))


if __name__ == "__main__":
    unittest.main()
