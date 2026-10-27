# Data Analysis

> **No cluster?** The JSON samples in [`dataset/`](./dataset/README.md) can be inspected offline with plain Python 3; see the [sample dataset guide](./dataset/README.md) for the data dictionary, provenance limits and one optional plot.
In this section, we discuss how to extract data from Prometheus TSDB databases using Python, and provide some examples of data analysis.

Prometheus, an open-source systems monitoring and alerting toolkit, uses a time series database (TSDB) to store all its data. This data can be queried using PromQL, Prometheus's built-in query language, but sometimes you may find it useful to extract this data and use it with other tools such as Python for further analysis.

To interact with Prometheus using Python, we can use the 'prometheus-api-client' library, which provides a set of tools to handle the metrics data stored in a Prometheus TSDB.

Here's a basic example of how to use this library:

```python
from prometheus_api_client import PrometheusConnect

# Create a connection to the Prometheus server
prom = PrometheusConnect(url="<http://localhost:9090>", disable_ssl=True)

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