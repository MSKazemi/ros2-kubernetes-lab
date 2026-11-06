"""Deterministic SYNTHETIC trace generator.

Every file it writes is labelled SYNTHETIC in its header. The models below are
ASSUMPTIONS written down in matrix/matrix.yaml (``synthetic_model``); they
exist to exercise the analysis code with known shapes (loss, duplicates,
reordering, outage gaps). They are not measurements and not claims about how
any DDS or Zenoh implementation behaves.

Same matrix + same seeds => byte-identical output (stdlib ``random.Random`` with
integer seeds; no clocks, no environment input).
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any, Dict, List, Tuple

from .trace import SCHEMA

GENERATOR = "ddsres.synth/1"
T0_NS = 1_000_000_000
LABEL = (
    "SYNTHETIC: deterministic fixture produced by ddsres.synth from fixed seeds and documented "
    "assumptions; NOT a measurement of any middleware, network or cluster."
)


def _ms(x: float) -> int:
    return int(round(x * 1_000_000))


def generate_cell(matrix: Dict[str, Any], cell: Dict[str, Any]) -> List[str]:
    """Return the JSONL lines (each ending in a newline) for one matrix cell."""
    rel, imp = cell["reliability"], cell["impairment"]
    wl = matrix["workload"]
    model = matrix["synthetic_model"]
    mrel = model[rel]
    params = matrix["impairments"][imp]
    rng = random.Random(cell["seed"])

    n = wl["message_count"]
    period = _ms(wl["publish_period_ms"])
    reliable = rel == "reliable"
    rto = _ms(model["reliable"]["retransmit_rto_ms"])

    fault_begin = fault_end = None  # (begin_ns, end_ns) absolute
    drop_window = None
    if imp == "restart":
        a = T0_NS + _ms(params["at_s"] * 1000)
        up = a + _ms(params["down_s"] * 1000)
        fault_begin, fault_end = a, up
        drop_window = (a, up + _ms(mrel["rediscovery_ms"]))
    elif imp == "partition":
        a = T0_NS + _ms(params["at_s"] * 1000)
        h = a + _ms(params["duration_s"] * 1000)
        fault_begin, fault_end = a, h
        drop_window = (a, h)

    sends: List[Tuple[int, int]] = []
    recvs: List[Tuple[int, int]] = []  # (t, seq)
    primary: Dict[int, int] = {}
    dup_of: Dict[int, int] = {}
    partition_buffer: List[int] = []

    for seq in range(n):
        t_send = T0_NS + seq * period
        sends.append((t_send, seq))
        lat = model["base_latency_ns"] + rng.randrange(model["base_noise_ns"])
        u_jit = rng.random()
        u_loss = rng.random()

        if imp == "delay":
            lat += _ms(params["delay_ms"])
        elif imp == "jitter":
            lat += max(0, _ms(params["delay_ms"]) + int((u_jit * 2 - 1) * _ms(params["jitter_ms"])))

        if drop_window and drop_window[0] <= t_send < drop_window[1]:
            if imp == "partition" and reliable:
                partition_buffer.append(seq)
            continue

        if imp == "loss":
            p = params["loss_pct"] / 100.0
            if not reliable:
                if u_loss < p:
                    continue
            else:
                attempts, u = 0, u_loss
                while attempts < model["reliable"]["max_attempts"] and u < p:
                    attempts += 1
                    u = rng.random()
                lat += attempts * rto
                if attempts and rng.random() < model["reliable"]["duplicate_prob_on_retransmit"]:
                    dup_of[seq] = t_send + lat + rto
        primary[seq] = t_send + lat

    if imp == "partition" and reliable:
        depth = model["reliable"]["partition_buffer_depth"]
        for k, seq in enumerate(partition_buffer[-depth:]):
            primary[seq] = fault_end + (k + 1) * _ms(1)  # catch-up burst, 1 ms apart

    if reliable and mrel["in_order_delivery"]:
        prev = 0
        for seq in sorted(primary):
            primary[seq] = max(primary[seq], prev)
            prev = primary[seq]

    recvs = [(t, s) for s, t in primary.items()] + [(t, s) for s, t in dup_of.items()]

    rows: List[Tuple[int, int, int, Dict[str, Any]]] = []
    clock = "sim_mono"
    for t, s in sends:
        rows.append((t, 0, s, {"type": "send", "seq": s, "t_ns": t, "clock": clock}))
    if fault_begin is not None:
        rows.append((fault_begin, 1, 0, {"type": "marker", "name": f"{imp}_begin", "t_ns": fault_begin, "clock": clock}))
        rows.append((fault_end, 1, 1, {"type": "marker", "name": f"{imp}_end", "t_ns": fault_end, "clock": clock}))
    for t, s in recvs:
        rows.append((t, 2, s, {"type": "recv", "seq": s, "t_ns": t, "clock": clock}))
    rows.sort(key=lambda r: r[:3])

    header = {
        "type": "header",
        "schema": SCHEMA,
        "synthetic": True,
        "label": LABEL,
        "generator": GENERATOR,
        "run_id": f"{cell['id']}.synthetic",
        "reliability": rel,
        "impairment": imp,
        "seed": cell["seed"],
        "rmw": None,
        "default_clock": clock,
    }
    out = [json.dumps(header, sort_keys=True) + "\n"]
    out += [json.dumps(r[3], sort_keys=True) + "\n" for r in rows]
    out.append(json.dumps({"type": "footer", "records": len(rows)}, sort_keys=True) + "\n")
    return out


def fixture_name(cell: Dict[str, Any]) -> str:
    return f"{cell['id']}.synthetic.jsonl"


def render_all(matrix: Dict[str, Any]) -> Dict[str, str]:
    """Map fixture file name -> full text, plus MANIFEST.json."""
    files = {fixture_name(c): "".join(generate_cell(matrix, c)) for c in matrix["cells"]}
    manifest = {
        "label": LABEL,
        "generator": GENERATOR,
        "synthetic": True,
        "files": {
            name: {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "lines": text.count("\n")}
            for name, text in sorted(files.items())
        },
    }
    files["MANIFEST.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return files


def write_fixtures(matrix: Dict[str, Any], out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, text in render_all(matrix).items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        written.append(path)
    return written
