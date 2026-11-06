"""Shared builders for the tiny hand-computed test scenarios."""

import copy

from servesim import parse_config, simulate


def make_raw(clients, models=None, **overrides):
    """A minimal valid raw config: 1 worker, deterministic service, no jitter."""
    raw = {
        "seed": 1,
        "duration": 100.0,
        "workers": 1,
        "cache_capacity": 10.0,
        "models": models or {"m": {"service_time": 1.0, "load_cost": 0.0, "size": 1.0}},
        "clients": clients,
    }
    raw.update(overrides)
    return raw


def fixed(cid, times, deadline, model="m", **extra):
    c = {"id": cid, "arrival": {"kind": "fixed", "times": times}, "models": [model],
         "deadline": deadline}
    c.update(extra)
    return c


def run(raw, **overrides):
    raw = copy.deepcopy(raw)
    raw.update(overrides)
    return simulate(parse_config(raw))


def finish_order(result):
    """Client-labelled request ids in order of completion time."""
    done = [r for r in result.requests if r.status == "done"]
    done.sort(key=lambda r: (r.finish, r.id))
    return [r.client for r in done]
