# Running the stage 6+7 freeze passes on Kaggle

Urdu Wikipedia is done locally. The two long passes — FineWeb2 (both train shards) and
Roman-Urdu-Parl — need more RAM than the local machine has: stage 7's index measured
**~2,010 bytes per document**, so FineWeb2's ~5.0M documents come to **~10 GB** against ~2 GB free.
Kaggle's CPU notebooks give ~30 GB, which fits.

**The constraint that shapes everything below is the session cap**, ~12 hours for a CPU notebook.
FineWeb2 measured at ~19 CPU-hours (extrapolated from the local run at 16% complete, where CPU time
and wall time were within 3% of each other — the pass is single-threaded). Kaggle's Linux hosts may
run 1.3–1.5× faster than a throttled Windows laptop, which puts it at 9–14 hours. **That straddles
the cap, so it has to be measured before it is trusted.** Roman-Urdu-Parl's runtime is not known at
all: 6.37M rows of ~74 characters is a different shape from anything measured so far, and a
two-point cost model fitted to Wikipedia and FineWeb2 produced a negative per-document cost, so
there is no basis for a projection. Measure it.

`neardedup.py` is **not resumable** — the shard *reader* checkpoints (session 5), but the MinHash
index lives in memory and is lost when a session ends. So a pass that overruns the cap is a pass
that produced nothing.

---

## 0. Account prep, once

1. Kaggle → **Settings → Phone Verification.** Required before a notebook can use the internet, and
   the fetch needs it.
2. In the notebook: **Settings → Accelerator: None** (this job never touches a GPU — a GPU session
   also has a *shorter* cap) and **Internet: On**.

Check the current limits on Kaggle's docs rather than trusting the figures here; they move.

---

## 1. Get the repo there

No git remote exists for this project, so either:

**(a) Upload as a private Kaggle Dataset — no GitHub needed.** From the repo root:

```bash
git archive --format=zip -o ravaan-code.zip HEAD -- ravaan scripts configs pyproject.toml README.md
```

Then Kaggle → Datasets → New Dataset → upload `ravaan-code.zip`, private. It mounts read-only at
`/kaggle/input/<slug>/`. **`data/manifest.json` is deliberately not in that archive** — see step 3.

**(b) Push to GitHub and `!git clone`.** Also finally exercises `.github/workflows/tests.yml`, which
has never run because there is no remote.

---

## 2. Save the corpus as a Kaggle Dataset, so it is fetched once

The corpus is ~6.5 GB (FineWeb2 both train shards) plus ~1.2 GB (Roman-Urdu-Parl train). Fetching
it inside every session wastes session time against the cap, and the cap is the binding constraint.
Fetch it once into `/kaggle/working`, then **Save Version → output as a Dataset**, and mount that
dataset read-only in every later session.

```python
!pip install -q -e "/kaggle/input/<code-slug>[data]"
!cd /kaggle/working && python /kaggle/input/<code-slug>/scripts/acquire.py fetch
!cd /kaggle/working && python /kaggle/input/<code-slug>/scripts/acquire.py verify
```

`fetch` pins every file to a commit SHA and verifies SHA-256 as it streams, so this reproduces the
exact bytes the local manifest describes — that is why uploading 6.5 GB from a home connection is
unnecessary. Anonymous HuggingFace downloads are sometimes rate-limited; if it stalls, add a
read-only HF token as a Kaggle Secret.

---

## 3. The manifest, and why the results come back valid

`ShardReader.plan_fingerprint()` hashes `[source, path, sha256]` per file, plus layout, order, seed
and sample rate. `path` is the **source-relative** path (`data/urd_Arab/train/000_00000.parquet`,
forward slashes); the machine-specific `local_path` is deliberately *not* in it. Verified:

```
this machine : 54b744f92e3949f8
rented box   : 54b744f92e3949f8      # same digests, POSIX local paths
```

So a removal list written on Kaggle carries a header that `--exclude` accepts on the local machine
with no editing. Let `acquire.py` write a fresh `data/manifest.json` on Kaggle rather than copying
the local one — the digests will match, and the local paths should not.

---

## 4. Measure before committing a session

**This is the step that decides whether Kaggle can do FineWeb2 at all.** Run a timed prefix and get
a real rate:

```python
import time, subprocess
t = time.time()
subprocess.run([
    "python", "/kaggle/input/<code-slug>/scripts/neardedup.py",
    "--source", "fineweb2-urd_Arab", "--split", "train",
    "--limit", "200000", "--single-pass",
    "--json", "/kaggle/working/trial.json",
], check=True)
print(f"200,000 documents in {time.time()-t:.0f}s")
```

Then: `total_hours = (seconds / 200_000) * 4_980_000 / 3600`.

- **Under ~10 h** → run it in one session (leave headroom; the cap is hard and there is no resume).
- **Over ~10 h** → do not start it. Either split the work or make the pass resumable; see step 6.

Do the same for Roman-Urdu-Parl with `--limit 500000 --shingle-unit char`, where there is no
projection at all to check against.

Also watch **peak RSS** during the trial — the ~2,010 bytes/document figure is measured on FineWeb2
and may differ on Roman-Urdu-Parl's short rows:

```python
import resource; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, "GB")
```

---

## 5. The runs

Use **Save & Run All (Commit)**, not the interactive session — a committed run continues headlessly
after the browser closes, and `/kaggle/working` is persisted when it finishes.

**Sequentially, never concurrently.** Session 11 measured two passes over one file at ~50 minutes
where either alone was ~20, and here they would also contend for the 30 GB.

```python
!mkdir -p /kaggle/working/reports/freeze /kaggle/working/logs

# FineWeb2 — only if step 4 said it fits
!cd /kaggle/working && python /kaggle/input/<code-slug>/scripts/neardedup.py \
    --source fineweb2-urd_Arab --split train --limit 0 --single-pass --sweep 0.7 0.8 0.9 \
    --removals reports/freeze/removals_67_fineweb2.txt \
    --pairs-out reports/freeze/pairs_67_fineweb2.jsonl \
    --json reports/freeze/neardedup_fineweb2.json

# Roman-Urdu-Parl — char shingles, because its rows are single sentences
!cd /kaggle/working && python /kaggle/input/<code-slug>/scripts/neardedup.py \
    --source roman-urdu-parl --split train --limit 0 --shingle-unit char --single-pass \
    --removals reports/freeze/removals_67_roman.txt \
    --json reports/freeze/neardedup_roman.json
```

`--single-pass` halves the read by sketching during stage 6's phase 1 and dropping its removals
before banding. Verified equivalent to the two-pass form on the complete Wikipedia dump: 47 of 48
report fields identical, the 48th being `dropped_before_build` itself, and the 188 removed ids
byte-identical.

**Watch `largest_cluster` in the output.** Nothing caps a component's size; the reason to believe it
stays small at threshold 0.80 is a measurement on Wikipedia (23), and a source with heavier
templating can chain. It is the number that would say the threshold does not transfer.

---

## 6. If FineWeb2 does not fit

In preference order:

1. **Make the pass resumable.** The shard reader already checkpoints with a plan fingerprint; what
   is missing is serializing `MinHashDeduplicator`'s parallel arrays (`_ids`, `_sigs`, `_sizes`,
   `_chars`, `_sources`, `_eligible`, `_position`) and `ExactDeduplicator._best`. The sketches are
   already a flat byte array, so this is bounded work — and it is worth having regardless: today a
   pass that dies at 80% restarts from zero.
2. **Band-partition to disk** — write `(band key, doc id)` pairs, sort, compare within buckets. The
   standard large-scale approach; removes the in-memory requirement entirely.
3. **Rent a 32 GB box for a day** (~$2–8). Changes nothing about the instrument.

**Not an option: sampling.** Finding G — a pair statistic sampled at rate *r* is measured at *r²*,
and this pass exists to measure FineWeb2's self-similarity.

---

## 7. Bringing the results back

Download from the notebook's Output tab, or add the run's output dataset locally. What comes back is
**~10 MB and contains no corpus text**:

```
reports/freeze/removals_67_fineweb2.txt      # ids + read-plan header
reports/freeze/removals_67_roman.txt
reports/freeze/neardedup_fineweb2.json       # the full stage 6/7 report
reports/freeze/neardedup_roman.json
reports/freeze/pairs_67_fineweb2.jsonl       # measured pairs, to read
```

Drop them into `reports/freeze/` here and check they are accepted:

```bash
python scripts/split.py --source urdu-wikipedia --source fineweb2-urd_Arab --split train \
    --source roman-urdu-parl --limit 0 --measure-only \
    --exclude reports/freeze/removals_67_wikipedia.txt \
    --exclude reports/freeze/removals_67_fineweb2.txt \
    --exclude reports/freeze/removals_67_roman.txt \
    --plan-out reports/freeze/plan.json --heldout-out data/freeze/heldout.jsonl
```

If a header was computed over a different read it refuses by name and exits 1. If a source has no
list it says so rather than assuming it is clean.
