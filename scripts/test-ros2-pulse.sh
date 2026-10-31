#!/usr/bin/env bash
# Opt-in ros2_pulse check (issue #52). Run inside the built ROS 2 Jazzy container; no
# Kubernetes cluster needed. Preloads the probe into a talker and a listener in ONE container,
# gates /chatter publish and callback rates with pulse-check, then reads the same windows back
# through pulse-export's /metrics on 127.0.0.1.
# Usage: docker run --rm -i --user 1000:1000 ros-jazzy-lab:local bash -s < scripts/test-ros2-pulse.sh
# This is a same-container check, not a Kubernetes, multi-pod or cross-worker DDS test.
# ROS setup scripts rely on optional environment variables. Source before nounset.
set -eo pipefail

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "${ROS_DISTRO:-}" == "jazzy" ]] || fail "ROS_DISTRO must be jazzy (got ${ROS_DISTRO:-unset})"
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

probe_lib=/opt/ros/jazzy/lib/libros2_pulse.so
pulse_check=/opt/ros/jazzy/lib/ros2_pulse/pulse-check
pulse_export=/opt/pulse-export/bin/pulse-export
demo_bin=/opt/ros/jazzy/lib/demo_nodes_cpp
period=5.0
min_windows=3
metrics_port=9464

# Instrumentation is opt-in: the image itself must not preload anything.
[[ -z "${LD_PRELOAD:-}" ]] || fail "image sets LD_PRELOAD by default (${LD_PRELOAD})"
[[ -f "$probe_lib" ]] || fail "probe library missing: $probe_lib"
[[ -x "$pulse_check" ]] || fail "pulse-check missing: $pulse_check"
[[ -x "$pulse_export" ]] || fail "pulse-export missing: $pulse_export"
# shellcheck disable=SC2016
dpkg-query -W -f='ros2_pulse apt package: ${Package} ${Version}\n' ros-jazzy-ros2-pulse
/opt/pulse-export/bin/python3 -c \
  'import importlib.metadata as m; print("pulse-export from ros2-pulse-top", m.version("ros2-pulse-top"))'

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"
export RCUTILS_LOGGING_BUFFERED_STREAM=0
tmpdir="$(mktemp -d)"
log_dir="$tmpdir/ros2_pulse"
mkdir -p "$log_dir"
listener_pid=""
talker_pid=""
export_pid=""

cleanup() {
  local pid
  for pid in "$export_pid" "$talker_pid" "$listener_pid"; do
    if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null || true; fi
  done
  for pid in "$export_pid" "$talker_pid" "$listener_pid"; do
    if [[ -n "$pid" ]]; then wait "$pid" 2>/dev/null || true; fi
  done
  rm -rf "$tmpdir"
}
trap cleanup EXIT

dump_and_fail() {
  local f
  for f in "$tmpdir"/*.out "$log_dir"/*.jsonl; do
    [[ -f "$f" ]] || continue
    printf -- '--- %s ---\n' "${f#"$tmpdir"/}" >&2
    cat "$f" >&2 || true
  done
  fail "$*"
}

count_windows() {
  if [[ -f "$1" ]]; then awk '/^\{/ { n++ } END { print n + 0 }' "$1"; else echo 0; fi
}

# Every published /chatter message must show up on both sides of the last full window.
cat > "$tmpdir/expected.yaml" <<'EOF'
topics:
  /chatter: {min_hz: 0.5, side: pub}
  /chatter: {min_hz: 0.5, side: recv}
nodes: [/talker, /listener]
EOF

# The probe variables go on the two ROS processes only, not on this shell or the exporter.
probe_env=(
  "LD_PRELOAD=$probe_lib"
  "ROS_TOPIC_STATS_FORMAT=jsonl"
  "ROS_TOPIC_STATISTICS_PUBLISH_PERIOD=$period"
)
env "${probe_env[@]}" "ROS_TOPIC_STATS_OUTPUT_FILE=$log_dir/listener.jsonl" \
  "$demo_bin/listener" > "$tmpdir/listener.out" 2>&1 &
listener_pid=$!
env "${probe_env[@]}" "ROS_TOPIC_STATS_OUTPUT_FILE=$log_dir/talker.jsonl" \
  "$demo_bin/talker" > "$tmpdir/talker.out" 2>&1 &
talker_pid=$!

talker_windows=0
listener_windows=0
for ((attempt = 1; attempt <= 60; attempt++)); do
  talker_windows="$(count_windows "$log_dir/talker.jsonl")"
  listener_windows="$(count_windows "$log_dir/listener.jsonl")"
  if (( talker_windows >= min_windows && listener_windows >= min_windows )); then
    break
  fi
  if ! kill -0 "$listener_pid" 2>/dev/null || ! kill -0 "$talker_pid" 2>/dev/null; then
    dump_and_fail "a probed ROS 2 demo process exited early"
  fi
  sleep 1
done
(( talker_windows >= min_windows && listener_windows >= min_windows )) ||
  dump_and_fail "expected ${min_windows} probe windows per process within 60 s" \
    "(talker ${talker_windows}, listener ${listener_windows})"

grep -Fq '[ros2_pulse] active' "$tmpdir/talker.out" || dump_and_fail "probe banner missing in talker output"
grep -Fq '[ros2_pulse] active' "$tmpdir/listener.out" || dump_and_fail "probe banner missing in listener output"
grep -Fq 'I heard:' "$tmpdir/listener.out" || dump_and_fail "listener received no message"

printf -- '--- last talker window ---\n'
tail -n 1 "$log_dir/talker.jsonl"
printf -- '--- last listener window ---\n'
tail -n 1 "$log_dir/listener.jsonl"

# Both processes are still running, so the last window is a full one (not the exit sliver).
if ! "$pulse_check" --spec "$tmpdir/expected.yaml" "$log_dir/talker.jsonl" "$log_dir/listener.jsonl"; then
  dump_and_fail "pulse-check: /chatter publish or callback rate below 0.5 Hz, or a node missing"
fi
printf 'PASS: pulse-check saw /chatter published and received at >= 0.5 Hz in one container.\n'

"$pulse_export" --bind 127.0.0.1 --port "$metrics_port" "$log_dir/*.jsonl" \
  > "$tmpdir/pulse-export.out" 2>&1 &
export_pid=$!

positive_series() {
  # True if the scrape has a $1{...topic="/chatter"...} sample above 0.
  awk -v name="$1{" 'index($1, name) == 1 && index($1, "topic=\"/chatter\"") && $2 + 0 > 0 { ok = 1 }
    END { exit !ok }' "$tmpdir/metrics.txt"
}

for ((attempt = 1; attempt <= 20; attempt++)); do
  if python3 - "$metrics_port" > "$tmpdir/metrics.txt" 2>/dev/null <<'PY'
import sys
import urllib.request

with urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/metrics", timeout=2) as resp:
    sys.stdout.write(resp.read().decode())
PY
  then
    if positive_series ros2_pulse_topic_publish_rate_hertz &&
       positive_series ros2_pulse_topic_receive_rate_hertz; then
      grep -F 'topic="/chatter"' "$tmpdir/metrics.txt"
      printf 'PASS: pulse-export served /chatter publish and receive rates on /metrics.\n'
      exit 0
    fi
  fi
  if ! kill -0 "$export_pid" 2>/dev/null; then
    dump_and_fail "pulse-export exited"
  fi
  sleep 1
done

[[ -f "$tmpdir/metrics.txt" ]] && cat "$tmpdir/metrics.txt" >&2
dump_and_fail "pulse-export /metrics had no positive /chatter publish and receive series within 20 s"
