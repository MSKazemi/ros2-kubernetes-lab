# Data Analysis

> **No cluster?** The JSON samples in [`dataset/`](./dataset/README.md) can be inspected offline with plain Python 3; see the [sample dataset guide](./dataset/README.md) for the data dictionary, provenance limits and one optional plot.

In this section, we discuss how to extract data from Prometheus TSDB databases using Python, and provide some examples of data analysis.

## What is in this folder

| Path | Needs | What it is |
|---|---|---|
| [`dataset/`](./dataset/README.md) | nothing | Committed JSON samples from one recording (2024-04-20). Data dictionary and provenance limits are in its README. |
| `plot_namespace_cpu.py` | matplotlib | Offline: plots the namespace CPU series in `dataset/` to a PNG (`--out`). |
| `backup.py` | a live Prometheus (`--prometheus-url`) | Exports the last `--days` of every metric to `data_json/<YYYYMMDD>/*.json.gz` at the repository root (git-ignored). Contacts nothing unless the URL is given. |
| `RH.py` | a live cluster (`kubectl`) | Deletes one pod and reports the seconds from the delete to the replacement pod's `Started` event. Dry run unless `--yes` is given. |
| `rehealing.py` | a live cluster (`kubectl`) | Older variant of `RH.py`, superseded (its docstring explains why). Dry run unless `--yes` is given. |
| `helper.py` | pandas, IPython | Helper functions imported by the notebooks (`import helper as hp`). `read_json()` expects a list, so it does not read the `{namespace: [...]}` files in `dataset/`. |
| `DataAnaysis.ipynb` | a live Prometheus at `192.168.56.10:30090` | The export recipe that wrote `dataset/` (the file name is misspelt, but other docs link to it, so it is kept). Plot cells 25-27 run offline from `dataset/`. |
| `HPA.ipynb` | a live Prometheus and a cluster | HPA/VPA experiment notebook. Cell 22 runs `kubectl delete pod` on a hard-coded pod name. Re-running it in place overwrites the `*.pdf` figures and appends to `pod_recreation_times.csv`. |
| `CPU.txt`, `prometheus_metrics.txt`, `pod_recreation_times.csv`, `*.pdf` | nothing | Outputs saved by earlier runs (metric names, a CSV log, figures). The scripts here do not regenerate them. |

## Set up

Install into a virtual environment (`.venv` is git-ignored):

```sh
python3 -m venv .venv
.venv/bin/pip install -r DataAnalysis/requirements.txt
```

The versions in [`requirements.txt`](./requirements.txt) are the latest stable PyPI releases at the time of writing.

## Offline: plot the sample data

```sh
.venv/bin/python DataAnalysis/plot_namespace_cpu.py --out /tmp/namespace_cpu.png
```

## Live: only when you pass the target explicitly

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
