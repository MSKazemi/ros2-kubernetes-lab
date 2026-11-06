# Data Analysis

This folder has two very different parts. Do not mix them up:

| Part | Needs a cluster? | What it is |
|---|---|---|
| [Offline analysis](#offline-analysis-no-cluster-no-network) | **No** | Reproducible summary CSV, plot and tests that read only the committed samples in [`dataset/`](./dataset/README.md). |
| [Live Prometheus queries](#live-prometheus-queries-needs-a-running-cluster) and the notebooks | **Yes** (Prometheus at `192.168.56.10:30090`) | How the historical data was exported; cannot be re-run without the original cluster. |

All committed data are **historical, Foxy-era samples** (a single recording of 2024-04-20 from the Vagrant lab cluster). They are not new benchmarks, say nothing about the Jazzy image in [`../ROS2/`](../ROS2/), and must not be quoted as performance results.

## Offline analysis (no cluster, no network)

Requires Python 3.12 or newer (tested with 3.12.3 on Linux). The pinned dependencies are in [`requirements-offline.txt`](./requirements-offline.txt).

```sh
# from the repository root; the network is only needed for this one install step
python3 -m venv .venv                      # .venv is not tracked
.venv/bin/pip install -r DataAnalysis/requirements-offline.txt

# one command: summary CSV for all 10 samples + the CPU plot + the offline tests
bash scripts/run-analysis-offline.sh       # uses ./.venv automatically; or: make analysis-offline
```

Outputs go to `DataAnalysis/output/` (ignored by version control, never committed): `<sample>_summary.csv` per sample, `namespace_cpu.png` and `PROVENANCE.txt` (the limitations that apply to every number there).

Smaller entry points:

```sh
python3 DataAnalysis/analyze_sample.py --list                        # standard library only, no install needed
python3 DataAnalysis/analyze_sample.py                               # default sample -> DataAnalysis/output/   (make analyze-sample)
python3 DataAnalysis/analyze_sample.py --sample container_memory_usage_bytes_pod
.venv/bin/python -m pytest DataAnalysis                              # offline tests                            (make analysis-test)
```

What the tool does and does not do:

- [`analyze_sample.py`](./analyze_sample.py) reads one file from `dataset/` by name (URLs and paths are rejected), validates the `{namespace: [series]}` layout and writes one CSV row per series: sample count, first/last time (UTC), min/max/mean, number of recording gaps (consecutive samples more than 120 s apart) and the longest gap. Values that are `NaN`/`Inf`/unparsable are dropped and counted, never kept.
- **Units are taken from the metric, not guessed.** CPU values in the committed files are a 1-minute *rate* in CPU cores (not raw counters and not a percentage); network values are bytes per second; memory is a byte gauge. No percent utilization is computed, because the number of CPUs a series could use is not recorded in the data. `counter_to_rate()` (reset-aware) exists for anyone who pulls *raw* cumulative counters; a warning is printed if a "rate" file looks like a raw counter.
- Nothing is smoothed, interpolated, resampled or summed across series. Gaps are reported, not filled.
- The CSV is deterministic: the test suite pins its SHA-256 for the default sample, and the tests run with network access blocked. [`plot_namespace_cpu.py`](./plot_namespace_cpu.py) (existing script) is exercised the same way; the PNG itself is only an illustration and is not byte-pinned.
- Schema, labels, units, the 2024-04-20 time axis, the ~1.5 h recording gap and everything that is **unknown/unverified** about the experiment (workload, node sizes, scrape interval, versions) are documented in the [sample dataset guide](./dataset/README.md); this README does not repeat them.

### Notebooks do not run offline

[`DataAnaysis.ipynb`](./DataAnaysis.ipynb) and [`HPA.ipynb`](./HPA.ipynb) are the original, executed lab notebooks. They are **not** part of the offline environment and are not executed by `run-analysis-offline.sh`:

- Both query a live Prometheus at `http://192.168.56.10:30090` (the Vagrant NodePort) and `HPA.ipynb` also calls `kubectl`; the data behind them died with that cluster.
- `DataAnaysis.ipynb` reads `../data_json/20240420/json/...`, a folder that is not in the repository (it is git-ignored), through [`helper.py`](./helper.py); it also uses `%reset -f`.
- Their stored outputs are historical lab output and are left untouched; do not re-save them from a different environment.

## What is in this folder

| Path | Needs | What it is |
|---|---|---|
| [`dataset/`](./dataset/README.md) | nothing | Committed JSON samples from one recording (2024-04-20). Data dictionary and provenance limits are in its README. |
| [`analyze_sample.py`](./analyze_sample.py), [`tests/`](./tests/), `pytest.ini` | nothing (standard library; tests need `pytest`) | Offline per-series summary CSV of one committed sample, plus its tests. See [Offline analysis](#offline-analysis-no-cluster-no-network). |
| [`requirements-offline.txt`](./requirements-offline.txt) | pip | Pinned, tested environment for the offline analysis only. |
| *(no pinned file)* | pip, by hand | The live-Prometheus script and the notebooks (`backup.py`, `helper.py`, the `.ipynb` files) need `prometheus-api-client`, `pandas`, `IPython` and similar packages that are deliberately **not** in `requirements-offline.txt`. Install them yourself into a separate virtual environment; this folder pins no versions for them. |
| `plot_namespace_cpu.py` | matplotlib | Offline: plots the namespace CPU series in `dataset/` to a PNG (`--out`). |
| `backup.py` | a live Prometheus (`--prometheus-url`) | Exports the last `--days` of every metric to `data_json/<YYYYMMDD>/*.json.gz` at the repository root (git-ignored). Contacts nothing unless the URL is given. |
| `RH.py` | a live cluster (`kubectl`) | Deletes one pod and reports the seconds from the delete to the replacement pod's `Started` event. Dry run unless `--yes` is given. |
| `rehealing.py` | a live cluster (`kubectl`) | Older variant of `RH.py`, superseded (its docstring explains why). Dry run unless `--yes` is given. |
| `helper.py` | pandas, IPython | Helper functions imported by the notebooks (`import helper as hp`). `read_json()` expects a list, so it does not read the `{namespace: [...]}` files in `dataset/`. |
| `DataAnaysis.ipynb` | a live Prometheus at `192.168.56.10:30090` | The export recipe that wrote `dataset/` (the file name is misspelt, but other docs link to it, so it is kept). Plot cells 25-27 run offline from `dataset/`. |
| `HPA.ipynb` | a live Prometheus and a cluster | HPA/VPA experiment notebook. Cell 22 runs `kubectl delete pod` on a hard-coded pod name. Re-running it in place overwrites the `*.pdf` figures and appends to `pod_recreation_times.csv`. |
| `CPU.txt`, `prometheus_metrics.txt`, `pod_recreation_times.csv`, `*.pdf` | nothing | Outputs saved by earlier runs (metric names, a CSV log, figures). The scripts here do not regenerate them. |

## Live Prometheus queries (needs a running cluster)

> These scripts, snippets and notebooks need a reachable Prometheus or cluster plus packages (`prometheus-api-client`, `pandas`, `requests`, `IPython`, ...) that are deliberately **not** in the pinned offline environment and have no pinned file in this folder. The scripts were hardened to be dry-run or explicit-target by default; none was re-run against a cluster for this documentation.

- `backup.py` needs `--prometheus-url`, for example `--prometheus-url http://<host>:30090`. There is no default server.
- `RH.py` and `rehealing.py` act on whatever cluster the current `kubectl` context points to. Check it with `kubectl config current-context` first. `--namespace` and `--prefix` default to `ros` and `ros-`. Run without `--yes` to see which pod would be deleted, then add `--yes` to delete it and measure.

## Extracting data from Prometheus with Python

Prometheus, an open-source systems monitoring and alerting toolkit, uses a time series database (TSDB) to store all its data. This data can be queried using PromQL, Prometheus's built-in query language, but sometimes you may find it useful to extract this data and use it with other tools such as Python for further analysis.

To interact with Prometheus using Python, we can use the `prometheus-api-client` library, which provides a set of tools to handle the metrics data stored in a Prometheus TSDB.

Here's a basic example of how to use this library (it needs a reachable Prometheus, so it is not run by this repository):

```python
import datetime

from prometheus_api_client import PrometheusConnect

# Create a connection to the Prometheus server (no trailing brackets around the URL)
prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

# Get a list of all the metrics that the Prometheus server has
all_metrics = prom.all_metrics()

# Choose a specific metric
metric = all_metrics[0]

# Get the metric data. The times must be datetime objects, not strings.
data = prom.get_metric_range_data(
    metric_name=metric,
    start_time=datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc),
    end_time=datetime.datetime(2021, 1, 2, tzinfo=datetime.timezone.utc),
)
```

In the above example, we first establish a connection to the Prometheus server. We then fetch a list of all available metrics, and choose one for further querying. Lastly, we fetch the data for this metric in a specific time range. The result is a list of series; each series has a `metric` label set and a `values` list of `[unix_timestamp, "value"]` pairs.

Once you have the data, you can proceed to analyze it as per your needs. For instance, you could use the Pandas library to explore the data and Matplotlib to visualize it. Here's a simple example of how to do this:

```python
import matplotlib.pyplot as plt
import pandas as pd

# Convert the first series to a Pandas DataFrame
df = pd.DataFrame(data[0]["values"], columns=["timestamp", "value"])
df["value"] = df["value"].astype(float)
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

# Plot the data
plt.plot(df["timestamp"], df["value"])
plt.show()
```

In this example, we convert the first series into a Pandas DataFrame, which then allows us to use the powerful data manipulation capabilities of Pandas to analyze the data. We then create a simple plot of the data using Matplotlib.

Note: The above examples are simplistic and meant only to illustrate the basic process. In a real use-case, you would likely need to deal with more complex queries and data transformations.
