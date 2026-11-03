"""Measure how long Kubernetes takes to re-heal (replace) a deleted pod.

Deletes one pod whose name starts with --prefix in --namespace, then reports the
seconds from the delete request to the replacement pod's "Started" event.

DESTRUCTIVE: without --yes the script only prints the pod it would delete.
The kubectl commands use the current kubectl context (check `kubectl config
current-context` first). Clocks: the delete time is taken from this machine's
UTC clock, the event times come from the API server, so the result is only as
accurate as the clock sync between them.

Example (dry run first, then the real measurement):
    python3 DataAnalysis/RH.py --namespace ros --prefix ros-
    python3 DataAnalysis/RH.py --namespace ros --prefix ros- --yes
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone


def get_k8s_events(namespace):
    """
    Fetch Kubernetes events for a namespace and return them as JSON.
    """
    result = subprocess.run(
        ["kubectl", "get", "events", "-n", namespace, "-o", "json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def event_time(event):
    """Events may carry lastTimestamp (core/v1) or only eventTime (events.k8s.io)."""
    return event.get("lastTimestamp") or event.get("eventTime")


def find_rehealing_timestamps(events, new_pod_name):
    """
    Find timestamps for new pod lifecycle events by matching the new pod name.
    """
    running_time = None

    for event in events['items']:
        involved_object = event['involvedObject']
        if involved_object['name'] == new_pod_name:  # Match exact new pod name
            if event['reason'] == "Started":
                running_time = event_time(event)

    return running_time


def calculate_time_difference(start, end):
    """
    Calculate time difference between two ISO timestamps.
    """
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    return (end_dt - start_dt).total_seconds()


def list_pods(namespace):
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)['items']


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--namespace", default="ros", help="namespace (default: %(default)s)")
    parser.add_argument("--prefix", default="ros-", help="pod name prefix (default: %(default)s)")
    parser.add_argument(
        "--yes", action="store_true",
        help="really delete the pod; without it only the pod that would be deleted is shown",
    )
    parser.add_argument(
        "--wait-timeout", type=float, default=120.0,
        help="seconds to wait for the replacement pod to appear (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    namespace, pod_prefix = args.namespace, args.prefix

    # Step 1: Get the current pod name dynamically
    print("Fetching current pod information...")
    pods = list_pods(namespace)
    if not pods:
        print(f"No pods found with prefix {pod_prefix} in namespace {namespace}.")
        return 1

    current_pod_name = next((pod['metadata']['name'] for pod in pods if pod['metadata']['name'].startswith(pod_prefix)), None)

    if not current_pod_name:
        print(f"Pod with prefix {pod_prefix} not found in namespace {namespace}.")
        return 1

    print(f"Found current pod: {current_pod_name}")

    if not args.yes:
        print(f"Dry run: would delete pod {current_pod_name} in namespace {namespace}. "
              "Re-run with --yes to delete it and measure.")
        return 0

    # Step 2: Delete the pod
    print("Deleting current pod...")
    delete_time = datetime.now(timezone.utc).isoformat()  # Record deletion time
    subprocess.run(["kubectl", "delete", "pod", current_pod_name, "-n", namespace], check=True)
    time.sleep(5)  # Allow time for Kubernetes to generate a new pod

    # Step 3: Wait for the replacement pod (bounded by --wait-timeout)
    print("Fetching new pod information...")
    new_pod_name = None
    deadline = time.monotonic() + args.wait_timeout
    while not new_pod_name:
        if time.monotonic() > deadline:
            print(f"No replacement pod appeared within {args.wait_timeout:.0f} s.")
            return 1
        pods = list_pods(namespace)
        new_pod_name = next((pod['metadata']['name'] for pod in pods if pod['metadata']['name'].startswith(pod_prefix) and pod['metadata']['name'] != current_pod_name), None)
        if not new_pod_name:
            time.sleep(1)

    print(f"New pod created: {new_pod_name}")

    # Step 4: Fetch events and find new pod Started timestamp
    print("Fetching Kubernetes events...")
    events = get_k8s_events(namespace)
    running_time = find_rehealing_timestamps(events, new_pod_name)

    if running_time:
        # Step 5: Calculate rehealing time
        rehealing_time = calculate_time_difference(delete_time, running_time)
        print(f"Pod rehealing time: {rehealing_time:.2f} seconds")
        return 0

    print("Could not find required events for the new pod. Ensure the pod is being recreated correctly.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
