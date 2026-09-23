#!/bin/bash
# Runs ON the rented instance. One 64-epoch arm-B diffusion run, then stops the box.
#
# This is the shippable-diffusion run (Finding BH), not a research run. §0.4 makes both
# arms take the same budget, so session 31's pair both stopped at 16 epochs -- but at
# that point AR had turned at 4 and was being actively ruined by more compute (+0.0803
# on its last doubling) while DIFF was still gaining -0.0520, more than AR's best
# doubling ever bought. A shippable checkpoint does not owe §0.4's constraint. So this
# run buys the epochs the experiment could not.
#
# What it is expected to land: a three-point fit puts 64 epochs at ~0.777 urdu bpb,
# level with the AR arm's best 0.7774 on the same corpus, against DIFF's 0.8322 +/-
# 0.0018 at 16 (Finding BJ, nine seeded draws). ⚠️ That is a FIT, not a measurement --
# arm A's own deltas wobble and the fit's limit is ~0.74, so the prize is a few
# hundredths of a bpb. The other half of the purchase is a matched-corpus release pair:
# the AR release is arm B and the best diffusion so far is arm A, and every artefact has
# had to disclose it.
#
# ⚠️ NOT a resume of ship-diff-b. RavaanTrainingConfig.lr_at is cosine to 10% of peak
# over total_steps, so that checkpoint has already annealed. This is a fresh run at full
# price, and its 16-epoch rung will read slightly WORSE than ship-diff-b's 0.8320
# because the cosine has not finished there. Expected, not a regression, not a reason to
# stop the run.
#
# §4.2's task mixture is KEPT (lm 65% / infill 10% / translit 10% / restore 8% /
# codeswitch 7%). A pure-LM run would generate marginally better, but the mixture is
# what makes the checkpoint comparable to the measured curves and what gives the
# released model infilling and transliteration as well as generation.
#
# Seven fraction checkpoints land at 0.64 / 1.3 / 3.2 / 6.4 / 16 / 32 / 64 epochs --
# four of them past where the curve currently stops. The shipped checkpoint is whichever
# scores best on held-out bpb, picked by scripts/curves.py after the fetch and NOT
# assumed to be the last one: on arm A the best AR checkpoint was the 2% one and the
# final one was worse than uniform random, so this choice is load-bearing.
set -euo pipefail
cd /workspace/ravaan

# ⚠️ microbatch is HOST-dependent and must be re-measured on every box, not inherited
# (Finding BE). The core runs' 5090 peaked at 16 (186,631 tok/s against 181,578 at 32);
# session 31's peaked at 32 and was 43% SLOWER at 16 -- 122,933 vs 175,821. Same card,
# opposite optimum. push.sh sweeps 16/32/48/64 on the diff arm before you get here;
# set MICROBATCH to whatever it reported as the peak.
EPOCHS=64
RUN=ship-diff-b64

# ⚠️ No default. The sweep in push.sh is what tells you this number, and a silent default
# is how Finding BE costs GPU-hours on a box whose optimum is the other one.
if [ -z "${MICROBATCH:-}" ]; then
    echo "MICROBATCH is unset. Run push.sh's sweep and start this with MICROBATCH=<peak>." >&2
    exit 2
fi

# --- the budget gate -------------------------------------------------------
#
# This run has a HARD ceiling of the credit already loaded, so throughput is a budget
# question before it is a performance one. At 5.46B tokens and $0.5647/h:
#
#     175k tok/s -> 8.7 h -> $4.90        123k tok/s -> 12.3 h -> $6.97
#
# and 123k is not hypothetical -- it is what session 31's 5090 did at the wrong
# microbatch, 43% off the same card's own peak. An unattended 12-hour run that nobody is
# watching is exactly how a ceiling gets breached, so the gate is here rather than in a
# human's judgement of push.sh's output.
FLOOR="${FLOOR:-150000}"
echo "== budget gate: measuring at microbatch $MICROBATCH, floor ${FLOOR} tok/s =="
measured=$(python -u scripts/train.py throughput --arm diff --size 70M \
    --microbatch "$MICROBATCH" --steps 30 --corpus-arm B \
    --corpus /workspace/data/packed \
    --tokenizer /workspace/data/tokenizer/ravaan-16k.model \
    | python -c 'import json,sys; print(json.load(sys.stdin)["tokens_per_second"])') || true

# A gate that cannot read its own measurement must not fall through to "start anyway".
case "${measured:-}" in
    ''|*[!0-9]*)
        echo "ABORTING: could not measure throughput (got '${measured:-}')." >&2
        echo "  the gate refuses to start a run it cannot price." >&2
        exit 3;;
esac

echo "measured ${measured} tok/s at microbatch $MICROBATCH"
if [ "$measured" -lt "$FLOOR" ]; then
    hours=$(python -c "print(f'{5463212032/$measured/3600:.1f}')")
    cost=$(python -c "print(f'{5463212032/$measured/3600*0.5647:.2f}')")
    echo "ABORTING: ${measured} tok/s is under the ${FLOOR} floor." >&2
    echo "  that is ${hours} h and \$${cost} of GPU for this run." >&2
    echo "  re-sweep the microbatch, or destroy this box and rent another." >&2
    echo "  override deliberately with FLOOR=<lower> if you have decided to accept it." >&2
    exit 3
fi
hours=$(python -c "print(f'{5463212032/$measured/3600:.1f}')")
cost=$(python -c "print(f'{5463212032/$measured/3600*0.5647:.2f}')")
echo "gate PASSED — projecting ${hours} h and ~\$${cost} of GPU for the run"

COMMON="--size 70M --seed 0 --corpus /workspace/data/packed --corpus-arm B
        --tokenizer /workspace/data/tokenizer/ravaan-16k.model --microbatch $MICROBATCH
        --epochs $EPOCHS --evaluate --eval-split validation --eval-limit 0"

mkdir -p /workspace/runs

python -u scripts/train.py run --arm diff $COMMON --out "/workspace/runs/$RUN" 2>&1 | tee "/workspace/runs/$RUN.log"

# Score the seven rungs HERE, on the rented card, before anything is downloaded.
#
# Two reasons, and the first one is money. The run writes ~5.9 GB of checkpoints and the
# box bills until the fetcher signals; scoring on the box means the download can be the
# ONE checkpoint worth shipping plus a few KB of JSON, instead of seven 840 MB files over
# a link that dropped every few hundred MB in session 31. The second is that it is simply
# faster here than on the 4060, where a seven-rung curve is ~35 min.
#
# Non-fatal on purpose: if this dies, the checkpoints are still on disk and still
# fetchable, and a scoring failure must not strand the box in its grace window.
echo "== scoring the seven rungs on the box =="
python -u scripts/curves.py --run "/workspace/runs/$RUN" --arm diff --seed 0 \
    --corpus /workspace/data/packed --corpus-arm B \
    --tokenizer /workspace/data/tokenizer/ravaan-16k.model \
    --out "/workspace/runs/$RUN/curve.json" 2>&1 | tee -a "/workspace/runs/$RUN.log" || \
    echo "WARNING: curves.py failed on the box — score locally after the fetch"

touch /workspace/runs/.run_done
echo "RUN COMPLETE — waiting for the fetcher before stopping"

# Grace window for the local fetcher. The watchdog waits on the sentinel the fetcher
# writes, never on a process name (Git Bash has no pgrep; that mistake cost sessions 23
# and 28). Hard cap so a dead fetcher cannot bill indefinitely.
#
# ⚠️ The watchdog triggers on the LAST run in the chain and the chain is now one run.
# $RUN above, fetch.sh's wait_for, and .fetched_all below are the three names that must
# agree; adding a run last time cost three coordinated changes and this is the same trap
# with the count going the other way.
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
