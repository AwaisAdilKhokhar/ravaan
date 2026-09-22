#!/bin/bash
# Runs LOCALLY. Ships code + arm-B corpus + tokenizer to a fresh instance, then starts
# the chain detached so an ssh drop cannot kill it.
#
#   ./vast/push.sh <host> <port>        e.g.  ./vast/push.sh 180.189.55.43 46220
set -euo pipefail
H="root@${1:?host}"; P="${2:?port}"
S="ssh -p $P -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"

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
for MB in 16 32 48 64; do
    echo "-- microbatch $MB --"
    $S "$H" "cd /workspace/ravaan && python -u scripts/train.py throughput --arm diff --size 70M --microbatch $MB --steps 30 --corpus-arm B --corpus /workspace/data/packed --tokenizer /workspace/data/tokenizer/ravaan-16k.model"
done

echo
echo "Take the PEAK from the sweep above. Do not start if it is far under ~150k tok/s."
echo "Start the run detached, passing that microbatch:"
echo "  ssh -p $P $H 'cd /workspace/ravaan && MICROBATCH=<peak> nohup bash vast/launch.sh > /workspace/runs/chain.log 2>&1 &'"
echo "Then locally:  ./vast/fetch.sh ${1} ${P}"
