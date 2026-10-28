import json
import gzip
import os
from prometheus_api_client import PrometheusConnect
from datetime import datetime, timedelta

# Setup connection
prom = PrometheusConnect(url="http://192.168.56.10:30090", disable_ssl=True)

# Fetch all metric names
all_metrics = prom.all_metrics()

# Define a starting point for data collection
start_time = datetime.now() - timedelta(days=1)  # Example: 5 years ago
end_time = datetime.now()  # Current time
step = '20s'  # Step size

# if there is no path and dir is not exist will create it recursively
path = f"../data_json/{datetime.now().strftime('%Y%m%d')}/"

os.makedirs(path, exist_ok=True)

for metric in all_metrics:
    # Perform a range query for each metric
    result_range = prom.custom_query_range(
        query=metric,
        start_time=start_time,
        end_time=end_time,
        step=step
    )

    # Define file path with .gz extension
    file_path = path + f'{metric.replace("/", "_").replace(":","_")}.json.gz'  # Replace '/' with '_' to avoid path issues

    # Write data to a gzipped JSON file
    with gzip.open(file_path, 'wt', encoding='utf-8') as file:
        json.dump(result_range
