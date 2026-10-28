# Sample monitoring datasets (offline)

This folder holds JSON files exported from a Prometheus server that monitored the Kubernetes cluster of this lab. You can inspect them with plain Python 3 on any laptop: **no cluster, Vagrant, Prometheus or cloud account is needed**.

Back to the [DataAnalysis README](../README.md) (how the data was extracted from Prometheus) and the broader benchmark plan in [issue #18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18).

> **What this data is, and is not.** These are *historical sample files* from a single recording on 2024-04-20. They are **not** a live benchmark, not a reproducible experiment, and they say nothing about the newer Jazzy image in [`ROS2/`](../../ROS2/). Do not quote them as performance results.

## Files

| File | Namespaces with data | Series | Samples |
|---|---|---|---|
| `container_cpu_usage_seconds_total.json` | default, kube-system, kubernetes-dashboard, prometheus, ros | 1 per namespace | 2075 |
| `container_cpu_usage_seconds_total_pod.json` | same | 3 / 13 / 2 / 8 / 4 (one per pod) | 13851 |
| `container_memory_usage_bytes.json` | same | 1 per namespace | 2122 |
| `container_memory_usage_bytes_pod.json` | same | 3 / 13 / 2 / 8 / 4 | 14150 |
| `container_network_receive_bytes_total.json` | same | 1 per namespace | 2055 |
| `container_network_receive_bytes_total_pod.json` | same | 3 / 13 / 2 / 8 / 4 | 12389 |
| `container_network_transmit_bytes_total.json` | same | 1 per namespace | 2055 |
| `container_network_transmit_bytes_total_pod.json` | same | 3 / 13 / 2 / 8 / 4 | 12389 |
| `container_fs_usage_bytes.json`, `container_fs_usage_bytes_pod.json` | **none: every namespace is an empty list** | 0 | 0 |

(Per-pod series order above is default / kube-system / kubernetes-dashboard / prometheus / ros. Counts were computed from the committed files with Python's `json` module.)

## Data dictionary

All counts and ranges below were read from the committed files; items that could not be established are marked **unknown/unverified**.

### Structure

Every file is a JSON object **keyed by Kubernetes namespace**. The seven namespace keys are always `default`, `kube-node-lease`, `kube-public`, `kube-system`, `kubernetes-dashboard`, `prometheus`, `ros`. Each value is a list of series (empty list = no data; this is always the case for `kube-node-lease` and `kube-public`).

```json
{
  "kube-system": [
    { "metric": {"pod": "etcd-controlplane"},
      "values": [[1713596820, "0.306..."], [1713596880, "0.313..."]] }
  ]
}
```

| Field | Meaning (as observed) |
|---|---|
| top-level key | Kubernetes namespace name. |
| `metric` | Prometheus label set of the series. `{}` (empty) in the namespace-level files; `{"pod": "<pod name>"}` in the `*_pod.json` files. No other label occurs (no `node`, `container`, `instance`). |
| `values` | List of `[timestamp, value]` pairs. `timestamp` is a JSON **integer**: Unix epoch seconds (UTC). `value` is a JSON **string** holding a decimal number; convert with `float()`. No missing/unparsable values were found. |

This is the layout of the dictionary returned per namespace by `prometheus-api-client`'s `custom_query_range`, wrapped in one `{namespace: result}` object by the export code (see Provenance). It is **not** a plain list, so `read_json()` in [`../helper.py`](../helper.py), which does `data[0]`, does not read these files unchanged (judged from reading the code; not run).

### Metrics, units and meaning

The file names reuse cAdvisor metric names, but the notebook queries wrap them, so the stored numbers are **not** the raw cumulative counters. The queries below are the ones in the committed notebook [`../DataAnaysis.ipynb`](../DataAnaysis.ipynb) that write these file names; the files themselves do not record their query, so this mapping is *inferred* (it is consistent with the observed value ranges).

| File prefix | Inferred PromQL (`NS` = namespace) | Unit of `value` | Observed range |
|---|---|---|---|
| `container_cpu_usage_seconds_total` | `sum(rate(container_cpu_usage_seconds_total{namespace="NS"}[1m]))` (`... by (pod)` for `_pod`) | CPU cores (CPU-seconds per second) | namespace files 0 to 1.03; pod files 0 to 0.97 |
| `container_memory_usage_bytes` | `sum(container_memory_usage_bytes{namespace="NS"})` (`... by (pod)` for `_pod`) | bytes (gauge, no rate) | namespace files 2,289,664 to 3,605,028,864; pod files 212,992 to 2,269,954,048 |
| `container_network_receive_bytes_total` | `sum(rate(container_network_receive_bytes_total{namespace="NS"}[1m]))` (`... by (pod)` for `_pod`) | bytes per second | namespace files 0 to 3,111,307; pod files 0 to 664,392 |
| `container_network_transmit_bytes_total` | same pattern with `..._transmit_...` | bytes per second | namespace files 0 to 3,433,716; pod files 0 to 727,839 |

Consistency check performed: at one timestamp (`1713608520` for CPU, `1713608220` for memory) the `kube-system` namespace value equals the sum of the 13 `kube-system` pod values to floating-point precision. That supports the "namespace = sum over pods" reading but was checked only at those single timestamps.

### Time axis

- All files cover **2024-04-20**, UTC. Earliest sample `07:06` (memory) / `07:07` (others), latest `17:25` (memory) / `17:20` (others).
- Nominal sampling interval is **60 s** (the `step` of the query). Per-series spacing is usually 60 s; some pod series show 120 s steps.
- **There is a recording gap** of roughly 1 h 36 min: no samples between about `08:00` and `09:36` UTC (for example `kube-system` CPU jumps from 08:00 to 09:36). The cause is **unknown/unverified**. Do not interpolate across it.
- `default` has only 5 (CPU, network) or 11 (memory) samples, i.e. a few minutes around `07:06`-`07:16` UTC. Its three pods (`ros-...-fx2vq`, `-kmztg`, `-mkn49`) appear only in that window, while the `ros` namespace holds different pod names (`ros-...-866bf`, `-knggl`, `-m6d94`, `-tds5p`). Why is **unknown/unverified** (the notebook query window was requested for the whole day, in a timezone it does not state).

### Labels

- `pod`: Kubernetes pod name including its generated suffix, for example `coredns-76f75df574-2ptm6`. These change whenever a pod is recreated, so they are not stable identifiers.
- Which **node** a pod ran on, the container, the Kubernetes/Prometheus versions, and the exact scrape interval are **not** in the data: **unknown/unverified**.

## Provenance and reproducibility limits

- **Source:** exported by the cells of [`../DataAnaysis.ipynb`](../DataAnaysis.ipynb) from a Prometheus server at `192.168.56.10:30090`, the NodePort address of the Vagrant lab cluster (see [`../../MonitoringSystem/`](../../MonitoringSystem/)). The notebook queried 2024-04-20 00:00:00 to 23:59:59 (naive local time) with `step='60s'` and `rate(...[1m])` and saved the result with `json.dump`. The repository history shows the files first added in commit `f112674` (2024-04-27, "data analysis"); a later commit (`eb42f5d`) changed only file modes, not content.
- **Not recorded anywhere in the repo (unknown/unverified):** which workload was running, what the `ros` pods were doing (the repository's `ros_dep_*.yaml` run stress-ng, but nothing links that to this recording), cluster size/VM resources, Kubernetes/Prometheus/ROS versions, whether any fault or scaling test was in progress, and the cause of the gap.
- **Cannot be regenerated by a reader:** the source Prometheus data is gone with that cluster. The notebook is only an export recipe; rerunning it on a new cluster gives *different* numbers.
- **Memory caveat (unverified):** the memory query sums `container_memory_usage_bytes` without filtering on the `container` label. cAdvisor can also export pod-level aggregate series, in which case a plain `sum` may count the same memory more than once. Whether that happens in these files is not verified, so treat absolute memory values with caution.
- **Files with no data:** the two `container_fs_usage_bytes*.json` files contain only empty lists.
- The numbers have not been modified by this documentation.

## Inspect one file with the Python standard library

From the repository root (Python 3, no packages to install):

```python
import json
import sys
from datetime import datetime, timezone

path = sys.argv[1] if len(sys.argv) > 1 else "DataAnalysis/dataset/container_cpu_usage_seconds_total.json"

with open(path, encoding="utf-8") as fh:
    data = json.load(fh)  # top level: {namespace: [series, ...]}

print(f"file: {path}")
for namespace, series_list in data.items():
    n_points = sum(len(s["values"]) for s in series_list)
    line = f"{namespace:22s} series={len(series_list):2d} points={n_points:5d}"
    if n_points:
        stamps = [t for s in series_list for t, _ in s["values"]]
        nums = [float(v) for s in series_list for _, v in s["values"]]  # values are strings
        first = datetime.fromtimestamp(min(stamps), timezone.utc).strftime("%Y-%m-%d %H:%M")
        last = datetime.fromtimestamp(max(stamps), timezone.utc).strftime("%Y-%m-%d %H:%M")
        labels = sorted({k for s in series_list for k in s["metric"]})
        line += f" utc={first}..{last} min={min(nums):g} max={max(nums):g} labels={labels}"
    print(line)
```

Save it as, say, `inspect.py` outside the repo (or paste it into `python3`) and pass any other `.json` path from this folder as the first argument. Output observed for the default file:

```text
file: DataAnalysis/dataset/container_cpu_usage_seconds_total.json
default                series= 1 points=    5 utc=2024-04-20 07:07..2024-04-20 07:11 min=0 max=0 labels=[]
kube-node-lease        series= 0 points=    0
kube-public            series= 0 points=    0
kube-system            series= 1 points=  519 utc=2024-04-20 07:07..2024-04-20 17:20 min=0.0139382 max=0.541429 labels=[]
kubernetes-dashboard   series= 1 points=  518 utc=2024-04-20 07:07..2024-04-20 17:20 min=0.000292344 max=0.0878309 labels=[]
prometheus             series= 1 points=  519 utc=2024-04-20 07:07..2024-04-20 17:20 min=0.000136309 max=1.03443 labels=[]
ros                    series= 1 points=  514 utc=2024-04-20 07:11..2024-04-20 17:20 min=0 max=0.0399005 labels=[]
```

## One simple plot (optional, needs matplotlib)

[`../plot_namespace_cpu.py`](../plot_namespace_cpu.py) draws the namespace-level CPU series for `kube-system`, `kubernetes-dashboard`, `prometheus` and `ros` from `container_cpu_usage_seconds_total.json`.

- Unit: CPU cores (1-minute rate, summed per namespace); x-axis in UTC.
- No smoothing, resampling or cross-namespace summing. The line is deliberately **broken at the recording gap** rather than drawn across it. `default` (5 samples) is left out to keep the plot readable.
- `matplotlib` is the only third-party dependency. It is not required for the inspection snippet above.

```sh
python3 -m venv .venv            # keep it out of the system Python (.venv is not tracked)
.venv/bin/pip install -r DataAnalysis/requirements-offline.txt   # pinned; matplotlib is the only one this plot needs
.venv/bin/python DataAnalysis/plot_namespace_cpu.py --out /tmp/namespace_cpu.png
```

Tested with Python 3.12.3, matplotlib 3.11.2 and numpy 2.5.4 (the pinned versions). The generated PNG is not committed; look at the plot only as an illustration of the file format, not as evidence about ROS 2 or Kubernetes performance. For a one-command offline run (summary CSVs, plot and tests) see the [offline analysis section](../README.md#offline-analysis-no-cluster-no-network).

## Related

- [`../README.md`](../README.md): extracting data from Prometheus with Python.
- [`../DataAnaysis.ipynb`](../DataAnaysis.ipynb), [`../HPA.ipynb`](../HPA.ipynb): the original (heavy, cluster-dependent) notebooks.
- [Issue #18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18): broader benchmark plan.
