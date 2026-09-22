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

echo "== throughput check (G2's rule: measure on the instance before committing) =="
$S "$H" 'cd /workspace/ravaan && python -u scripts/train.py throughput --arm ar --size 70M --microbatch 16 --steps 30 --corpus-arm B --corpus /workspace/data/packed --tokenizer /workspace/data/tokenizer/ravaan-16k.model'

echo
echo "If that cleared ~150k tok/s, start the chain:"
echo "  ssh -p $P $H 'cd /workspace/ravaan && nohup bash vast/launch.sh > /workspace/runs/chain.log 2>&1 &'"
echo "Then locally:  ./vast/fetch.sh ${1} ${P}"
