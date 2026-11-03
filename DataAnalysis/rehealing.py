"""Delete one pod and report the Killing -> Started interval of that same pod name.

SUPERSEDED by RH.py, which measures delete -> replacement pod "Started" and is
the script the measurements use. This one matches events by the *deleted* pod's
name, and a pod's "Started" event is always recorded before its "Killing" event,
so the value reported here is <= 0 and is not a re-healing time. Kept for
reference only.

DESTRUCTIVE: without --yes the script only prints the pod it would delete.
Example:
    python3 DataAnalysis/rehealing.py --namespace ros --prefix ros-          # dry run
    python3 DataAnalysis/rehealing.py --namespace ros --prefix ros- --yes
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


def find_event_timestamps(events, pod_name):
    """
    Find timestamps for pod lifecycle events by matching pod name exactly.
    """
    killing_time = None
    running_time = None

    for event in events['items']:
        involved_object = event['involvedObject']
        if involved_object['name'] == pod_name:  # Match by exact pod name

            if event['reason'] == "Killing":
                killing_time = event.get('lastTimestamp') or event.get('eventTime')

            if event['reason'] == "Started":
                running_time = event.get('lastTimestamp') or event.get('eventTime')

    return killing_time, running_time


def calculate_time_difference(start, end):
    """
    Calculate time difference between two ISO timestamps.
    """
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    return (end_dt - start_dt).total_seconds()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--namespace", default="ros", help="namespace (default: %(default)s)")
    parser.add_argument("--prefix", default="ros-", help="pod name prefix (default: %(default)s)")
    parser.add_argument(
        "--yes", action="store_true",
        help="really delete the pod; without it only the pod that would be deleted is shown",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    namespace, pod_prefix = args.namespace, args.prefix

    # Step 1: Get the exact pod name dynamically
    print("Fetching pod information...")
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
        capture_output=True, text=True, check=True,
    )
    pods = json.loads(result.stdout)['items']
    if not pods:
        print(f"No pods found with prefix {pod_prefix} in namespace {namespace}.")
        return 1

    pod_name = next((pod['metadata']['name'] for pod in pods if pod['metadata']['name'].startswith(pod_prefix)), None)

    if not pod_name:
        print(f"Pod with prefix {pod_prefix} not found in namespace {namespace}.")
        return 1

    print(f"Found pod: {pod_name}")

    if not args.yes:
        print(f"Dry run: would delete pod {pod_name} in namespace {namespace}. "
              "Re-run with --yes to delete it.")
        return 0

    # Step 2: Delete the pod
    print("Deleting pod...")
    subprocess.run(["kubectl", "delete", "pod", pod_name, "-n", namespace], check=True)
    time.sleep(3)  # Allow time for Kubernetes to generate events

    # Step 3: Fetch events and find timestamps
    print("Fetching Kubernetes events...")
    events = get_k8s_events(namespace)
    killing_time, running_time = find_event_timestamps(events, pod_name)

    if killing_time and running_time:
        # Step 4: Calculate recreation time (see the SUPERSEDED note above)
        recreation_time = calculate_time_difference(killing_time, running_time)
        print(f"Pod recreation time: {recreation_time:.2f} seconds")
        return 0

    print("Could not find required events. Ensure the pod is recreated correctly.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
