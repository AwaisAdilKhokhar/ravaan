#!/bin/bash
# Runs LOCALLY. Ships code + arm-B corpus + tokenizer to a fresh instance, then starts
# the chain detached so an ssh drop cannot kill it.
#
#   ./vast/push.sh <host> <port>        e.g.  ./vast/push.sh 180.189.55.43 46220
set -euo pipefail
H="root@${1:?host}"; P="${2:?port}"
S="ssh -p $P -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"

echo "== pre-flight: is this card already someone else's? =="
# Session 33 rented a 5090 that was already running another tenant's job at 100%. The
# symptoms looked like a slow box and cost fifteen minutes to diagnose: throughput flat
# at ~62k tok/s across microbatch 16/32/48 (a GPU that wants a bigger batch does not do
# that), then an OOM at 64 whose message gave it away -- 31.36 GiB total, 17.89 GiB ours,
# 1.13 GiB free, so ~12.3 GiB belonged to nobody we could see.
#
# ⚠️ `nvidia-smi --query-compute-apps` is EMPTY in a Vast container even when the card is
# busy: container isolation hides the other tenant's PID. memory.used and utilization.gpu
# are the only signals that cross the boundary, which is why this checks those two and
# not the process list. A clean card reads ~0 MiB and 0%.
preflight=$($S "$H" 'nvidia-smi --query-gpu=memory.used,utilization.gpu,clocks.sm,clocks.max.sm --format=csv,noheader,nounits' 2>/dev/null | head -1)
echo "  $preflight  (memory MiB, util %, sm MHz, sm max MHz)"
used=$(echo "$preflight"  | cut -d, -f1 | tr -d ' ')
util=$(echo "$preflight"  | cut -d, -f2 | tr -d ' ')
case "${used:-}${util:-}" in ''|*[!0-9]*) echo "could not read the GPU state — aborting" >&2; exit 4;; esac
if [ "$used" -gt 500 ] || [ "$util" -gt 10 ]; then
    echo >&2
    echo "ABORTING: this GPU is already in use — ${used} MiB resident, ${util}% utilised," >&2
    echo "  before we have shipped a single byte. You are sharing the card." >&2
    echo "  Destroy this instance and rent another; do not try to tune around it." >&2
    exit 4
fi
echo "  card is clean"

echo "== creating layout =="
$S "$H" 'mkdir -p /workspace/ravaan /workspace/data/packed /workspace/data/tokenizer /workspace/runs'

echo "== code =="
tar czf - scripts ravaan vast pyproject.toml README.md LICENSE | $S "$H" 'tar xzf - -C /workspace/ravaan'

echo "== tokenizer =="
scp -P "$P" data/tokenizer/ravaan-16k.model "$H:/workspace/data/tokenizer/"

echo "== corpus: arm B train + validation only (169 MB, not the whole freeze) =="
tar czf - data/packed/manifest.json \
          data/packed/*/train/B \
          data/packed/*/validation \
  | $S "$H" 'tar xzf - -C /workspace'

echo "== deps =="
# --no-deps is deliberate. The Vast PyTorch images ship an NVIDIA NGC torch build
# (2.14.0a0+...nv26.08) matched to the host driver; resolving "torch>=2.4" against the
# index can pull a stock wheel over it and lose CUDA. Only what is genuinely absent is
# installed, and the package itself goes in without its dependency closure.
$S "$H" 'python -c "import torch, numpy" && pip install -q sentencepiece'
$S "$H" 'cd /workspace/ravaan && pip install -q --no-deps -e .'
$S "$H" 'cd /workspace/ravaan && python -c "import torch, sentencepiece, ravaan; print(\"imports OK\", torch.__version__, torch.cuda.is_available())"'

echo "== throughput sweep (G2's rule: measure on the instance before committing) =="
# ⚠️ A SWEEP, not one setting (Finding BE). The microbatch optimum is a property of the
# host, not the card: the core runs' 5090 peaked at 16 (186,631 tok/s), session 31's
# peaked at 32 and was 43% SLOWER at 16 -- 122,933 against 175,821, with 48 and 64
# falling back to 166,685 and 157,753. Inheriting the previous box's setting would have
# cost ~2 GPU-hours on a 4-hour job, and this run is longer. Measured on --arm diff
# because that is the arm being paid for; AR and DIFF cost the same per token within
# 2.2% (Finding AM), but there is no reason to measure the arm we are not running.
#
# ⚠️ ONLY DIVISORS OF 256. `TrainingConfig.tokens_per_step` is 131,072 = 256 sequences of
# 512, and `resolve_batching` REFUSES a microbatch that does not divide it rather than
# rounding -- §4.1's "same number of tokens processed" is a per-step property, and a run
# that quietly used 240 sequences a step is not the same run. But `train.py throughput`
# does not go through `resolve_batching`, so it will happily measure 48 and report it as
# the peak. Session 33 swept 16/32/48/64, took 48, and the run died on its first line:
#   ValueError: microbatch 48 does not divide the 256 sequences in a step
# The sweep must not offer a setting the trainer will reject.
#
# ⚠️ EQUAL TOKENS PER MEASUREMENT, not equal steps. At ~150k tok/s, 30 steps at microbatch
# 32 is ~3 SECONDS of timed work, and session 33 saw the same box and setting measure
# 137,329 / 156,540 / 161,586 on three runs. That noise band is wider than the differences
# the sweep exists to detect, and it tripped a threshold twice on a demonstrably healthy
# card. 8192/MB steps puts ~4.2M tokens through every setting -- ~28 s each, and the same
# work per setting so the comparison is fair rather than merely longer.
for MB in 16 32 64 128; do
    echo "-- microbatch $MB --"
    $S "$H" "cd /workspace/ravaan && python -u scripts/train.py throughput --arm diff --size 70M --microbatch $MB --steps $((8192 / MB)) --corpus-arm B --corpus /workspace/data/packed --tokenizer /workspace/data/tokenizer/ravaan-16k.model"
done

echo
echo "Take the PEAK from the sweep above. Do not start if it is far under ~150k tok/s."
echo "Start the run detached, passing that microbatch:"
echo "  ssh -p $P $H 'cd /workspace/ravaan && MICROBATCH=<peak> nohup bash vast/launch.sh > /workspace/runs/chain.log 2>&1 &'"
echo "Then locally:  ./vast/fetch.sh ${1} ${P}"
