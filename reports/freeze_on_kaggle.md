# Running the stage 6+7 freeze passes on Kaggle

> **⛔ This path is closed, and the reason is not fixable in code.** A Kaggle notebook gets no
> network without **phone verification**, which is not available on this account — Kaggle records
> `enable_internet: True`, returns it on the live kernel, and still gives the container no DNS
> (Finding Z′). **The freeze runs on Colab: see [`colab/README.md`](../colab/README.md).**
>
> Everything below stays accurate and is worth keeping. The kernels, the driver and its guards are
> built and tested (`kaggle/`, 20 tests), three of this project's findings came from getting them
> working, and §3 onward — read plans, the trial gate, what comes back and how it is checked — is
> host-independent. If phone verification ever becomes possible, `python kaggle/push.py push 00`
> is the whole of what is left here.

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
   the fetch needs it. **This is the step that is currently blocking the freeze**, and its symptom
   is not the one you would expect — see the box below.

   > **⚠️ An unverified account fails with a DNS error, not a permissions error.** Measured
   > 2026-09-10: kernel 00 was pushed with `enable_internet: true`, Kaggle **accepted the flag and
   > reported it back on the live kernel**, and the container still had no name resolution. The
   > fetch died 41 s in on `socket.gaierror: [Errno -3] Temporary failure in name resolution` under
   > thirty lines of urllib traceback, which name neither the internet nor verification. So
   > `enable_internet: True` in the metadata is **not** evidence that a notebook has a network — the
   > only evidence is a resolved hostname inside a run. `freeze_00` now checks that first and exits
   > with the fix in the message.
   >
   > **If phone verification is not possible on this account**, the fallback is to upload the corpus
   > itself as a private dataset from here (~7.7 GB over a home connection) instead of fetching it
   > there. Slow and dull, but it needs no network inside the notebook at all — and steps 4 onward
   > are unaffected, because they only read the mount.
2. In the notebook: **Settings → Accelerator: None** (this job never touches a GPU — a GPU session
   also has a *shorter* cap) and **Internet: On**.
3. **Log in to the CLI:** `kaggle auth login`. Session 15 note — the installed CLI is **2.2.3**,
   which authenticates by **OAuth**, not the `~/.kaggle/kaggle.json` username+key pair that older
   docs (and most search results) describe. `KAGGLE_API_TOKEN` or `~/.kaggle/access_token` are the
   non-interactive alternatives. Every subcommand, including `config view`, refuses until this is
   done.

Check the current limits on Kaggle's docs rather than trusting the figures here; they move.

**Steps 1–7 below are automated** by `kaggle/push.py` and the three kernel scripts beside it, which
encode everything in this document. The runbook remains the explanation; run
`python kaggle/push.py` for the commands. Only the account signup, the OAuth login and the phone
verification are irreducibly manual.

**Two things `push.py` now refuses rather than lets you do**, both learned by doing them:

- **A kernel's address comes from its *title*, not from the slug in `id`.** Session 15 set the two
  independently, so all three kernels landed at addresses `status`, `logs` and `pull` then queried
  with the other string and got a 403 — which is how kernel 00's first failure sat unread for five
  weeks. Worse was still ahead: 01 and 02 name 00 in `kernel_sources`, so under the drift they would
  have mounted **no corpus** and died after their session was already spent. `title_for()` now
  derives one from the other, and `assert_ref_live()` checks the pushed kernel is reachable at the
  address this file will ask for.
- **A dataset must finish processing before a kernel is pushed against it.** `wait_for_dataset()`
  polls `datasets status` until it reports `ready` (403 means it does not exist). This was not
  what broke the first run — the mount path was — but a kernel started against an unprocessed
  dataset mounts nothing and fails identically, so the guard stays.

---

## 1. Get the repo there

No git remote exists for this project, so either:

**(a) Upload as a private Kaggle Dataset — no GitHub needed.** From the repo root:

```bash
git archive --format=zip -o ravaan-code.zip HEAD -- ravaan scripts configs pyproject.toml README.md
```

Then Kaggle → Datasets → New Dataset → upload `ravaan-code.zip`, private. Kaggle extracts the
archive, so the dataset mounts read-only as the repo tree.
**`data/manifest.json` is deliberately not in that archive** — see step 3.

> **⚠️ The mount is not where the documentation says it is.** Measured 2026-09-10 by a kernel whose
> only job was to print the tree (`kaggle/diag_input.py`): a dataset attached to a script kernel
> arrives at
> ```
> /kaggle/input/datasets/<owner>/<slug>/scripts/neardedup.py
> ```
> — **two levels deeper** than the `/kaggle/input/<slug>/` that Kaggle's docs, every tutorial, and
> earlier drafts of this runbook describe. Kernel 00 failed twice on that assumption, one second
> into each run, with the dataset correctly attached and reporting `ready` the whole time. Every
> kernel now locates the mount by searching for a file it must contain
> (`kaggle/mount_bootstrap.py`), so the depth is never assumed again. Do not hardcode either form.

**(b) Push to GitHub and `!git clone`.** Also finally exercises `.github/workflows/tests.yml`, which
has never run because there is no remote.

---

## 2. Save the corpus as a Kaggle Dataset, so it is fetched once

The corpus is ~6.5 GB (FineWeb2 both train shards) plus ~1.2 GB (Roman-Urdu-Parl train). Fetching
it inside every session wastes session time against the cap, and the cap is the binding constraint.
Fetch it once into `/kaggle/working`, then **Save Version → output as a Dataset**, and mount that
dataset read-only in every later session.

```python
!pip install -q "pyarrow>=17" "zstandard>=0.23"
!cd /kaggle/working && python /kaggle/input/datasets/<owner>/<code-slug>/scripts/acquire.py fetch
!cd /kaggle/working && python /kaggle/input/datasets/<owner>/<code-slug>/scripts/acquire.py verify
```

**There is no project install step, and the `pip install -e` this used to prescribe would have
failed.** `/kaggle/input` is a read-only mount and an editable install has to write `egg-info`
into it. None is needed: every driver in `scripts/` does its own
`sys.path.insert(0, parents[1])`, and the package that *decides* anything is stdlib-only by
design (§`pyproject.toml`). Only `pyarrow` is genuinely required, to read parquet — and Kaggle's
image ships it, so the line above is belt-and-braces.

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

**All three, measured on this machine 2026-09-10** (`neardedup.py --source <s> --limit 1` prints the
plan on its first line). Roman-Urdu-Parl's was never recorded before, and Wikipedia's is
independently corroborated as the header of session 14's frozen `removals_67_wikipedia.txt`:

| source | files | plan |
|---|---|---|
| `urdu-wikipedia` | 1 | `8743e78c000775aa` |
| `fineweb2-urd_Arab` (train) | 2 | `54b744f92e3949f8` |
| `roman-urdu-parl` (train) | 1 | `db3a15522463a364` |

`freeze_00` now checks all three after the fetch and **refuses the session on a mismatch**, because
a differing plan means every removal list that session would write is refused by name when
`--exclude` reads it back here — a ten-hour pass for nothing. The line this replaced was
`neardedup.py --limit 1` with no `--source`, which is a required argument: it would have exited 2
under `check=True` and killed the kernel in the minute after the 7.7 GB fetch. Nothing in a push
validates the code it uploads.

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
    "python", "/kaggle/input/datasets/<owner>/<code-slug>/scripts/neardedup.py",
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
import resource; print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e6, "GB")
```

**`RUSAGE_CHILDREN`, not `RUSAGE_SELF`** — the pass runs in a subprocess, so `SELF` measures the
notebook, reports ~0, and looks exactly like the memory problem having gone away. This is the
number Finding X is about; reading the wrong process would be the quietest possible way to lose it.

---

## 5. The runs

Use **Save & Run All (Commit)**, not the interactive session — a committed run continues headlessly
after the browser closes, and `/kaggle/working` is persisted when it finishes.

**Sequentially, never concurrently.** Session 11 measured two passes over one file at ~50 minutes
where either alone was ~20, and here they would also contend for the 30 GB.

```python
!mkdir -p /kaggle/working/reports/freeze /kaggle/working/logs

# FineWeb2 — only if step 4 said it fits
!cd /kaggle/working && python /kaggle/input/datasets/<owner>/<code-slug>/scripts/neardedup.py \
    --source fineweb2-urd_Arab --split train --limit 0 --single-pass --sweep 0.7 0.8 0.9 \
    --removals reports/freeze/removals_67_fineweb2.txt \
    --pairs-out reports/freeze/pairs_67_fineweb2.jsonl \
    --json reports/freeze/neardedup_fineweb2.json

# Roman-Urdu-Parl — char shingles, because its rows are single sentences.
# NO --single-pass here: see below.
!cd /kaggle/working && python /kaggle/input/datasets/<owner>/<code-slug>/scripts/neardedup.py \
    --source roman-urdu-parl --split train --limit 0 --shingle-unit char \
    --removals reports/freeze/removals_67_roman.txt \
    --pairs-out reports/freeze/pairs_67_roman.jsonl \
    --json reports/freeze/neardedup_roman.json
```

**`--single-pass` on FineWeb2, not on Roman-Urdu-Parl** — this snippet carried it on both until
2026-09-10, against the reasoning in its own next paragraph and against `freeze_02_roman.py`, which
never had it. Two reasons it stays off there, and the second is the one that settles it:

1. Peak memory under `--single-pass` rises with the source's exact-duplicate rate — nil on FineWeb2
   (Finding H), but ~2× on 6.37M Roman rows collapsing toward 3.48M distinct.
2. **Kernel 00's trial measures Roman-Urdu-Parl in the two-pass form.** A run that differs from the
   pass that authorised it is not covered by that authorisation — and the authorisation is a
   projection against a hard, unresumable session cap.

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
