"""Offline tests for DataAnalysis/analyze_sample.py (no cluster, no network).

Fixtures are tiny hand-written files in the exact layout of the committed
samples ({namespace: [{"metric": {...}, "values": [[epoch_int, "str"], ...]}]});
they are NOT real measurements. One test also pins the CSV derived from the
real committed CPU sample so any change to the code or to the data is noticed.
"""
import ast
import csv
import hashlib
import json
import runpy
import socket
from pathlib import Path

import pytest

import analyze_sample as a

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
REAL_DATASET = ANALYSIS_DIR / "dataset"

# SHA-256 of the CSV produced from the committed container_cpu_usage_seconds_total.json.
# Update only when the tool or the committed sample intentionally changes.
GOLDEN_CPU_CSV_SHA256 = "9556d6692a48369690ec7c205535712998a31eead4a5c173055429889140add6"


def run_main(tmp_path, name, data):
    """Write `data` as a sample file in the committed layout, run the CLI, return (rc, rows)."""
    ds = tmp_path / "ds"
    ds.mkdir(exist_ok=True)
    (ds / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    rc = a.main(["--sample", name, "--dataset-dir", str(ds), "--out-dir", str(out)])
    csv_path = out / f"{name}_summary.csv"
    rows = []
    if csv_path.exists():
        with open(csv_path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    return rc, rows


# ---- empty series / missing labels ------------------------------------------------

def test_empty_namespace_and_empty_values(tmp_path):
    data = {
        "kube-public": [],
        "ros": [{"metric": {}, "values": []}],
    }
    rc, rows = run_main(tmp_path, "container_cpu_usage_seconds_total", data)
    assert rc == 0
    assert [r["namespace"] for r in rows] == ["kube-public", "ros"]
    for r in rows:
        assert r["n_samples"] == "0" and r["first_utc"] == "" and r["mean"] == ""
        assert r["n_gaps"] == "0"


def test_missing_pod_label_and_missing_metric_key(tmp_path):
    data = {"ros": [
        {"metric": {"pod": "ros-abc"}, "values": [[1713596820, "1.5"]]},
        {"metric": {}, "values": [[1713596820, "2.5"]]},
        {"values": [[1713596820, "3.5"]]},  # no "metric" key at all
    ]}
    rc, rows = run_main(tmp_path, "container_cpu_usage_seconds_total_pod", data)
    assert rc == 0
    assert [r["pod"] for r in rows] == ["ros-abc", "", ""]
    assert [r["mean"] for r in rows] == ["1.5", "2.5", "3.5"]


# ---- timestamps / gaps / bad values ----------------------------------------------

def test_timestamps_are_utc_and_sorted(tmp_path):
    # 1713596820 == 2024-04-20T07:07:00Z; samples given out of order
    data = {"ros": [{"metric": {}, "values": [[1713596940, "3"], [1713596820, "1"], [1713596880, "2"]]}]}
    _, rows = run_main(tmp_path, "container_cpu_usage_seconds_total", data)
    r = rows[0]
    assert (r["first_utc"], r["last_utc"]) == ("2024-04-20T07:07:00Z", "2024-04-20T07:09:00Z")
    assert (r["min"], r["max"], r["mean"]) == ("1", "3", "2")
    assert r["n_gaps"] == "0"


def test_gap_is_counted_not_filled(tmp_path):
    t = 1713596820
    data = {"ros": [{"metric": {}, "values": [[t, "1"], [t + 60, "1"], [t + 60 + 5760, "1"]]}]}
    _, rows = run_main(tmp_path, "container_cpu_usage_seconds_total", data)
    assert rows[0]["n_samples"] == "3"  # no interpolated points
    assert (rows[0]["n_gaps"], rows[0]["longest_gap_s"]) == ("1", "5760")
    # a 120 s step is nominal for some pod series and must NOT count as a gap
    assert a.gap_stats([0, 60, 180]) == (0, 0)
    assert a.gap_stats([0, 121]) == (1, 121)


def test_nan_and_garbage_values_are_dropped_and_counted():
    pts, bad = a.parse_values([[1, "1"], [2, "NaN"], [3, "+Inf"], [4, "oops"], [5, None], [6, "2"]])
    assert pts == [(1, 1.0), (6, 2.0)]
    assert bad == 4


# ---- counter -> rate ---------------------------------------------------------------

def test_counter_to_rate_basic():
    assert a.counter_to_rate([(0, 0.0), (60, 30.0), (120, 90.0)]) == [(60, 0.5), (120, 1.0)]


def test_counter_to_rate_reset_and_irregular_step():
    # reset at t=120 (counter restarted): the new value counts as the increase since the reset
    got = a.counter_to_rate([(0, 100.0), (60, 160.0), (120, 12.0), (240, 132.0)])
    assert got == [(60, 1.0), (120, 0.2), (240, 1.0)]


def test_counter_to_rate_degenerate_inputs():
    assert a.counter_to_rate([]) == []
    assert a.counter_to_rate([(0, 5.0)]) == []
    assert a.counter_to_rate([(10, 1.0), (10, 2.0)]) == []  # dt == 0 skipped, no ZeroDivisionError


# ---- units / metric semantics --------------------------------------------------------

def test_units_are_reported_and_cpu_is_never_a_percentage(tmp_path):
    _, rows = run_main(tmp_path, "container_cpu_usage_seconds_total",
                       {"ros": [{"metric": {}, "values": [[1713596820, "0.5"]]}]})
    assert "cores" in rows[0]["unit"].lower()
    header = "".join(a.CSV_COLUMNS).lower()
    assert "%" not in header and "percent" not in header
    assert "percent" not in rows[0]["unit"].lower() and "%" not in rows[0]["unit"]
    assert "bytes per second" in a.metric_info("container_network_receive_bytes_total_pod")[1]
    assert a.metric_info("container_memory_usage_bytes")[0] == "gauge"
    with pytest.raises(a.SampleError):
        a.metric_info("node_cpu_seconds_total")


def test_raw_counter_in_a_rate_file_triggers_warning():
    values = [[1713596820 + 60 * i, str(1000 + 10 * i)] for i in range(12)]  # steadily growing
    _, warnings = a.summarize("container_cpu_usage_seconds_total",
                              {"ros": [{"metric": {}, "values": values}]})
    assert warnings and "raw cumulative counter" in warnings[0]


def test_committed_rate_files_do_not_look_like_raw_counters():
    for name in a.list_samples(REAL_DATASET):
        kind, _ = a.metric_info(name)
        if kind != "rate":
            continue
        _, warnings = a.summarize(name, a.load_sample(REAL_DATASET / f"{name}.json"))
        assert warnings == [], (name, warnings)


# ---- input validation / local-only ------------------------------------------------------

@pytest.mark.parametrize("bad", ["http://192.168.56.10:30090/x", "../secret", "a/b", ".hidden"])
def test_sample_name_must_be_a_plain_local_stem(bad):
    with pytest.raises(a.SampleError):
        a.resolve_sample(REAL_DATASET, bad)


def test_malformed_layout_returns_error_code(tmp_path, capsys):
    rc, _ = run_main(tmp_path, "container_cpu_usage_seconds_total", [1, 2, 3])
    assert rc == 2 and "keyed by namespace" in capsys.readouterr().err
    rc, _ = run_main(tmp_path, "container_cpu_usage_seconds_total", {"ros": [{"metric": {}}]})
    assert rc == 2


def test_analyzer_imports_no_network_or_third_party_modules():
    tree = ast.parse((ANALYSIS_DIR / "analyze_sample.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {n.name.split(".")[0] for n in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert names <= {"__future__", "argparse", "csv", "json", "math", "sys", "datetime", "pathlib"}


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("network access attempted during an offline run")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def test_real_sample_runs_with_network_blocked_and_is_deterministic(tmp_path, no_network):
    digests = []
    for i in range(2):
        out = tmp_path / f"run{i}"
        assert a.main(["--out-dir", str(out)]) == 0
        csv_bytes = (out / "container_cpu_usage_seconds_total_summary.csv").read_bytes()
        digests.append(hashlib.sha256(csv_bytes).hexdigest())
    assert digests[0] == digests[1]
    assert digests[0] == GOLDEN_CPU_CSV_SHA256


def test_provenance_file_is_written_next_to_the_csv(tmp_path):
    assert a.main(["--out-dir", str(tmp_path)]) == 0
    text = (tmp_path / "PROVENANCE.txt").read_text(encoding="utf-8")
    for needle in ("2024-04-20", "not a benchmark", "Unknown/unverified", "never a percentage"):
        assert needle in text


def test_all_committed_samples_summarize(tmp_path, no_network):
    for name in a.list_samples(REAL_DATASET):
        assert a.main(["--sample", name, "--out-dir", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*_summary.csv"))) == 10


def test_existing_plot_script_runs_offline(tmp_path, no_network, monkeypatch):
    pytest.importorskip("matplotlib")
    out = tmp_path / "namespace_cpu.png"
    monkeypatch.setattr("sys.argv", ["plot_namespace_cpu.py", "--out", str(out)])
    runpy.run_path(str(ANALYSIS_DIR / "plot_namespace_cpu.py"), run_name="__main__")
    assert out.stat().st_size > 1000 and out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
