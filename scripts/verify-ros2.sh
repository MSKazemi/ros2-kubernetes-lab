#!/usr/bin/env bash
# Verify that the self-starting ROS 2 talker/listener demo (ROS2/jazzy/talker-listener.yaml)
# delivers messages ACROSS two different Kubernetes nodes. Issues #14 and #16.
#
# Checks, in order (each failure prints diagnostics and exits non-zero):
#   1. kubectl can reach the cluster and the Deployments finish rolling out;
#   2. the discovery-server, talker and listener pods are Ready;
#   3. the talker and listener pods are scheduled on DIFFERENT nodes;
#   4. the listener log shows "I heard: [Hello World: N]" lines that keep advancing and whose
#      latest N was really published by the talker pod.
#
# Usage:
#   scripts/verify-ros2.sh                  verify (exit 0 only if every check passes)
#   scripts/verify-ros2.sh --negative-test  prove the check can fail: break delivery on purpose
#                                           (listener pointed at a dead ROS_DISCOVERY_SERVER; pods
#                                           stay Ready and stay on different nodes), expect this
#                                           script to fail, restore, and verify again. Exit 0 only
#                                           if all three phases behaved as expected.
#   scripts/verify-ros2.sh --help
#
# Environment (all optional):
#   KUBE_CONTEXT     kubectl context   (default: kind-ros2k8s-demo)
#   ROS_NAMESPACE    namespace         (default: ros)
#   VERIFY_TIMEOUT   seconds allowed per waiting stage (default: 120)
#
# Exit codes: 0 verified | 1 verification failed | 2 usage or missing prerequisite
#
# This script reads pod state and container logs only. It never prints kubeconfig contents,
# tokens or Secret objects. A pass proves delivery for THIS cluster and CNI at the time it ran;
# it says nothing about other clusters.
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-kind-ros2k8s-demo}"
NS="${ROS_NAMESPACE:-ros}"
TIMEOUT="${VERIFY_TIMEOUT:-120}"
NEGATIVE_SERVER="127.0.0.1:11811" # nothing listens here: the listener cannot find the talker
MIN_NEW_MESSAGES=3      # the listener's counter must advance by at least this much

log() { printf '%s\n' "$*"; }
err() { printf 'ERROR: %s\n' "$*" >&2; }

kc() { kubectl --context "$KUBE_CONTEXT" --request-timeout=20s "$@"; }
kn() { kc -n "$NS" "$@"; }

usage() { sed -n '2,/^set -euo/p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'; }

# Print what a maintainer needs to debug a failure; read-only, no Secrets, no kubeconfig.
diagnostics() {
  {
    printf '\n===== DIAGNOSTICS (context=%s namespace=%s) =====\n' "$KUBE_CONTEXT" "$NS"
    printf '%s\n' '--- nodes'
    kc get nodes -L ros2k8s-demo/role -o wide || true
    printf '%s\n' '--- pods'
    kn get pods -o wide || true
    printf '%s\n' '--- recent events'
    kn get events --sort-by=.lastTimestamp 2>/dev/null | tail -n 25 || true
    local app
    for app in discovery-server talker listener; do
      printf '%s\n' "--- describe (tail) app=$app"
      kn describe pod -l "app=$app" 2>/dev/null | tail -n 20 || true
      printf '%s\n' "--- logs (last 15 lines) app=$app"
      kn logs -l "app=$app" --tail=15 --all-containers=true --prefix=true 2>&1 || true
    done
    printf '%s\n' '===== END DIAGNOSTICS ====='
  } >&2
}

fail() {
  err "$*"
  diagnostics
  exit 1
}

# Echo the name of the single non-terminating pod for an app label, or nothing.
pod_for() {
  kn get pods -l "app=$1" --no-headers \
    -o custom-columns='NAME:.metadata.name,DEL:.metadata.deletionTimestamp' 2>/dev/null |
    awk '$2 == "<none>" { print $1 }'
}

node_of() { kn get pod "$1" -o jsonpath='{.spec.nodeName}'; }

# Highest N found in "I heard: [Hello World: N]" lines (empty when there are none).
last_heard() {
  kn logs "$1" --tail=2000 2>/dev/null |
    sed -n 's/.*I heard: \[Hello World: \([0-9][0-9]*\)\].*/\1/p' | tail -n 1
}

verify() {
  command -v kubectl >/dev/null 2>&1 || { err 'kubectl not found in PATH'; exit 2; }

  log "== 1/4 cluster reachable and Deployments rolled out (context $KUBE_CONTEXT, timeout ${TIMEOUT}s)"
  kc get namespace "$NS" >/dev/null 2>&1 ||
    fail "cannot reach namespace '$NS' with context '$KUBE_CONTEXT'; run 'make demo' first"
  local d
  for d in discovery-server talker listener; do
    kn rollout status "deployment/$d" --timeout="${TIMEOUT}s" >/dev/null 2>&1 ||
      fail "deployment/$d did not finish rolling out within ${TIMEOUT}s"
  done

  log '== 2/4 pods Ready'
  local app pods=()
  for app in discovery-server talker listener; do
    kn wait --for=condition=Ready pod -l "app=$app" --timeout="${TIMEOUT}s" >/dev/null 2>&1 ||
      fail "pod(s) with app=$app are not Ready within ${TIMEOUT}s"
  done
  local talker_pod listener_pod ds_pod
  talker_pod="$(pod_for talker)"
  listener_pod="$(pod_for listener)"
  ds_pod="$(pod_for discovery-server)"
  pods=("$talker_pod" "$listener_pod" "$ds_pod")
  [[ -n "$talker_pod" && -n "$listener_pod" && -n "$ds_pod" ]] ||
    fail "expected exactly one live pod each for talker, listener and discovery-server (got: ${pods[*]})"
  [[ "$(wc -w <<<"$talker_pod")" == 1 && "$(wc -w <<<"$listener_pod")" == 1 ]] ||
    fail 'more than one live talker or listener pod; scale each Deployment to 1 replica'

  log '== 3/4 placement'
  local talker_node listener_node ds_node
  talker_node="$(node_of "$talker_pod")"
  listener_node="$(node_of "$listener_pod")"
  ds_node="$(node_of "$ds_pod")"
  printf '%-18s %-28s %s\n' 'POD' 'NODE' 'NAME'
  printf '%-18s %-28s %s\n' 'talker' "$talker_node" "$talker_pod"
  printf '%-18s %-28s %s\n' 'listener' "$listener_node" "$listener_pod"
  printf '%-18s %-28s %s\n' 'discovery-server' "$ds_node" "$ds_pod"
  [[ -n "$talker_node" && -n "$listener_node" ]] || fail 'talker or listener has no node assigned'
  [[ "$talker_node" != "$listener_node" ]] ||
    fail "talker and listener are both on node '$listener_node'; this is not a cross-node test"

  log "== 4/4 message delivery across nodes ($talker_node -> $listener_node)"
  local deadline first="" now_last="" start
  start="$(date +%s)"
  deadline=$((start + TIMEOUT))
  # Wait for the first delivered message, then for the counter to advance (live flow).
  while :; do
    now_last="$(last_heard "$listener_pod")"
    if [[ -n "$now_last" && -z "$first" ]]; then first="$now_last"; fi
    if [[ -n "$first" && -n "$now_last" ]] && ((now_last >= first + MIN_NEW_MESSAGES)); then break; fi
    if (($(date +%s) >= deadline)); then
      if [[ -z "$first" ]]; then
        fail "FAIL delivery: listener ($listener_node) logged no 'I heard' message from the talker ($talker_node) within ${TIMEOUT}s"
      fi
      fail "FAIL delivery: listener counter stalled at $now_last (first seen $first, wanted +$MIN_NEW_MESSAGES) within ${TIMEOUT}s"
    fi
    sleep 2
  done
  # The newest heard counter must really have been published by the talker pod.
  if ! kn logs "$talker_pod" --tail=2000 2>/dev/null | grep -Fq "Publishing: 'Hello World: ${now_last}'"; then
    fail "FAIL delivery: listener heard 'Hello World: ${now_last}' but the talker pod never logged publishing it"
  fi
  log "listener heard 'Hello World: $first' .. 'Hello World: $now_last' (counter advanced by $((now_last - first)))"
  kn logs "$listener_pod" --tail=3 2>/dev/null | sed 's/^/  listener log: /'
  log "PASS: ROS 2 messages crossed from $talker_node to $listener_node"
}

negative_test() {
  command -v kubectl >/dev/null 2>&1 || { err 'kubectl not found in PATH'; exit 2; }
  local self out rc=0 restored=0
  out="$(mktemp)"
  self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

  restore() {
    if ((restored == 0)); then
      restored=1
      log '-- restoring listener to the cluster ROS_DISCOVERY_SERVER'
      kn set env deployment/listener ROS_DISCOVERY_SERVER- >/dev/null 2>&1 || true
      kn rollout status deployment/listener --timeout="${TIMEOUT}s" >/dev/null 2>&1 || true
    fi
  }
  trap restore EXIT

  log '##### phase 1/3: baseline must PASS'
  "$self" || { err 'negative test aborted: the baseline verification already fails'; trap - EXIT; exit 1; }

  log "##### phase 2/3: break delivery (listener ROS_DISCOVERY_SERVER=$NEGATIVE_SERVER) -> verification must FAIL"
  kn set env deployment/listener "ROS_DISCOVERY_SERVER=$NEGATIVE_SERVER" >/dev/null
  kn rollout status deployment/listener --timeout="${TIMEOUT}s" >/dev/null
  # Short timeout: we expect a failure, there is no reason to wait two minutes for it.
  VERIFY_TIMEOUT=45 "$self" >"$out" 2>&1 || rc=$?
  # Show the decisive lines only (the full diagnostics are noisy).
  grep -E '^(==|ERROR|[a-z-]+ +ros2k8s)|FAIL' "$out" | sed 's/^/  | /' || true
  local reason=0
  grep -q 'FAIL delivery' "$out" && reason=1
  rm -f "$out"
  if ((rc == 0)); then
    err 'NEGATIVE TEST FAILED: verification passed although delivery was broken (the check is not trustworthy)'
    exit 1
  fi
  if ((reason == 0)); then
    err "NEGATIVE TEST INCONCLUSIVE: verification failed (status $rc) but not at the message-delivery check"
    exit 1
  fi
  log "negative test: verification exited with status $rc (non-zero), at the message-delivery check, as required"

  log '##### phase 3/3: restore -> verification must PASS again'
  restore
  trap - EXIT
  "$self" || { err 'negative test: verification did not recover after restore'; exit 1; }
  log "PASS: negative test (broken delivery was detected with exit status $rc, then recovered)"
}

case "${1:-}" in
  '') verify ;;
  --negative-test) negative_test ;;
  -h | --help) usage ;;
  *) err "unknown argument: $1 (see --help)"; exit 2 ;;
esac
