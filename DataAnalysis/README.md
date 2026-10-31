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

## Live Prometheus queries (needs a running cluster)

> These snippets and the notebooks need a reachable Prometheus plus packages (`prometheus-api-client`, `pandas`, `requests`, ...) that are deliberately **not** in the pinned offline environment, and they were not re-run for this documentation.

In this section, we discuss how to extract data from Prometheus TSDB databases using Python, and provide some examples of data analysis.

Prometheus, an open-source systems monitoring and alerting toolkit, uses a time series database (TSDB) to store all its data. This data can be queried using PromQL, Prometheus's built-in query language, but sometimes you may find it useful to extract this data and use it with other tools such as Python for further analysis.

To interact with Prometheus using Python, we can use the 'prometheus-api-client' library, which provides a set of tools to handle the metrics data stored in a Prometheus TSDB.

Here's a basic example of how to use this library:

```python
from prometheus_api_client import PrometheusConnect

# Create a connection to the Prometheus server
prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

# Get a list of all the metrics that the Prometheus server has
all_metrics = prom.all_metrics()

# Choose a specific metric
metric = all_metrics[0]

# Get the metric data
data = prom.get_metric_range_data(
    metric_name=metric,
    start_time="2021-01-01T00:00:00Z",
    end_time="2021-01-02T00:00:00Z",
)

```

In the above example, we first establish a connection to the Prometheus server. We then fetch a list of all available metrics, and choose one for further querying. Lastly, we fetch the data for this metric in a specific time range.

Once you have the data, you can proceed to analyze it as per your needs. For instance, you could use the Pandas library to explore the data and Matplotlib to visualize it. Here's a simple example of how to do this:

```python
import pandas as pd
import matplotlib.pyplot as plt

# Convert the data to a Pandas DataFrame
df = pd.DataFrame(data)

# Plot the data
plt.plot(df['value'])
plt.show()

```

In this example, we convert the input data into a Pandas DataFrame, which then allows us to use the powerful data manipulation capabilities of Pandas to analyze the data. We then create a simple plot of the data using Matplotlib.

Note: The above examples are simplistic and meant only to illustrate the basic process. In a real use-case, you would likely need to deal with more complex queries and data transformations.
