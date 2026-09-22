# The shippable-checkpoint run

**Goal:** one Urdu checkpoint per arm that has *not* memorised its corpus, trained on the
data the core runs never touched. This is not a research run — §4.5's endpoint is already
answered — it is the model that can be released.

## Why arm B

| | core runs (arm A) | this run (arm B) |
|---|---|---|
| unique tokens | 23,214,080 | **85,362,688** |
| native Urdu share | 68.80% | **74.27%** |
| epochs | 426.5 | **16** |
| verbatim 32-gram copy, final ckpt | **0.249** (AR) | expected ~0 |

`core-ar-s0`'s final checkpoint reproduces a quarter of its output verbatim from training
data — 11% in blocks of 128 tokens — and scores 3.6143 held-out bpb, worse than uniform
random (Finding BC). Arm B was dropped from the *experiment* because a 25M-vs-40M bracket
around a 33M pivot cannot falsify the fitted law (PRD §0.3). That rejection is about the
bracket, not about the data, and does not bear on using arm B to train a releasable model.

⚠️ **The shipped checkpoint is chosen, not assumed.** Seven fractions land at
0.16 / 0.33 / 0.82 / 1.6 / 4.1 / 8.2 / 16.4 epochs. Score them all with `scripts/curves.py`
and ship the best. On arm A the best AR checkpoint was the **2%** one.

## Cost

~1.37B tokens per arm. At the 5090's measured 181,600 tok/s that is **2.1 h and ~$1.18 per
arm**, ~$2.40 for both, against ~$122 unspent of the $150 cap. On the local 4060 (13,783
tok/s measured) the same run is ~27 h per arm.

## Running it

1. Rent a 5090-class box on Vast. **Prepaid credit only — never enable automatic billing**,
   that removes the hard ceiling. Note the ssh host and port.
2. `./vast/push.sh <host> <port>` — ships code, tokenizer and the 169 MB arm-B corpus, then
   runs G2's throughput check. **Do not start the chain if it is far under ~150k tok/s.**
3. Start the chain detached, as the script prints:
   `ssh -p <port> root@<host> 'cd /workspace/ravaan && nohup bash vast/launch.sh > /workspace/runs/chain.log 2>&1 &'`
4. `./vast/fetch.sh <host> <port>` — pulls each run as it lands, then signals the watchdog.
5. **Destroy the instance in the console.** Stop halts the GPU charge; only destroy halts
   the $0.75/day storage.

## Lessons this encodes

- **Wait on a file the producer writes, never a process name.** Git Bash has no `pgrep`, so
  `until ! pgrep -f foo.py` returns immediately; that cost sessions 23 and 28.
- **The watchdog triggers on the *last* run in the chain**, and on the fetcher's own
  sentinel. Adding a third run means rearming it.
- **The watchdog only ever stops**, so the disk survives a failed download.
- **This tooling lives in the repo.** Last time it lived only on the instance and died with it.
