#!/usr/bin/env bash
# Open question 5's measurement chain, run after the infill-50% training run finishes.
#
# Chained on the producer's own completion line rather than on a process check: session 23's first
# chain used `pgrep`, which Git Bash does not have, so the wait fell through and the next stage
# started on a half-written artefact. `until grep -q <the line the producer prints> <log>` is the
# form that worked.
set -u

LOG=logs/train_ar_fim50.log
until grep -q "held-out (" "$LOG" 2>/dev/null; do
    if ! grep -q "step" "$LOG" 2>/dev/null; then sleep 30; continue; fi
    sleep 30
done
echo "TRAIN-DONE $(date -Is)"

# The control first: at 2 epochs neither arm should be reciting, and session 23 measured ~0.05 for
# both on this corpus. If the 50% run's gap is different the infill numbers are about memorization
# rather than about the share, and that has to be known before the table is read.
python -u scripts/memorization.py \
    --checkpoint runs/urdu-ar/ar-s0_f1.pt \
    --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \
    --checkpoint runs/urdu-diff/diff-s0_f1.pt \
    --corpus data/packed-urdu --corpus-arm A --sequences 384 \
    --out reports/eval/memorization_infill_share.json
echo "MEMORIZATION-DONE $(date -Is)"

python -u scripts/infill_eval.py \
    --checkpoint runs/urdu-ar/ar-s0_f1.pt \
    --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \
    --checkpoint runs/urdu-diff/diff-s0_f1.pt \
    --corpus data/packed-urdu --split validation \
    --items 64 --spans 4 8 16 32 64 \
    --out reports/infill_share
echo "INFILL-DONE $(date -Is)"
