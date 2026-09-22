#!/bin/bash
# Runs ON the rented instance. Chains both arm-B runs, then stops the box.
#
# This is the deployable-checkpoint run, not a research run: arm B (85.4M unique
# tokens, 74.27% native Urdu) at 16 epochs, against the core runs' arm A (23.2M,
# 68.80%) at 426. The point is a checkpoint that has not memorised its corpus --
# core-ar-s0 reproduces 25% of its output verbatim at 32 tokens, and 11% at 128.
#
# §4.2's task mixture is KEPT (lm 65% / infill 10% / translit 10% / restore 8% /
# codeswitch 7%). A pure-LM run would generate marginally better, but the mixture
# is what makes the checkpoint comparable to the measured curves and what gives the
# released model infilling and transliteration as well as generation.
#
# Seven fraction checkpoints per run land at 0.16 / 0.33 / 0.82 / 1.6 / 4.1 / 8.2 /
# 16.4 epochs. The shipped checkpoint is whichever scores best on held-out bpb --
# picked by scripts/curves.py after the fetch, NOT assumed to be the last one. On
# arm A the best AR checkpoint was the 2% one and the final one was worse than
# uniform random, so this choice is load-bearing.
set -euo pipefail
cd /workspace/ravaan

# microbatch is HOST-dependent and must be re-measured on every box, not inherited. The
# core runs' 5090 peaked at 16 (186,631 tok/s against 181,578 at 32); this one peaks at
# 32 and is 43% slower at 16 -- 122,933 vs 175,821. Same card, opposite optimum. Run
# `train.py throughput --corpus-arm B --corpus ...` over 16/32/48/64 before trusting this.

EPOCHS=16
COMMON="--size 70M --seed 0 --corpus /workspace/data/packed --corpus-arm B
        --tokenizer /workspace/data/tokenizer/ravaan-16k.model --microbatch 32
        --epochs $EPOCHS --evaluate --eval-split validation --eval-limit 0"

mkdir -p /workspace/runs

# AR first: it is the one most likely to be the released generator, so if anything
# goes wrong it goes wrong on the arm we care about most while the box is watched.
python -u scripts/train.py run --arm ar   $COMMON --out /workspace/runs/ship-ar-b   2>&1 | tee /workspace/runs/ship-ar-b.log
python -u scripts/train.py run --arm diff $COMMON --out /workspace/runs/ship-diff-b 2>&1 | tee /workspace/runs/ship-diff-b.log

touch /workspace/runs/.both_done
echo "BOTH RUNS COMPLETE — waiting for the fetcher before stopping"

# Grace window for the local fetcher. The watchdog waits on the sentinel the
# fetcher writes, never on a process name (Git Bash has no pgrep; that mistake
# cost sessions 23 and 28). Hard cap so a dead fetcher cannot bill indefinitely.
for _ in $(seq 1 96); do
    [ -f /workspace/runs/.fetched_all ] && break
    sleep 300
done

# stop, never destroy: the disk survives a failed download. Stopping halts the GPU
# charge; only destroy halts the $0.75/day storage, and that is a manual decision.
if [ -n "${CONTAINER_API_KEY:-}" ] && [ -n "${CONTAINER_ID:-}" ]; then
    curl -s -X PUT "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" \
         -H "Authorization: Bearer $CONTAINER_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"state": "stopped"}' && echo "instance stop requested"
else
    echo "WARNING: CONTAINER_API_KEY/CONTAINER_ID unset — stop the box by hand"
fi
