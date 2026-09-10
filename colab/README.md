# Running the stage 6+7 freeze passes on Google Colab

The two long passes — FineWeb2 (both train shards) and Roman-Urdu-Parl — need ~10 GB of RAM
(Finding X: stage 7's index measured ~2,010 bytes per document, not the ~980 the module documents).
The local machine has ~2 GB free of 16 GB.

**Kaggle was the plan and is fully built** (`kaggle/`, `reports/freeze_on_kaggle.md`). It is blocked
for a reason no amount of code fixes: a Kaggle notebook gets **no network without phone
verification**, which is not available on this account. Kaggle records `enable_internet: True`,
returns it on the live kernel, and still gives the container no DNS (Finding Z′). Colab has internet,
so `acquire.py fetch` reproduces the pinned corpus from HuggingFace and nothing is uploaded from a
home connection.

## What is riskier here than on Kaggle, and what is done about it

| | Kaggle | Colab |
|---|---|---|
| RAM | ~30 GB | **~12.7 GB** on a free CPU runtime |
| against a projection of | ~9–10 GB | ~9–10 GB |
| when RAM runs out | — | **process killed**; no pagefile to absorb it |
| network in notebook | needs phone verification | yes |
| corpus | fetch once, mount as a dataset | **re-fetched each session** (~7.7 GB) |
| disk | ~30 GB | ~100 GB |

Colab's margin over the projection is thin, and the projection is the thing Finding X already got
wrong by 2× in the direction that costs a day. So `freeze_colab.py` treats it as a measurement
rather than a fact:

- **`env`** prints the RAM the runtime actually reports, not a number from a doc.
- **`trial`** runs a timed prefix of each pass, projects hours *and* peak RSS to full size, and
  compares the memory projection against **80% of measured available RAM**. It refuses rather than
  warns.
- **A pass will not start without a passing trial on record.** `neardedup.py` is not resumable — the
  shard reader checkpoints, the MinHash index does not — so an OOM at 90% produces nothing at all.
  `--force` exists to override deliberately; there is no way to do it by accident.
- The trial and the real pass are built by one function, so they agree on every computational flag.
  A flag in the pass but not the trial means the projection authorised a different computation.

## Order

Runtime → **Change runtime type → CPU**. A GPU runtime buys nothing here (these passes never touch
one) and its session limits are tighter. High-RAM is a Colab Pro feature; if it is available, take
it — it removes the entire risk this page is about.

```python
# 1. Get the code there. Build ravaan-code.zip locally first:
#      git archive --format=zip -o ravaan-code.zip HEAD -- ravaan scripts configs colab \
#          pyproject.toml README.md
from google.colab import files
files.upload()                       # pick ravaan-code.zip — it is ~230 KB
!mkdir -p /content/ravaan && unzip -q -o ravaan-code.zip -d /content/ravaan
%cd /content/ravaan
```

```python
# 2. What this runtime actually has. Read it before spending a session on it.
!python colab/freeze_colab.py env
```

```python
# 3. Somewhere for the results to survive a disconnect.
from google.colab import drive
drive.mount('/content/drive')
```

```python
# 4. The corpus. ~7.7 GB, pinned to commit SHAs and SHA-256 verified as it streams.
!pip install -q "pyarrow>=17" "zstandard>=0.23"
!python colab/freeze_colab.py fetch
```

```python
# 5. THE GATE. Read its verdict before going further.
!python colab/freeze_colab.py trial
```

```python
# 6. The real passes — one per session, never both at once.
!python colab/freeze_colab.py fineweb2 --drive /content/drive/MyDrive/ravaan
```

```python
!python colab/freeze_colab.py roman --drive /content/drive/MyDrive/ravaan
```

`--drive` copies each pass's three outputs to Drive as soon as it finishes, because a Colab session
that disconnects takes `/content` with it.

## If the trial says a pass does not fit

Do not run it. In preference order:

1. **Make `neardedup.py` resumable.** The shard reader already checkpoints against a plan
   fingerprint; what is missing is serializing `MinHashDeduplicator`'s parallel arrays (`_ids`,
   `_sigs`, `_sizes`, `_chars`, `_sources`, `_eligible`, `_position`) and `ExactDeduplicator._best`.
   Bounded work, and worth having regardless: today a pass that dies at 80% restarts from zero.
2. **Band-partition to disk** — write `(band key, doc id)`, sort, compare within buckets. Colab has
   ~100 GB of disk, which is precisely the resource this runtime has spare and the local machine
   (5.6 GB free) does not.
3. **Rent a 32 GB box for a day**, ~$2–8 against a $150 cap with $0 spent.

**Sampling is not an option.** Finding G: a pair statistic sampled at rate *r* is measured at *r*²,
and these passes exist to measure self-similarity.

## Things to know before you start

- **The session re-fetches the corpus.** `acquire.py fetch` has no `--source`, so all 7.7 GB comes
  down each session, and `check_read_plans()` needs all three sources present anyway. On Colab's
  network this is minutes, not hours. If it proves slow, adding `--source` to `_cmd_fetch` is a
  small change — deliberately not made now, with a freeze pending.
- **Keep the tab open.** Colab disconnects idle sessions well before the ~12 h cap, and the pass has
  no resume. `SAFE_HOURS` is 9.0 for that reason.
- **The read plans must match**, and `fetch` checks them: `8743e78c000775aa` (Wikipedia),
  `54b744f92e3949f8` (FineWeb2), `db3a15522463a364` (Roman-Urdu-Parl). These are hashes of
  `[source, path, sha256]` and never of a local path, so any machine with the same pins reproduces
  them — and a mismatch means every removal list the session writes would be refused by `--exclude`
  back home. Pinned in `tests/test_colab_freeze.py`.
- **Watch `largest_cluster`** in each report. Nothing caps a component's size; the only evidence
  that threshold 0.80 does not chain is a measurement on Wikipedia (23). A source with heavier
  templating can chain, and that number is what would say the threshold does not transfer.
- **Wikipedia is already frozen** locally — `reports/freeze/removals_67_wikipedia.txt`, 188 ids.
  Colab only owes the other two.

## Bringing the results back

Three files per pass, ~10 MB total, no corpus text:

```
reports/freeze/removals_67_fineweb2.txt      # ids, with a read-plan header
reports/freeze/pairs_67_fineweb2.jsonl       # measured pairs, to read
reports/freeze/neardedup_fineweb2.json       # the full stage 6/7 report
```

Drop them into `reports/freeze/` here, then check they are accepted — a header computed over a
different read is refused by name rather than silently applied:

```bash
python scripts/split.py --source urdu-wikipedia --source fineweb2-urd_Arab \
    --source roman-urdu-parl --split train --limit 0 --measure-only \
    --exclude reports/freeze/removals_67_wikipedia.txt \
    --exclude reports/freeze/removals_67_fineweb2.txt \
    --exclude reports/freeze/removals_67_roman.txt \
    --plan-out reports/freeze/plan.json --heldout-out data/freeze/heldout.jsonl
```

Then stage 8, then stage 10 — both take the same `--exclude` lists. `reports/freeze_on_kaggle.md`
§7 and `progress.md`'s "Next session" carry the rest of the order; only the *host* changed.
