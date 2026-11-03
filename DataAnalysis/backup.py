#!/usr/bin/env python3
"""Back up the last N days of every metric from a live Prometheus to gzipped JSON.

This is the only script here that needs a running Prometheus. Nothing is
contacted unless --prometheus-url is given (there is no default server).

Output: <out-dir>/<YYYYMMDD>/<metric>.json.gz
        default <out-dir> is <repo>/data_json (git-ignored).

Requires prometheus-api-client (see DataAnalysis/requirements.txt):
    python3 DataAnalysis/backup.py --prometheus-url http://<host>:30090
"""
import argparse
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

from prometheus_api_client import PrometheusConnect

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "data_json"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--prometheus-url",
        required=True,
        help="Prometheus base URL, e.g. http://192.168.56.10:30090",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="directory that receives a YYYYMMDD sub-folder (default: %(default)s)",
    )
    parser.add_argument(
        "--days", type=float, default=1.0, help="look-back window in days (default: %(default)s)"
    )
    parser.add_argument("--step", default="20s", help="query resolution (default: %(default)s)")
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="verify TLS certificates (off by default, as in the original script)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    prom = PrometheusConnect(url=args.prometheus_url, disable_ssl=not args.verify_tls)
    all_metrics = prom.all_metrics()

    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.days)
    out_path = args.out_dir / end_time.strftime("%Y%m%d")
    out_path.mkdir(parents=True, exist_ok=True)

    for metric in all_metrics:
        result_range = prom.custom_query_range(
            query=metric,
            start_time=start_time,
            end_time=end_time,
            step=args.step,
        )

        # '/' and ':' are not safe in file names
        file_path = out_path / f"{metric.replace('/', '_').replace(':', '_')}.json.gz"
        with gzip.open(file_path, "wt", encoding="utf-8") as file:
            json.dump(result_range, file, indent=4)

        print(f"Data for {metric} has been saved to {file_path}.")


if __name__ == "__main__":
    main()
