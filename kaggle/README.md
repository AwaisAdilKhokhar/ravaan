# Kaggle freeze runners

The stage 6+7 freeze passes for FineWeb2 and Roman-Urdu-Parl need ~10 GB of RAM (Finding X) and
run on Kaggle's CPU notebooks. [`reports/freeze_on_kaggle.md`](../reports/freeze_on_kaggle.md) is
the runbook and the reasoning; this directory is that runbook executed.

| File | What it is |
|---|---|
| `push.py` | Driver — uploads the code dataset, pushes kernels, polls, pulls results back |
| `mount_bootstrap.py` | The canonical mount-discovery block. Never imported; copied into each kernel |
| `diag_input.py` | Prints what is actually mounted. Settled Finding Z in one minute |
| `freeze_00_fetch_and_trial.py` | Fetches the corpus **and** times both passes. A decision gate |
| `freeze_01_fineweb2.py` | Stage 6+7 over FineWeb2 both train shards, unsampled |
| `freeze_02_roman.py` | Stage 6+7 over Roman-Urdu-Parl train, char shingles, unsampled |

## Order

```bash
kaggle auth login                     # one-time, interactive, opens a browser
#  ... and Settings -> Phone Verification on kaggle.com, or the notebook gets no network
python kaggle/push.py code            # upload ravaan-code.zip as a private dataset
python kaggle/push.py push 00         # fetch + trial
python kaggle/push.py status 00
python kaggle/push.py logs 00         # read the verdict
python kaggle/push.py push 01         # refuses while 00 is not COMPLETE
python kaggle/push.py pull 01
```

Both manual steps are one-time and neither is automatable: the login opens a browser, and phone
verification is an account property. Everything else refuses rather than misbehaves.

## Why 00 is a gate and not a formality

`neardedup.py` is **not resumable**. The shard reader checkpoints with a plan fingerprint, but the
MinHash index lives in memory and dies with the session. A pass that overruns the ~12 h cap
produces nothing at all — not a partial result, nothing. FineWeb2 projects to 9–14 h, which
straddles the cap, and Roman-Urdu-Parl had no projection at all before this trial (a two-point cost
model fitted to Wikipedia and FineWeb2 returns a *negative* per-document cost).

If a pass does not fit, the options in preference order are: make the pass resumable, band-partition
to disk, or rent a 32 GB box for a day. **Sampling is not one of them** — Finding G, a pair
statistic sampled at rate *r* is measured at *r*², and these passes exist to measure
self-similarity.

## Why the results come back valid

`ShardReader.plan_fingerprint()` hashes source-relative paths and digests, never local paths, so a
removal list written on Kaggle is accepted by `--exclude` here with no editing — and refused by
name if it was computed over a different read. Verified identical on both machines:
`54b744f92e3949f8`.

Let `acquire.py` write a fresh `data/manifest.json` on Kaggle rather than copying the local one.
The digests will match; the local paths should not, and the local manifest has Windows separators
baked into `local_path`, which is a single nonsense filename on Linux.

## Things that bit, so they do not bite again

Three of these cost a run each on 2026-09-10, and the first cost five weeks of not knowing.

- **A kernel's address comes from its *title*, not the slug in `id`** (Finding Y). Set them
  independently and the kernel lands somewhere `status`, `logs` and `pull` cannot reach — and the
  error blames permissions, so it reads like an auth problem. `title_for()` derives one from the
  other; `assert_ref_live()` checks the push landed where this file will look. The larger cost was
  ahead: 01 and 02 name 00 in `kernel_sources`, so under the drift they would have mounted no corpus
  and died after a ~12 h session was spent.
- **The mount is `/kaggle/input/datasets/<owner>/<slug>/`** (Finding Z), two levels below what
  Kaggle's docs and every tutorial say. Do not build that path — `find_mount()` searches for a
  marker file instead, because the layout is Kaggle's to change and a marker is a fact about this
  repo. `diag_input.py` is what answered this, after a wrong guess about a processing race.
- **`enable_internet: True` is not a network** (Finding Z′). Kaggle stores the flag, returns it on
  the live kernel, and still gives an unverified account no DNS. The symptom is `socket.gaierror`
  thirty lines into a urllib traceback. `freeze_00` resolves a hostname first and exits with the fix
  in the message.

- **No `pip install -e` of this project.** `/kaggle/input` is read-only; editable installs need to
  write `egg-info` there. The drivers bootstrap their own `sys.path` and the deciding code is
  stdlib-only, so only `pyarrow` is actually needed.
- **`RUSAGE_CHILDREN`, not `RUSAGE_SELF`,** for peak RSS. The pass is a subprocess; `SELF` measures
  the notebook and reports a reassuring ~0.
- **kaggle CLI 2.2.3 uses OAuth**, not `~/.kaggle/kaggle.json`. Most documentation you will find
  describes the old scheme.
- **Never run 01 and 02 concurrently.** Session 11 measured two passes over one file at ~50 minutes
  where either alone was ~20, and here they would also contend for the 30 GB.
- **Watch `largest_cluster`.** Nothing caps a component's size; the only evidence that 0.80 does not
  chain is a measurement on Wikipedia (23). A source with heavier templating can chain, and that is
  the number that would say the threshold does not transfer.
