#!/bin/bash
# Runs LOCALLY. Pulls each run as it lands, then signals the instance watchdog.
#
#   ./vast/fetch.sh <host> <port> [dest]
set -euo pipefail
H="root@${1:?host}"; P="${2:?port}"; DEST="${3:-/d/ravaan-runs}"
S="ssh -p $P -o BatchMode=yes -o ConnectTimeout=20"

wait_for () {
  echo "$(date +%m-%d' '%H:%M:%S) waiting for $1 ..."
  # wait on the artefact the producer writes, never on a process name
  until $S "$H" "test -f /workspace/runs/$1/evaluation.json" 2>/dev/null; do sleep 120; done
  echo "$(date +%m-%d' '%H:%M:%S) $1 DONE — downloading"
  scp -P "$P" -o BatchMode=yes -r "$H:/workspace/runs/$1" "$DEST/"
  echo "$(date +%m-%d' '%H:%M:%S) $1 -> $DEST/$1"
}

wait_for ship-ar-b
wait_for ship-diff-b
$S "$H" 'touch /workspace/runs/.fetched_all'

echo
echo "BOTH RUNS DOWNLOADED. The watchdog stops the box within ~5 min."
echo "DESTROY it in the Vast console afterwards — stop halts the GPU charge,"
echo "only destroy halts the \$0.75/day storage."
