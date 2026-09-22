#!/bin/bash
# Runs LOCALLY. Waits for the run to land, pulls it safely, then signals the watchdog.
#
#   ./vast/fetch.sh <host> <port> [dest]
#
# ⚠️ This script used to end in `scp -P $P -r`, which is the single transfer that lost
# 4 GB of a 6.3 GB run in session 31 and, under `set -e`, died without writing the
# watchdog's sentinel -- so the box billed idle for an hour with nobody watching. The
# transfer is now delegated to pull.sh, which resumes at a byte offset and md5-verifies
# every file. "fetch.sh then pull.sh" in the old runbook is one step now.
set -uo pipefail
H="root@${1:?host}"; P="${2:?port}"; DEST="${3:-/d/ravaan-runs}"
S="ssh -p $P -o BatchMode=yes -o ConnectTimeout=20"
HERE="$(cd "$(dirname "$0")" && pwd)"

# One run, not two. This name must match launch.sh's $RUN -- the watchdog triggers on
# the last run in the chain and the chain is one run long.
RUN=ship-diff-b64

echo "$(date +%m-%d' '%H:%M:%S) waiting for $RUN ..."
# wait on the artefact the producer writes, never on a process name
until $S "$H" "test -f /workspace/runs/$RUN/evaluation.json" 2>/dev/null; do sleep 120; done
echo "$(date +%m-%d' '%H:%M:%S) $RUN DONE — downloading with resume + md5"

bash "$HERE/pull.sh" "$1" "$P" "$RUN" "$DEST"
status=$?

if [ "$status" -ne 0 ]; then
    echo
    echo "PULL INCOMPLETE — the sentinel was NOT written, so the box stays up."
    echo "Rerun this, or just the pull, and it resumes where it stopped:"
    echo "  ./vast/pull.sh $1 $P $RUN $DEST"
    echo "⚠️ launch.sh's grace window is 96 x 300 s = 8 h. After that it stops the box"
    echo "   on its own and the disk survives, but do not leave it to burn the cap."
    exit 1
fi

$S "$H" "touch /workspace/runs/.fetched_all"

echo
echo "$RUN DOWNLOADED AND VERIFIED. The watchdog stops the box within ~5 min."
echo "DESTROY it in the Vast console afterwards — stop halts the GPU charge,"
echo "only destroy halts the \$0.75/day storage."
