# The shippable-diffusion run — 64 epochs on arm B

**Goal:** the diffusion half of the release, trained long enough to be worth releasing, on
the same corpus as the AR half. This is not a research run — §4.5's endpoint is already
answered and nothing here touches it.

## Why 64 epochs

§0.4 makes both arms take the same budget, so session 31's pair both stopped at 16 epochs.
At that point the two arms were doing opposite things (Finding BH):

| epochs | AR | Δ | DIFF | Δ |
|---|---|---|---|---|
| 4 | **0.7774** | −0.0551 | 0.9637 | −0.1244 |
| 8 | 0.7887 | **+0.0113** | 0.8841 | −0.0796 |
| 16 | 0.8690 | **+0.0803** | **0.8322 ± 0.0018** | **−0.0520** |

AR had turned at 4 and was being actively ruined by more compute; DIFF's last doubling
bought more than AR's best doubling ever did. **A shippable checkpoint does not owe §0.4's
equal-budget constraint**, so this run buys the epochs the experiment could not.

Corroboration rather than extrapolation: `core-diff-s0` reached **0.8059** on arm A — a
corpus 3.7× smaller with a worse mixture — by running 426 epochs, at **0.000 verbatim
overlap at n ≥ 16**. Heavy repetition is safe on this arm in a way Finding BD proves it is
not on AR's.

⚠️ **The ~0.777 target is a three-point log-linear fit, not a measurement.** Arm A's own
deltas wobble and the fit's limit is ~0.74, so the prize is a few hundredths of a bpb. The
other half of the purchase is a **matched-corpus release pair**: the AR release is arm B,
the best diffusion so far is arm A, and every artefact has had to disclose it.

⚠️ **Not a resume.** `RavaanTrainingConfig.lr_at` is cosine to 10% of peak over
`total_steps`, so `ship-diff-b` has already annealed. This is a fresh run at full price,
and **its 16-epoch rung will read slightly worse than 0.8320** because the cosine has not
finished there. Expected, not a regression, not a reason to stop the run.

## Cost

5.46B tokens (64 × 85,362,688). At the 5090's measured diffusion throughput ~175k tok/s
and $0.5647/h: **~8.7 h, ~$4.90 GPU, ~$6 all-in.**

⚠️ **~$9.80 of Vast credit does not cover this** once storage and a margin are counted.
Load more first, **prepaid only — never enable automatic billing**, which removes the hard
ceiling.

## Running it

1. Rent a 5090-class box on Vast. Note the ssh host and port.
2. `./vast/push.sh <host> <port>` — ships code, tokenizer and the 169 MB arm-B corpus, then
   **sweeps microbatch 16/32/48/64 on the diff arm.**
3. Take the **peak** from that sweep. Don't start if it is far under ~150k tok/s.
   `ssh -p <port> root@<host> 'cd /workspace/ravaan && MICROBATCH=<peak> nohup bash vast/launch.sh > /workspace/runs/chain.log 2>&1 &'`
4. `./vast/fetch.sh <host> <port>` — waits for `evaluation.json`, pulls with byte-offset
   resume and md5 verification, then signals the watchdog. One step; it calls `pull.sh`.
5. **Destroy the instance in the console.** Stop halts the GPU charge; only destroy halts
   the $0.75/day storage.

## Afterwards, locally ($0 on the 4060)

Seven fractions land at **0.64 / 1.3 / 3.2 / 6.4 / 16 / 32 / 64 epochs** — four of them
past where the curve currently stops.

```bash
# score every rung and SHIP THE BEST, not the last
python -u scripts/curves.py --run D:/ravaan-runs/ship-diff-b64 --arm diff --seed 0 \
    --corpus data/packed --corpus-arm B --out reports/eval/curve_diff_b64.json

# a real error bar on the rung you intend to ship (Findings BA, BJ)
python -u scripts/elbo.py --run D:/ravaan-runs/ship-diff-b64 --seed 0 --draws 9 \
    --corpus data/packed --corpus-arm B --check-denominators \
    --out reports/eval/elbo_diff_b64.json

# is it reciting? the held-out control is what makes the number readable
python scripts/overlap.py --samples reports/b64_samples.jsonl \
    --corpus data/packed --corpus-arm B --verify --out reports/eval/overlap_b64.json

# samples at BG's settings — NOT the 160-step default
python -u scripts/sample.py --checkpoint D:/ravaan-runs/ship-diff-b64/diff-s0_<best>.pt \
    --corpus data/packed --tokenizer data/tokenizer/ravaan-16k.model \
    --out reports/b64_samples --samples 12 --new-tokens 160 \
    --forbid-eos always --steps 8 --schedule gumbel --gumbel 2
```

⚠️ **Re-run the A3/A4 sweep on this checkpoint.** Finding BG's 8-step optimum is a property
of a checkpoint, not a law, and should not be assumed to carry over untested.

## Lessons this encodes

- **Wait on a file the producer writes, never a process name.** Git Bash has no `pgrep`, so
  `until ! pgrep -f foo.py` returns immediately; that cost sessions 23 and 28.
- **Never `scp -r` a finished run.** One transfer, and a reset at 2 GB lost 4 GB of 6.3 GB.
  `fetch.sh` now delegates to `pull.sh`, which resumes at a byte offset and md5-verifies.
- **The watchdog triggers on the last run in the chain and the chain is one run.**
  `launch.sh`'s `$RUN`, `fetch.sh`'s `$RUN` and `.fetched_all` are the names that must agree.
- **The watchdog only ever stops**, so the disk survives a failed download.
- **Microbatch is a property of the host, not the card** — 43% swing between two identical
  5090s (Finding BE). Sweep it every time.
