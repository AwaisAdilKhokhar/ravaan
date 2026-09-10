# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read the "Next session" section at the bottom
first.**

- **Started:** 2026-08-03 (Week 1 of 16)
- **Current phase:** Weeks 1–2 complete → Weeks 3–4, corpus freeze. Pipeline stages 1–9 are built
  and validated on real text; stage 5's 200-sample validation is adjudicated, scored and written up
  ([`reports/quality_validation.md`](reports/quality_validation.md)), stage 6 has run **complete
  passes over every source**, stage 7's threshold is chosen from measured pairs and written up
  ([`reports/neardedup_threshold.md`](reports/neardedup_threshold.md)), and stage 8's instrument and
  thresholds are chosen the same way ([`reports/decontamination.md`](reports/decontamination.md)).
  **Session 11 built stage 9 and ran the decontamination pass it was blocking**
  ([`reports/splits.md`](reports/splits.md)) — and found that PRD §6.1 and §4.3 disagree about what
  U counts, in a direction that would have put arm A 6× short of the crossover (Finding R).
  **Session 12 paid that debt: PRD v2.2 is amended**, and tightening Gate G1 to match it found that
  the gate reported `pass` on a corpus from which arm B cannot be assembled (Finding U). It also
  **built stage 10, the last pipeline stage** ([`reports/packing.md`](reports/packing.md)), fetched
  FineWeb2 shard 000, and measured the corpus that resulted: **Gate G1 now returns `PASS` on both
  the aggregate and the mixture, with both arms fundable.** **Session 13 built the PII pass**
  ([`reports/pii.md`](reports/pii.md)) — the last unbuilt thing in §6.3 — and reading its matches
  found that 11 of its first 13 phone hits on Wikipedia were ISBNs (Finding V). **Session 14 went
  to start the freeze and found the freeze order was not runnable** (Finding W): every driver runs
  stages 2–5 and then its own stage, and none of them chains — stages 6, 7 and 8 each *wrote* a
  removal list and stages 9 and 10 could not *read* one. Stage 10 would have packed a corpus that
  had been through no dedup and no decontamination. `ravaan/data/exclusions.py` is the missing
  hand, and **Urdu Wikipedia is now frozen through stage 7** — 188 ids, reproducing sessions 8 and
  9 exactly. Then **Finding X: stage 7's index costs 2× what the module documents**, so FineWeb2
  needs ~10 GB against this machine's 0.9 GB free. **The freeze moves to Kaggle** —
  [`reports/freeze_on_kaggle.md`](reports/freeze_on_kaggle.md).
  **Session 16 (2026-09-10, after a five-week gap) made the Kaggle side work and found three
  reasons it had not.** Kernel 00 had errored on 2026-08-06 and the failure was unreadable because
  a kernel's address comes from its *title*, not the slug in `id` (Finding Y). Fixed, re-pushed, and
  it failed again: the mount is `/kaggle/input/datasets/<owner>/<slug>/`, two levels below what
  Kaggle's own docs describe (Finding Z) — settled in one minute by a kernel that printed the tree.
  Fixed as a class; third push reached the fetch and died on DNS, because `enable_internet: True` is
  recorded and returned by the API while an unverified account gets no network (Finding Z′).
  A fourth bug was found by running the driver locally instead of on Kaggle: the read-plan check
  was `neardedup.py --limit 1` with no `--source`, which is required, so it would have exited 2 in
  the minute after a 7.7 GB fetch. **Then phone verification turned out not to be available, which
  closes the Kaggle path for good — and the freeze moved to Colab**
  ([`colab/README.md`](colab/README.md)). Colab has internet, so the fetch works as designed; what
  it does not have is Kaggle's ~30 GB, so `colab/freeze_colab.py` is built around a memory gate that
  refuses any pass projecting past 80% of measured available RAM. Both passes' flag sets were
  exercised against the real corpus at `--limit 2000` before anything was trusted to a session.
  **Everything is built and tested. What remains is running it, which needs a browser and someone
  to keep the tab open.**
- **Gate G0:** ✅ **PASSED** 2026-08-03 — comparison confirmed unpublished. See
  [`reports/literature_review.md`](reports/literature_review.md).
- **Design decision:** ✅ **Option 2 (two-point law) chosen** 2026-08-03. U ∈ {25M, 100M}; 3 seeds
  at 25M, 1 at 100M. PRD amended to v2.1; preregistration committed.
- **Preregistration:** ✅ committed [`reports/preregistration.md`](reports/preregistration.md) —
  4 falsifiable predictions, before any training.
- **PRD version:** **v2.2** (2026-08-05) — §0.2 amends §6.1, §4.3, §8.2, §10 and §11 for Finding R.
- **Spend to date:** $0.00 of $150 hard cap
- **Tests:** 682 passing (72 splits · 70 pii · 69 normalization · 60 decontamination · **57 minhash**
  · 57 encoding · 57 acquisition · 51 packing · **44 dedup** · 43 quality · 32 langid ·
  **20 exclusions** · 18 shards · **20 kaggle** · **12 colab**). The exclusion file carries the first
  driver-level tests in the suite; the kaggle file is the first to cover the boundary between this
  repo and the machine the freeze runs on.
- **Committed** through session 16, on branch `stages-7-and-8` (main is at session 8;
  fast-forward it when convenient). Session 15's Kaggle work was written 2026-08-06 and left
  uncommitted; session 16 committed it together with the three fixes it needed. Sessions 6 and 7 are one commit — stage 5, its 200-sample validation and the
  write-up are one deliverable. Sessions 9–14 are one commit each: stage 7, stage 8, stage 9 with
  the second stage-8 run, stage 10 with the PRD v2.2 amendment, and the PII pass. Session 14 is
  five: the exclusion chain, its write-up, the eval-side redaction, the header guard, and the
  single-pass driver.

---

## Status board

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⛔ blocked

### Weeks 1–2 — lit review + acquisition
| Item | PRD | Status |
|---|---|---|
| Repo scaffold, packaging, license, CI-able test suite | §13 | ✅ |
| Literature review → `reports/literature_review.md` (**G0**) | §11 | ✅ |
| Verify Finding A against typeset PDF | — | ✅ |
| Act on Findings A & B — PRD amended to v2.1 | §0.1 | ✅ |
| Preregistration → `reports/preregistration.md` | §4.5 | ✅ |
| Source manifest + acquisition (stage 1), licence gate | §6.2, §6.3.1 | ✅ |
| FineWeb2 `urd_Arab` acquisition + checksums | §6.2, §6.3.1 | ✅ |
| Roman-Urdu-Parl acquisition + checksums | §6.2 | ✅ |
| Urdu Wikipedia dump acquisition + checksums | §6.2 | ✅ |
| Encoding validation (stage 2) | §6.3.2 | ✅ |
| Streaming shard reader (`ravaan/data/shards.py`) | §6.3 | ✅ |
| Language / script ID (stage 3) | §6.3.3 | ✅ |

### Weeks 3–4 — corpus freeze (**G1**: clean corpus ≥ 100M tokens — PRD v2.1 §11; was 150M in v2.0)
| Item | PRD | Status |
|---|---|---|
| **Urdu normalization (stage 4)** | §6.3.4 | ✅ |
| Arabic-variant spelling is site-correlated (Finding F) | §6.3.4 | ✅ answered |
| Quality filtering (stage 5) | §6.3.5 | ✅ |
| 200-sample validation — drawn, adjudicated, scored, written up | §6.3.5 | 🟡 native-speaker pass outstanding |
| **Exact dedup (stage 6)** | §6.3.6 | ✅ |
| Full passes: Wikipedia, Roman-Urdu-Parl (both columns), FineWeb2 ∩ Wikipedia | §6.3.6 | ✅ |
| **MinHash near-dedup (stage 7)** | §6.3.7 | ✅ |
| Threshold chosen from measured pairs + sweep → `reports/neardedup_threshold.md` | §6.3.7 | ✅ |
| Full passes: Urdu Wikipedia; Wikipedia × FineWeb2's wiki-host documents | §6.3.7 | ✅ |
| Full passes: FineWeb2 self-similarity, Roman-Urdu-Parl (char shingles) | §6.3.7 | ⬜ deferred to freeze (~2.3 h) |
| **Eval decontamination (stage 8)** | §6.3.8 | ✅ |
| Instrument + thresholds chosen from read hits → `reports/decontamination.md` | §6.3.8 | ✅ |
| Acceptance test: Roman-Urdu-Parl test-in-train, both columns | §6.2, §6.3.8 | ✅ |
| Full passes: Urdu Wikipedia (complete); FineWeb2 at 5% | §6.3.8 | ✅ |
| Full pass: FineWeb2 complete shard | §6.3.8 | ⬜ deferred to freeze |
| Second stage-8 run, against the held-out split | §6.3.8 | ✅ 15/6,748 held-out items at 5%; ~4.4% projected |
| **Split creation (stage 9)** | §6.3.9 | ✅ |
| What U counts — §6.1 vs §4.3 resolved (Finding R) | §4.3, §6.1 | ✅ answered |
| **PRD amended to v2.2 for Finding R** | §0.2, §4.3, §6.1, §8.2, §10, §11 | ✅ |
| Gate G1 checks per-population sufficiency, not just the total (Finding U) | §11 | ✅ |
| FineWeb2 train shard 000 fetched + verified — the code-switched fix | §6.2 | ✅ 4.84 GB |
| **Gate G1 measured over both FineWeb2 shards** | §11 | ✅ **PASS**, both arms fundable |
| Full passes: Urdu Wikipedia (complete); FineWeb2 at 5% | §6.3.9 | ✅ |
| One unsampled pass over **all** sources together | §6.3.9 | ⬜ deferred to freeze |
| **Tokenization + packing (stage 10)** | §6.3.10 | ✅ |
| Real pass: Wikipedia → 7 shards, verified off disk | §6.3.10 | ✅ |
| Fertility measured with §7's tokenizer, stage 9 re-solved | §6.3.10, §7 | ⬜ **Week 5** |
| **PII regex pass (phones, emails)** | §6.3 | ✅ |
| Wired into all five drivers, between stage 5 and stage 6 | §6.3 | ✅ |
| Real passes: Wikipedia, FineWeb2, Roman-Urdu-Parl → `reports/pii.md` | §6.3 | ✅ 56,214 documents |
| 11 of 13 first Wikipedia phone matches were ISBNs (Finding V) | §6.3 | ✅ fixed, re-measured |
| Eval sets must go through the same redaction before stage 8 | §6.3.8 | ✅ both loaders, measured |
| **Stages 9 and 10 could not read a removal list (Finding W)** | §6.3 | ✅ `--exclude`, 17 tests |
| Removal lists carry the read plan they were computed over | §6.3 | ✅ refuses a mismatch |
| cp1252 hole closed as a class — `ravaan/console.py`, all 12 entry points | — | ✅ |
| **Freeze run: stage 6+7, complete Urdu Wikipedia** | §6.3.6, §6.3.7 | ✅ 188 ids, 118 clusters |
| PII pass did not move stage 6 or 7 on Wikipedia — measured, not assumed | §6.3 | ✅ 9 groups, 118 clusters |
| Single-pass stage 6+7 (`--single-pass`) — one corpus read, not two | §6.3.7 | ✅ 12 tests |
| Single-pass verified against the two-pass run on the complete dump | §6.3.7 | ✅ 47/48 fields identical |
| **Freeze run: stage 6+7, FineWeb2 both train shards** | §6.3.7 | ⛔ **needs ~10 GB (Finding X)** |
| Freeze run: stage 6+7, Roman-Urdu-Parl (`--shingle-unit char`) | §6.3.7 | ⛔ same wall |
| Kaggle runbook for both → `reports/freeze_on_kaggle.md` | §6.3.7 | ✅ |
| Kaggle runners: `push.py` + three kernels, driven from here | §6.3.7 | ✅ |
| Code dataset uploaded, extracted, byte-exact against HEAD | §6.3.7 | ✅ 49 files |
| Kernel address comes from the title, not `id`'s slug (Finding Y) | — | ✅ derived + asserted |
| Mount is `/kaggle/input/datasets/<owner>/<slug>` (Finding Z) | — | ✅ searched, not built |
| `enable_internet: True` is not a network (Finding Z′) | — | ✅ preflight in kernel 00 |
| **Kaggle phone verification** | — | ⛔ **not available — Kaggle path closed** |
| **Freeze re-hosted on Colab** → `colab/README.md` | §6.3.7 | ✅ driver + 8 tests |
| Colab memory gate: refuses a pass over 80% of measured RAM | §6.3.7 | ✅ |
| Both passes' flag sets validated on real corpus at `--limit 2000` | §6.3.7 | ✅ |
| Colab run: `trial` — fineweb2 refused (11.69 h, 12.7 GB), roman `FITS` | §6.3.7 | ✅ |
| **Freeze run: stage 6+7, Roman-Urdu-Parl, complete** | §6.3.7 | ✅ 1.38 h, 4,307,848 ids |
| Its 82% character loss is genuine near-duplication (Findings AA, AB) | §6.3.7 | ✅ read, not inferred |
| **roman_urdu cannot fund arm B — 0.44x** | §11 | ⛔ **PRD decision open** |
| Freeze run: stage 6+7, FineWeb2 both shards | §6.3.7 | ⬜ **needs a rented 32 GB box, ~$2-4** |
| `neardedup.py` resumability | §6.3.7 | ⬜ not needed if FineWeb2 runs on a rented box |
| `--safe-hours`, so a capless host need not `--force` past the memory gate | §6.3.7 | ✅ 2 tests |
| Both passes carry `--sweep`, floor asserted (Finding AC) | §6.3.7 | ✅ 2 tests |
| Corpus manifest + statistics | §6.3 | 🟡 acquisition manifest done; stage stats pending |

### Weeks 5–16
All ⬜. Tokenizer (W5) → backbone + objectives (W6–7, **G2**) → 20M pilots (W8, **G3**) →
core runs (W9–11, **G4**) → automatic eval (W12) → human eval (W13, **G5**) → demo (W14) →
report and release (W15–16).

---

## Session log

### Session 1 — 2026-08-03

**Done**

1. **Repo scaffold** matching PRD §13: `configs/ ravaan/{data,tokenization,models/{ar,diffusion},training,sampling,evaluation}/ tests/ scripts/ demo/ reports/`.
   - `pyproject.toml` — package metadata, ruff + pytest config, dependency *extras* (`data`,
     `tokenizer`, `train`, `dev`) rather than a flat requirement list.
   - `LICENSE` (Apache-2.0), `README.md`, `.gitignore` (corpus and checkpoints never committed,
     per the §6.3 release policy).

2. **Urdu normalization — corpus pipeline stage 4** (`ravaan/data/normalization.py`, 67 tests).
   This is the component every later stage depends on: dedup hashes, quality thresholds, the
   tokenizer, and every corruption task all read post-normalization text, so a bug here silently
   contaminates the whole comparison. Built first for that reason.
   - `normalize_text()` — fast path (`str.translate` + regex) for the full corpus run.
   - `normalize()` — same output plus per-rule counts; `NormalizationResult` carries original,
     normalized, and log, as §6.3.4 requires.
   - `NormalizationLog` — corpus-level aggregation, JSON-serializable straight into the manifest.
   - `NormalizationConfig` — every transform individually switchable, with a `fingerprint()` hash
     over version + settings that goes into the manifest. Shipped defaults live in
     `configs/data/normalization.json`, and a test asserts the file matches the code defaults.
   - CLI: `python scripts/normalize.py input.txt -o out.txt --log log.json` (also installed as
     `ravaan-normalize`).

**Decisions made**

| Decision | Rationale |
|---|---|
| **NFKC only inside U+FB50–U+FDFF and U+FE70–U+FEFC**, character-by-character | The PRD's "never apply NFKC blindly" in code. Global NFKC rewrites `x²`→`x2`, `ﬁ`→`fi`, `½`→`1⁄2` — none of which is Urdu normalization — while failing to unify the Yeh/Kaf/Heh variants Urdu actually needs. Locked by `test_nfkc_is_not_applied_globally`. |
| Fold Heh (`ه`→`ہ`) and Alef (`أ إ ٱ`→`ا`) as well as the PRD's Yeh/Kaf list | The PRD list is representative, not exhaustive. `ه` vs `ہ` is the single most common spelling variation in Urdu web text; leaving it would put the same word in two vocabulary entries. Both are separately switchable so the choice stays auditable. |
| **Never fold** `ے ۓ ھ آ ئ ء` | Distinct graphemes. `ہے`≠`ہی`, `کھانا`≠`کہانا`, `آم`≠`ام`. A normalizer that folds bari ye has destroyed the language to tidy a metric. Every one is a parametrized preservation test. |
| Digits → ASCII by default (switchable to `urdu` / `keep`) | Three digit families for one meaning wastes a 16k vocab. |
| Harakat preserved by default (opt-in removal) | They are information, not noise. Removing them is a corpus decision the config should own, not a default. |
| ZWNJ removed (switchable) | Morphemic in Persian, overwhelmingly web noise in Urdu, which writes real spaces. |
| Core package has **zero** runtime dependencies | Keeps the one component everything depends on auditable. torch/datasets/sentencepiece are opt-in extras. |

**Measured**

- Fast path ≈ 2.7 Mchar/s single-threaded; logging path ≈ 1.6× slower. A ~1.5 GB corpus is
  therefore ~9 minutes single-threaded, once, at freeze time. Fine — not optimizing.
- Verified on realistic dirty Urdu: Arabic-keyboard letters, BOM, kashida, Arabic-Indic digits,
  bidi marks, presentation forms and ZWNJ all handled; Urdu-specific letters untouched.

**Fixed during the session**

- U+FEFF (BOM) sits inside the Forms-B block and was being counted as both `presentation_forms`
  and `zero_width`, inflating the manifest. Range now stops at U+FEFC. Regression test added.

**Not committed to git.** The repo still has zero commits; say the word and I'll make the initial
commit (and, if you want it, add a GitHub remote + CI workflow).

### Session 2 — 2026-08-03

**Done**

1. **Initial commit** (`afa0cc9`) — 20 files, 1,792 lines. Caught a `.gitignore` bug while staging:
   a bare `data/` pattern matches at *any* depth, so it silently excluded `ravaan/data/` (the whole
   normalization module) and `configs/data/`. Anchored to `/data/`. Added `.gitattributes` pinning
   `eol=lf` — CRLF drifting into a corpus file would change its checksum.

2. **Literature review → `reports/literature_review.md`. Gate G0 PASSES on novelty.**
   No masked diffusion LM for Urdu exists; the data-constrained diffusion result has not been
   replicated outside English. The precise claim that is now supportable in writing, with its
   hedge and search date, is in §8.1 of the review.

3. **`scripts/crossover.py`** — reproduces the review's compute arithmetic from the reference
   paper's fitted scaling law.

**Two findings that outrank the novelty verdict**

- **Finding A — the planned budget is ~125× below the predicted crossover.** Applying
  Prabhudesai et al.'s own fitted law to PRD §4.3/§5 (70M params, U = 300M, 33 epochs = 4.16e18
  FLOPs) against C_crit(300M) = 5.19e20 FLOPs. Reaching the crossover at U = 300M would take
  ~4,120 epochs. **PRD §4.3's claim that "epoch 33 is deep into the regime where the diffusion
  advantage is predicted to appear" is incorrect by two orders of magnitude.** As specified, the
  headline experiment returns "no crossover" predictably — a null by construction, the same class
  of flaw v2 was written to remove from v1.
  - The reading is trustworthy: the paper's *own* max budget lands at 1.01× its *own* crossover.
  - **U is free.** Compute is parameters × tokens processed; how much unique data those 10B tokens
    are drawn from costs nothing. At the same compute, U = 25M reaches 1.78× past the crossover.

- **Finding B — "naturally data-constrained" does not hold at 70M params.** UrduLM (arXiv:2601.17664,
  Jan 2026) released a 33 GB / ~5–6B-token Urdu corpus. Chinchilla-optimal for 70M is ~1.4B tokens,
  so Urdu has ~4× more data than the model can use. PRD §1's contrast — English *artificially*
  subsampled vs Urdu *naturally* constrained — does not survive. This does settle §6.1's "could we
  have collected more" question on the record: **capping is deliberate.**

**Decisions made**

| Decision | Rationale |
|---|---|
| Every load-bearing number tagged ⚠️VERIFY in the review | The `C_crit` constants and one half-life value came from automated extraction of HTML/blog, not the typeset PDF, and two sources disagreed ~2× on the AR half-life. A gate document that hides its own uncertainty is worse than no gate. |
| Review states its own search limits explicitly | "No Urdu diffusion LM found" across seven query families is not proof none exists; regional venues are under-indexed. The novelty claim carries a hedge and a search date. |
| MARIA (arXiv:2502.06901) flagged as prior art | It reports properly-equipped AR beating discrete diffusion at infilling. PRD §4.1's fairness argument is real but **not novel**, and the A2 ablation is weaker without citing it. |

---

## ✅ Decision taken 2026-08-03 — Option 2 (two-point law)

Findings A and B are one problem seen twice: the PRD picked a model size at which Urdu is not
data-constrained, so the unique-data budget must be chosen artificially regardless. Because U costs
nothing, this was fixable at **zero additional GPU spend** — only run *count* changed.

| Option | Design | Reaches crossover? | Cost |
|---|---|---|---|
| 0. Unchanged | U = 300M, 33 epochs | No (0.01×) | 6 core runs |
| 1. Retarget U | U = 25M, ~400 epochs, 3 seeds | Yes (1.78×) | 6 core runs |
| **2. Two-point law** *(recommended)* | U ∈ {25M, 100M}; 3 seeds at 25M, 1 at 100M | Yes at 25M, brackets at 100M | 8 core runs |
| 3. Scale model up | ~300M params | Yes | Far over $150 |

Option 2 keeps the 3-seed protocol on the primary endpoint and brackets the crossover so its
*location* — not just its sign — can be tested against the English fit. Full reasoning: review §8.
**Applied** in PRD v2.1 §0.1 and `reports/preregistration.md`.

---

### Session 3 — 2026-08-03 (same day)

**Done**

1. **Verified Finding A against the typeset PDF** (`pymupdf`; the automated PDF reader had failed).
   **Finding A survives: 124× short**, essentially unchanged.
   - **Constant corrected.** The fit is `log10(U) = 0.460·log10(C) − 1.050` with **U in raw
     tokens**. The earlier draft's −7.052 was the same fit with U in millions
     (7.052 − 1.050 = 6.002 = log10(10⁶)), so every downstream number held — but the units had been
     unstated. The paper's closed form `C_crit = 2.12×10^1.956·U^2.174` agrees to **0.1%**; both are
     now implemented and cross-checked on every run of `scripts/crossover.py`.
   - **Half-life discrepancy resolved — it was never a contradiction.** ≈15 is *Muennighoff et al.'s*
     prior AR estimate, quoted for contrast; **31.93** is this paper's own AR fit; **512.85** is its
     diffusion fit. Cite 512.85/31.93 — the only like-for-like pair.
   - **The authors corroborate Finding A themselves.** At U = 500M they needed a **2.3B**-parameter
     model, ran **130 epochs**, and reported *no signs of convergence*. U in the hundreds of
     millions is not reachable at small scale.
   - **Bonus:** the paper's Table 5 lists a 74M config at `d_model 640, ffw 1664, kv 64, heads 10` —
     nearly identical to PRD §5's 70M spec. Ravaan's models line up with a row of the reference
     sweep; the report should say so.
   - **Bonus (a problem):** the authors note their hyperparameters, taken from Muennighoff et al.,
     "may provide a slight advantage to autoregressive models." Ravaan inherits this. Now handled
     explicitly in preregistration §6.

2. **PRD amended to v2.1** with a §0.1 changelog. Edits: §1 (research question reframed), §4.3
   (two-arm sweep), §4.4 (MARIA prior art), §4.5, §6.1 (corpus 300M → 120M), §9 (budget: 8 runs,
   ~$134), §10, §11 (G1, G4), §12, §14. Every correction is marked inline — nothing silently
   changed.

3. **`reports/preregistration.md` committed** — PRD §4.5's requirement, satisfied in Week 1 rather
   than Week 9. Four falsifiable predictions (P1–P4), a committed reading for **every** outcome
   combination including the one that indicates a bug, and §7 "what would make this report a
   negative result" written before any data exists.

**Decisions made**

| Decision | Rationale |
|---|---|
| Both arms placed **inside** the reference paper's fitted range U ∈ {25,50,100}M | Their law is *estimated* there; the 300M figure was an extrapolation. No Ravaan claim now depends on trusting the law outside where it was fitted — which also de-risks open item 2 (the OpenReview critique still unread). |
| Arm A's 25M corpus is a **seeded subsample of** the frozen 100M corpus, not a separate collection | The arms must differ in size and nothing else. Separately collecting 25M would confound U with source mix. |
| Preregistration commits a reading for the incoherent outcome (no cross in A, cross in B) | Naming it in advance as *"indicates a bug — debug, do not report"* is what stops it being rationalised into a finding later. |
| Budget rebalanced, not raised | 6 → 8 runs funded by trimming the failed-run contingency 80 → 60 GPU-h. Total ~$134, still under the $150 cap. Arm A's 3 seeds are named as the last thing to cut. |

**Still open:** OpenReview `W5Ht05jF4c` sits behind a browser-verification wall. The only critique
that would materially weaken Finding A is a reviewer disputing `C_crit` extrapolation — and keeping
both arms inside the fitted range largely neutralises that risk.

---

### Session 4 — 2026-08-03 (same day)

**Done**

1. **Corpus acquisition — stage 1** (`ravaan/data/acquisition.py`, `configs/data/sources.json`,
   57 tests). All three PRD §6.2 sources pinned to commit SHAs, every file carrying its SHA-256
   *before* download. Three properties it is built around:
   - **Pinning is enforced, not documented.** A `revision` that is not a 40-hex commit SHA is a
     hard load error. FineWeb2 and Wikipedia both move; `main` describes a different corpus every
     month, and the failure is silent unless something refuses to load it.
   - **Digests come from upstream, not from us.** HF stores large files in Git LFS, whose object
     id *is* the SHA-256 of the content. So the manifest states what the bytes should be rather
     than what we happened to download. `fetch_file` verifies as it streams, writes to `.part`,
     and renames only on a match — an interrupted run cannot leave a truncated file that looks
     complete to stage 2.
   - **The licence gate executes.** `LICENSES` encodes four terms per licence; a source whose
     licence forbids derivatives or commercial use *cannot enter* `sources`, only `rejected`.
     PRD §6.3's "one permissive checkpoint" is only as good as the most restrictive source, and
     that is exactly the check that gets made once during planning and then drifts.
   - CLI: `python scripts/acquire.py {plan,fetch,verify}`, with `--max-bytes` so the default
     fetch takes the smallest prefix that clears the target rather than all 8.3 GB.

2. **Encoding validation — stage 2** (`ravaan/data/encoding.py`, 57 tests). Strict UTF-8 decode,
   mojibake detection *and repair*, replacement-character and control-byte rates, per-document
   verdicts, corpus-level log for the manifest. Still zero runtime dependencies.
   - Mojibake matters far more for Urdu than for English: every Arabic-script codepoint is a
     2-byte UTF-8 sequence, so a page served with a Latin-1 charset header contains **no Urdu
     characters at all**. Stage 3 would score it as European and drop it; stage 5's Urdu-script
     ratio would agree. These documents are fully recoverable, so stage 2 repairs them.
   - Repair is a byte-exact cp1252→UTF-8 round trip, iterated for the double-encoded case, and
     accepted only when it measurably improves the document. Never a guess.

3. **`scripts/corpus_probe.py`** — runs stages 2 and 4 over a sample of a real shard and reports
   what fired. Built because both stages had been tested only against hand-written fixtures,
   which prove the rules do what they say and say nothing about whether they fire on Ravaan's
   actual material. It found a corpus-destroying bug within one run (below).

4. **Real corpus on disk.** Urdu Wikipedia (167.6 MB) and the Roman-Urdu-Parl eval splits
   verified against their pinned digests; FineWeb2 `urd_Arab` train shard 001 (2.02 GB), its
   test shard, and the Roman-Urdu-Parl train file fetched the same way. `data/manifest.json`
   records every file with its digest, licence, source revision and URL.

**Finding C — UrduLM's 33 GB corpus does not exist as a public artifact.**

The next-session task was "check the licence first — the arXiv listing shows CC BY-NC-ND." The
licence was never the blocker, and the arXiv term covers the *paper*, not the data.

- The paper (arXiv:2601.17664, 25 Jan 2026) releases via the ALIF project: `orature/ALIF-Base-100M`
  (Apache-2.0) and `orature/ALIF_Urdu_Corpus_AUC` (CC BY-SA-4.0). The dataset card describes
  itself as **"a preview to our entire 33GB Dataset"** — 5,000 rows, 14.5 MB. The full corpus is
  not published anywhere findable. **"Released openly" is not met for the corpus.**
- **This qualifies Finding B's headline number.** Of the claimed 33 GB, **5.5 GB is English
  FineWeb machine-translated to Urdu with the Google Translate API**, 19.4 GB is CommonCrawl
  (which overlaps Ravaan's own primary source), and 1.3 GB is Google Vision OCR of scanned books.
  So "~5–6B collectable Urdu tokens" is not 5–6B tokens of independent human-authored Urdu.
  **Finding B's conclusion survives** — even discounting the translated share and crawl overlap,
  collectable Urdu still exceeds the ~1.4B Chinchilla-optimal budget for 70M params several times
  over, so Urdu is not data-constrained at this scale — but the report must state the number with
  that caveat rather than quoting 33 GB flat.
- **Bonus for Week 5:** `orature/ALIF-Base-100M` is Apache-2.0 and ships a 32k Urdu SentencePiece
  model. That is a legitimate external fertility baseline for PRD §7, at no licence cost.

All of this is recorded in `configs/data/sources.json` under `rejected`, next to the sources we
did use — which is what makes PRD §6.1's "capping is deliberate" claim checkable rather than
asserted.

**Finding D — the first mojibake detector would have silently deleted 3% of a clean corpus.**

Caught by the probe on its first run against real text — not by the unit tests, every one of
which passed.

- v1 counted any run of two or more characters from the cp1252 alphabet. On 20,000 Urdu Wikipedia
  articles that rejected **591 of them (3.0%)**, at ~20 flagged characters each — real mojibake
  flags the whole document, so the shape of the number was the tell.
- The flagged runs name the cause: `‘‘` (2,234 hits) and `’’` (2,226) — **Urdu Wikipedia's own
  quotation marks** — plus U+00A0 layout padding, `——————` rules, `\xa0–`, and Portuguese `çã`.
  All ordinary text.
- **The fix is a definition, not a threshold.** Mojibake *is* the property of re-encoding to
  well-formed UTF-8, so the round trip is the detector, and the character class survives only as
  a cheap pre-filter. `‘‘` is bytes 0x91 0x91 — two bare continuation bytes no sequence can start
  with — while `ÛŒ` is D9 8C, a valid 2-byte sequence. Both are "a run of two cp1252 characters";
  only one is mojibake.
- Acceptance on the same 20,000 articles: **97.03% → 99.99%**. Every one of those strings is now
  a named regression test with its hit count.

**Finding E — a prefix of a FineWeb2 shard is not a sample of it.**

`sources.json` carried a "TO CHECK AT FREEZE" note: we fetch train shard 001 of 2, assuming shard
assignment is document-random rather than correlated with CommonCrawl dump. Checked now, because
it is cheap now and expensive after the freeze.

- **Shards are not dump-partitioned.** 88 distinct dumps appear across a 16,542-document sample
  spanning CC-MAIN-2019-43 to CC-MAIN-2024-18, and every row group individually mixes several.
  Taking shard 001 alone does **not** restrict us to a slice of the crawl's history. The original
  worry is answered.
- **But documents are not shuffled either.** Row group 0 skews to CC-MAIN-2021-25/2022-21; row
  group 206 skews to CC-MAIN-2024-18; row groups 1341 and 1444 swing back to 2020–2021. There is
  block-level structure, so **reading the first N documents measures one slice of the crawl.**
- **This invalidated my own first measurements.** The stage-2/stage-4 numbers were taken from the
  head of the shard, and correcting to an even spread across row groups moved them by 25–50%:
  yeh 1.05 → 0.83 per document, digits 0.83 → 0.57, kaf 0.45 → 0.21, documents changed 15.1% →
  13.7%. The table above is the corrected version.
- **`corpus_probe.py` now spreads across row groups by default**, with `--head` to opt back in.
- **The consequence that outlives this session:** stage 9 split creation and arm A's seeded 25M
  subsample must select **randomly across the shard**, never a prefix or a contiguous block. PRD
  §6.1 requires the two arms to differ in size and nothing else; a prefix-based subsample would
  make arm A systematically older web text than arm B, silently confounding the primary endpoint
  with crawl date.

**Decisions made**

| Decision | Rationale |
|---|---|
| The licence gate refuses at load time; restrictive sources may only appear under `rejected` | PRD §6.3 promises a permissive checkpoint. Encoding that as data (`LICENSES`, four terms each) rather than prose is what makes it survive contact with a new source at week 9. It is also what would have caught the UrduLM question automatically. |
| Rejected sources stay in the manifest, with reasons | §6.1 requires the report to say the cap is deliberate. That is only checkable if what we declined, and why, sits next to what we took. |
| Corpus fingerprint covers repo + revision + licence + file digests — **not** prose or fetch order | Reordering a download or fixing a typo in a note does not make it a different corpus. A fingerprint that said otherwise would invalidate a frozen corpus for a comment change. |
| `data/manifest.json` merges across runs instead of overwriting | A 6.9 GB source arrives over several sessions, often one `--source` at a time. A manifest describing only the last invocation would understate the corpus, and stage 9 would split over files it does not list. |
| Stage 2 strips C0/C1 controls; stage 4 does not | Normalization owns *script* decisions — which Urdu graphemes fold into which. Control bytes are not graphemes; they are a byte-layer symptom. Left alone they reach the tokenizer, where byte fallback dutifully gives them vocabulary entries. `\t \n \r \v \f` are excluded — stage 4 already understands those. |
| Mojibake is repaired *before* controls are counted | U+0080–U+009F are C1 controls in correct text and the signature of mojibake in broken text. ہ (U+06C1) is UTF-8 D9 **81**, so a mis-decoded Urdu page is full of apparent control bytes. Checking controls first would reject exactly the recoverable documents — and would look like a quality filter working. |
| Replacement-rate threshold left tight at 0.001 | It rejects 3 of 20,000 Wikipedia articles, all with genuine U+FFFD in the source. U+FFFD means information was destroyed upstream and no later stage can recover it; at 0.015% loss with ~5B tokens available, strictness is free. |
| Acquisition stays standard-library-only | Same argument as normalization. `datasets`/`huggingface_hub` are more convenient, but this is the code that decides which bytes the entire project is built on. `[data]` starts at stage 3, where parquet must be parsed. |

**Measured — first contact with real Urdu, 20,000 documents from each of two sources**

This closes the "validate the normalizer on real text" caveat, and the two sources disagree in a
way that is more informative than either alone.

~19,500 documents per source, sampled **across row groups, not from the head** — see Finding E.

| | Urdu Wikipedia | FineWeb2 `urd_Arab` |
|---|---|---|
| **Stage 2** accepted | 19,153 / 19,154 (99.995%) | 19,540 / 19,542 (99.990%) |
| rejected | 1, genuine U+FFFD | 2, genuine U+FFFD |
| mojibake / control chars | 0 / 1 | 0 / 0 |
| **Stage 4** documents changed | **91.3%** | **13.7%** |
| chars in → out | 30.77M → 30.57M | 43.74M → **43.77M** |
| whitespace (per doc) | **11.34** | **0.02** |
| yeh unification | 0.61 | **0.83** |
| heh unification | 0.29 | **0.48** |
| kaf unification | 0.11 | **0.21** |
| digits | 0.28 | **0.57** |
| teh marbuta / alef | 0.14 / 0.07 | **0.18 / 0.13** |
| presentation forms | 0.58 | 0.22 |
| tatweel / zwnj / zero-width / bidi | 0.03 / 0.03 / 0.02 / 0.01 | 0.07 / 0 / 0 / 0 |

**Two things follow, and both are worth stating in the report.**

- **Stage 2 is nearly a no-op on FineWeb2, and that is the correct outcome.** FineWeb2 already ran
  an encoding pass — zero mojibake, zero control bytes, 7 replacement characters in 20,000
  documents. Stage 2 should be described as an *assertion* on this source, not as cleaning it. It
  earns its keep on Wikipedia and would earn it on raw crawl; claiming otherwise would be
  measuring the thermometer (PRD §8.1's own phrase).
- **Stage 4 is the opposite, and this is the justification for the whole module.** FineWeb2
  normalized everything a *language-agnostic* pipeline can normalize — whitespace drops from
  10.62 hits per document to 0.02 — and left **every Urdu-specific letter variant in place**. Yeh,
  heh, kaf, teh marbuta and alef folds all fire at rates comparable to or higher than Wikipedia's.
  No general-purpose Western pipeline does Urdu script unification, and the numbers say so
  directly.
- **Arabic-variant spelling is concentrated, not diffuse.** Only 13.7% of FineWeb2 documents change
  at all, yet yeh substitutions average 0.83 across *all* documents — so the affected minority
  carries roughly six each. Almost certainly a per-site property (Arabic-keyboard input at
  particular publishers). Worth checking against the `url` column at stage 3, because if it is
  site-correlated it interacts with dedup and with the arm A subsample.
- **Normalization makes FineWeb2 slightly *longer*** (43.74M → 43.77M chars) while shortening
  Wikipedia. Presentation-form expansion adds characters — `ﻼ` becomes two — and FineWeb2 has no
  whitespace slack to reclaim. Worth knowing before anyone reads a shrinking character count as
  evidence the pipeline is working.

**Sizing, for G1.** FineWeb2 shard 001 holds **1,547,542 documents** averaging ~2,240 characters,
so roughly **3.5G characters before any filtering** — around an order of magnitude past the ~120M
token target even at a pessimistic characters-per-token ratio. The G1 threshold of 100M clean
tokens is not in danger from raw volume; it will be decided by stage 5 and stage 7 yields.

Download throughput ≈ 2.4 MB/s, so the 3.4 GB working set is ~25 minutes. Not a bottleneck.

**Fixed during the session**

- **`scripts/normalize.py -o` was writing CRLF into corpus text on Windows.** `Path.write_text`
  translates every `\n` to `os.linesep` by default, so the normalizer's own CLI put carriage
  returns straight back into text that `_LINE_BREAK_RE` had just removed — and the same corpus
  would hash differently on Windows than on Linux, invalidating every downstream checksum for one
  platform's operator only. Surfaced by git's CRLF warning while staging, which is the *third*
  time this repo has been bitten by a platform default (session 2's `.gitattributes` note
  anticipated exactly this failure for corpus files and it happened anyway, one layer up). Every
  text write in the pipeline now pins `newline="\n"`, and two regression tests assert no `\r`
  reaches disk. **This is why `.gitattributes` alone was not enough**: it normalizes what git
  stores, not what the pipeline writes to a corpus file git never sees.
- **`.gitignore` could not have tracked the manifest.** `/data/` excludes the *directory*, and git
  cannot re-include a file whose parent directory is excluded — so the existing `!/data/.gitkeep`
  was silently dead, and `!/data/manifest.json` would have been too. Changed to `/data/*` plus
  explicit exceptions, with `/data/raw/` still excluded. This is the same class of bug as session
  2's bare `data/`, in the opposite direction. Verified with `git check-ignore -v`.

---

### Session 5 — 2026-08-04

**Done**

1. **Streaming shard reader** (`ravaan/data/shards.py`, 18 tests). The iterator every stage from 3
   onward consumes: parquet and CSV, `(source, doc_id, text, meta)`, resumable. Built around
   three properties.
   - **A prefix is not a sample — enforced, not documented.** Finding E's consequence is now
     structural: the default read order is a seeded shuffle of row groups *and* of rows inside
     them, and `order="sequential"` is the option you have to ask for by name. The biased read is
     still available and still fast; it just cannot happen by accident.
   - **Selection is stable, and it is not the shuffle.** `stable_unit(doc_id, salt)` hashes a
     document id to [0, 1) with blake2b, so `sample_rate` — and, later, stage 9's splits and arm
     A's 25M subsample — depend only on the id. Two runs that read the corpus in different
     orders, or resume at different offsets, select the *same* documents. Shuffling decides what
     you look at first; hashing decides what belongs to what. Conflating them is how arm A stops
     being a subsample of arm B.
   - **Resumption is exact or it fails.** A checkpoint carries a plan fingerprint over file
     digests + layout + seed + sample rate, and `resume()` refuses a checkpoint from a different
     plan rather than resuming into a different document order. A pass that silently skips and
     duplicates documents is worse than one that crashed.
   - CSV gets a byte-offset block index built in one pass and cached beside the file, keyed on the
     acquisition digest. Re-reading from the top for every block is quadratic and Roman-Urdu-Parl's
     train split is 1.2 GB / 6.37M rows.
   - Column layouts are **declared per source**, not auto-detected. Auto-detection picks "the
     first string column", and a corpus accidentally made of the `url` column would score as
     English and vanish at stage 3, looking exactly like a language filter working.

2. **Language / script ID — stage 3** (`ravaan/data/langid.py`, `configs/data/langid.json`,
   32 tests). Document-level, sentence-level only for mixed documents, per §6.3.3. Separates the
   three populations §6.1 budgets separately rather than just accepting or rejecting.
   - Script is measured (Unicode ranges, one `str.translate` pass over letters only); language is
     inferred. Every result carries its script ratios *and* its language scores, so a label can be
     argued with.
   - **Roman Urdu vs English is answered with word lists, not a model — recorded as the decision
     §6.3.3 left open.** fastText's lid.176 has no Roman Urdu label at all (it knows `ur` only in
     Arabic script), so it would scatter this population into English/Indonesian/Malay and we
     would lose it silently. Roman Urdu has no standard orthography, so what discriminates it is
     frequent function words *in all their spellings* — which is what a word list is and what a
     model trained on standardised text is not. And it costs no GB-scale dependency in a pipeline
     that is otherwise standard-library-only.
   - **Urdu vs Persian vs Arabic leans on Urdu's own letters first.** Stage 3 runs *before*
     normalization, so Arabic-keyboard Urdu still writes که for کہ — the Persian word. Folding
     first would merge the evidence instead of separating it. ٹ ڈ ڑ ں ے ھ ہ ۓ ۂ have no such
     problem: no Arabic key produces them.

3. **`scripts/stage3_probe.py`** — stages 2→3 over a real source, with `--expect` for
   known-truth sources and `--sites` for the per-domain analysis. It found two corpus-level
   mislabels within its first two runs (below). Reports in `reports/probe_stage3_*.json`.

**Measured — stage 3 on real text**

| | FineWeb2 `urd_Arab` | Urdu Wikipedia | Roman-Urdu-Parl (Roman col.) | English prose |
|---|---|---|---|---|
| documents | 19,997 | 19,999 | 16,218 | 148 |
| **urdu** | **99.4%** | **93.6%** | — | — |
| **roman_urdu** | — | — | **79.1%** (96.3% of non-empty) | **0%** |
| **code_switched** | 0.6% | 5.7% | — | — |
| english / arabic / persian | 0 / 0 / 0 | 0.4% / 0.1% / 0.0% | 0.2% / — / — | 84.5% / — / — |
| `other` (no evidence) | 0 | 0.2% | 2.8% | 15.5% |
| `empty` (too short) | 0 | 0.1% | 17.8% | 0 |
| labelled **by prior**, not evidence | **0.00%** | 0.18% | — | — |

- **Both error directions are cheap.** English → Roman Urdu is **0%** (the direction that would
  pollute a population the report makes claims about); Roman Urdu → English is **0.2%**. The
  `other` bucket is an abstention, not a guess, and that is where the residual sits.
- **FineWeb2 agrees with itself.** Cross-tabulated against FineWeb2's own GlotLID output, all
  19,997 documents are `urd_Arab`, and mean GlotLID confidence is **0.978** for documents we call
  Urdu against **0.922** for the ones we call code-switched — independent corroboration that the
  code-switched set is the harder material, from a classifier we did not write.
- **Stage 3 is an assertion on FineWeb2, a filter on Wikipedia** — the same shape as stage 2, for
  the same reason: FineWeb2 is already GlotLID-filtered to `urd_Arab`. Nothing was rejected, and
  claiming stage 3 "cleaned" that source would be measuring the thermometer.
- **The Roman-Urdu-Parl `empty` rate is a unit mismatch, not a failure.** Its rows are single
  sentences, and 17.8% of them have fewer than 20 letters. The Arabic-script side of the same
  rows classifies as Urdu **99.95%** of the time excluding those. For a curated parallel corpus
  the source declaration *is* the label; stage 3 is a sanity check there, not a gate.

**Finding F — Arabic-variant spelling is a property of publishers, not of the language.**

Session 4 left this open: FineWeb2 changes only 13.7% of documents yet averages 0.83 yeh
substitutions across all of them, so a minority carries ~6 each. Checked against the `url` column
over 2,935 domains, and the answer is unambiguous.

- **The top 1% of domains carry 65.3% of all Arabic-variant hits.** Against a corpus-wide rate of
  **1.37 variants per 1,000 characters**: `alhassanain.com` **54.4** (40×, 100% of documents
  changed), `tebyan.net` **37.1** (27×, Iranian), `banuri.edu.pk` **22.2** (16×, a Karachi
  seminary, 62 documents), `mazameen.com` **21.1**, `urdufatwa.com` **14.2** (96% changed).
  Pakistani news sites sit at **exactly zero**: `aaj.tv` (69 documents, 97k characters) 0.00,
  `archive.urdu.siasat.com` 0.00, `24newshd.tv` 0.00.
- **Measured per character, not per document — the first version of this table was wrong.** Rates
  per document conflate the property with length, and the domains at the top publish book-length
  pages: `alhassanain.com` showed 3,484 hits per document over six documents, which is exactly
  what six very long documents look like. Per character it is still 40× the corpus rate, so the
  conclusion survives the correction — but it did not have to.
- The mechanism is legible: publishers who set Arabic alongside Urdu, and Iranian/Arab-world
  publishers producing Urdu editions, compose on Arabic and Persian input systems. Pakistani
  newsrooms use Urdu ones. The split is by *publisher type*, not by topic or by crawl date.
- **Three consequences, all of which outlive this session.**
  1. **Stage 4 is doing publisher-level orthographic unification, not cosmetic tidying.** Without
     it the same word from `alhassanain.com` and from `aaj.tv` occupies two vocabulary entries.
  2. **The stage order 4 → 6/7 is now justified by data, not by taste.** Religious publishers
     republish the same hadith and tafsir texts across many domains; normalizing *before* dedup is
     what makes those cross-publisher duplicates hash alike. Deduping raw text would miss exactly
     the duplicates that are most concentrated.
  3. **Arm A's subsample stays sound, and only because selection is per document.** A property
     this concentrated would be badly distorted by any site-level or block-level sampling; random
     document selection keeps it in proportion, with somewhat higher variance. This is the second
     independent argument for the reader's design.

**Two mislabels the probe caught that the unit tests could not**

Both are Finding D's lesson again, and both would have moved a *population* rather than a
document.

- **30% of Urdu Wikipedia came out "code-switched" on the first run.** The cause was Urdu prose
  quoting a foreign name — "سینٹ-موریس، ہوتے-مرنے (فرانسیسی: Saint-Maurice, Haute-Marne) فرانس کا
  ایک فرانسیسی کمیون" is a quarter Latin letters by volume. The fix is not a threshold but a
  distinction: **names are capitalised and embedded content words are not.** A mixed span now has
  to be lowercase *running text* on the Latin side to count as switching (those stubs score 0.00;
  real switching scores ~1.00). This matters because the misrouted documents would have left the
  ~120M-token native budget for the ~10M-token code-switched one.
- **The alternation threshold was set from a measured distribution, not chosen.** Across 1,920
  mixed Wikipedia articles the English share has a sharp mode at 0.10–0.20 (1,064 documents) that
  is not bilingual writing at all — it is the English reference list and category footer every
  Wikipedia article carries — and then collapses (298 at 0.20–0.30, 39 at 0.30–0.40). The
  threshold sits at **0.30**, in the valley after the artifact. Wikipedia's code-switched share
  went 30.4% → 26.4% → **5.7%** across the two fixes.
- The word lists were extended the same way: by mining the sentences Roman-Urdu-Parl's validation
  split *failed* to label and reading what they were made of. `aik`, `ne`, `na`, `hi`, `hon`,
  `tak`, `koi` — among the most frequent words in the language — were simply missing.

**Decisions made**

| Decision | Rationale |
|---|---|
| Roman Urdu vs English by **word list**, no model | Recorded above. The deciding argument is not cost: lid.176 has no `urd_Latn` label at all, so the off-the-shelf option fails *silently* on the population §6.1 budgets 40M tokens for. |
| Ambiguous words are removed from **both** lists, and the intersection is public | `the` (they were), `to` (then), `or` (and), `he` (is), `us` (that), `do` (two), `main` (I/in), `so`, `say` are frequent in both languages. Left in, they hand a free vote to whichever list is longer. `AMBIGUOUS_LATIN_WORDS` is exported because it is the classifier's main known weakness and belongs in the report. |
| Arabic-script text with no function-word evidence is called Urdu, and **flagged as decided by the prior** | Headings, name lists and poetry fragments have nothing to measure. Calling them Urdu is right for an Urdu-filtered corpus; reporting them alongside documents that were actually classified is not. `prior_rate` goes in the manifest — 0.00% on FineWeb2, 0.18% on Wikipedia. |
| Urdu quoting Arabic scripture stays **urdu**; Arabic and Persian are not code-switch partners | Religious and legal Urdu quotes Arabic constantly. A classifier tuned to reject Arabic-looking text strips a *register* of Urdu, not a language — and that is a corpus-composition change disguised as a quality filter. |
| Two code-switch thresholds, not one | They measure different things. Intra-sentential mixing is unambiguous evidence (0.10); a document that merely alternates between monolingual blocks needs much more (0.30) because "Urdu article + English reference list" is document furniture. One knob for both is how Wikipedia ended up 30% bilingual. |
| One `mixed_min_ratio`, not a `dominant_script_ratio` as well | Two names for one boundary is how a band of documents ends up matching neither rule and falling through to `other` with nothing having decided it. |
| Reader stays parquet-only for `[data]`; the *deciding* stages stay stdlib | Same argument as stages 1–2. `[data]` is now needed to **read** the corpus, never to decide anything about it. |

**Fixed during the session**

- **Document ids moved when the read seed moved.** The positional id fallback was built from the
  row's index *in the shuffled block* rather than in the file, so the same document got a
  different id under a different seed — which would have silently repartitioned stage 9's splits,
  broken arm A's "same documents, fewer of them" guarantee, and made exact dedup miss. Caught by
  reading three ids in a row that were suspiciously `0, 1, 2`. The permutation now moves the pair,
  never the number inside it; two tests lock it.
- **`random.Random((seed, index))` is a TypeError on Python 3.14** — tuple seeds were removed.
  Replaced with an integer seed derived through blake2b, which is stable across interpreter
  versions; string seeds are not something a resumable corpus pass should depend on. CI runs 3.11
  and 3.13, so this would have been a local-only failure on the operator's machine.
- **`csv.field_size_limit` defaults to 128 KiB** and silently truncates longer fields. Raised;
  corpus documents are routinely larger.

---

### Session 6 — 2026-08-04

**Done**

1. **Quality filtering — stage 5** (`ravaan/data/quality.py`, `configs/data/quality.json`,
   43 tests). All five §6.3.5 rule families — script ratio, repetition, URL density, HTML residue,
   replacement-character frequency — plus a length floor. Four properties it is built around.
   - **Every rule is evaluated; none short-circuits.** The log records `rejections` (documents each
     rule fired on, overlapping) *and* `sole_rejections` (documents only that rule rejected). The
     second number is the one that says whether a rule is filtering the corpus or agreeing with
     another rule. Stages 2 and 3 both turned out to be assertions rather than filters on FineWeb2
     and the only reason that is known is that it was measured; stage 5 measures it by
     construction.
   - **Thresholds are per population.** §6.3.5 reads as one Urdu-script floor, and that floor
     deletes the entire ~40M-token Roman Urdu population, which is Latin script by definition. The
     rule is instead "share of letters in the scripts this stage-3 label is *expected* to be
     written in", and the label is threaded through from stage 3.
   - **Measurement is separable from scoring.** `measure()` produces thresholds-free metrics;
     `score()` applies a config to them. This is what let the 200-sample validation be adjudicated
     once and then replayed against every candidate threshold in seconds instead of re-reading
     40,000 documents per candidate.
   - **Stage 5 rejects; it does not repair.** Stage 2 repairs mojibake because the correct output
     is not a matter of opinion. Stripping a document's boilerplate to save it means deciding what
     its content was.

2. **The 200-sample manual validation (PRD §6.3.5)** — `scripts/quality_sample.py` (draw + score),
   `reports/quality_sample.md` (the review sheet, adjudicated), `reports/quality_sample.jsonl`,
   `reports/quality_validation.json`. **This changed four of the six rule families.**
   - **The sample is stratified and the strata are never pooled.** 100 uniform (50 per source) to
     estimate false *accepts* honestly; 100 oversampled from rejections, spread across families
     smallest-first, to measure each rule's precision. A uniform 200 would have contained zero or
     one rejected FineWeb2 document and could not have validated a single rejection.
   - Both strata are drawn by `stable_unit` on the document id, so the sample is reproducible from
     the seed on any machine and in any read order.

3. **`scripts/probe.py`** — stages 2→5 over a real source, replacing **both** `corpus_probe.py` and
   `stage3_probe.py`, which are deleted. This closes the carried-forward item. It reproduces
   session 5's Finding F numbers exactly (top 1% of domains carry 65.3% of variant hits, corpus-wide
   1.37/kchar, `alhassanain.com` 54.39, `aaj.tv` 0.00), which is the cross-check that the
   consolidation changed nothing. It adds per-metric percentile distributions and a reservoir of
   *rejected* examples per rule family — a threshold is only defensible once you have read what it
   deletes.

**The validation is the finding: inherited English thresholds do not transfer, in three
different ways**

Rae et al.'s Gopher repetition values reject **13.7% of FineWeb2 `urd_Arab`**, and reading that
13.7% shows it is almost entirely clean Urdu news prose. Two mechanisms, both specific to this
material:

- **Urdu news wire copy restates the headline verbatim in the lead paragraph.** It is the house
  style. A 500-character article carrying its own 60-character headline twice is over 20% duplicate
  5-grams by arithmetic, with nothing wrong with it.
- **Function-word density.** Urdu's compound verbs and postpositional phrases (کے مطابق، کی جانب
  سے، ہو گیا ہے) make a repeated five-word run ordinary where the English equivalent is a template.

The other half of the argument is that the repetition which matters in *this* corpus is
cross-document, not within-document: Wikipedia's geographic stub farms and Finding F's republished
religious texts are near-duplicates of each other, which is stages 6–7's job. So stage 5's
repetition family is a backstop against a single pathological document, not the corpus's repetition
control.

**What the 200 documents changed, and by how much**

| | before validation | after |
|---|---|---|
| Agreement, uniform stratum | 0.76 | **0.92** |
| Agreement, all 200 | 0.675 | **0.855** |
| False accepts (uniform, n=91→67) | **24** | **4** |
| `too_short` precision | 1.00 (32) | 0.93 (75) |
| `repetition` precision | 0.60 | **1.00** |
| `html_residue` precision | 0.38 | **1.00** |
| `script_ratio` precision | 0.55 | 0.50 |

Four threshold changes, each forced by documents rather than by taste:

- **`min_chars` 200 → 400.** The largest single result. At 200 the rule had *perfect* precision —
  32 of 32 rejections agreed with — and was still the filter's biggest error source, because it was
  letting through 24 of the 91 documents a human would drop: Urdu Wikipedia's template geo-stubs,
  one factual sentence wrapped in section headers and category footers, running 200–420 characters.
  **A rule can be perfectly precise and still be set far too low, and only the accept side shows
  it.** That is what the uniform stratum is for.
- **`max_dup_ngram_ratio` 0.40 → 0.60, and n=2 dropped from `max_top_ngram_ratio`.** The validation
  split the repetition family cleanly: **the top-n-gram rules discriminate and the duplicate-n-gram
  rules did not.** Every top-n-gram rejection was a Wikipedia disambiguation or list page and a
  human agreed with all of them; the duplicate rules were rejecting *biographies*, because an
  article about one person repeats that person's name and the formulae of the genre. Separately,
  n=2 was the one top-n-gram rule with a false positive — a 4,700-character article on the UN
  Convention on the Rights of the Child scores 0.38 on بچوں کے, which is its topic, not its
  boilerplate. Dropping n=2 took the family to precision 1.00 while still rejecting every list page.
- **`max_html_ratio` 0.02 → 0.10.** The pattern is precise about what it *matches* — across 7,999
  probed documents every hit was a genuine tag, including wiki `<ref>`/`<noinclude>`, with no false
  positives — and 0.02 was wrong about what that means. It was deleting clean Wikipedia biographies
  carrying five stray `</i>` tags. The rule should fire when a document *is* markup, not when it
  *contains* some.
- **`min_urdu_script_ratio` 0.70 → 0.60, and this one is not fixed.** It is the rule the validation
  could not repair, and the report should say so. At 0.70 precision was 0.55; at 0.60 it is 0.50.
  The failure is structural rather than a threshold: an Urdu news article quoting an English tweet
  scores 0.57, a porn-spam page with Urdu keyword salad scores 0.58, and an Urdu ghazal printed
  beside its Roman transliteration scores 0.52. Latin share does not separate them because it is
  not what distinguishes them. 0.60 keeps Urdu journalism and still removes the wholly-English
  pages stage 3 let through. The language decision belongs to stage 3, which made it on far better
  evidence.

`max_url_ratio` was also raised (0.10 → 0.30) from the distribution alone, before the sample: every
document between 0.10 and 0.30 was a legitimate Wikipedia article whose *references and
external-links section* is made of URLs — structurally identical to a link farm by this metric, and
the same artefact that made Wikipedia look 30% bilingual to stage 3 in session 5. Citation-heavy
articles are systematically the longer, better-sourced ones, so a threshold that catches them
changes corpus composition in the wrong direction.

**Measured — stage 5 on real text, 20,000 documents per source**

| | FineWeb2 `urd_Arab` | Urdu Wikipedia |
|---|---|---|
| documents kept | **96.48%** | **46.72%** |
| **characters kept** | **99.48%** | **87.38%** |
| `too_short` fired / sole | 694 / 694 | 10,568 / 10,174 |
| `script_ratio` | 9 / 9 | 61 / 22 |
| `repetition` | 0 | 406 / 55 |
| `html_residue` | 0 | 12 / 4 |
| `url_density` | 0 | 7 / 4 |
| `replacement_chars` | 0 | 0 |

- **Stage 5 is very nearly an assertion on FineWeb2 — the same shape as stages 2 and 3, for the
  same reason.** FineWeb2 already ran encoding, language and Gopher-style repetition filtering, so
  what is left for stage 5 to remove is 0.5% of the characters. This is now the third stage where
  the honest report is "this source was already clean in this dimension", and the three together
  are a real finding about what FineWeb2 is.
- **Wikipedia loses half its documents and an eighth of its characters**, which is the right shape:
  the rejected half is the template stub farm, and stage 7 would have collapsed those anyway.
- **`replacement_chars` never fired on either source, as designed.** Stage 2 already enforces the
  same 0.001 rate, so in the assembled pipeline this rule cannot fire; it exists so stage 5 is
  sound when run standalone. `sole_rejections` reporting zero for it is the honest way to say so.
- **G1 is not at risk.** FineWeb2 shard 001 is ~3.5G characters before filtering and keeps 99.48%,
  which is roughly an order of magnitude past the ~120M-token target.

**The normalizer on FineWeb2 — session 4's carried-forward caveat, now closed**

The same 200 documents went through stage 4. On the 96 FineWeb2 documents in the sample, **14.6%
were changed** (against 13.7% measured over 20,000 in session 4 — consistent), and the rules that
fired are the Urdu-specific ones: heh 37, yeh 29, teh_marbuta 6, zero_width 5, presentation_forms 5,
alef 4, digits 2, kaf 1. Net character delta +80 across the sample, i.e. normalization makes
FineWeb2 very slightly *longer*, as session 4 predicted (presentation-form expansion, no whitespace
slack to reclaim). **No rule misfired on any of the 200** — nothing folded a preserved grapheme,
and every change inspected was a genuine variant unification.

**Decisions made**

| Decision | Rationale |
|---|---|
| The 200-sample validation is **stratified**, and the strata are scored separately and never pooled | Stage 5 rejects 0.26% of FineWeb2 under the pre-validation config. A uniform 200 contains zero or one rejected document and cannot validate a rejection; a purely rejection-sampled 200 cannot estimate false accepts. Both questions are real, so both strata exist, and the report says which number came from which. |
| `measure()` and `score()` are separate functions | Human adjudication is the expensive half and it is a judgement about *documents*, so it survives a threshold change. Storing metrics rather than verdicts is what made a five-threshold sweep against human labels a minute's work. |
| A length floor is added although §6.3.5 does not list it | The population it removes is the one every other rule measures badly: a 200-character document has no repetition, no meaningful URL density, and a script ratio computed over a dozen letters. It is also, measured, the single highest-precision rule in the stage. Flagged inline as an addition, as the normalizer's extra folds were. |
| Sentence-unit sources get a **named** config (`for_sentences()`), not a special case in the driver | Roman-Urdu-Parl's rows are ~45-character sentences; the document floor would delete the entire source. Making it a named config keeps it in the fingerprint, so the manifest records which rules ran on which source instead of it being implicit in a script. |
| Rejection examples are sampled per rule family, smallest family first | Rules that fire rarely are exactly the ones whose thresholds rest on the least evidence. A proportional draw leaves them uninspected — `html_residue` fired 12 times in 20,000 Wikipedia documents and its threshold was wrong. |
| Both probe scripts are replaced by one, and the old two deleted | The carried-forward item. Two probes that disagree about how to sample are worse than one; the consolidation is verified by reproducing Finding F's numbers exactly. |

**Fixed during the session**

- **`.gitignore`'s blanket `*.jsonl` would have silently dropped half the validation deliverable.**
  `reports/quality_sample.jsonl` holds the metrics the review sheet is scored against — without it
  the marked-up `.md` cannot be replayed and the validation is not reproducible. Added
  `!/reports/*.jsonl`. **This is the third time a blanket ignore has nearly cost this repo
  something load-bearing** (session 2's bare `data/`, session 4's `/data/`), and the lesson is now
  explicit in the file: verify with `git status`, not with `git check-ignore`, whose exit code
  reports the *last matching pattern* and returns 0 even when that pattern is the negation.
- **Urdu on a Windows console raises rather than mangles.** `PYTHONIOENCODING` is not set by
  default and cp1252 cannot encode Arabic script, so any probe printing a sample crashed with
  `UnicodeEncodeError`. Both new scripts pin `sys.stdout`/`sys.stderr` to UTF-8 at import. This is
  the fourth platform-default bug in this repo (sessions 2, 4 ×2, 6) and they have all been the
  same shape: a default that is invisible on Linux and wrong here.

**Not committed to git.** Session 6's work is on disk, lint-clean and with all 276 tests passing,
but no commit was made — stopping point was called before that. `git status` shows the full set:
`ravaan/data/quality.py`, `configs/data/quality.json`, `tests/test_quality.py`, `scripts/probe.py`,
`scripts/quality_sample.py`, the four `reports/` artefacts, the deletions of `scripts/corpus_probe.py`
and `scripts/stage3_probe.py`, and edits to `pyproject.toml`, `ravaan/data/__init__.py` and
`.gitignore`.

---

### Session 7 — 2026-08-04

**Done — the two leftovers from session 6, then the repo is clean.**

1. **`reports/quality_validation.md` written** — the paper trail PRD §6.3.5 asks for. Method (why
   two strata), the before/after table, one section per threshold change with the documents that
   forced it, `script_ratio` written up as the rule that could not be fixed, the shipped filter's
   full error budget, and four open items. Every number in it was re-derived from the committed
   artefacts during the write-up rather than copied from session 6's notes, which is how the three
   corrections below surfaced.

2. **Session 6 + 7 committed.** One commit: stage 5, the validation, and the write-up are one
   deliverable. 276 tests passing, `ruff check` clean.

**Three things the write-up found by re-deriving instead of quoting**

- **The 13.7% Gopher claim now has a decomposition, and it is sharper than the claim.** Re-ran the
  probe under Rae et al.'s repetition values (`reports/probe_fineweb2_gopher.json`): 2,753 / 19,997
  = **13.77%**, reproducing session 6. The new part is *which* rules do it — `dup_5gram` 2,353,
  `dup_6gram` 1,675, down to `dup_10gram` 1,185, while **`top_2gram` and `top_4gram` fire on zero
  documents and `top_3gram` on one.** The entire 13.77% is the duplicate-n-gram half. Session 6
  inferred the top/dup split from 200 adjudicated documents; it now also holds corpus-wide, from a
  completely different instrument. Two independent measurements agreeing is worth more in the
  report than either.
- **The duplicate-n-gram rules are near-inert at the shipped thresholds.** Disabling them entirely
  changes Wikipedia's kept count by **4 documents in 19,999** and FineWeb2's by **0**. On the 200
  they reject nothing the top-n-gram rules do not already reject. They stay as a backstop, but
  `quality.py`'s own doctrine — a rule with no sole rejections is agreeing, not filtering — says
  this has to be stated rather than left to be discovered. Added to the report's open items.
- **The `script_ratio` failure is worse than session 6 recorded, in the direction that helps.**
  Session 6 quoted the band from memory as "news 0.66, spam 0.58, ghazal 0.52". Measured, the
  documents interleave far more tightly — 0.479 keep, 0.481 drop, 0.517 keep, 0.542 drop, 0.543
  drop, 0.570 keep, 0.578 drop, 0.579 drop, 0.587 drop, 0.589 keep, 0.594 keep. There is no cut
  anywhere in the range. A four-point sweep confirms it: precision 0.25 / 0.50 / 0.55 / 0.56 at
  thresholds 0.50 / 0.60 / 0.70 / 0.80, while the number of documents affected changes 16×. **No
  threshold makes this rule better than a coin flip.** progress.md's 0.66 is corrected above.

**Also measured while writing it**

- **The stratification argument is now a number, not an estimate.** Re-measured the pre-validation
  config on FineWeb2: **51 rejections in 19,997 = 0.2550%**. A uniform 200 would have contained
  zero or one rejected FineWeb2 document. This is the justification for having a rejection stratum
  at all and it should not have rested on a remembered figure.
- **`min_words` is slack.** At the shipped settings it never rejects a document `min_chars` does
  not — 0 of 200. This corpus runs 4.82 characters per word, so `min_words` 40 ≈ 193 characters
  against a 400-character floor. The length rule is `min_chars` alone in practice.
- **The length floor does not separate cleanly either, and the report says so.** All four remaining
  false accepts are Wikipedia template stubs at 411–602 characters; all four false rejects are
  genuine articles at 276–388. Good short news and bad short stubs occupy the same band. 400 vs 500
  is one document out of 67 decided — statistically indistinguishable, and 400 was kept as the more
  conservative of the two.
- **Raising `max_html_ratio` to 0.10 has a named cost:** two `{{Infobox}}` dumps become false
  accepts. The fix is not a lower threshold — `{{Infobox}}` is *wiki* markup and the rule counts
  HTML tags. Belongs in Wikipedia preprocessing. Open item.

**Fixed during the session**

- **The pre-validation config existed only as a fingerprint.** `quality_sample.jsonl` recorded
  `57790136526b` and nothing anywhere recorded what it *was*, so the before/after table could not
  be reproduced — the "before" column was only replayable because the JSONL happens to store the
  verdicts it was drawn with. Recovered by inverting the stored metrics against the stored
  rejections to bracket every threshold, then confirming against the fingerprint, and committed as
  `reports/quality_config_before.json`. **A fingerprint identifies a config; it does not preserve
  one.** Both scoring commands in the report were re-run and reproduce the committed JSON exactly.

**Decisions made**

| Decision | Rationale |
|---|---|
| The report leads with the machine-adjudication caveat in a callout, not a footnote | It is the one place the deliverable does not match what §6.3.5 implies. A caveat at the bottom of a report is one that gets dropped when the report is summarised. |
| Precision going *down* on two rules is reported as the headline, next to agreement going up | `too_short` 1.00 → 0.93 and `script_ratio` 0.55 → 0.50 while false accepts fell 24 → 4. The pre-validation filter was not making precision errors, it was making coverage errors — confidently rejecting too little of the wrong kind. Hiding the precision drop would hide the actual finding. |
| The Gopher comparison config is quoted inline in the report, not added to `configs/data/` | `configs/data/` means "configs the pipeline runs with". A config that exists only to reproduce a comparison belongs in the document that makes the comparison; the probe output it produced is committed as evidence. |
| `reports/probe_stage3_*.json` kept although `stage3_probe.py` is gone | The English and Roman-Urdu-Parl runs are the evidence for stage 3's 0% / 0.21% cross-language error rates, which the new probe's two source runs do not cover. Deleting the tool does not make its measurements wrong. |

---

### Session 8 — 2026-08-04

**Done**

1. **Exact deduplication — stage 6** (`ravaan/data/dedup.py`, `configs/data/dedup.json`, 41 tests).
   Document and paragraph level, raw and normalized hashes, per §6.3.6. Four properties it is
   built around.
   - **Which copy survives does not depend on the order the corpus was read in.** This is the
     property that costs a second pass over the corpus, and it is the reason the module is
     two-phase. PRD §6.3 releases code, manifest and checksums and **no raw text**, so re-running
     this pipeline is the only way anyone — including us in week 15 — ever reconstructs the frozen
     corpus. "Keep the first copy you see" makes that reconstruction depend on read order, and
     `shards.py` deliberately reads in a *seeded shuffle*: a different seed would then produce a
     different corpus from identical inputs and identical code. So the survivor of a duplicate
     group is the document whose **id hashes lowest**, which is a property of the group rather
     than of the pass. It is `stable_unit`'s argument one stage on — shuffling decides what you
     look at first, hashing decides what belongs to what — except that here conflating the two
     changes the corpus rather than a measurement of it.
   - **Normalized text decides, raw text is counted beside it, on the same pass.** §6.3.6 asks for
     both hashes and Finding F made it a prediction. Reporting the counterfactual as a measured
     number is what turns "stage 4 before stage 6" from an argument into a result.
   - **Canonicalization is whitespace collapse and case folding, and stops there.** Every further
     "harmless" fold — punctuation, harakat, sorted lines — makes this a near-dedup with an
     unstated similarity threshold, which is stage 7's job and which stage 7 does with a
     measurable one. Four parametrized tests pin the boundary: one changed character, one removed
     comma, one harakat, one bari-ye must all leave *both* documents standing.
   - **The output is a decision, not a corpus** — a list of removed ids plus a statistics block,
     which is exactly what the release policy can ship and what lets someone who cannot be given
     the text still check the corpus.

2. **`scripts/dedup.py`** — stages 2→6 over real sources, two passes, several sources at once so
   cross-source duplication can be measured at all. Dedup yield is measured on **stage 5's
   survivors** by default (`--no-quality` for the other way), because half of Urdu Wikipedia is a
   template stub farm stage 5 already removes on length and measuring dedup on raw text counts
   that win twice.

**Finding G — a duplicate rate cannot be measured on a sample, and my first run was wrong.**

The first FineWeb2 run reused the probe's habit of `--limit 20000 --sample-rate 0.02` and reported
zero duplicates. That number was meaningless, and not by a little.

- Every statistic before this stage has been **per document**, and a uniform sample estimates those
  honestly. A duplicate is a property of a **pair**, and a sample of rate *r* retains a given pair
  with probability *r²* — so a 2% sample under-reports duplicate pairs by **2,500×**.
- Worse, the subset problem does not go away when the sampling does: reading *n* of *N* documents
  finds a given pair with probability ≈ (*n*/*N*)², so the unsampled 20,000-document window still
  under-reports by ~80×. **There is no window size that fixes this; only a full pass measures it.**
- **Demonstrated rather than argued.** The complete Urdu Wikipedia dump contains exactly 9 duplicate
  groups. Re-run at `--source urdu-wikipedia=0.05`, the same pass over the same dump finds **0** —
  which is what 9 × 0.05² = 0.02 expected groups predicts.
- This is Finding E's shape a second time — the sampling that is correct for one class of
  statistic is silently invalid for another — and it is the reason every stage-6 run below is a
  complete pass over its source rather than a probe.
- **The exception is worth stating, because it makes the expensive measurement cheap.** The *r²*
  penalty applies when both members of a pair are subject to sampling. For **cross-source** overlap
  it need not be: index one source *completely* and sample the other at rate *r*, and a shared
  document is detected with probability *r*, not *r²* — an unbiased estimate scaled by a known
  constant. So "how much of Urdu Wikipedia is inside FineWeb2" does not need a full FineWeb2 pass;
  it needs all of Wikipedia (93,606 documents, minutes) against a fraction of FineWeb2. This is why
  `--source NAME=RATE` takes a per-source rate rather than one rate for the run.

**Finding H — FineWeb2 removed 31% of `urd_Arab` as near-duplicates before we ever saw it, and the
shard says so.**

The shard carries FineWeb2's own `minhash_cluster_size` column. Read over **all 1,547,542
documents** (`reports/probe_fineweb2_minhash.json`):

- **73.08%** of retained documents were singletons; **26.92%** were the representative of a
  near-duplicate cluster. Largest cluster **266**.
- Summing cluster sizes gives an implied pre-dedup population of **2,243,346**, so **695,804
  documents — 31.02% — were removed upstream**.
- **The reading is verified, not assumed.** If FineWeb2 had retained every cluster member and
  merely annotated it, the number of documents labelled *k* would be an exact multiple of *k*. On
  the full population none of them are (262,101 at *k*=2, 32,901 at *k*=4, 6,916 at *k*=6). One
  representative is kept and the rest are dropped. The same test on a row-group *sample* was
  inconclusive, which is why it was re-run over the whole column.
- **This is the fourth stage in a row whose honest report on FineWeb2 is "already clean in this
  dimension"** — encoding (stage 2), language (stage 3), quality (stage 5) and now dedup — and the
  four together are a real finding about what FineWeb2 is, worth a paragraph of the technical
  report rather than four separate apologies.
- **It also sets stage 7's expectation before stage 7 is written.** Near-dedup has little left to
  find on the primary source; its real target is Finding F's cross-publisher republication.

**Finding I — the four documents session 7 named will not be caught by stage 6 *or* stage 7.**

Session 7 sharpened stage 5's error budget into a test with named documents: the four surviving
false accepts (`urdu-wikipedia:122264`, `:122214`, `:363641`, `:122110` — Fortune-1000 company and
geo stubs at 411–602 characters) "are exactly what a length rule cannot see and a dedup pass should
not miss." Measured, the prediction is wrong, and it is wrong in a way that matters.

- **Exact dedup cannot catch them, and the full pass confirms it.** All four come back
  `kept=True, group_size=1` — each is its own group of one. Read side by side, `:122264`
  (Washington Mutual) and `:122214` (Alaska Air Group) share their template sentences verbatim,
  but the differing city and CEO names sit *inside* those sentences, so neither the documents nor
  their lines are exact duplicates. The short footers that *are* identical ("مزید دیکھیے",
  "حوالہ جات") sit below any sane paragraph floor, and are legitimate section headings besides.
  The prediction was measured before the pipeline ran and the pipeline agrees with it.
- **Near-dedup will not catch them either, at any shingle size.** Over 82 US-geography stubs drawn
  from the dump (3,321 pairs), word-shingle Jaccard runs: n=2 median 0.371 / max **0.677**; n=3
  median 0.268 / max 0.574; n=5 median 0.157 / max 0.423; n=8 median 0.067 / max 0.271. **Not one
  pair reaches 0.7 at any n**, against the 0.8 that RefinedWeb and FineWeb use. The stubs average
  91.7 words and the variable parts — place name, county, area, population, elevation, category
  footer — are a large share of them, so a shingle spanning any changed word is destroyed.
- **The consequence is a correction to stage 5's error budget, not to stage 7's design.** The four
  false accepts survive the whole pipeline. `quality_validation.md`'s error budget says two of the
  four are the stub farm and "that is stage 7's"; measured, it is nobody's. The instrument that
  actually removes the stub farm is the one that already did — stage 5's 400-character floor, which
  removes 53% of Urdu Wikipedia — and the residue it leaves is residue.
- **This is worth more as a stage 7 acceptance test than as a stage 6 result.** It is a measured,
  named, negative expectation recorded *before* the near-dedup is written, which is the only time
  such a thing is credible.

**Measured — stage 6 on Urdu Wikipedia, complete dump (`reports/probe_dedup_wikipedia.json`)**

| | Urdu Wikipedia |
|---|---|
| documents reaching stage 6 (after stages 2–5) | 93,606 of 200,148 |
| distinct | 93,597 |
| **duplicate groups** | **9**, every one of size 2 |
| documents kept | **99.99%** (99.99% of characters) |
| hashing raw instead of normalized would remove | **9** — identical |
| line occurrences / distinct | 480,481 / 471,453 |
| line characters repeating another document's line | **0.89%** |

- **The nine are one bot's duplicate output.** They are stub biographies of Punjab Assembly members
  at consecutive ids — `1100322`, `1100323`, `1100327`, `1100338`, `1100341` — plus a handful of
  others. One batch job wrote several articles twice. That is the entire exact-duplicate content of
  the Urdu Wikipedia dump, and it is the right shape for an encyclopedia: redirects are not separate
  articles.
- **Normalized and raw remove the same 9, and that is the correct null rather than a
  disappointment.** Finding F is about *cross-publisher* orthography; both copies of a Wikipedia
  duplicate come from the same publisher on the same keyboard, so stage 4 has nothing to unify. The
  place that comparison can bite is the joint FineWeb2 run, where Arabic-keyboard religious
  publishers meet Wikipedia.
- **Paragraph level is not where the win is either.** 0.89% of line characters are a repeat of
  another surviving document's line. Stage 6 measures it and removes nothing, and this number is
  the argument for leaving it that way: rewriting documents to reclaim 0.89% is a bad trade against
  invalidating stage 5's length floor.
- Stage 5's full-dump rate lands at **46.77% of documents / 86.25% of characters**, against the
  46.72% / 87.38% session 6 measured on a 20,000-document sample. The full-population figures
  supersede those; the agreement is also the cross-check that `scripts/dedup.py`'s reimplementation
  of the stage 2→5 chain matches `scripts/probe.py`'s.

**What is and is not known about FineWeb2 at stage 6.** `reports/probe_dedup_fineweb2.json` is a
19,256-document *window* and it found zero duplicates. Per Finding G that is a statement about a
window and **not** about the shard — it under-reports by ~80× — and it is kept, labelled, rather
than deleted, for the same reason session 7 kept `probe_stage3_*.json` after retiring the tool that
made it: a measurement does not become wrong because it is easy to misread. The authoritative
FineWeb2 result is Finding H, which is stronger evidence from a completely different instrument:
the source arrived with 31.02% of its population already removed by MinHash, and zero exact
duplicates in a window is exactly what that predicts. The full-shard exact count is a deferred
run, not an unknown quantity — see "Next session".

**Finding J — 99.6% of the apparent dedup win on Wikipedia is stage 5's length floor, counted twice.**

Session 7 carried a warning that dedup yield must be measured *after* stage 5 "or the win will be
double-counted". Run both ways over the complete dump, the warning was right by two orders of
magnitude:

| Urdu Wikipedia | documents | distinct | duplicate groups | duplicates | largest group |
|---|---|---|---|---|---|
| dedup **after** stage 5 | 93,606 | 93,597 | 9 | **9** | 2 |
| dedup **before** stage 5 (`--no-quality`) | 200,148 | 197,744 | 190 | **2,404** | **177** |

**2,395 of the 2,404 are documents stage 5 had already removed** — and the group-size distribution
says what they are: 177, 91, 81, 77, 70, 63, 59, 59, 59, 58. Those are not articles, they are
near-empty category shells and navigation stubs, byte-identical in their hundreds, dying on the
400-character floor long before a hash sees them. After stage 5 the largest group in the entire
dump is **2**. A stage-6 result quoted on raw text would credit dedup with almost the whole
length-floor win; the ordering is not a preference, it is the difference between 0.01% and 1.2%.

One extra datum falls out of the same run, and it is Finding F pointing the right way for the first
time in this stage: on the pre-filter population, deciding on normalized text removes **2,404** and
deciding on raw removes **2,403**. Normalizing before hashing found exactly one duplicate pair that
raw bytes missed. The effect is real and, on Wikipedia, negligible — which is what Finding F
predicts, since it is a claim about publishers and Wikipedia is one publisher.
`reports/probe_dedup_wikipedia_noquality.json`.

**Finding K — Roman-Urdu-Parl collapses harder than PRD §6.2's own warning, and this is the first
stage-6 result that removes anything.**

Full pass over the train split's **Urdu** column, 6,333,218 rows
(`reports/probe_dedup_roman.json`):

| | |
|---|---|
| sentences reaching stage 6 | 5,856,384 |
| **distinct** | **889,292** |
| removed | **4,967,092 = 84.8%** |
| duplicate groups | 845,060 — **95.0% of distinct sentences appear more than once** |
| largest group | **228** |
| hashing raw instead of normalized would remove | 4,966,392 — **700 fewer** |

- **PRD §6.2 predicted ~1.09M unique Urdu sentences. Measured: 889,292 — 18.4% *below* the
  warning.** §6.2 was written as a caution and turns out to have been optimistic. This is the only
  source where stage 6 does real work, and it does a great deal of it.
- **Finding F finally fires, on the source where it should.** Deciding on normalized text removes
  **700 more** sentences than deciding on raw bytes: 700 pairs that are the same Urdu sentence typed
  on an Arabic keyboard and an Urdu one. Wikipedia's equivalent number was 1, because Wikipedia is
  one publisher. Roman-Urdu-Parl was built by crawling Urdu sentences from the open web, so it
  inherits exactly the publisher-level orthographic spread Finding F measured — and stage 4 before
  stage 6 is what collapses it. Small in absolute terms, correct in direction, and measured rather
  than argued, which was the whole point of hashing both variants on one pass.
- **The Urdu side is not the side §6.1's budget turns on**, and running both columns is what makes
  that visible (`reports/probe_dedup_roman_latin.json`):

| | Urdu column | Roman column |
|---|---|---|
| indexed | 5,856,384 | 6,032,599 |
| **distinct** | **889,292** | **3,478,770** |
| removed | 84.8% | **42.3%** |
| largest group | 228 | 124 |
| mean sentence length | 62.9 chars | **74.2 chars** |
| normalized vs raw removals | 4,967,092 / 4,966,392 | 2,553,829 / **2,553,829 — identical** |

  The Roman column holds **3.91× more distinct strings** than the Urdu column, which is precisely
  what the corpus was built to contain: §6.2 records that crowdsourcing was added *for spelling
  variation*, so one Urdu sentence maps to several Roman spellings. And the Latin side shows
  **exactly zero** difference between normalized and raw hashing — the correct null, since stage 4's
  folds are Arabic-script and the only transform touching Latin is case folding, which the
  canonicalizer applies to both variants. The two columns together are a clean internal check that
  the variant comparison isolates stage 4 and nothing else.

**Finding K′ — §6.1's 40M-token Roman Urdu budget survives, and the carried-forward estimate that
said otherwise was wrong twice in the same direction.**

progress.md has carried "Roman Urdu's 40M-token target is unverified after dedup… ~1.09M unique
sentences at ~45 characters is ~49M characters ≈ 12M tokens, well under the ~40M target." Measured,
both inputs were wrong:

- It used the **Urdu**-column unique count (1.09M, itself now 889,292) to size a budget for the
  **Roman** population. The right figure is 3,478,770.
- It assumed **45 characters** per sentence. Measured, the Roman column averages **74.2**.

Corrected: 3,478,770 × 74.2 ≈ **258M characters**, which at the 4.1 chars/token the old estimate
itself used is ~63M tokens, and even at a pessimistic 5 chars/token is ~52M. **Either way it clears
§6.1's ~40M target rather than falling to a third of it.** The exact post-dedup character count
needs a two-phase run (`--index-only` reports group structure, not characters) and is the one number
here still carrying an assumption — but the direction is not in doubt, and the corpus-freeze
decision this was blocking can be made. The native-Urdu side contributes 889,292 × 62.9 ≈ 56M
characters to the native pool, already deduplicated as §6.2 concern (a) requires.

**Finding L — Wikipedia *is* inside FineWeb2, exact hashing finds none of it, and that is a
requirement for stage 8 rather than a curiosity.**

The cross-source run indexed Urdu Wikipedia whole (93,606 documents) against FineWeb2 at 25%
(372,879 documents), using Finding G's linear-detection design
(`reports/probe_dedup_joint.json`):

| | |
|---|---|
| indexed | 466,485 |
| **cross-source groups** | **0** |
| duplicate groups found at all | 10, every one within a single source |

Zero is the wrong answer to believe, so it was checked against the shard's own `url` column, over
all 1,547,542 documents:

| host | documents |
|---|---|
| `ur.wikipedia.org` | 1,700 |
| `ur.m.wikipedia.org` | 636 |
| other wiki\* hosts | 52 |
| **total** | **2,388 = 0.154% of the shard** |

- **So Urdu Wikipedia is unambiguously present in FineWeb2 — roughly 1.2% of the dump's articles —
  and exact dedup detects none of it.** The reason is legible once stated: the `wikimedia/wikipedia`
  dump is *processed wikitext*, clean article prose, while FineWeb2's copy is an HTML-to-text
  extraction of the **rendered page**, carrying navigation chrome, edit links, rendered infoboxes
  and category footers. Same content, different rendering, never byte-identical. Nothing is wrong
  with either the hash or the sources.
- **The consequence lands on stage 8, and it is the reason to record this now.** PRD §6.3.8
  specifies decontamination by "hash + fuzzy match against all test sets". This measurement says
  the two halves are not co-equal: for the *most likely* contamination path in this project —
  §8.2's held-out evaluation text is drawn from Urdu Wikipedia, and the same articles sit in the
  training data as crawled HTML — **the hash half returns a confident zero and the fuzzy half is
  the entire mechanism.** A stage 8 that reports "0 contaminated documents" from hashing alone
  would be reporting the artefact measured here.
- **It also re-frames stage 7.** Cross-rendering duplication is a near-duplicate problem, and this
  is the one population in the corpus where a near-dedup has something substantial to find that
  exact dedup cannot — unlike the Wikipedia stub farm (Finding I), where it will find nothing.
- The sampled design bounds the claim honestly: at 25% detection, observing zero puts the number of
  byte-identical cross-source pairs below ~10 with 95% confidence. It does **not** bound the number
  of *same-article* pairs, which the URL census puts at ~2,388.

**Decisions made**

| Decision | Rationale |
|---|---|
| The survivor of a duplicate group is the **lowest-hashing id**, not the first one read — and the cost is a second pass over the corpus | §6.3 ships code, manifest and checksums and no text, so re-running the pipeline is the *only* way the frozen corpus is ever reconstructed, and `shards.py` reads in a seeded shuffle. Keep-first would make the released corpus a function of a seed that is not part of the release. Twelve shuffles of the same input are asserted to give byte-identical survivors. |
| 128-bit hashes, not 64 | A collision here does not mis-file a document, it **deletes** one, with no trace in any log — the single failure this stage cannot detect after the fact. At 64 bits over the ~12M line hashes a full shard produces the birthday bound is ~1e-5; at 128 it is ~1e-24. The difference is one machine word per distinct unit. |
| Canonicalization stops at whitespace and case folding | Anything further — punctuation, harakat, sorted lines — is a near-dedup with an unstated threshold. Stage 7 has a threshold and can report it. Four parametrized tests pin the boundary so a later tidy-up cannot quietly widen it. |
| Paragraph level **measures and removes nothing**; `strip()` exists, is a third pass, and is off | Dropping a line from the middle of a document is a rewrite, which is what stage 5's reject-do-not-repair doctrine forbids, and it silently invalidates the 400-character floor stage 5 applied one stage earlier. Measured, the whole prize is 0.89% of line characters — not a trade worth making. |
| Per-group side tables are **not** sized by the number of groups | Sources are stored only for groups that genuinely span sources, and example ids only for the largest 200, picked in `seal()` once sizes are final. On FineWeb2 the naive version is harmless; on Roman-Urdu-Parl, where PRD §6.2 predicts nearly every group repeats, it is ~1 GB of Python objects to describe a corpus that indexes in a fraction of that. |
| Which groups get an example *snippet* is chosen after sizes are known, not by arrival | Capping snippet capture by arrival order shows whichever groups the read order reached first rather than the largest — on the first Roman-Urdu-Parl run every top group printed an empty string, which is how this was found. |
| `--index-only` is a supported mode, and it deletes the phase-2 fields from its own output | The entire group structure — duplicate counts, largest groups, the raw-vs-normalized comparison, all cross-source overlap — is known when indexing finishes; phase 2 only adds per-document verdicts and character accounting. It halves a full-shard pass. Emitting a character count of zero from a run that never counted characters would be worse than not running it. |
| `decide()` on a document phase 1 never saw is a `KeyError`, not a drop | A phase 2 reading a different set than phase 1 — changed sample rate, a limit, a checkpoint from another plan — would silently shorten the corpus, and nothing downstream could detect it. |
| `strip()` refuses until `finish_paragraphs()` has been called with no `decide()` after it | Stripping against half-built line counts keeps every line whose second copy has not been read yet, i.e. a corpus that depends on where the pass got to. It is the two-phase argument one level down, so it gets the same enforcement. |

**Fixed during the session**

- **The first FineWeb2 run was measured with `--sample-rate 0.02` and its answer was meaningless.**
  Finding G. Every stage-6 run is now a complete pass over its source, and the driver's help text
  says why.
- **`README.md` still pointed at `scripts/corpus_probe.py`**, deleted in session 6, and described
  the pipeline as "stages 1, 2 and 4". Updated, along with the standard-library-only claim, which
  now correctly covers every deciding stage through 6.

---

### Session 9 — 2026-08-04

**Done**

1. **MinHash near-deduplication — stage 7** (`ravaan/data/minhash.py`, `configs/data/minhash.json`,
   52 tests). Document level, word 5-grams, Jaccard ≥ 0.80, per §6.3.7. Four properties it is
   built around.
   - **The estimator is one-permutation hashing with densification, not k-permutation MinHash.**
     Classic MinHash applies K permutations to every shingle: at K=128 over the ~400 word-5-grams
     an average document carries, that is ~50,000 modular operations per document, and the deciding
     stages are standard-library-only by doctrine, so the constant factor *is* the design. OPH
     hashes each shingle **once**, bins it, and fills empty bins from a fixed random probe order.
     Measured: **~0.25 ms per document against ~3.6 ms**, hours against minutes on a full shard.
   - **Unbiasedness is measured, not asserted** — the one thing a hand-rolled estimator must not be
     trusted about. Against exact set Jaccard the bias is **< 0.008** across overlaps 0.5–0.95, and
     the spread matches the theoretical `sqrt(J(1-J)/K)` = 0.035 at J = 0.8. It also holds in the
     regime that worried me: at 30 words a document leaves five bins in six empty and densification
     does nearly all the work, and the estimate stays unbiased with the standard error rising only
     0.026 → 0.048. That is what makes `min_shingles` 8 rather than 128. A per-bin breakdown pins
     the subtle half directly: **bins empty in *both* documents match at 0.7311 against an exact
     Jaccard of 0.7297** — densification agreeing at exactly the Jaccard rate is the property the
     whole stage rests on, and it is now a test.
   - **Jaccard decides; containment is measured beside it**, the same move stage 6 makes with
     raw-vs-normalized hashes. Containment is free — the sketch already needs the set sizes and the
     algebra is exact — and Finding L's population is the reason. It turned out to matter for a
     minority rather than the majority (below), which is a better outcome than the module was
     designed for and is still not nothing.
   - **Which copy survives does not depend on read order**, and `document_key` is *imported* from
     stage 6 rather than reimplemented: two dedup stages that disagreed about which of two copies is
     canonical would produce a corpus neither of them describes. Bucket representatives are chosen
     the same way, so even the candidate set is a function of the corpus rather than of the pass.
   - **Stage 7 is single-pass, and that is a real difference from stage 6.** Stage 6 stores one
     integer per distinct *content* and pays a second read to stay order-independent. Stage 7
     cannot — comparing documents to each other means holding a sketch per *document* — so the ids
     are already in memory and a second pass would buy nothing. The cost is memory, stated rather
     than discovered: ~700 bytes a document, so a full 1.5M-document FineWeb2 shard is ~1 GB.

2. **`scripts/neardedup.py`** — stages 2→7 over real sources. Two things it does that the earlier
   drivers do not, both forced by what stage 7 is.
   - **It runs on stage 6's survivors by default.** Every exact duplicate is also a near duplicate
     at J = 1.0, so a stage 7 measured on pre-stage-6 text claims stage 6's removals as its own —
     Finding J's double-count, one stage on. `--no-exact-dedup` measures the other way.
   - **`--host-filter NAME=SUBSTRING`, applied before any stage.** Finding L's population is 0.154%
     of FineWeb2 shard 001, so reaching it by sampling means reading the shard many times over.
     Naming it by URL costs one parquet scan and answers the question exactly — and because the
     filter runs ahead of stages 2–5, the expensive stages only ever see the 2,388 documents that
     matter.

3. **`reports/neardedup_threshold.md`** — the threshold decision record, in the shape session 7
   wrote for stage 5. Every table in it comes from two corpus passes rather than twenty, because
   the pass retains each candidate pair with its measured similarity and `sweep()` re-clusters at
   any threshold exactly.

**The threshold is 0.80, and the largest-cluster column is the argument**

Urdu Wikipedia, complete dump, after stages 2–6 (`reports/probe_minhash_wikipedia.json`):

| threshold | clusters | removed | largest cluster |
|---|---|---|---|
| 0.30 | 1,236 | 15,853 | **9,979** |
| 0.50 | 1,502 | 6,734 | 518 |
| 0.60 | 1,157 | 2,795 | 88 |
| 0.70 | 357 | 657 | 25 |
| **0.80** | **118** | **179** | **23** |
| 0.90 | 38 | 45 | 6 |

Clustering is connected components, so transitivity is deliberate — A ≈ B and B ≈ C are one
document even when the A–C estimate lands under the cut — and chaining is the price. The table
shows where that price becomes ruinous: at 0.30 a **single component swallows 9,979 documents,
10.7% of the entire dump**, all but one of which would be deleted. Nothing in Urdu Wikipedia is
9,979 copies of one article. Above 0.70 the largest cluster is stable at 23–25 and removals fall
smoothly; **0.80 sits inside that stable region with margin on both sides**, which is what a
threshold should look like. Stage 7 removes **0.19% of Urdu Wikipedia** there.

**Finding M — stage 7 finds 633 cross-source clusters where exact dedup finds 1, and the acceptance
test session 8 wrote before the code passes.**

Session 8's test: Urdu Wikipedia articles also sit inside FineWeb2 as crawled HTML, 2,388 documents
in shard 001 come from wiki hosts, not one is byte-identical to its counterpart, and "if stage 7
does not cluster those, it is not doing the job stage 8 needs it to have done." Measured by pulling
that population out by URL and running it against the complete Wikipedia dump — 2,159 survive
stages 2–6 and join 93,597 Wikipedia documents (`reports/probe_minhash_joint.json`):

| | stage 6 (exact) | stage 7 at 0.80 |
|---|---|---|
| cross-source groups / clusters | **1** | **633** |
| FineWeb2 wiki-host documents removed | — | 302 of 2,159 (14.0%) |
| Wikipedia documents removed as cross-source | — | 331 |

- **Every cross-source cluster is size 2** — one article, one crawled copy — which is the right
  shape and says the clusters are not chaining.
- **The accounting balances against the standalone run exactly.** 179 Wikipedia-internal removals
  here, the same 179 the Wikipedia-only pass produced, plus 331 + 302 cross-source and 1
  FineWeb2-internal = 813. Two independent runs agreeing to the document.
- **The module's central expectation was wrong about the majority, and right about the residue.**
  It was built expecting the crawled copy to be the article buried in navigation chrome, which
  Jaccard cannot see and containment can. Measured, most joint pairs are *high* Jaccard with
  near-identical shingle counts — 0.992 at 884/882, 0.984 at 174/173 — because FineWeb2's
  HTML-to-text extraction strips most chrome. So the shipped Jaccard threshold suffices for them.
  But **11 of 49 sampled cross-source pairs fall below 0.80**, and those are the predicted shape:
  **J = 0.656 with containment 1.000 at 150/96 shingles** — a Wikipedia article whose every shingle
  is in the FineWeb2 copy, scoring 0.656 because the crawled page carries 54 shingles it does not.
- **This converts Finding L's requirement on stage 8 from an argument into a measurement.** §6.3.8
  says "hash + fuzzy match". A Jaccard-thresholded fuzzy match cannot see that pair and a
  containment-thresholded one cannot miss it. **Stage 8 must score containment against the eval
  sets, not Jaccard**, or it reports a confident under-count on the most likely contamination path
  in the project.

**Finding I confirmed against the real code, and more decisively than predicted**

Session 8 predicted stage 5's four surviving false accepts would not be caught at any shingle size.
Measured at threshold **0.50** with high-recall banding — far more aggressive than ships — all four
come back `kept=True, cluster=-1, cluster_size=1` (`reports/probe_minhash_findingI.json`). The
highest pairwise similarity among them is **J = 0.258** (`:122214`–`:122264`, the two company
stubs); four of the six pairs measure **0.000**. They are not near the cut, they are nowhere near
it. **The four survive the whole pipeline**, so `quality_validation.md`'s error budget correction
is now confirmed rather than predicted: stage 5's false-accept rate is stage 5's, not a debt owed
to a later stage.

**A claim that did not survive its own control — recorded because it nearly shipped**

An early comparison showed (16, 8) banding removing 178 documents and (32, 4) removing 813 at the
same threshold. That looks like a 4.6× recall gap, it was briefly written into the config as one,
and it is a **confound**: the 813 came from the *joint* run, whose population includes the 2,159
FineWeb2 documents that duplicate Wikipedia. Two different corpora, and the difference attributed
to the parameter that happened to change. Run on the identical population:

| Urdu Wikipedia, threshold 0.80 | clusters | removed | largest |
|---|---|---|---|
| bands 16 × 8 (`probe_minhash_wikipedia_bands16x8.json`) | 118 | 178 | 23 |
| bands 32 × 4 (shipped) | 118 | 179 | 23 |

The same corpus to within one document. **The banding does not change what stage 7 removes.** It
changes what the *sweep* can measure: (16, 8) has 6% recall at J = 0.5, so every row of the table
above below ~0.70 would be reporting the banding rather than the corpus, and a threshold chosen
from that is chosen from an artefact. (32, 4) has 87% recall at J = 0.5 and costs 60,355 candidates
against 240 that verify — banding precision **0.004**, about a second of exact verification. It
ships for that reason and the config says so. This is Finding E's lesson in a third costume: the
instrument has to be able to measure the quantity being asked for, and a number that moved in the
expected direction is not evidence that it moved for the expected reason.

**Decisions made**

| Decision | Rationale |
|---|---|
| One-permutation hashing with densification, not k-permutation MinHash | 14× faster per document in pure Python, which is what makes a full-corpus pass affordable at all without a numpy dependency in a deciding stage. Its risk is that it is subtly wrong rather than slow, so unbiasedness is a measurement against exact Jaccard and the jointly-empty-bin match rate is a test. |
| Jaccard decides removal; containment is reported beside it | A removal decision should rest on a symmetric measure. Containment is what detects an article contained in a larger copy, which is stage 8's problem rather than stage 7's, and it costs nothing to carry. Measured, 11 of 49 cross-source pairs need it. |
| `document_key` imported from stage 6, not reimplemented | The two stages must agree about which copy of a document is canonical, or the released corpus is one neither module describes. |
| Clusters are connected components, and the chaining is stated rather than mitigated | Transitivity is what makes a cluster a document rather than a pair, and its failure mode is legible in one number (`largest_cluster`) that the threshold table reports at every setting. Capping component size would be a second, unmeasured threshold. |
| Stage 7 runs on stage 6's survivors by default | Every exact duplicate is a near duplicate at J = 1.0. Finding J measured what the same mistake costs one stage earlier: 99.6% of the apparent dedup win on Wikipedia was stage 5's length floor counted twice. |
| Documents below `min_shingles` are kept and counted, never clustered | Stage 7 must not delete what it cannot measure. Below ~8 shingles Jaccard takes a handful of discrete values and a threshold comparison measures granularity, not similarity. |
| The pass retains every candidate pair with its similarity, so `sweep()` is exact | Session 6's lesson was that a threshold has to be moved by documents. Re-running the corpus per candidate threshold is hours; re-running union-find over the retained pairs is seconds and is exact at any threshold above the retention floor. |
| `--host-filter` runs ahead of stages 2–5, not after | Finding L's population is 0.154% of the shard. Filtering first means the expensive stages see 2,388 documents instead of 1.5M, which is the difference between a 20-minute answer and a 2-hour one. |

**Fixed during the session**

- **The same pair was counted once per band it collided in.** `candidate_pairs`, `verified_pairs`,
  the similarity histograms and the sampled pairs were all inflated, and the histograms were
  additionally *tilted*: a similar pair collides in more bands by construction, so the bias ran
  toward the high end — the region the threshold is chosen from. Caught by reading the sampled
  pairs and seeing the same document pair printed twelve times. Now one entry per distinct pair,
  which also skips the redundant verification.
- **`--host-filter`'s skip counter accumulated across both of stage 6's passes**, reporting
  FineWeb2 as 3,188,286 documents — twice its own size. Counted on the first pass only now, like
  the stage 2–5 logs beside it.
- **A test asserted the property the measurement overturned.** `candidate_probability(0.3) < 0.01`
  encoded the assumption that banding should cast a narrow net, which is exactly what the sweep
  needs it not to do. Rewritten to pin the trade that survives the control.

---

### Session 10 — 2026-08-04

**Done**

1. **Evaluation decontamination — stage 8** (`ravaan/data/decontamination.py`,
   `configs/data/decontamination.json`, 60 tests). Both halves of §6.3.8, containment as the
   primary score per Finding M, thresholds per test set. Four properties it is built around.
   - **The eval sets are held exactly, and the MinHash sketch is not used** — Finding N below. The
     *shingling* is imported from stage 7 so the two stages agree what a document is made of; the
     sketch and the banding are not, because they cannot answer this stage's question.
   - **Containment of the *eval item* decides, and the direction is load-bearing.** Stage 7's
     `containment_from_jaccard` divides by `min(|A|, |B|)`, which is right for a symmetric question
     and wrong for a directed one: when the eval item is the larger of the two it silently measures
     the training document instead and reports a number about the wrong object.
   - **Removal is always of the training document.** No survivor rule, no lowest-key tie-break —
     stage 8 is not choosing between two copies, and shrinking a test set to fit the corpus is
     measuring the thermometer. This also makes the stage order-independent *for free*, which is
     the property stages 6 and 7 each pay a second corpus pass to obtain.
   - **What cannot be measured is counted and reported loudly, and the doctrine inverts.** Stage 7's
     rule is "must not delete what it cannot measure". Stage 8's dual is harsher: an eval item too
     short to shingle is contamination that *cannot be detected*, so silence would be a false clean
     bill of health. 30.3% of the Roman-Urdu-Parl test set lands there and is covered by the exact
     half alone.

2. **`scripts/decontaminate.py`** — stages 2→8 over real sources. It reads **both columns** of a
   parallel source (`id#roman`, `id#urdu`), because Roman-Urdu-Parl is the transliteration test
   set's own source and can leak on either side.

3. **`reports/decontamination.md`** — the decision record, in the shape sessions 7 and 9 wrote for
   stages 5 and 7.

**Finding N — the instrument session 9 specified cannot measure the quantity it was specified to
measure, and the exact answer is affordable.**

Session 9's handoff said stage 8 "should import `ravaan.data.minhash` rather than grow a second
estimator with a second threshold nobody swept". Half of that is right and the other half is
backwards, and the arithmetic is not close.

- An eval item sitting **verbatim** inside a training document — containment 1.000, the exact shape
  Finding M says stage 8 must catch — has Jaccard |E|/|T|, which *falls as the document grows*. A
  100-shingle item inside a 1,500-shingle document scores **J = 0.067**, and the shipped (32, 4)
  banding proposes that pair with probability **0.0006**. The pair has to become a candidate before
  any containment can be computed from it, and it does not.
- **Retuning does not rescue it.** (128, 1) reaches 0.9999 recall there and simultaneously makes
  **12% of all pairs** candidates — ~9 × 10⁸ verifications over a corpus × eval-set cross product.
  Either the recall collapses or the precision does, because MinHash estimates *Jaccard* and
  Jaccard between a small item and a large document is low however complete the containment is.
- **The estimator turns out to be unnecessary, not merely wrong.** MinHash exists to avoid the
  all-pairs comparison of a corpus against itself. Stage 8 compares a corpus against a *bounded*
  artifact — §8.2's test sets are ~6K items — so an inverted index over the eval shingles fits in
  memory and one dict lookup per corpus shingle gives the **true** intersection. Containment and
  Jaccard both come out exact, with no standard error, no S-curve and no second threshold.
- **This is Finding E's lesson in a fourth costume:** the instrument has to be able to measure the
  quantity being asked for. A stage 8 built on the sketch would have run, raised nothing, removed
  almost nothing, and reported a clean corpus — the silent failure this stage exists to prevent.

**Finding O — stage 8's first run over real text was wrong by 59×, and only reading the hits showed
it.**

The acceptance test — is Roman-Urdu-Parl's reference split already inside its own train split? —
first reported **648 contaminated documents of 35,858 (1.81%)**. The number was plausible and it
matched the prior, since PRD §6.2 warns the source is machine-produced and collapses 6.37M pairs to
~1.09M unique sentences. It was **59× too high**, and the errors fell into two families that need
two different fixes.

- **Degenerate fragments — two thirds of every hit.** 918 of 1,389 came from eval items of 8–15
  character 5-grams: `angrezi blog` genuinely contained in `az rashid Kamraan urdu blog angrezi blog
  az Shah`, `Pakistani bhai`, `chahiye chahiye`. Real containment, no contamination. **The cause is
  that `min_shingles = 8` means two different things in the two units** — ~12 *words* in the word
  unit, ~12 *characters* in the character unit — and nothing in the config said so. The character
  unit exists precisely because Roman-Urdu-Parl needed it (77.8% of its test rows carry fewer than
  8 word-5-grams), so the two settings had to be introduced together and were not.
- **Templates — long, and untouched by any shingle floor.** `qaisrani , September 4 , 2006` against
  `qaisrani , September 25 , 2006` at containment 0.800; `scan safha number 36 : ( kitaab safha 29 )`
  against `... 21 : ( ... 14 )` at 0.809. A byline with a different year is not contamination. Only
  the threshold moves these.
- **Both fixes are per test set, which is stage 5's shape exactly** — its single Urdu-script floor
  turned out to delete the whole Roman Urdu population, and the rule became per population.
  `EvalSetSpec.for_sentences()` moves all three together because they were measured together:
  character 5-grams, `min_shingles` 8 → **25**, `containment_threshold` 0.80 → **0.90**.
- After both fixes: **11 documents of 35,858 (0.031%)**. Read one by one, **8 are genuine and 3 are
  false positives — precision 0.73 — and all three errors are the one named byline-with-date
  family.** They are left in rather than tuned away: at stage 8 a false positive costs one training
  row out of millions and a false negative costs the validity of an evaluation number.

**The acceptance test passes, and containment is what makes it pass**

| eval item | training document | containment | Jaccard |
|---|---|---|---|
| `parcham sitara o Halal` | `parcham sitara o halal` | 1.000 (exact) | 1.000 |
| `layibriri ka naya project hona chahiye jis **se** aap...` | `... jis **hum** aap ...` | 0.935 | 0.870 |
| `bohat si daad qubool kijiyej !` | `is achay intikhab par bohat si daad qubool kijiyej` | 0.923 | **0.500** |

- The second row is the mechanism §6.2 names: the **same sentence re-transliterated by a second
  crowdworker**, one word apart, split across train and test. Its Urdu column is *identical*.
- **The third row is the argument for containment inside the primary corpus**, not just on the wiki
  path Finding M measured. The test row is a verbatim *suffix* of a longer training row —
  containment 0.923, **Jaccard 0.500**. A Jaccard-thresholded fuzzy match misses it at any sane cut.

**A defect in the reference test set, found on the way.** Nine test rows (`test_set.csv:1:606`
through `1:614`) are spelling variants of one sentence — `jis se` / `jis say` / `jiss se`, `haasil`
/ `hasil` — all matching the same training row, with an *identical* Urdu column. That is not a
contamination finding but an instrument finding: **the reference transliteration split contains
internal near-duplicates**, so any metric computed on it weights that sentence nine times. It
belongs beside the chrF number in the report, and it is an independent reason §8.2's human-written
set exists.

**Finding P — a retention floor carried across the same unit change would have failed the freeze
pass nine tenths of the way through, and it was caught by watching memory, not by reasoning.**

Finding O's lesson recurred within the same session, on a different parameter, and this one was
found only because two detached passes were left running and their RSS grew from 320 MB to 565 MB.

- `retain_hits_above = 0.50` is the floor that makes `sweep()` exact. In *word* shingles it is
  nearly free — unrelated documents measure mean Jaccard 0.00034, so containment ≥ 0.50 between two
  unrelated documents is genuinely rare. In *character* shingles a 30-shingle test sentence shares
  half its 5-grams with a long article **constantly**.
- Measured on Urdu Wikipedia: **11.9 retained hits per document, of which 0.05% are above
  threshold.** 99.95% noise, held in memory so a sweep could explore a range nobody would sweep.
- Projected over a full FineWeb2 shard that is **17.7M retained hits against the 20M
  `max_retained_hits` ceiling — 88% consumed**, i.e. a `MemoryError` hours into the multi-hour pass
  that writes the frozen corpus, presenting as a stage-8 bug rather than as a floor set for the
  wrong unit.
- Fixed in `for_sentences()`, where the other three measured settings already live. Verified on real
  text: retention falls **151×** (11.91 → 0.08 per document, 17.7M → 0.12M projected) and **every
  verdict is identical**. `sweep()` now reports the highest *per-set* floor rather than the config's,
  because one number covering both would be a lie about the half it does not cover.

**Finding Q — one sixth of the reference transliteration split is sitting in Urdu Wikipedia, and
nothing but containment can see it.**

The largest contamination result in the project, measured on the **complete** Urdu Wikipedia dump
and a 5% FineWeb2 sample, both at the shipped per-set settings.

| | Urdu Wikipedia (complete) | FineWeb2 `urd_Arab` (5%) |
|---|---|---|
| documents checked | 93,606 | 74,489 |
| training documents removed | **674 (0.72%)** | **214 (0.29%)** |
| **Urdu-side test items compromised** | **2,729 of 16,241 = 16.8%** | **1,977 = 12.2%** |
| Roman-side test items compromised | 0 | 0 |
| **max Jaccard over every hit** | **0.2616** | **0.0749** |

- **The mechanism is legible.** Roman-Urdu-Parl's Urdu side was crawled from the web and Urdu
  Wikipedia is in that crawl, so §8.2's reference transliteration split overlaps a *training*
  source it shares no lineage with. §4.5 makes transliteration chrF a Holm-corrected secondary
  endpoint; a sixth of its Urdu side was in the training data.
- **A Jaccard-thresholded decontamination finds none of it.** The single highest Jaccard among all
  2,729 compromised items is **0.26**, against stage 7's removal threshold of 0.80. This is
  Finding M's requirement demonstrated at corpus scale rather than on 49 sampled pairs.
- **The hash half found 1 of 899 removals across every population measured**, and zero document-level
  matches over 168,095 native-corpus documents. Finding L is confirmed as a general property of this
  corpus rather than a Wikipedia quirk.
- **Roman-side zero is the control that says the stage is not hallucinating.** Both native sources
  are Arabic-script Urdu, so only the Urdu column can appear in them.
- Two caveats on the artifacts, neither affecting the numbers above: `eval_coverage` inside the two
  native JSONs under-reports (those passes predate the fix recording *every* compromised item, so
  Wikipedia's field reads 193 where the truth is 2,729) — the counts here are computed from the hit
  files, which were always complete; and the hit files are committed **filtered to the threshold**,
  because at the pre-Finding-P floor the Wikipedia one is 890 MB.

**Decisions made**

| Decision | Rationale |
|---|---|
| The eval sets are held **exactly**; no sketch, no banding | Finding N. The sketch cannot propose the candidate, and the exact answer costs one dict lookup per corpus shingle because the eval side is bounded by §8.2 rather than by the corpus. Both scores come out exact as a consequence, which is strictly better than the estimate stage 7 has to live with. |
| The *shingling* is imported from stage 7 even though the sketch is not | Two stages that disagreed about what a document is made of would report overlaps neither of them measured. This is the half of session 9's instruction that survives. |
| Containment is **directed** at the eval item; `min()` is not reused | A 500-shingle eval item sharing 100 shingles with a 100-shingle training row is 20% contaminated. `min()` calls it 100% and deletes a clean document. |
| Thresholds live on the **eval set**, not on the stage | Finding O. The same shape as stage 5's per-population thresholds, and arrived at the same way — by a single global number producing a wrong answer on a population it was not measured on. |
| `retain_hits_above` moves with `for_sentences()`, not globally | Finding P. The floor is nearly free in word shingles and ruinous in character shingles, which is the *third* time in this session a number meant two things in two units. The global default is right for the document-unit sets and would have blown the ceiling on the sentence ones. |
| The exact half stays, despite firing once in 35,858 documents | Its yield is not the argument. It is the **only** cover for the 30.3% of eval items too short to shingle, and it is the right instrument for a 20-character string, where partial containment is not evidence. |
| Line-level exact matching, with a 40-character floor | Document hashing structurally cannot see an eval sentence quoted inside a longer training document, which is the shape of every sentence-unit set in §8.2. The floor is because `اہم خبریں` is a true exact match against thousands of documents and evidence of nothing. |
| Sampling is **honest** at stage 8, uniquely among the cross-document stages | Finding G forbids sampling stages 6 and 7 because a pair statistic sampled at rate *r* is measured at *r*². Stage 8 indexes the eval side **whole** and samples only the corpus, so a contaminated document is found with probability *r*. Same exception Finding G names for the cross-source case. |
| Stage 5 is **not** run on the eval side; stages 2 and 4 are | A test set is an instrument, not corpus. Quality-filtering it would drop exactly the items stage 8 can least afford to lose, and an item stage 5 would reject is still contamination if it is in the training data. Normalization *must* run, or the comparison measures the normalizer. |

**Fixed during the session**

- **`min_shingles` was one number with two meanings** — see Finding O. Now per eval set, with
  `for_sentences()` carrying the measured trio, and a test that pins the two units apart.
- **The first driver defaulted the shingle unit but not its companion thresholds.** Selecting
  `char` for a sentence source while leaving the floor and the threshold at the document defaults
  is what produced the 59× over-count; the unit is no longer separable from the numbers it was
  measured with.
- **The per-set thresholds were stored in an `array("f")`, and single precision rounds 0.80 *up*.**
  float32 holds 0.80 as 0.80000001192, so a document containing **exactly** 0.80 of an eval item —
  20 of 25 shingles, an ordinary value at these sizes — compared as below threshold and was kept.
  The config said 0.80 and the code meant 0.80000001: silent, boundary-only, and on the *removal*
  side. 0.90 happens to round the other way, so the bug's direction varied with the value. Caught
  because a histogram band that could not have changed lost 16 hits between two runs. Now
  `array("d")` — Python floats are doubles, so the stored value round-trips whatever the config
  declares — with a parametrized regression test over five thresholds, verified to fail if the
  `"f"` is restored.

---

### Session 11 — 2026-08-04/05

**Done**

1. **Split creation — stage 9** (`ravaan/data/splits.py`, `configs/data/splits.json`, 69 tests) and
   **`scripts/split.py`**, the fifth driver (stages 2→5 → 9). Written up in
   [`reports/splits.md`](reports/splits.md). Stage 9 has no threshold to validate against read
   documents the way stages 5, 7 and 8 did; what it has instead are guarantees the PRD states in
   prose, so they are built into the construction rather than checked afterwards.
   - **A document's entire fate is one integer.** `bucket_of(doc_id)` hashes the id into
     `[0, 100000)` and every split and arm is a *range of buckets*. Arm A is a **prefix** of arm B,
     so §6.1's "deterministic, seeded subsample of the frozen 100M corpus — not a separate
     collection" is not a property this stage maintains, it is one it cannot violate.
   - **Membership is a per-document function, never "take documents until the budget is full".**
     The fill rule makes membership depend on read order, which is Finding E's defect exactly. A
     bucket range is order-independent and resumable — and it is what lets Finding G's softened form
     apply, so a sampled phase 1 estimates the band quantiles honestly.
   - **Both arms share one held-out set**, carved from the top of the same number line. Per-arm
     held-out sets would make §4.3's primary endpoint a comparison of two BPB numbers computed on
     different data. Bands grow down from the top and arms grow up from zero, so re-sizing §6.1's
     ~5K sequences cannot move a document between the arms.
   - **Every boundary is an integer.** Session 10 lost a stage-8 removal to `array("f")` holding
     0.80 as 0.80000001; `bucket < cut` between two ints has no boundary behaviour to get wrong.
   - **Both columns of a parallel row hash to the same bucket.** `pair_key()` strips stage 8's
     `#roman` / `#urdu` suffix first — hashing them independently would put a sentence's Roman side
     in train and its Urdu side in test about half the time, **the splitter manufacturing the
     contamination stage 8 exists to remove**.

2. **The tokenizer-ordering problem is defused rather than worked around.** §7's tokenizer is Week 5
   and the freeze is Weeks 3–4, so stage 9 cannot count the tokens its budgets are written in. It
   measures **characters** and converts at *solve* time, and the plan carries its histogram — so a
   corrected fertility re-solves every boundary with no corpus pass. Measured on the real Wikipedia
   plan: **0.32 s**, against the ~20 minutes the pass that produced it took. Every run also prints
   the characters-per-word it measured beside the ratio it solved with (urdu 4.89 → 1.40
   tokens/word), so the assumption is auditable in units a reader has intuition for.

3. **`scripts/decontaminate.py` grew `--eval-file`** — a test set from JSONL rather than from the
   acquisition manifest. Three of §8.2's five test sets are not manifest sources and never will be:
   the held-out split is *produced* by stage 9, and the ~200 human transliteration pairs and ~300
   real-OCR lines are hand-built. This is what unblocked item 2 below.

**Finding R — PRD §6.1 and §4.3 do not describe the same corpus, and the reading §6.1 invites is
fatal to the primary endpoint.**

This is the session's largest result and it is a design correction, not a measurement.

- §6.1 lists per-component targets (~120M native "100M for arm B + ~20% headroom", ~40M Roman Urdu,
  ~10M code-switched). §4.3 fixes U ∈ {25M, 100M}. **Assembling an arm by taking each population's
  target gives arm A 25M + 40M + 10M = 75M unique tokens, not 25M.** Both cannot be right.
- **§4.3's own arithmetic settles it.** 396 × 25M = 9.9B and 99 × 100M = 9.9B, so epochs are counted
  over the *whole training set* — and so is the U the reference paper's law takes as its independent
  variable.
- **The cost of the other reading is Finding A's error again, on the arm carrying the primary
  endpoint.** At 70M params and the same 9.9B tokens processed, arm A at a true U = 75M sits **6×
  short** of C_crit instead of 1.79× past it. Reproduce with
  `python scripts/crossover.py --params 70e6 --unique 75e6 --epochs 132`.
- Arm B is the check that this is the *intended* reading and not a convenient one: at U = 100M total
  and 99 epochs the arithmetic gives 0.09× of C_crit, **exactly** the figure §4.3's table already
  states. The table is only reproducible under the total-U reading.
- **So U is the total unique-token budget of an arm**, §6.1's component figures are *pool* targets,
  and the arms are assembled at a fixed mixture (§6.1's targets in proportion, 120 : 40 : 10). Arm
  B is 70.59M native + 23.53M Roman + 5.88M code-switched; arm A is a quarter of each. Holding the
  mixture fixed is what "differ in size and nothing else" means once there is more than one
  population.
- **Two consequences.** (a) **The PRD needs amending at §6.1**, the way §4.3 and §6.1 were amended
  in v2.1 for Finding A — the component figures labelled as pool targets and the arm mixture stated.
  (b) **The code-switched shortfall more than halves**: arm B needs 5.88M, not §6.1's 10M.

**Measured — a complete pass over the Urdu Wikipedia dump, and FineWeb2 at 5%**

93,606 documents reach stage 9 from Wikipedia (200,148 read; stage 5 keeps 46.8%, matching session
6's 46.72%); 416 fall outside the budgeted populations and are counted rather than dropped silently.

| | urdu train | urdu validation | urdu test | code_switched train |
|---|---|---|---|---|
| documents | 83,488 | 3,080 | 2,754 | 2,954 |
| characters | 167,932,053 | 6,321,365 | 6,322,883 | 3,252,802 |
| ~tokens | 47.98M | 1.81M | 1.81M | 0.86M |

- **The band solve is accurate to five decimal places on real text.** Arm A's native budget targeted
  61,764,706 characters and realized **61,764,222** — an undershoot of **484 characters, 0.00078%**.
  Held-out bands land within 0.05%. The undershoot is **always** an undershoot by construction: an
  arm's budget *is* §4.3's U, so a boundary that rounded upward would quietly buy fewer epochs than
  the design specifies.
- **Both structural guarantees were checked against the 93,606 real assignments, not only in
  tests**: arm A ⊂ arm B strictly (33,557 of 86,442), and **0** held-out documents carry an arm.
- **Projected corpus** (Wikipedia complete + FineWeb2 shard 001 ×20). The freeze must re-measure
  this in one unsampled pass, but only one line is close to the boundary:

| population | total chars | ~tokens | arm B needs | margin |
|---|---|---|---|---|
| urdu | 3,852.4M | **1,100.7M** | 70.59M | **15.6×** |
| roman_urdu | 453.6M pre-dedup | **61.5M** post-dedup | 23.53M | **2.6×** |
| code_switched | 21.8M | **5.7M** | 5.88M | **0.97×** |

- **Roman-Urdu-Parl supplies the whole roman_urdu population and the two estimates agree.** A 5%
  pass assigns 281,215 of 301,389 rows (the remainder is 14,210 `empty`, 5,669 `other`, 295
  `english` — session 5's unit mismatch). Its Roman column projects to 453.5M characters *before*
  stage 6; Finding K′ measured 258M *after*, a 43% collapse matching §6.2's warning that the source
  is machine-produced.
- **The band precision tracks document size**, which is the honest way to state it: arm A's error is
  −0.0041% on Roman-Urdu-Parl's ~74-character sentences, −0.0008% on Wikipedia's ~2,000-character
  articles, and **−6.86% on FineWeb2**, whose long tail reaches 240K characters. Same mechanism, and
  FineWeb2's own arm B — four times the budget, same lump — is −0.0110%. The bound is **the largest
  document at the cut divided by the budget**, not a bucket and not a fixed percentage.

**Finding S — a sampled pass reported Gate G1 twenty times too low, and the two wrong numbers
agreed with each other.**

Findings O and P a third time — one number meaning two things depending on how it was produced —
arriving at the one number in this stage that is a **project decision** rather than a statistic.

- `gate_g1()` read the measured character total without scaling by the sample rate. The FineWeb2 5%
  pass therefore printed `ARM_A_ONLY — 52.7M clean tokens` for a shard that holds **~1.05B**.
- **The complete Wikipedia pass independently printed 52.8M.** Two figures that mean entirely
  different things, agreeing to within 0.2% by coincidence — which is exactly the shape that reads
  as corroboration rather than as a bug. G1's ladder cuts arm B at 25–100M and stops the project
  below 25M.
- Fixed: the gate scales by the sample rate and reports the measured figure beside the scaled one;
  arm targets print at the rate they were solved against. `PASS — 1,053.7M (from 52.7M measured at
  r=0.05)`. Two regression tests pin the sampled and unsampled cases apart.

**A correction to how stage 9's precision should be described, from the same pass.** Wikipedia's
0.00078% is not the general case. On FineWeb2 arm A undershot by 211,883 characters, and the bucket
at the cut held a **single 238,787-character document**. With 76,940 documents in 100,000 buckets
most buckets hold at most one document, so **the undershoot is bounded by the largest single
document at the cut, not by an average bucket** — and raising `buckets` cannot reduce it below one
document. At full-scale budgets that is ~0.2%, which is fine; quoting five decimals would not be.

**Finding T — the second stage-8 run, and Finding L is refined rather than confirmed.**

Session 10 left this as "the most important decontamination run in the project and it has not
happened", blocked because the held-out split did not exist. The eval set is the 6,748 held-out
Wikipedia documents; the corpus is FineWeb2 at 5%.

| | |
|---|---|
| training documents removed | **15 of 76,940 = 0.0195%** |
| **held-out items compromised** | **15 of 6,748 = 0.222%** (~4.4% projected to the full shard) |
| by `exact_line` / containment / `exact_document` | 13 / 2 / **0** |

- **Finding L still holds for *document*-level hashing — 0 of 15 — and does not hold for
  *line*-level.** Line matching was added in session 10 on a structural argument with no measurement
  behind it, and it carries **13 of 15** here. Re-running the fuzzy half alone over the same
  documents: **9 of 15 survive without the exact half, 2 of 15 survive without the fuzzy half.**
  Both halves are load-bearing on this path and neither subsumes the other.
- **The two containment-only catches are Finding M's cleanest demonstration yet.** Both are
  `ur.wikipedia.org` crawls sharing **zero** whole lines with the held-out article — HTML rendering
  re-flows the line breaks — while 92% and 90% of the word 5-grams are present. Document hashing
  cannot see them, line hashing cannot see them, and Jaccard would not have proposed them.
- **The hits were read, not assumed.** 9 of 15 removed documents are crawled `ur.wikipedia.org` /
  `ur.m.wikipedia.org` pages — Finding L's mechanism, at corpus scale for the first time. One is
  `top.hatnote.com/ur/`, Wikipedia's own top-articles aggregator. Three are Urdu news and religious
  sites sharing a specific sentence verbatim.
- **Precision ≈ 13/15 ≈ 0.87** (0.73 on session 10's Roman-Urdu-Parl path), and the two errors are
  one *new* nameable family: **the 40-character line floor admits shared quotations — a line of a
  well-known ghazal, and the genre formula "he was a prolific poet and author; among his collections
  the following are important" — which are common third-source text rather than evidence that one
  document contains the other.** Left in, on the standing argument that a false positive costs one
  training row and a false negative costs the validity of an evaluation number.

**Decisions made**

| Decision | Rationale |
|---|---|
| **U is the total unique-token budget of an arm**, not its native component | Finding R. §4.3's epoch arithmetic is only self-consistent under this reading, and the alternative puts arm A 6× short of the crossover — Finding A's error a second time, on the arm carrying the primary endpoint. |
| The arms hold a **fixed population mixture**, §6.1's targets in proportion | "Differ in size and nothing else" (§4.1) has no other meaning once there is more than one population. Scaling only the native component would confound U with source mix, the same failure §6.1 already forbids for crawl date. |
| Splits and arms are **bucket ranges over one hashed integer**, not float thresholds or fill rules | A fill rule makes membership depend on read order (Finding E); a float threshold has boundary behaviour (session 10's `array("f")`). A bucket range has neither, and makes arm A a prefix of arm B for free. |
| Held-out is carved **at the same mixture as the arms** | §8.3 reports validation BPB *by script*. If the held-out mixture differed from the training mixture, aggregate BPB would move with the mixture rather than with the model. |
| **Two** held-out sets (validation and test), not §8.2's one | Gate G4 at mid-W10 *reads the arm A curves* and may cut arm B on what it sees. That is a decision taken on validation data, so §8.2's reported number cannot come from the same set. Costs 5K sequences from a pool with 15.6× margin. |
| An unmet budget is **reported, not raised** | §11's G1 ladder has documented fallbacks ("25–100M → run arm A only"). A stage that raised here would remove the operator's choice; one that truncated silently would hide it. |
| The held-out bands report `unmet_heldout` **separately** from `unmet_arms` | Found on a 2,482-document smoke run: bands are solved from the top, so a pool below §6.1's ~5K sequences eats the train pool and *every* arm then reports unmet for a reason that is not its own. The upstream cause has to be named or the diagnosis is wrong. |
| Stage 9 does **not** normalize `--eval-file` text by default | Stage 9 emits post-stage-4 text. Normalizing twice is harmless, but claiming a pass that did not happen is not, so the hand-built sets opt in explicitly. |

**Fixed during the session**

- **`gate_g1()` did not scale a sampled pass** — Finding S. Two regression tests pin the sampled and
  unsampled cases apart.
- **The unmet-arm check used an average-bucket tolerance.** Buckets vary by more than an order of
  magnitude, so a cut stopped by one heavy bucket looked identical to an exhausted pool and a
  *sufficient* corpus was reported as failing G1. The correct signal costs nothing and is exact:
  whether the bucket *range* ran out rather than the budget.
- **`unbudgeted_measured` and `unassigned_labels` were one counter**, incremented in both phases, so
  a full run double-counted and a plan applied by a later stage under-counted. Split in two.
- **`unmet_arms` came back from JSON as a list**, so a round-tripped plan compared unequal to the one
  that produced it — which is how a freeze ends up unable to prove the plan it applied is the plan
  it measured.
- **`SplitPlan.resolve()` silently re-solved a plan written without its histogram**, returning a
  complete and entirely plausible plan with **every band at zero**. Caught while trimming the
  committed artifacts, which is exactly the path that produces such a plan: the two 5% sample plans
  are committed with their histograms stripped (2.9 KB rather than 2.9 MB) because the freeze
  supersedes them, while `plan_wikipedia.json` keeps its histogram as the only complete-source
  measurement and the one the Week 5 re-solve is demonstrated against. Now refuses.

---

### Session 12 — 2026-08-05

**Done**

1. **PRD amended to v2.2 for Finding R** — the documentation debt session 11 named as the first
   thing owed. §0.2 carries the changelog in the same shape §0.1 used for Finding A, and every
   correction is marked inline rather than silently applied.
   - **§4.3** now says what U counts: an arm's *total* unique-token budget across all three
     populations, which is what its epoch count divides 9.9B by.
   - **§6.1** is split into two tables — **pool targets** (what to collect: 120M + 40M + 10M ≈
     170M) and **arm budgets** (what to train on: arm B = 70.59M native + 23.53M Roman + 5.88M
     code-switched, arm A a quarter of each) — with the mixture, 120 : 40 : 10, stated as the thing
     held fixed across arms.
   - **The headroom claim is corrected.** v2.1 said "100M for arm B + ~20% headroom for filtering
     losses". Arm B's native share is 70.59M, the pools total ~170M against its U of 100M, and the
     headroom is **1.70× on every component** — it falls out of 170/100 and is identical for all
     three by construction, which is a better sentence than the one it replaces.
   - **§8.2 and §10** picked up the two consequential edits session 11 decided and never wrote down:
     two held-out sets rather than one (G4 reads validation and may cut arm B on it, so §8.2's
     reported number cannot come from the same set), and the frozen corpus described as a ~170M
     pool rather than "~120M tokens".
   - Nothing in the design changed. Stage 9 was built to the corrected reading before the amendment
     was written, so there is no code change owed *by* the amendment — but writing it produced one.

2. **Gate G1 now checks the mixture, not just the total (PRD v2.2 §11).** `gate_g1()` reports
   `verdict_aggregate` and `verdict_mixture` separately, takes the more severe, and carries the
   per-population supply / requirement / margin. `scripts/split.py` prints all of it.

3. **Tokenization and sequence packing — stage 10** (`ravaan/data/packing.py`,
   `configs/data/packing.json`, `scripts/pack.py`, 51 tests, `reports/packing.md`). **The last
   pipeline stage; every §6.3 stage now exists.** Four decisions, each protecting a specific
   downstream requirement rather than expressing a preference:
   - **Sequences never cross a population boundary.** §8.3 reports validation BPB *by script*, and
     a sequence built from Urdu Wikipedia and Roman-Urdu-Parl rows has no script to report it
     under — the aggregate would move with the mixture rather than with the model, which is the
     failure stage 9 avoids by carving held-out at the arm mixture. Costs one partial sequence per
     population instead of one per corpus.
   - **Documents *are* concatenated within a population.** Roman-Urdu-Parl rows are single
     sentences averaging ~18 tokens; one document per sequence would be **97% padding** on the
     population §6.1 budgets 23.53M tokens for.
   - **There is no pad token.** §4.3's arithmetic is 396 × 25M = 9.9B tokens processed and
     C = 6ND over exactly that D, so a pad token costs compute and carries no data — the epoch
     count and the unique-token budget would stop meaning the same thing. The tail is dropped and
     counted instead: ≤511 tokens per stream, and an *undershoot*, the same direction stage 9's
     band solve errs in for the same reason.
   - **Each arm packs independently.** Arm A ⊆ arm B in *documents*; taking arm A as a prefix of
     arm B's packed stream would make it a contiguous block of the corpus — **Finding E's defect,
     one stage after stage 9 spent its whole design avoiding it.**

4. **`ravaan-pack` verifies a packed corpus against its own manifest** — digest, length, sequence
   count and the byte sidecar, each of which can fail independently. §6.3's release policy ships
   "manifest, checksums and statistics" and no raw text, so the manifest is the only thing a reader
   can check the corpus against; that makes checking it something the pipeline should do rather
   than describe.

**The tokenizer does not exist yet, and the stage refuses to pretend otherwise**

§7's tokenizer is Week 5 and timeboxed; the freeze is Weeks 3–4. Stage 10 is built against a
`Tokenizer` protocol with a `SentencePieceTokenizer` for Week 5 and a `ByteTokenizer` placeholder
so the plumbing can run now.

- **The placeholder is refused by default and its id says what it is.** `PackedWriter` raises on
  any tokenizer whose id starts with `placeholder:` unless `--allow-placeholder` is passed, and
  every shard manifest carries the tokenizer id, fingerprint, vocabulary size and a `placeholder`
  flag. This is stage 1's licence gate again: a placeholder indistinguishable from the real thing
  is Finding D's shape — a component that passes every test it has and is wrong about the corpus.
- Measured on real Wikipedia the placeholder reads **0.573 chars/token** against stage 9's 3.5. An
  84% "error" that is entirely a property of UTF-8 and says nothing about Urdu, which is exactly
  why a number like that must never reach a report without the word *placeholder* attached.

**Measured — how much the unknown fertility actually costs, swept over the complete Wikipedia plan**

The standing worry was that stage 9's arm cuts move when the real ratio arrives. They do, and the
budget does not (0.3 s per re-solve, no corpus pass):

| chars/token | arm A cut | arm B cut | arm A realized | A ⊆ B |
|---|---|---|---|---|
| 2.50 | 24,389 | 95,448 | **17.65M** | ✅ |
| **3.50** *(shipped)* | **34,161** | **93,470** | **17.65M** | ✅ |
| 4.50 | 43,648 | 91,252 | **17.65M** | ✅ |
| 5.00 | 48,631 | 90,302 | **17.65M** | ✅ |

- **The budget is held exactly at every ratio** — by construction, so this is a check that the
  construction works rather than evidence about Urdu.
- **The reach moves by a factor of two.** Arm A's cut runs 24,389 → 48,631 buckets, so *which
  documents are in arm A roughly doubles* across the plausible range. That is precisely why the
  re-solve must happen **before** the corpus is written: a corpus packed to the old cuts holds the
  wrong documents even though its token count is right.
- Nothing breaks in either direction — nesting, band ordering and reproducibility all hold, which
  is what stage 9 bought by carrying the histogram instead of the answer.

**Verified against real text, which is where the interesting things happen**

A pass over Urdu Wikipedia through stages 2→5→9→10 wrote **7 shards across 7 streams**, and each
was read back cold: **7 of 7 digests match**, sequence counts match the manifest, and every
`.bytes` sidecar has one entry per sequence summing exactly to the recorded `text_bytes`. The
corpus decodes back to Urdu — sequence 3 of `urdu/train/A` is a geo-stub about a French commune,
which is session 9's Finding I looking back out of the packed corpus. Mean bytes per sequence
**511.7 against a 512-token cap**, the gap being separators, which carry no bytes.

**Decisions made**

| Decision | Rationale |
|---|---|
| Fertility is measured against **encoded** tokens, not written ones | They differ by the dropped tail, and `chars` is counted over every document while `tokens_written` is not. A ratio whose numerator and denominator cover different sets of documents is the defect Findings O, P, S and U were each an instance of — four times is enough to build against it rather than watch for it |
| A document that tokenizes to **nothing** is excluded from both sides of the ratio | Whitespace a SentencePiece model drops. Its characters against zero tokens inflate chars/token, so bands come out larger and an arm ends up over budget — and the bias is in the *safe-looking* direction, which is the kind that survives review |
| The separator share is **in** the fertility handed back to stage 9 | ~0.2% on native Urdu but ~5% on Roman-Urdu-Parl, whose documents are one sentence. A ratio computed on content alone would put stage 9's Roman band 5% over its budget |
| Per-sequence byte counts are written, not just totals | §8.3's BPB is NLL / bytes and §4.5's paired bootstrap resamples *sequences*, so the denominator has to exist per sequence or it cannot be reconstructed. 4 bytes against a 1,024-byte sequence — 0.4% |
| Byte order is **pinned**, not inherited | `array` is native-endian. A corpus written big-endian and read little-endian decodes to entirely different, entirely *valid* token ids — silent corruption with no symptom until the loss curve |
| The dtype width is checked against the vocabulary rather than assumed | An id past `uint16` wraps to a plausible token and no later stage could tell. Both the config and the packer refuse it |
| Held-out streams are **not** arm-scoped | Stage 9 carves one validation and one test set shared by both arms; §4.3's endpoint compares the A and B curves, and two held-out sets would make that a comparison of numbers computed on different data |
| Determinism is **inherited** from the reader, not re-invented | The shard reader is already a seeded shuffle with a plan fingerprint over file digests, layout and seed. Stage 10 adds the packer's partial buffer to the checkpoint, because without it a resumed pass restarts each buffer empty and shifts every later sequence boundary — producing a valid corpus that is not the one the checkpoint claims to continue |

**Also done**

5. **FineWeb2 train shard 000 fetched and verified** — **4.84 GB**, not the ~2 GB the earlier note
   implied, and ~50 minutes rather than ~25. All three FineWeb2 files now verify against their
   pinned digests; `data/manifest.json` records 8.30 GB across three files. This is the
   code-switched fix, and Finding U raised its urgency: the requirement is 6.18M rather than 5.88M
   once both held-out sets are counted against the pool, so the shortfall is 8%, not 3%.

6. **`scripts/split.py --measure-only`** — phase 1 and stop, printing pool totals per population
   and writing the plan. Added because the freeze's central operation is "measure once over all
   sources, then apply that one plan everywhere with `--plan-in`", and running that as a two-phase
   pass doubles the most expensive read in the project for a phase 2 whose output is discarded.
   It refuses `--plan-in`, which is its opposite.

7. **Measured the corpus shard 000 was fetched to fix — and Gate G1 passes.** Phase 1 over **both**
   FineWeb2 train shards at 5%, 231,825 documents reaching stage 9
   (`reports/stage9/measure_fineweb2_both_5pct.json`, ~35 minutes, one pass not two).

   | population | supply | needed for arm B + held-out | margin |
   |---|---|---|---|
   | urdu | 3,461.94M | 74.20M | **46.66×** |
   | roman_urdu | 61.43M | 24.73M | **2.48×** |
   | code_switched | **14.52M** | 6.18M | **2.35×** |

   ```
   GATE G1: PASS   (aggregate pass, mixture pass)
     arms fundable at the mixture: ['A', 'B']   short: none
   ```
   - **The projection was checked rather than inherited, and it was wrong in a helpful direction.**
     It said ~10.3M on the assumption that shard 000 ≈ shard 001. Shard 000 is **2.4× the size**
     and contributes 33.4M code-switched characters against shard 001's 17.4M — a factor of
     **1.92**, marginally *less* dense than shard 001 (native Urdu scales at 2.25×) while being far
     more material. **A better answer than projected, from a projection that had the reason wrong**
     — worth checking precisely because this quantity's estimate had already moved three times.
   - **What the fetch actually bought is margin against stage 7.** FineWeb2's exact-duplicate rate
     is nil (Finding H: 31% removed upstream by MinHash) but its *self-similarity* has never been
     measured, and stages 6/7/8 have not run on this sample. At 2.35× the code-switched population
     survives a 50% stage-7 loss; at 0.92× it would not have.

**Finding U — Gate G1 returned `pass` on a corpus from which arm B cannot be assembled, and the
number it printed was 11.7× past the threshold.**

Writing §11's amendment meant deciding what "clean corpus ≥ 100M tokens" means once §6.1 has three
pools and a fixed mixture. It does not mean what the code checked.

| | |
|---|---|
| aggregate, session 11's projected corpus | **1,167.9M** clean tokens against a 100M threshold → `pass` |
| `code_switched` supply | **5.70M** |
| `code_switched` needed for arm B **+ both held-out sets** | **6.18M** |
| margin | **0.92× — short** |
| corrected verdict | **`arm_a_only`** |

- **The binding constraint is a population, not the total**, and the two are not close: native Urdu
  sits at 14.83× while code-switched sits at 0.92×. An aggregate gate cannot see that, and the
  wrong answer is *plausible* — 1,167.9M against a 100M threshold does not look like a corpus that
  fails a gate.
- **This is Finding S one layer up.** There `gate_g1()` read the right quantity in the wrong units;
  here it read the right number and the wrong *quantity*. Both land on the one output of stage 9
  that is a project decision rather than a statistic. §11's ladder cuts arm B on this verdict.
- **The shortfall is 8%, not the 3% session 11 recorded.** 5.88M is arm B's *training* share; the
  validation and test sets are carved from the same pool at the same mixture and are disjoint from
  the arms, so the requirement is 5.88M + 2 × 2.56M × 5.88% = **6.18M**. The recommended fix is
  unchanged and still covers it with room (shard 000 takes the population to ~10.3M), but 0.92× is
  the number to quote.
- **It was already visible** as `unmet_arms` in the stage-9 logs. What changed is that it is now a
  gate verdict rather than a line in a log nobody reads as one — which is the same argument that put
  `unmet_heldout` in its own field in session 11.

**Decisions made**

| Decision | Rationale |
|---|---|
| G1's two conditions are reported **separately** and the verdict is the more severe | "Below 25M" and "no pool can fund an arm" are different projects with different fallbacks. A single merged verdict names neither, and §11's ladder is chosen by the operator reading the cause. Same argument as `unmet_heldout` vs `unmet_arms` |
| The held-out sets **count against the pool** in G1's requirement | They are carved from the pool at the arm mixture and are disjoint from the arms, so a pool that supplies exactly arm B supplies no validation set. Excluding them would make the gate pass a corpus that cannot produce the instrument the gate exists to protect |
| The per-population requirement is computed against the **largest** arm | That is what G1's `pass` means. The smaller arms are reported through `arms_fundable`, which is exactly §11's fallback ladder expressed in the units the fallback is taken in |
| PRD §6.1's headroom is stated as **1.70× on every component** rather than per line | It is 170/100 and is identical for all three by construction. Quoting three numbers would invite the reader to think they were chosen independently — which is the mistake v2.1's "~20% headroom" already made once |
| The v2.2 amendment does **not** touch §4.3's numbers, §9's budget or §12's risk table | Finding R is a reading, not a redesign. Every arithmetic result in those sections was already computed under the correct reading — arm B's 0.09× of C_crit is the proof, since it is only reproducible that way |

**Fixed during the session**

- **`scripts/crossover.py` crashed on any redirected stdout on Windows.** It prints `≈`, `→` and
  `×`; Windows picks cp1252 for a pipe, and `reports/splits.md` §1 tells the reader to run exactly
  this command. Every invocation in this session's own verification died before printing a number.
  Now reconfigures stdout to UTF-8. This is the fourth platform-default bug in the repo (session 2's
  `.gitattributes`, session 4's `Path.write_text` CRLF and `.gitignore` re-inclusion) and the first
  to hit a *reader* rather than the corpus.
- Its docstring advertised the default invocation as "Ravaan as specified in PRD v2", which has been
  v2.0's specification since v2.1 landed. Relabelled, and the three current readings are given as
  examples: arm A, arm B, and Finding R's alternative.
- **The other installed console scripts are one character away from the same failure.** Checked:
  `ravaan-splits`, `ravaan-shards` and `ravaan-normalize` print non-ASCII from `main()` and survive
  only because an em-dash *is* in cp1252 (0x97) while `≈` is not. `ravaan-pack` reconfigures; the
  rest do not, and the day one of them prints Urdu, a `→` or a `×`-free `≈`, it will raise rather
  than mangle. A three-line guard in each would close it — not done here to keep this session's
  diff to its two deliverables, but it is a known hole rather than a discovered one.

**Verified, not assumed**

All three of Finding R's readings reproduce from the script rather than from the report's table:
arm A at U = 25M / 396 epochs is **1.79× past** C_crit, the native-only reading at 75M / 132 is
**6× short** and needs ~802 epochs, and arm B at 100M / 99 is 11× short = **0.09×**, which is
exactly §4.3's published figure and the reason the total-U reading is the intended one.

---

### Session 13 — 2026-08-05

**Done**

1. **PII redaction — PRD §6.3's minimal pass** (`ravaan/data/pii.py`, `configs/data/pii.json`,
   70 tests, `reports/pii.md`). The last unbuilt thing in §6.3, and it belonged before the corpus
   is written. Two regexes, no model, no gazetteer, no name detection — §6.3 says "do not build a
   PII system" and that is the ceiling, not a shortcut. Wired into all five drivers
   (`dedup.py`, `neardedup.py`, `split.py`, `decontaminate.py`, `pack.py`) and into `probe.py`;
   `ravaan-pii` runs it over a single file.

2. **Pointed at real text, three sources, 56,214 documents** —
   `reports/probe_pii_{wikipedia,fineweb,roman}.json`. This is what produced Finding V, below.

**Finding V — 11 of the PII pass's first 13 phone matches on Urdu Wikipedia were ISBNs.**

Finding D's lesson for the seventh time, in Finding D's exact shape, and this time on a stage whose
failure mode is **silent by construction**: a redaction leaves a placeholder, so an over-eager
pattern deletes bibliography entries and nothing is left in the corpus to notice it by.

- **An unhyphenated ISBN-10 in the English registration group is ten digits beginning with a
  zero** — character-for-character a ten-digit landline written without separators. Both matched.
  `آئی ایس بی این [#]` and `بین الاقوامی معیاری کتابی عدد-13: 978-[#]` are what it looked like.
- **The unit test that was supposed to cover this used the hyphenated form** `0-306-40615-2`,
  which the pattern rejects for an unrelated reason (the first group has to be a contiguous
  trunk-zero-plus-prefix, and `0-` is not). It passed and proved nothing. 61 tests passed.
- **The obvious fix was worse than the one the data chose.** A flat floor of eleven national
  digits removes every ISBN *and* one of Wikipedia's two genuine numbers, a ten-digit Multan
  landline. The discriminator is not length: **people separate phone numbers, databases do not.**
  Requiring a separator below eleven digits removed all eleven false positives and kept both true
  positives. Unseparated is still accepted at eleven digits because that is the Pakistani mobile
  format, which is 49 of FineWeb2's 142 phone matches.
- **A second, smaller instance of the same thing surfaced only after the first was fixed:** two
  matches remained, both ISBN-10s beginning `00`, entering through the *international* branch
  because `00` plus eight digits cleared an E.164-theoretical floor no country actually uses.
  `min_international_digits` 8 → 10.
- **What the correction cost on the source that actually has phone numbers: three matches out of
  286.** 10 of 14 removed on Wikipedia against 3 of 286 on FineWeb2 is the evidence that the rule
  discriminates rather than merely being stricter.

**Measured — shipped config, fingerprint `ac44c4eb5021`**

| | Urdu Wikipedia | FineWeb2 `urd_Arab` | Roman-Urdu-Parl |
|---|---|---|---|
| documents | 19,999 | 19,997 | 16,218 |
| documents redacted | 3 (**0.02%**) | 201 (**1.01%**) | **0** |
| phone / email | 3 / 1 | 142 / 141 | 0 / 0 |
| characters removed | 52 | 4,270 | 0 |
| per million characters | **2.3** | **84.2** | **0.0** |

- **FineWeb2 is where the PII is**, at 40× Wikipedia's rate per character, with contexts that say
  so directly: `برائے رابطہ`, `موبائل:`, `ٹیلی فون:`, `واٹس ایپ:`, `ہمارے آفیشل ای میل`.
- **Roman-Urdu-Parl matched nothing at all** — the fourth time a stage has turned out to be an
  *assertion* on a source rather than a filter, after stage 2 and stage 3 on FineWeb2 and stage 6
  on both native sources. The report must say "did not fire", not "cleaned".

**Decisions made**

| Decision | Rationale |
|---|---|
| Placeholders are `[@]` and `[#]` — **no letters, no digits, no angle brackets**, enforced in `__post_init__` | `<EMAIL>` is matched by stage 5's `_HTML_TAG_RE`, so re-running the quality filter over the frozen corpus would score our own redactions as HTML residue and reject documents the run that produced it kept. `[EMAIL]` puts five Latin letters into stage 3's letter count and stage 5's `script_ratio` denominator — the one rule whose measured precision is already 0.50. No digits is what makes redaction idempotent. Two tests assert the consequence (`html_ratio == 0.0`, `script_ratio` unchanged to 1e-9) rather than the property |
| Runs **after stage 5, before stage 6** | Both edges load-bearing. Stage 5's thresholds were moved by 200 adjudicated *unredacted* documents, so redacting first applies a validated filter to text the validation never saw. Stages 6 and 7 hash, so hashing first fingerprints a corpus the release does not contain |
| The phone pattern is anchored on **dialling structure**, not on runs of digits | A "7+ digits" rule deletes dates, year ranges, prices, ISBNs and Quranic citations, and Finding F put religious publishers among this corpus's largest contributors. `:` is deliberately not a separator — that is how surah:ayah is written |
| **Nothing ever stores what it matched.** `PIIResult` has no `original`; matches carry a *shape* (`dddd-ddddddd`) | `NormalizationResult` keeps an original because §6.3.4 requires auditability. Here the original *is* the personal data, and a result that carried it would serialise the corpus's phone numbers into whatever log wrote it out — the artifact this stage exists to prevent. The shape is sufficient: the whole Finding V diagnosis came from the shape table |
| Probe context windows are cut from the **redacted** text, *and* residual digit runs in them are masked to their length (`{10d}`) | The first half came from reasoning about the failure mode; the second came from grepping the file that was about to be committed, which had **29 live phone numbers** in it — the ones the pass had *missed*, sitting in the redacted text untouched. The stage that exists to remove phone numbers from a corpus had put twenty-nine of them into its own report. Years, prices and page numbers stay legible because the floor is six digits |
| Counts are taken on the corpus pass, not sampled by `probe.py` | Unlike stage 4's per-rule counts, "N phone numbers and M email addresses removed" is a claim the release makes about the corpus. `pack.py` is the pass that writes it, so it is the pass that counts |
| Indian mobile formats, dot-separated numbers and `[at]` obfuscation are **left uncaught and stated** | All three are measured in the FineWeb2 sample. Catching bare ten-digit runs with no trunk prefix is exactly the ISBN shape Finding V removed. §6.3 caps this stage's scope; `reports/pii.md` §6 is what the cap costs |

**Carried into the freeze**

- **The eval sets must go through the same redaction before stage 8 runs.** Stage 8 compares
  training text against them; if a training document's only overlap with an eval item is a phone
  number, redacting one side and not the other makes the match disappear and leaves the document
  in. Same function, called on both sides.

---

### Session 14 — 2026-08-05

The session began by trying to start the freeze and got as far as reading the drivers.

**Finding W — the freeze order is not runnable. Stages 9 and 10 cannot see stages 6, 7 and 8.**

Session 13 signed off with "**Nothing in §6.3 is unbuilt** … every remaining item is a freeze run,
not a new component." Both halves of that are true about the *stages*. Neither is true about the
pipeline, because there is no pipeline — there are six drivers, each of which runs stages 2→5 and
then its own stage, and **none of them chains**.

| driver | stages it runs | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|
| `probe.py` | 2–5 | | | | | |
| `dedup.py` | 2–6 | ✅ | | | | |
| `neardedup.py` | 2–7 | ✅ | ✅ | | | |
| `decontaminate.py` | 2–5, 8 | opt | | ✅ | | |
| `split.py` | 2–5, **9** | ❌ | ❌ | | ✅ | |
| `pack.py` | 2–5, **9, 10** | ❌ | ❌ | ❌ | ✅ | ✅ |

`dedup.py`, `neardedup.py` and `decontaminate.py` each *write* `--removals`. **Nothing could read
one.** So the freeze order 6 → 7 → 9 → 8 → 10 was a sequence of passes with no way to hand anything
between them, and running it as written would have produced:

- **a stage-9 pool measured over undeduplicated text** — overstated, and Gate G1 read off it;
- **a held-out split carved from that pool**, containing near-duplicates of training documents.
  This is the exact failure the 6 → 7 → 9 ordering was introduced to prevent, one layer below where
  it was being prevented: the *order* was right and the *mechanism* was missing;
- **a packed corpus that had been through no dedup and no decontamination** — and the packed shards
  are byte-identical in shape either way, so nothing downstream could tell.

It is Finding S and Finding U's family again: the quantity was right, the plumbing that carries it
was not, and the wrong answer is the plausible-looking one.

**What was built — `ravaan/data/exclusions.py`, 17 tests**

The ids are the easy half. The hard half is that **a list of ids carries no evidence of the corpus
it was computed over**, and every way of getting that wrong is silent:

- a list from a 5% pass removes a twentieth of what it should, and **every id in it matches**, so
  no count anywhere is out of place;
- a list from `--limit 20000` is **fingerprint-identical** to one over the whole corpus, because
  `plan_fingerprint()` deliberately does not cover the limit — a limit does not change *which
  documents in what order*, which is precisely what the fingerprint is a hash of;
- a source with **no** list is the freeze order not having been run for it, and looks exactly like
  a source that had nothing to remove.

So the file carries a header naming the read plan of every source it covers, the consuming pass
checks its own readers against it, and refuses on a mismatch. Verified against real text — the two
fingerprints in the refusal below are **the same string**, which is the whole point:

```
exclusions for 'urdu-wikipedia' were computed over a different read:
  plan 8743e78c000775aa limit 4,000 rate 1.0
  against this pass's plan 8743e78c000775aa limit all rate 1.0
```

A source with no coverage is *reported*, not refused — it legitimately has none until its own stage
6/7 pass has run — and a pass given no list at all prints one line rather than one per source,
because a measurement run without exclusions is correct and should not drown in warnings.

**Two bugs the wiring found, both of which would have reached the corpus**

- **`neardedup.py --removals` wrote only stage 7's half.** Stage 6's removals were computed, used,
  and dropped on the floor. A stage-9 run handed that list would have put **every exact duplicate**
  back into the pool it was measuring. On the 4,000-document Wikipedia smoke run this is the
  difference between 1 removal and 0 — the whole file, because stage 7 removed nothing there.
- **`decontaminate.py --removals` wrote `id#roman` / `id#urdu` variant ids.** Stage 8 reads a
  parallel row as two documents because contamination arrives on one side or the other; every later
  stage reads it as one. Those ids match nothing downstream, so the list would have removed
  *nothing* while the pass reported a removal count. Now written as row ids through `pair_key` —
  the same function stage 9 splits on, which is the function that already owns this rule.

**Also closed: session 13's eval-side redaction, and it is bigger than "hygiene"**

Stage 8 compares the corpus against the eval sets. The corpus side is redacted in every driver's
`Pipeline` before anything hashes it; **neither eval loader redacted at all.** Measured on a
28-word document with one phone number and one email:

| eval side | corpus side | stage 8's verdict |
|---|---|---|
| redacted | redacted | **removed** — `eval_set=probe` |
| **not** redacted | redacted | **kept** |

Two redactions move containment below the threshold, because each placeholder sits inside five
word-shingles. So the document was not merely scored lower — it was **kept, and the pass reported a
clean corpus.** The test asserts `kept` on the broken configuration deliberately: this is the one
stage whose failure leaves nothing behind to notice it by.

Unconditional, with no flag — there is no configuration in which redacting one side and not the
other is correct. Safe to apply twice because the placeholders carry no digits and no letters
precisely so that redaction is idempotent (session 13's decision, now load-bearing for a reason it
was not chosen for). Verified idempotent on Finding V's negatives too: ISBN, `surah:ayah` and bare
years all survive both passes untouched. These are also **the first driver-level tests in the
suite** — `scripts/` is ~2,900 lines with no coverage, and this property was worth starting on.

**Also closed: the cp1252 hole, as a class rather than as its three named instances**

Session 12 diagnosed `ravaan-splits`, `ravaan-shards` and `ravaan-normalize` as one character from
raising, and prescribed "a copy-paste into each". There are **twelve** console entry points and two
of them had the guard. `ravaan/console.py` now holds it and all twelve call it. This is the fifth
Windows text default this repo has been bitten by, after `.gitattributes` (session 2),
`Path.write_text`'s `os.linesep` and `.gitignore` re-inclusion (session 4) and `crossover.py`
dying on a redirected stdout (session 12).

**Measured — the machine, which no freeze estimate had ever checked**

Every pass so far was 5% or Wikipedia-only, so nothing in the log says whether the freeze *fits*.

| | |
|---|---|
| RAM | **16.0 GB total, ~2.0 GB free**, 48 GB pagefile on `D:` |
| disk | **29 GB free of 377 GB — 93% used** |
| cores | 16 |

Stage 7's index is ~700 bytes per document at K=128. FineWeb2's two train shards hold ~5.26M
documents, so **the stage-7 freeze pass projects to ~3.2 GB of sketches plus ~1.3 GB of stage 6's
index**, and Roman-Urdu-Parl's Roman column at 6.37M rows projects similarly. That is survivable on
this machine only with the browser and editor closed, and it will page rather than fail if not —
the pagefile is on a different drive, so the failure mode is a pass that takes four times as long
rather than one that stops. **`max_index_entries` is 8,000,000, so the guard does not fire first.**
This is a number the freeze plan should have carried and did not.

**Decisions made**

| Decision | Rationale |
|---|---|
| The removal list keeps its plain-text format — ids, one per line — and the header is a `#` comment | These files get read by hand and `grep -v '^#'` is still the whole format. It is also what lets `reports/dedup_removals_wikipedia.txt`, written before headers existed, still load — against a stated warning rather than a crash |
| A mismatched read plan **raises**; an uncovered source is **reported** | They are different mistakes. Applying a list from the wrong read silently removes the wrong documents and nothing downstream can tell. A source with no list is the normal state until its own pass has run, and refusing it would make the first freeze run impossible to start |
| The header records `limit` separately from `plan_fingerprint()` | The fingerprint deliberately excludes it, and that is correct — but it means a smoke-test list and a corpus list are the same string. This is the one field that separates them, and the test that locks it asserts the fingerprints are equal |
| Exclusions are applied **ahead of stage 2**, not after stage 5 | They cost nothing there, and — the part that matters — they never enter this pass's stage 2/3/5 logs, which should describe the corpus that survives rather than the one that was read |
| The post-condition is `applied == len(list)`, and a shortfall is printed | Exclusions are applied before stage 2, so on a matching read every id is a document the reader still emits. This catches the *limit* mistake from the other side. It cannot catch the *sample-rate* mistake, where the list is a subset and every id fires — only the header catches that one, which is why both exist |
| Stage 8's list is written as **row** ids | A parallel pair whose halves land in different splits is not a pair (§6.1's "~500K deduplicated pairs"). Removing one column and keeping the other is how a pair stops being one |
| `neardedup.py` writes stages 6 **and** 7 as one list, labelled `6+7` | They are one pass and one decision about the corpus. Two files would be two chances to pass only one of them |
| The cp1252 guard went to one module rather than three copy-pastes | Closing three instances of a twelve-member class is how the same bug comes back in session 17 |

**The first freeze run — stage 6+7 over the complete Urdu Wikipedia dump**

`reports/freeze/removals_67_wikipedia.txt`, 188 ids, header carrying
`plan 8743e78c000775aa limit null rate null`. The first genuine freeze artifact.

| | |
|---|---|
| reaching stage 6 | 93,606 documents |
| distinct | 93,597 — **9 exact duplicate groups** |
| stage 7 sketched | 93,597 (0 below `min_shingles`) |
| kept | **93,418 / 93,597 = 99.81%** of documents, 99.80% of characters |
| clusters | **118**, largest 23, 179 documents removed |
| candidate → verified → retained pairs | 60,355 → 240 → 12,976 |

**Both headline numbers reproduce sessions 8 and 9 exactly — and that is the finding, not the
formality.** Session 8 measured 9 exact duplicate groups on the whole dump; session 9 measured 118
clusters at threshold 0.80 ("118 either way" across the band sweep). **Session 13 inserted the PII
pass between stage 5 and stage 6**, which changes the text every subsequent stage hashes, and
nothing had ever checked what that did downstream — session 13 measured redaction in isolation.
It does nothing here, which is the right answer for a source where redaction touched 3 documents in
19,999, and it is now measured rather than assumed. **The first FineWeb2 pass is where this stops
being safe to assume**: 1.01% of documents redacted there, at 40× Wikipedia's rate per character.

The run also demonstrates the `--removals` bug in the size it would have had: stage 7 removed 179
and stage 6 removed 9, and the file holds **188**. Before this session it would have held 179, and
those 9 would have gone back into stage 9's pool.

**Also taken: the single-pass stage 6+7 driver** — session 13's "cheap halving", deferred earlier in
this session and then taken once the Wikipedia pass was running against committed code (the running
process had its modules loaded; editing cannot reach it).

`--single-pass` sketches during stage 6's phase 1 and calls `MinHashDeduplicator.drop()` afterwards.
**The equivalence is by construction, not by argument**: `drop` runs before `build`, and both
`_band` and `_cluster` iterate `_eligible`, which `drop` has already left — so a dropped document is
never banded, never a candidate, never in a component, never a keeper. Eleven counters are asserted
identical against a two-pass index over the survivors.

**And then checked against real text at full scale, which is the part that matters.** The same
complete Wikipedia dump, single-pass, compared field by field against the two-pass freeze run:

| | |
|---|---|
| top-level report fields compared | **48** |
| differing | **1** — `dropped_before_build` (9 against 0), the field that exists to record the mode |
| removed ids | **188 in both, byte-identical** |
| identical | `clusters`, `largest_cluster`, `documents_kept`, `chars_kept`, `candidate_pairs`, `verified_pairs`, `retained_pairs`, `shingles_total`, `similarity_histogram`, `top_clusters`, `pair_examples`, every per-source table |

A unit test asserting eleven counters on nine synthetic documents is not evidence that a mode is
safe to spend six hours on; this is. It is the same practice as every threshold in this project —
Finding D's lesson, which by now has cost the repo seven findings: **fixture tests prove a rule does
what it says, and only real text shows whether it does it to the right documents.**

**Session 13's note had the accessor wrong, and it is worth recording why.** It said the work needed
"a small public accessor on `ExactDeduplicator` to avoid reaching into `_best`". `is_kept()` already
is that accessor — and it takes the **text**, which a single-pass driver has thrown away by the time
phase 1 seals. The text-free form is `wins_group(doc_id)`: `_best`'s values are exactly the set of
winning keys, a key identifies one document, and that document belongs to one group in which it is
the minimum, so *"my key is a winning key"* and *"I win my group"* are the same statement. The real
work was on the other side — `MinHashDeduplicator` had no way to un-index anything.

**Opt-in, because it costs two real things and both are per source.** Peak memory rises by the
source's exact-duplicate rate: nil on FineWeb2 (Finding H), but ~2× on Roman-Urdu-Parl's Roman
column, whose 6.37M rows collapse toward 3.48M distinct — and that is the one source this machine
cannot afford it on. And **stage 6's phase-2 counters are not measured at all**, because `decide()`
never runs; the payload says `phase2_measured: false` rather than emitting a block of zeros a reader
would take for "stage 6 removed nothing".

**Finding X — stage 7's index costs twice what the module documents, and the freeze does not fit on
this machine.**

The FineWeb2 pass was launched on a projection of ~5.4 GB built from `minhash.py`'s own docstring
(~700 bytes per document for the sketch and its bookkeeping, plus ~279 for stage 6's index).
Measured on the running pass:

| | |
|---|---|
| parquet read | **1.26 GB of 6.5 GB — 19%** |
| private memory at 19% | **1.71 GB** |
| implied per document | **~2,010 bytes**, against ~980 projected |
| extrapolated to ~4.98M documents | **~9–10 GB** |
| free physical RAM | **0.9 GB** |
| CPU | 3.25 h for 19% → **~17–19 CPU-hours** for the pass |

The excess is Python object overhead the docstring's `tracemalloc` figure did not carry: the id
strings in `_ids`, the `_position` dict, and `measure_alternate`'s second hash set in stage 6. **It
will not fail** — the 48 GB pagefile on `D:` absorbs it, and neither ceiling is near (3.4M candidate
pairs against `max_candidate_pairs` 20M; 0.7M retained against 40M). It will simply become
unusable, because banding reads every sketch 32 times and most of those reads would come from disk.

Two things follow, and the second outlives this session.

1. **The freeze needs a machine with ~30 GB, and the plan is now Kaggle** — free, ~30 GB on a CPU
   notebook, and PRD §9 already assumes an account. `reports/freeze_on_kaggle.md` is the runbook.
   **The binding constraint there is the ~12-hour session cap against FineWeb2's ~19 CPU-hours**,
   and `neardedup.py` is not resumable — the shard *reader* checkpoints, the MinHash index does not
   — so an overrun produces nothing. The runbook's step 4 is a timed trial that turns the
   extrapolation into a measured rate *before* a session is committed to it.
2. **A projection built from a docstring is not a measurement**, and this one was wrong by 2× in the
   direction that costs a day. The number was there to be taken — one read of
   `PrivateMemorySize64` in the first hour would have caught it — and it was not taken because the
   pass had already started. Finding D's lesson now has a memory-shaped instance: **a profile in a
   docstring describes the object, not the process holding a million of them.**

**Also, on the estimate that could not be made at all.** Roman-Urdu-Parl's runtime has no
projection. A two-point cost model fitted to Wikipedia and FineWeb2 returned a **negative**
per-document cost (−26 ms) and a negative runtime, because two observations cannot separate a
per-document term from a per-character one when both sources are character-dominated and one of the
two observations was itself a guess. It is recorded here as discarded rather than quoted, and the
runbook asks for a timed trial instead. 6.37M rows of ~74 characters is a shape nothing in this
project has measured.

**On the halving**

Session 13's "cheap halving" was taken after all — see above. The reasoning that deferred it
stands as written and is why it landed *after* the Wikipedia pass rather than before: a freeze pass
should not run against corpus behaviour that has just been rewritten. What changed is that the
Wikipedia pass turned out to be long enough to build it underneath.

**Still not taken, and the next thing to weigh:** the freeze is four to five full corpus reads
(6+7, then 9, then 8, then 10), and `--single-pass` removes one of the five. A driver that ran
stages 2–5 **once** and spilled the surviving normalized text to a compact intermediate would remove
three of the five — but the spill is ~19 GB of UTF-8 for FineWeb2 alone against 29 GB of free disk,
so it needs compression to be viable at all on this machine. **Not recommended before the freeze**;
recorded because it is the shape the freeze wants and the reason it is not being taken is a disk
measurement rather than a preference.

### Session 16 — 2026-09-10

**Five weeks passed with no work logged.** Session 15's Kaggle automation was written on 2026-08-06
and never committed; the calendar is now week 6 of 16, against a plan that has the corpus freeze
finishing in week 4 and **G2 due end of week 7**. Nothing about the design has changed in the gap.

The session's whole subject is the boundary between this repo and Kaggle, and it produced three
findings that are one family: **every fact about that boundary had been taken from documentation
rather than measured, and each wrong one failed either silently or illegibly.** Kernel 00 has now
failed three times, for three different reasons, and the third one is the user's to fix.

**What session 15 had already done, and what was wrong with it**

`kaggle/` holds a driver (`push.py`) and three kernel scripts. Checked against the live account
rather than read: the OAuth login had gone through (`awaisbinadil`, `auth_method: ACCESS_TOKEN`),
the code dataset was uploaded, processed and **correctly extracted** — 49 files, and its
`ravaan/data/dedup.py`, `ravaan/data/decontamination.py` and `scripts/neardedup.py` are byte-exact
matches for HEAD, so no re-upload was needed. Kernel 00 had been pushed and had **errored 1.6 s
into its run on 2026-08-06**, and nobody knew, for the reason below.

**Finding Y — a kernel's address comes from its *title*. The slug in `id` is discarded.**

`push.py` stored `slug` and `title` as independent fields and all three kernels disagreed. Pushing
`id: …/ravaan-freeze-00-fetch-trial` under the title "ravaan freeze 00 fetch and trial" produced a
live kernel at **`…/ravaan-freeze-00-fetch-and-trial`**, so `status`, `logs` and `pull` all queried
an address that answers:

```
Cannot access kernel 'awaisbinadil/ravaan-freeze-00-fetch-trial'
  (Permission 'kernels.get' was denied)
```

That is why a failed run sat unread for five weeks: the poller could not see the kernel it had
pushed, and the error message blames permissions.

**The cost still ahead of it was larger.** Kernels 01 and 02 mount kernel 00's output as their
corpus by naming it in `kernel_sources`. Under the drift that name pointed at nothing, so both long
passes would have started with **no corpus** and died at `find_corpus_root()` — after a ~12-hour
session and the trial that authorised it had been spent. `neardedup.py` is not resumable, so that
is a day for nothing.

Fixed by deriving one from the other: `title_for(slug)` returns the title Kaggle will slugify back
into exactly `slug`, so both fields carry the same string and it stops mattering which one the
server honours. `assert_ref_live()` then confirms the pushed kernel is reachable at the address this
file will ask for — the check whose absence hid the first failure.

**Finding Z — the mount is `/kaggle/input/datasets/<owner>/<slug>/`, two levels below where the
documentation says.**

With the address fixed, kernel 00 was re-pushed and **failed again at 1.1 s, identically**:
`no code dataset found under /kaggle/input`. The dataset was attached — its own live metadata says
`dataset_sources: ['awaisbinadil/ravaan-code']` — and `datasets status` said `ready`. The first
hypothesis was a processing race, since the dataset's files landed 16 seconds before the original
run started. **That hypothesis was wrong, and it was cheap to stop guessing:** a kernel whose only
job is to print the tree (`kaggle/diag_input.py`, pushed and complete in under a minute) answered it.

```
/kaggle/input holds 1 entry:
  dir  datasets
--- /kaggle/input/datasets ---
  dir  awaisbinadil
        ravaan-code
kernel 00's test — */scripts/neardedup.py: []
anywhere at all: ['/kaggle/input/datasets/awaisbinadil/ravaan-code/scripts/neardedup.py']
```

The file was there the whole time. `glob("*")` against `/kaggle/input` was one directory level too
shallow, in **five places across three files** — the same wrong assumption copy-pasted, which is
session 14's cp1252 lesson arriving on schedule.

Fixed as a class. `find_mount(marker, what=…)` searches breadth-first for a file the mount must
contain and returns the shallowest directory holding it, so the depth is never assumed again. It
lives in `kaggle/mount_bootstrap.py` — **the one place in this repo where a copy-paste is correct**,
because a kernel push uploads a single `code_file` and the code that *locates* the uploaded project
cannot be imported from it. Two parametrized tests hold the three copies to that source character
for character and assert the shallow form is absent.

**Finding Z′ — `enable_internet: True` is recorded, returned by the API, and not a network.**

Third push. The mount fix worked — `code dataset: /kaggle/input/datasets/awaisbinadil/ravaan-code`,
pip install, then the fetch started on `data/urd_Arab/train/001_00000.parquet` — and died at 41 s:

```
socket.gaierror: [Errno -3] Temporary failure in name resolution
```

No DNS. The kernel was pushed with `enable_internet: true`, and pulling the **live** kernel's
metadata back confirms Kaggle stored and returns `enable_internet: True`. The container had no
network regardless, which is what an account without **phone verification** gets. The runbook has
had "Phone Verification, required before a notebook can use the internet" as step 0.1 since session
14; what it did not have is the symptom, and the symptom is a DNS error thirty lines deep in a
urllib traceback that names neither the internet nor verification.

So the flag is not evidence. The only evidence a notebook has a network is a hostname resolving
inside a run, and `freeze_00` now checks exactly that, first, and exits with the fix in the message:

```
no network in this container — huggingface.co does not resolve (…).
Kaggle records `enable_internet: True` and still gives an unverified account no DNS.
Fix: kaggle.com -> Settings -> Phone Verification …
```

A test pins the ordering, because a preflight after the fetch is not a preflight.

**A fourth bug, found locally instead of on Kaggle — and the read plans are now pinned**

With the fetch blocked there was no way to exercise kernel 00 past its first minute, so the pieces
after the fetch were run here instead. One of them does not work: the line whose comment reads
*"the fingerprint that has to match back home for --exclude to accept these removal lists"* was

```python
run([sys.executable, str(code / "scripts" / "neardedup.py"), "--limit", "1"])
```

and `--source` is **required**. Under `check=True` that exits 2 and kills the kernel in the minute
after the 7.7 GB fetch. **Nothing in a push validates the code it uploads**, so this was only ever
going to be found by running the driver.

Replaced with a check rather than a print, since the quantity is worth refusing on. All three plans
measured here for the first time — Roman-Urdu-Parl's had never been recorded anywhere:

| source | files | plan |
|---|---|---|
| `urdu-wikipedia` | 1 | `8743e78c000775aa` |
| `fineweb2-urd_Arab` (train) | 2 | `54b744f92e3949f8` |
| `roman-urdu-parl` (train) | 1 | `db3a15522463a364` |

Two of the three corroborate independently: Wikipedia's is the header of session 14's frozen
`reports/freeze/removals_67_wikipedia.txt`, and FineWeb2's is the value session 15's runbook claimed
after checking it on a rented box. `check_read_plans()` compares all three after the fetch and
**refuses the session on a mismatch** — a differing plan means every removal list the session would
write is refused by name when `--exclude` reads it back, which is a ten-hour pass for nothing. The
literals are pinned in `tests/test_kaggle_push.py`, as this repo pins every other hash.

**One more inconsistency, in the runbook rather than the code**

Every flag all three kernels pass was checked against `neardedup.py --help`: all valid. But the
runbook's §5 snippet carried **`--single-pass` on Roman-Urdu-Parl**, which `freeze_02_roman.py` never
had and which contradicts the paragraph directly beneath it. The kernel is right and the doc was
wrong, for a reason stronger than the memory argument it states: **kernel 00 times Roman-Urdu-Parl in
the two-pass form**, so a single-pass run is not covered by the projection that authorised it — and
that projection is the only thing standing between this pass and a hard, unresumable session cap.

Both properties are now tests, and both read the *argv the kernel builds* rather than its text — the
first version searched the source and failed, because `freeze_02` names `--single-pass` in a comment
explaining why it does not pass it.


**The freeze moves again — to Colab, because phone verification is not available**

Finding Z′ is not a bug that can be fixed in code: a Kaggle notebook gets no network without phone
verification, and that is not available on this account. Four hosts were weighed — Kaggle with the
corpus uploaded (7.6 GB from a home connection, no resume, and 5.6 GB of free disk here means no
staging copy), a rented 32 GB box (~$2–8 against a $150 cap with $0 spent), local with resumability
plus band-partitioning built, and Colab. **Colab chosen.**

The trade is precise and worth stating, because it moves the binding constraint from an account
property to a physical one:

| | Kaggle | Colab |
|---|---|---|
| RAM | ~30 GB | **~12.7 GB** free CPU runtime |
| against Finding X's projection | ~9–10 GB | ~9–10 GB |
| when RAM runs out | — | **process killed**, no pagefile to absorb it |
| network in notebook | needs phone verification | yes |
| corpus | fetched once, mounted | **re-fetched each session** (~7.7 GB, no `--source` on `fetch`) |
| disk | ~30 GB | ~100 GB |

**So `colab/freeze_colab.py` is built around the memory gate rather than around the passes.** `env`
prints what the runtime reports rather than what a doc claims; `trial` projects hours *and* peak RSS
from a prefix and refuses when either exceeds **80% of measured available RAM**; and a pass will not
start without a passing trial on record. `--force` overrides deliberately, and nothing overrides it
by accident. `child_peak_gb()` raises off-Linux rather than returning 0.0, because a memory gate that
cannot measure memory must refuse instead of always opening.

**One design point that is the session's own lesson applied to itself.** The first draft had
`--sweep` on the real pass and not on the trial. That is the same class of error as everything above:
the projection authorising a ten-hour unresumable run would have been measured on a *different
computation*. Both argvs now come from one `build_argv()`, and a test asserts they differ in document
count and output paths and in nothing else.

**And the driver was actually exercised, which is the part that has been missing all along.** It
imports on Windows on purpose — `resource` and `/proc/meminfo` deferred to their call sites — so its
argument parsing and gate logic are testable here. Then the exact computational flags each Colab pass
will use were run against the real corpus at `--limit 2000`:

| | FineWeb2 (`--single-pass --sweep 0.7 0.8 0.9`) | Roman-Urdu-Parl (`--shingle-unit char`) |
|---|---|---|
| documents kept | 1,930 / 1,930 | **1,294 / 2,000** |
| clusters | 0 | **224**, largest 7 |
| candidate → verified → retained | 2 → 0 → 0 | 712 → 451 → 687 |
| sweep at 0.70 / 0.80 / 0.90 | 0 / 0 / 0 removed | — |

Nothing errored, `--sweep` composes with `--single-pass`, and the threshold sits above the retention
floor — all four things that would have killed a Colab session minutes after a 7.7 GB fetch.
Roman-Urdu-Parl's 35% removal at 2,000 rows is not a corpus number (it is one file's first rows) but
it is the first direct sighting of what PRD §6.2 warns about: ~6.37M machine-transliterated pairs
collapsing toward ~1.09M unique Urdu sentences. It is also why `--single-pass` stays off that source.

**Decisions made**

| Decision | Rationale |
|---|---|
| **Colab over Kaggle-with-upload, a rented box, or local** | Kaggle's blocker is an account property, not code. Uploading 7.6 GB has no resume and no disk here to stage it; a rented box costs money the project has not needed yet; local costs a week and 5.6 GB of free disk will not hold spilled sketches. Colab keeps the fetch working and moves the risk to memory, which is measurable — and `trial` measures it |
| The Colab gate refuses on **memory** as well as time | Kaggle's ~30 GB made time the only real question. At ~12.7 GB against a ~9–10 GB projection, memory is the question, and an OOM there kills the process rather than paging |
| One `build_argv()` for trial and pass | A flag in one and not the other means the projection did not measure the run it authorised. The first draft had exactly that, with `--sweep` |
| The Colab driver imports on Windows | `resource` and `/proc/meminfo` at their call sites instead of the top. Otherwise nothing here can import it, and it goes unvalidated until an hour into a session on another machine — which is precisely how the four bugs above survived |
| `slug` is the only kernel name; the title is derived from it | Kaggle honours the title and discards the slug in `id`. Deriving one from the other means both fields carry the same string, so which one the server prefers stops being a thing this repo can be wrong about |
| A mismatched or unreachable kernel ref **raises** after a push | The push succeeds either way. This is the only check that can catch a slug the server rewrote, and its absence is what hid a failed run for five weeks |
| The mount is *searched for*, not constructed | Kaggle's layout is theirs to change and it already differs from their own documentation. A marker file is a fact about our own repo; a path is a guess about their platform |
| The bootstrap is duplicated on purpose, and a test holds the copies together | It is the code that finds the uploaded project, so it cannot be imported from the uploaded project. Where sharing is impossible, the test is the sharing |
| `wait_for_dataset()` stays, though it was not the bug | A kernel pushed against an unprocessed dataset mounts nothing and fails *identically* to Finding Z. The race was a wrong diagnosis, not an impossible one, and 16 seconds is how close the first run came to it |
| The network check goes in the kernel, not the runbook | The runbook already said to verify the phone. A document cannot fail a run at second one with the fix in the message |
| A read-plan mismatch **raises**, rather than printing and continuing | It is the same decision `ExclusionSet` already makes one layer down (session 14), for the same reason: a list computed over a different read removes the wrong documents and nothing downstream can tell. Refusing costs a re-fetch; continuing costs a ten-hour pass and produces something that looks like a result |
| `diag_input.py` is committed rather than deleted | It converted five weeks of a wrong hypothesis into one measurement in under a minute, and the next unexplained mount is what it is for |

**Measured, and worth keeping**

| | |
|---|---|
| kernel 00 attempts | 3 — errored at 1.6 s (v1), 1.1 s (v2), 41 s (v3) |
| code dataset | 49 files, extracted, byte-exact against HEAD on three spot-checked files |
| diagnostic kernel | pushed → COMPLETE in under one minute |
| tests | **678 passing** (+28: `tests/test_kaggle_push.py` and `tests/test_colab_freeze.py`, the first tests covering this repo's boundary with the machines the freeze runs on) |
| read plans | three, measured; two corroborated against independent earlier records |
| spend | still **$0.00** — Kaggle CPU notebooks are free, and no paid instance has been touched |

**What is left on the Kaggle side, and it is one manual step**

Everything automatable is now automated and tested. The freeze is blocked on **phone verification**,
which is the account holder's to do and was always listed as irreducibly manual. After it:
`push.py push 00` → read the trial verdict → `push 01` → `push 02`. The `needs_corpus` precondition
now refuses 01 and 02 while 00 is not `COMPLETE`, so the gate cannot be skipped by accident.

**The lesson, which is Finding D's again in a new place**

Finding D said fixture tests prove a rule does what it says and only real text shows whether it does
it to the right documents. Finding X said a profile in a docstring describes the object, not the
process holding a million of them. This session says the same thing about a *platform*: three
failures, three assumptions, none of them taken from the system itself. The measurement that settled
Finding Z cost **one minute** and was available at any point in the preceding five weeks. The
project's own practice — probe before trusting a threshold — had never been applied to the
environment the pipeline runs in, only to the data it reads.

---

### Session 17 — 2026-09-10

**The Roman-Urdu-Parl freeze pass ran on Colab and answered the question G1 had been carrying
unmeasured since session 12: the corpus loses 82% of that population, and the loss is real.**

Complete pass, unsampled, 1.38 h, peak child RSS 5.60 GB against a 9.7 GB budget:

| | documents | characters |
|---|---|---|
| read (post stages 2-5 + PII) | 6,032,599 | 465,303,750 |
| after stage 6 (exact) | 3,478,770 | 258,876,832 (55.64%) |
| after stage 7 (near, 0.80) | 1,724,751 | **81,791,735 (17.58% end to end)** |

3,478,770 distinct reproduces session 8's Finding K' figure exactly, on a completely different code
path — the strongest cross-check the corpus work has had.

**Finding AA — the 82% is genuine near-duplication, not the chaining artifact the numbers implied.**
`largest_cluster` came back **10,757** against Wikipedia's 23, which `colab/README.md` names as the
signal that threshold 0.80 does not transfer. The aggregate evidence pointed the same way: 2,395,785
verified pairs over 3,478,770 documents is an average degree of 1.38, above the percolation
threshold where single-linkage produces a giant component whether or not any individual pair is
correct. **Both were wrong, and reading the text settled it in minutes.** Every one of the five
largest clusters is one Wikipedia geo-stub template:

```
cluster 0 (10,757)  lingdn knsas ka Raqba murabba kilomitr hai aur is ki majmoi abadi ...
                    Ali ganj    ka Raqba murabba kilomitr hai aur is ki majmoi abadi ...
cluster 1 (1,806)   Pakistan riloyz ki sarkari Website ke mutabiq <NAME> railway station ka code hai
```

The decisive detail is that **the source has the numbers stripped** — "rqba murabba kilomitr hai"
is "area is __ square kilometres", with no figure. So these sentences differ in a proper noun and
nothing else, and collapsing them is exactly what stage 7 is for.

**Finding AB — 0.80 is if anything too conservative here, so no threshold move recovers budget.**
Read across the cut, the pairs *below* it are still duplicates:

| band | verdict | example |
|---|---|---|
| 0.75-0.80 | **kept** | `baah shehar ki majmoi abadi ... sataa darya` / `... Majmui abadi ... satah darya` |
| 0.80-0.85 | deleted | `sooch ka nagar pathar` / `soch ka nagar pathar` |
| 0.85-0.90 | deleted | `bohot mubarakbaad` / `bohat mubarakbaad` |

These are the crowdsourced spelling variants §6.2 warns the corpus was built from. Raising the
threshold retains more of them; it does not recover unique text. **The sweep re-run was therefore
not needed** — the question it would have answered is answered by 24 sentences.

**Consequence for G1, and it is conversion-independent.** The margin scales by the retention factor
regardless of what chars-per-token turns out to be:

| | session 12 margin | x 0.1758 | verdict |
|---|---|---|---|
| roman_urdu vs **arm B** + held-out | 2.48x | **0.44x** | **cannot be assembled** |
| roman_urdu vs **arm A** + held-out | ~8.7x | **~1.53x** | fundable, thin, and **before stage 8** |

`urdu` (46.66x) and `code_switched` (2.35x) are unaffected: the FineWeb2 trial measured that
source's self-similarity at 9 clusters in 193,666 documents, largest 2, and 0 removed at 0.90.

**Arm B is not dead, it moves.** `scripts/crossover.py` puts the predicted crossover at **U = 33M**
for this compute. Arm A at 25M sits below it and is predicted to cross; the largest arm B the
corpus can now build is **U ~= 40M** (9.58M roman tokens after a fixed ~1.20M held-out, at the
23.53% mixture share), which sits *above* 33M and is predicted not to. The bracket survives at 25M
vs 40M around a 33M pivot — narrower than 25 vs 100 around the same pivot, and still a bracket.
**This is a decision for the PRD, not for a session log**, and the alternative is G1's written
fallback of a single-arm report.

**Finding AC — the sweep is not recoverable after the fact, and the run carried no `--sweep`.**
`sweep()` re-clusters from the retained pairs held in the index; `--pairs-out` writes only banded
examples. The 5.3M retained pairs died with the process. It happened to cost nothing because the
text answered the question, but the flag is free and is now in both passes with a test asserting
its floor against `retain_pairs_above`.

**Also this session:** `--safe-hours` on the trial, so a rented box with no session cap can relax
the clock without `--force` waiving the memory verdict along with it. The FineWeb2 trial refused on
both counts at once (11.69 h > 9.0; 12.7 GB > 9.7), and memory is the projection Finding X already
got wrong by 2x.

**The lesson.** Two independent quantitative signals — a 10,757 component and an average degree
above percolation — both said "artifact", and both were wrong. The corpus was on this machine the
whole time and reading twenty-four sentences from it settled what neither statistic could. Session
16's lesson was that the platform had never been probed the way the data had; this one is narrower
and older: **an aggregate can only ever say where to look.**

---

## Open questions for you

1. ~~**Config format.**~~ **Decided in session 4: JSON, for the whole data pipeline.** Three
   configs now exist (`normalization.json`, `encoding.json`, `sources.json`), all stdlib-parsed
   and all fingerprinted into the manifest. Revisit only if training configs get unwieldy in
   Week 6 — a YAML training config alongside JSON data configs is a fine outcome, and by then
   nothing in the pipeline has to change to get it.
2. **Compute account.** PRD §9 wants a provider spending limit set on day one and **Kaggle used for
   all validation**. Session 16 answers half of this and complicates the other half.
   - **Kaggle account: exists** (`awaisbinadil`), CLI authenticated by OAuth, and
     `kaggle/push.py` drives it end to end.
   - **But its notebooks get no internet**, because phone verification is not available on the
     account (Finding Z′). That does **not** rule Kaggle out for §9's validation role — a validation
     run needs no network if its inputs are uploaded as datasets, and the Week 8 pilots read packed
     shards measured in hundreds of MB rather than the freeze's 7.7 GB. It does mean **no Kaggle job
     can ever fetch anything**, so every input has to be uploaded from here or produced there.
     Worth knowing before Week 6 plans around it.
   - **Still open: the spot-GPU provider** (Vast/RunPod/Lambda) for the paid runs. Nothing blocks
     until Week 6, but the $150 cap wants the spending limit set early — and a ~$2–8 CPU box is now
     also the standing fallback for any pass too large for a free tier.
3. **Annotators.** §8.4 needs 3 fluent Urdu speakers for ~2 hours each in Week 13, and §8.2 needs
   ~200 hand-written transliteration pairs. Both are favour-sized asks that take weeks of lead
   time. Worth lining up people now, not in Week 12.
4. **Hardware here.** Is there a local GPU on this machine for the tiny pilots, or is everything
   going to Kaggle? Changes how the Week 6–7 throughput work gets set up. Two measurements from
   session 16 bear on it: **free disk is 5.6 GB**, down from 29 GB in session 14, and **free RAM is
   ~2 GB of 16 GB** — so this machine can no longer stage a large intermediate, and Colab's ~100 GB
   of scratch disk is now the project's largest spare resource. If the answer is "no local GPU",
   Colab is the pilot host too, and its ~12.7 GB is the number Week 6's throughput work has to fit.

---

## Deferred / parked

- **Offset mapping through normalization.** Not built. The OCR-restoration and spacing-repair
  tasks (§4.2) may need to align normalized text back to original character offsets to build gold
  pairs. Revisit when building the corruption generators in Week 6 — if it is needed, it is much
  easier to add to the normalizer than to reconstruct downstream.
- **Parallelizing normalization.** Single-threaded is fast enough for one pass over 1.5 GB.
- ~~**CI workflow.**~~ Added session 4 — `.github/workflows/tests.yml`, ruff + pytest on 3.11 and
  3.13. PRD §14 makes "all §8.1 invariants passing in CI" a ship criterion, so it stopped being
  optional once the suite covered three pipeline stages. Two Python versions because Urdu
  handling depends on Unicode data, which moves between releases. **Untested — there is no
  GitHub remote yet**; it will run on the first push.
- **Parquet shards are not resumable across a schema change.** `fetch_file` resumes a partial
  download via HTTP Range and re-hashes the prefix, but a `.part` from a *different* pinned
  revision is only caught by the final digest check, which means re-downloading. Acceptable:
  revisions change rarely and the failure is loud.

---

## Next session

**⚠️ START HERE: `colab/README.md`. The freeze runs on Colab now, and the next step is a
session at a keyboard rather than any more code.**

Phone verification is not available, so the Kaggle path is closed for good — its notebooks get no
network without it. Colab has internet. The driver, the gate and the runbook are built and tested;
what remains is running it, and the one thing that cannot be automated is that a Colab session needs
someone to keep the tab open.

Paste the cells from `colab/README.md` in order. `ravaan-code.zip` is already rebuilt with `colab/`
in it (234 KB, 62 entries):

```python
!python colab/freeze_colab.py env       # what this runtime actually has
!python colab/freeze_colab.py fetch     # ~7.7 GB, verified, read plans checked
!python colab/freeze_colab.py trial     # THE GATE — read the verdict
!python colab/freeze_colab.py fineweb2 --drive /content/drive/MyDrive/ravaan
!python colab/freeze_colab.py roman    --drive /content/drive/MyDrive/ravaan
```

**The verdict to expect, and what to do with it.** Finding X projects ~9–10 GB against a free
runtime's ~12.7 GB, so `fits_memory` is genuinely uncertain — the gate exists because the honest
answer is "measure it". If it refuses, the order is: make `neardedup.py` resumable, then
band-partition to disk (Colab has ~100 GB spare and this machine has 5.6 GB), then rent a 32 GB box
for ~$2–8. **Sampling is never an option** — Finding G.

**Two things that are true regardless of the verdict:**

- **`--drive` is not optional in practice.** A disconnected Colab session takes `/content` with it,
  and the pass is unresumable.
- **Watch `largest_cluster`.** Nothing caps a component's size; the only evidence 0.80 does not chain
  is Wikipedia's 23.

**The Kaggle runbook remains accurate for everything after the corpus arrives** — only the host
changed, and stages 9, 8 and 10 were always local:

Session 14 found the freeze order was not executable (Finding W) and built the missing piece —
`--exclude` now carries stages 6/7/8's removals into stages 9 and 10 and refuses a list computed
over a different read. **Urdu Wikipedia is frozen through stage 7.** Then Finding X: stage 7's index
costs ~2,010 bytes per document, not the ~980 the module documents, so FineWeb2 needs **~9–10 GB
against this machine's 0.9 GB free.** It will page, not fail, and take about a week. Kaggle's CPU
notebooks give ~30 GB, free.

**A local FineWeb2 pass was left running at session end** — pid was 31548, 19% read after 20.7
hours, ~1.71 GB resident. It is the same job the Kaggle runbook does properly. **Kill it**
(`Stop-Process -Id <pid>`); nothing depends on it and it is holding memory. Its log is
`logs/freeze_67_fineweb2.log` and its partial outputs are not written until the pass completes, so
there is nothing to salvage.

Three things to carry in.

- **The G1 margins have not been through stages 6/7/8.** Code-switched sits at 2.35×, which survives
  a 50% stage-7 loss — but FineWeb2's self-similarity has never been measured, and that is exactly
  what the blocked pass exists to measure.
- **The fertility estimate moves arm A's document set by a factor of two**, so Week 5's re-solve has
  to land before the corpus is *written*. It does not block stages 6/7/9/8.
- **`neardedup.py` is not resumable**, and on a 12-hour session cap that is now load-bearing. If the
  Kaggle trial says FineWeb2 needs more than ~10 hours, **build resumability before running it** —
  the shard reader already checkpoints with a plan fingerprint, so what is missing is serializing
  `MinHashDeduplicator`'s parallel arrays and `ExactDeduplicator._best`. Bounded work, and worth
  having regardless: today a pass that dies at 80% restarts from zero.

**The freeze order, and what each step now needs:**

```
6+7  neardedup.py --source S --limit 0 --removals reports/freeze/removals_67_S.txt
9    split.py --source ALL --limit 0 --measure-only --exclude <each 6+7 list> --plan-out plan.json
                                                     --heldout-out data/freeze/heldout.jsonl
8    decontaminate.py --source ALL --limit 0 --exclude <each 6+7 list> --removals removals_8.txt
10   pack.py --source ALL --limit 0 --plan-in plan_resolved.json
                           --exclude <each 6+7 list> --exclude removals_8.txt --out data/packed
```

1. **Stage 6+7, per source, unsampled.** Finding G forbids sampling either — a pair statistic
   sampled at rate *r* is measured at *r²*. **Wikipedia is done** —
   `reports/freeze/removals_67_wikipedia.txt`, 188 ids, 118 clusters, reproducing sessions 8 and 9
   exactly. The two long ones remain:
   ```
   python scripts/neardedup.py --source fineweb2-urd_Arab --limit 0 --single-pass \
       --removals reports/freeze/removals_67_fineweb2.txt --json reports/freeze/neardedup_fineweb2.json
   python scripts/neardedup.py --source roman-urdu-parl --split train --limit 0 --shingle-unit char \
       --removals reports/freeze/removals_67_roman.txt --json reports/freeze/neardedup_roman.json
   ```
   - **`--single-pass` on FineWeb2, not on Roman-Urdu-Parl.** It halves the read, and its cost is
     peak memory proportional to the exact-duplicate rate — nil on FineWeb2 (Finding H), ~2× on
     Roman-Urdu-Parl's collapsing rows, which this machine has no headroom for.
   - **Close the browser and the editor before the FineWeb2 run.** Projected from Wikipedia's
     measured ratios (0.645 candidate pairs and 0.139 retained pairs per document) at 5.26M
     documents: sketches and ids **3.68 GB**, stage 6's index **1.47 GB**, the `seen_pairs` set
     **0.24 GB**, retained-pair arrays 0.01 GB — **~5.4 GB**, against ~2 GB free on a 16 GB machine
     whose pagefile is on `D:`. Neither `max_candidate_pairs` (20M) nor `max_retained_pairs` (40M)
     is close at the projected 3.4M and 0.7M, so the ceilings will not fire first — memory will.
     FineWeb2 should sit *below* Wikipedia's pair ratios, since Finding H says 31% was already
     MinHash-removed upstream; if it comes out above them, that is the number to report.
   - **Watch `largest_cluster` on both.** Nothing caps a component's size; the reason to believe it
     stays small at 0.80 is a measurement on Wikipedia (23 here), and a source with heavier
     templating can chain.

2. **Stage 9, one unsampled phase 1 over all sources together.** The passes so far are per source,
   so each set of bands is calibrated to that source's totals rather than to the corpus — which
   gives each source its own held-out share instead of the corpus's. Measure once over everything,
   then apply that one plan everywhere with `--plan-in`.
   - **`--measure-only` is the flag for it** (session 12) — one pass, not two. The both-shard 5%
     run took ~35 minutes that way; unsampled over 8.3 GB is the freeze's longest single read.
   - **Stage 9 must come after 7.** Stage 9 ran *before* dedup in every pass so far, so the
     held-out split can still contain near-duplicates of training documents from within Wikipedia —
     the geo-stub farms session 9 measured at 10.7% of the dump. Stage 8 catches the cross-source
     case and structurally cannot catch that one. **The held-out split's integrity depends on stage
     7 having run first**, and now depends on `--exclude` actually being passed.

3. ~~Take the single-pass halving.~~ **Done in session 14** — `--single-pass`, 12 tests, equivalence
   asserted across eleven counters. Use it as shown in step 1.

4. **Then stage 8, then stage 10.** Both take the same `--exclude` lists; stage 8 additionally
   indexes the held-out split stage 9 writes, so it runs after stage 9 even though its removals feed
   stage 10. The eval sets now go through PII redaction on both sides automatically (session 14) —
   nothing to remember there.

5. **Week 5 blocks the corpus write, not the measurement.** `pack.py --measure-only
   --resolve-plan` needs §7's tokenizer, and the arm cuts move by a factor of two across the
   plausible fertility range. Stages 6/7/9/8 can all complete before it; only step 4's `pack.py`
   run that *writes* has to wait.

2. **Week 5, and it is stage 10's outstanding half.** Train §7's tokenizer, then:
   ```
   python scripts/pack.py --source … --measure-only --tokenizer <model> --resolve-plan <plan.json>
   ravaan-splits <plan.json> --chars-per-token urdu=… roman_urdu=… code_switched=…
   ```
   `orature/ALIF-Base-100M` (Apache-2.0, 32k Urdu SentencePiece, found in session 4) is a free
   external fertility bracket to sanity-check the result against — deliberately *not* run in
   session 12, because measuring with a 32k model and quoting it for a 16k one is the same class of
   error as quoting the placeholder's 0.573.

3. **Deferred to freeze time, unchanged from session 10:**
   - **Stage 8 over FineWeb2's complete shard**, both for the Roman-Urdu-Parl eval sets and for the
     held-out split. The held-out number here (15 of 6,748 = 0.22%) is at a 5% sample and projects
     to **~4.4%**; that is the figure §8.2 needs and it should be measured, not projected.
   - **Stage 7: FineWeb2 self-similarity (complete shard) and Roman-Urdu-Parl with
     `shingle_unit="char"`.** ~2.3 hours two-pass. Finding G forbids sampling either.
   - ~~Redact the eval sets before stage 8 runs.~~ **Done in session 14**, unconditionally in
     both loaders, and measured: one-sided redaction moves stage 8 from `removed` to `kept`.

**Still not taken, and now sequenced — see item 3 above and session 14's entry for the settled
design.** The driver reads the
corpus twice because stage 6 is two-phase, and stages 2–5 are 90% of that cost (profiled: stage 5
53%, stage 3 27%, stage 4 9%). But stage 6 knows its survivors at the end of *phase 1* — that is
what `--index-only` already claims — so a driver that sketched during phase 1 and applied stage 6's
verdict from the index would need one pass, not two. Worth taking before the FineWeb2 and
Roman-Urdu-Parl passes above, which is where it pays for itself. **Stage 9 does not need it** —
its phase 2 can be skipped entirely by carrying the plan.

**Correction to the sentence this note used to end on**, which said the work "needs a small public
accessor on `ExactDeduplicator` to avoid reaching into `_best`". `is_kept()` is already that
accessor and it is not enough: it takes the *text*, and a single-pass driver has thrown the text
away by the time stage 6 has sealed. The text-free form is a key-membership test —
`document_key(doc_id) in {winning keys}`, which is sound because a winning key belongs to exactly
one document and that document is its own group's winner. **The harder half is on the other side:**
`MinHashDeduplicator` has no way to un-index a document, and the removals have to leave its
`_eligible` list, its six log counters and `_cluster`'s final accounting loop. That is where the
work actually is.

**Do not start** tokenizer training or modelling. The tokenizer is timeboxed to Week 5, and stage
10 is deliberately built so that waiting costs one command rather than a rewrite.

**A note on running long passes here.** Tracked background jobs in this environment were killed
three times at somewhere under 14 minutes, and foreground calls cap at 10 minutes. What works is
`nohup … &` as a detached process; sessions 9, 10 and 11 all confirm it. Session 11 adds a
measurement to session 10's contention correction: **two** concurrent passes over the *same* 2 GB
parquet file (a stage-9 two-phase run and a stage-8 run, both on FineWeb2 at 5%) took ~50 minutes
where either alone is ~20. Parallel passes are free in cores and are not free when they contend on
one file. Complete-Wikipedia stage 9 is ~20 minutes two-phase, alone.

**Carried forward**

- ~~**⚠️ The PRD has not been amended for Finding R.**~~ **Done in session 12 — PRD v2.2.** §0.2
  carries the changelog, §6.1 separates pool targets from arm budgets and states the mixture, §4.3
  says what U counts, and §8.2/§10/§11 pick up the consequences.
- ~~**⚠️ Gate G1 reads `ARM_A_ONLY`, not `PASS` (Finding U).**~~ **Resolved in session 12 by the
  shard 000 fetch, and measured rather than projected.** Phase 1 over both FineWeb2 train shards at
  5% gives `code_switched` **14.52M against 6.18M = 2.35×**, and G1 now returns
  **`PASS` on both the aggregate and the mixture, with both arms fundable.** Every population sits
  above 2×: urdu 46.66×, roman_urdu 2.48×, code_switched 2.35×.
  **Still to close at the freeze:** this is a 5% sample and stages 6/7/8 have not run on it.
  FineWeb2's exact-duplicate rate is nil (Finding H) but its *self-similarity* has never been
  measured, so the margin has to survive stage 7. At 2.35× it survives a 50% loss; at 0.92× it
  would not have, which is what the fetch actually bought.
- **The PII pass's precision is adjudicated from context and shape, not by a native speaker.**
  Finding V's ISBN family was unmistakable and the correction is measured, but one Wikipedia match
  remains ambiguous: an eleven-digit unseparated run sitting next to an author's name, exactly
  where an ISBN would also sit. It is one line for the same native-speaker sitting that owes stage
  5 its 29 disagreements and stage 7 its sampled pairs. **The recall side is the one that matters
  more and it is stated rather than fixed** — Indian mobile formats (ten digits, no trunk prefix),
  dot-separated numbers and `[at]` obfuscation are all measured in the FineWeb2 sample and all
  uncaught, because catching bare ten-digit runs is precisely what Finding V removed.
  `reports/pii.md` §6 is the list, and the report must carry it.
- ~~**⚠️ Three installed console scripts still have the cp1252 hole.**~~ **Closed in session 14, as
  a class rather than as three instances.** The diagnosis named `ravaan-splits`, `ravaan-shards` and
  `ravaan-normalize` and prescribed a copy-paste; there are **twelve** console entry points and two
  of them had the guard. `ravaan/console.py` holds it now and all twelve call it. Fifth Windows text
  default in this repo, and the note it replaces is the reason to fix the class: a prescription that
  names three of twelve members is the same bug returning in session 17.
- **⚠️ ~4.4% of the held-out split is likely inside FineWeb2 (Finding T), and the measured figure is
  0.22% at a 5% sample.** The projection assumes an eval item with one crawled copy is found with
  probability *r*. §8.2's held-out native set is the primary endpoint's own instrument, so the
  freeze must run this pass **complete**, not sampled, and the report must state the number.
- **Stage 8's line-level half now has a measured false-positive family of its own.** Session 10's
  was bylines-with-a-different-year on the Roman-Urdu-Parl path; session 11's is **shared
  quotations** — a ghazal line at exactly the 40-character floor, and a biographical genre formula.
  Precision 0.87 on this path against 0.73 on that one. Both are left in deliberately, and both
  belong in the report as stated precision rather than implied correctness. If the floor is ever
  revisited, the discriminator is whether the shared line is *quoted* material, which is closer to
  stage 3's lowercase-running-text test than to a length.
- **⚠️ `scripts/` has ~2,900 lines and almost no test coverage, and Finding W lived there.** Every
  stage's *library* is tested to the point of pinning literal hash values; the six drivers that
  compose them into a pipeline had nothing, which is exactly why "stages 9 and 10 cannot read a
  removal list" survived thirteen sessions of careful work on the stages themselves. Session 14
  adds the first two driver tests. The properties still uncovered and worth having are the ones
  where a driver *composes* stages rather than calls one: that `neardedup.py` writes stage 6's
  removals as well as stage 7's (found by hand this session), that `decontaminate.py`'s removals
  are row ids rather than column variants (same), and that every driver's `Pipeline` applies stage
  4 before stage 5 before PII before whatever it owns. **The lesson is not "write more tests" but
  the specific one Finding W is an instance of: the stage boundaries are where this project's bugs
  live, and nothing was looking at them.**
- **⚠️⚠️ 16.8% of the reference transliteration split's Urdu side is in Urdu Wikipedia (Finding Q),
  and Wikipedia is a training source.** §4.5 makes transliteration chrF a Holm-corrected secondary
  endpoint. Stage 8 removes the contaminated *training* documents, which is the correct action and
  does **not** repair the metric: the test items remain compromised for any model trained on a
  corpus assembled before this ran. Two things follow. (a) The freeze must run stage 8 against these
  eval sets — it is no longer optional hygiene. (b) The report must state the 16.8% and say the
  reference-set transliteration number is weaker evidence than the human-written set of §8.2, which
  is now carrying more weight than originally planned.
- **⚠️ The reference transliteration split contains internal near-duplicates, and that is an
  instrument defect independent of contamination.** Nine test rows (`test_set.csv:1:606`–`1:614`)
  are spelling variants of one sentence with an *identical* Urdu column. Any chrF computed on that
  split weights that sentence nine times. §4.5 makes transliteration chrF a Holm-corrected
  secondary endpoint, so this belongs in the results section next to the number, and it is an
  independent argument for §8.2's human-written set. **Not yet measured at the whole-split level** —
  the obvious check is stage 7 pointed at the test split alone, which is one cheap pass.
- **Stage 8's precision is 0.73 and its three errors are one named family.** Every false positive
  in the adjudicated 11 was a byline whose year differs (`Sayeda shagufata , May 17 , 2007` against
  `... 2009`). Left in deliberately — a false positive costs one training row out of millions, a
  false negative costs the validity of an evaluation number — but the report must state the
  precision rather than imply the removals are all genuine. If it is ever worth fixing, the fix is
  a byline rule in stage 5, not a threshold here.
- **Two of §8.2's five test sets do not exist yet** — the ~200 human-written transliteration pairs
  and the ~300 real-OCR lines. Both are sentence/line unit, so `EvalSetSpec.for_sentences()` is the
  variant they inherit, and **neither has been through stage 8**. The held-out native split is the
  third, and it is blocked on stage 9.
- **The 200-sample validation was adjudicated by Claude, not by a native speaker.** This is the
  one place the deliverable does not yet match what §6.3.5 implies. The judgements are real work
  and they found four wrong thresholds, but "200 manually inspected samples" in a report should
  mean a fluent Urdu speaker, and the sheet is built to be marked up by one:
  `reports/quality_sample.md` has a `**verdict:**` line per document and
  `scripts/quality_sample.py score --quality-config …` replays any marking against any config
  without re-reading the corpus. **The highest-value thing a native speaker could do is re-mark
  the 29 disagreements** listed in `reports/quality_validation.json`, which is maybe twenty
  minutes of work rather than a full pass. Until then the technical report must describe the
  validation as machine-adjudicated, and say so in those words.
- **`script_ratio` is the weak rule and its weakness is now measured, not suspected.** Precision
  0.50 at the shipped threshold, and session 7's sweep shows **no threshold anywhere in the usable
  range beats 0.56** while the affected document count moves 16×. If a native-speaker pass confirms
  it, the honest options are to drop the rule entirely (stage 3 already made the language decision
  on better evidence) or to replace Latin *share* with something that actually separates the cases
  — the discriminator in the sample was whether the Latin was quoted material or the page's own
  content, which is closer to stage 3's lowercase-running-text test than to a ratio. Tuning the
  number is not an option. Decide before the freeze.
- **The duplicate-n-gram rules are near-inert and it is on the record.** 4 documents in 19,999 on
  Wikipedia, 0 on FineWeb2, 0 on the 200-sample beyond what the top-n-gram rules already catch.
  Keep them as a backstop with that stated, or drop them — but they must not be described as the
  corpus's repetition control. **Session 8 answers the comparison this was waiting on, and the
  answer is a wording change rather than a code change.** Cross-document *exact* repetition on the
  two native sources is essentially nil after stage 5 (9 groups in the whole Urdu Wikipedia dump;
  FineWeb2 zero) — but only because it was already dealt with: FineWeb2 removed 31.02% of
  `urd_Arab` by MinHash upstream (Finding H). So the honest sentence for the report is not "this
  corpus has little cross-document repetition", it is "**this corpus had a great deal of it and
  FineWeb2 removed it before we saw the data**", which is a statement about the source rather than
  about Urdu. The within-document rules stay as a backstop, described as one.
- **Wiki markup is not HTML.** `{{Infobox}}` template dumps clear `max_html_ratio` at any usable
  threshold — the rule counts HTML tags, and lowering it to catch them costs ~8 clean biographies
  per 2 stubs. The fix belongs in Wikipedia-specific preprocessing ahead of stage 5, not in the
  threshold. Two of the shipped filter's four false accepts would remain regardless; the other two
  were booked as "the stub farm, which is stage 7's" — **and session 8's Finding I retired that
  booking, which session 9 has now confirmed against the shipped stage 7.** Run at threshold 0.50
  with high-recall banding, all four come back `kept=True, cluster_size=1`; the highest pairwise
  similarity among them is J = 0.258 and four of the six pairs measure 0.000. All four are residue
  that survives the whole pipeline. `reports/quality_validation.md`'s error budget needs the
  sentence corrected the next time it is touched: stage 5's false-accept rate is the filter's, not
  a debt owed to a later stage.
- **Stage 7's threshold is validated against clusters and pairs, not against read documents.** The
  0.80 decision rests on the largest-cluster collapse (9,979 documents in one component at 0.30
  against 23 at 0.80) and on 168 sampled pairs carrying their measured similarity — a stronger
  footing than stage 5 had before its 200-sample, but not a fluent speaker saying "yes, these two
  are the same document". `reports/minhash_pairs_*.jsonl` is built to be read that way, and the
  same native-speaker sitting that owes stage 5 its 29 disagreements could settle this too.
- **Chaining is bounded by measurement, not by design.** Nothing in stage 7 caps a component's
  size; the threshold table is the reason to believe it stays small at 0.80 on Wikipedia. A source
  with heavier templating could behave differently, so `largest_cluster` is the number to watch
  when FineWeb2 and Roman-Urdu-Parl are run. Capping it would be a second threshold nobody swept.
- **Paragraph-level dedup is implemented, measured, and deliberately off.** §6.3.6 asks for
  document *and* paragraph level; stage 6 counts the second and rewrites nothing, because dropping
  a line out of a document is a rewrite that invalidates the 400-character floor stage 5 applied
  one stage earlier. The number that justifies leaving it off is **0.89%** of line characters on
  Urdu Wikipedia (1.34% on a FineWeb2 window). `ExactDeduplicator.strip()` will do it, in a third
  pass, and a caller that uses it owes the corpus a second stage-5 pass. Revisit only if stage 7
  shows the boilerplate matters; the report should state the number and the choice either way.
- **The infilling share is unresolved.** PRD §4.2 sets 10%; reported FIM practice is 50–90% with no
  left-to-right degradation (review §6). If 10% leaves Ravaan-AR genuinely bad at infilling, A2
  loses its meaning — the *fair* baseline would also be undertrained, and §4.1's whole fairness
  argument weakens. **Decide before the task mixture is frozen ahead of Stage C.** This is the last
  substantive open design question.
- **Hyperparameter provenance.** Preregistration §6 commits to taking the reference paper's config
  untuned, and to stating that it likely favours AR. Record the source when the training config is
  written in Week 6 — not retroactively.
- **Test the stages against a noisy source before trusting their thresholds.** Finding D is the
  general lesson, not a one-off: 57 unit tests passed on a detector that would have deleted 3% of a
  clean corpus. Fixture tests prove a rule does what it says; only real text shows whether it fires
  on the right things. Every threshold in stages 2, 3 and 5 gets a probe run before the freeze.
  Session 5 did this for stage 3 and it caught two population-level mislabels; session 6 did it for
  stage 5 and the distribution pass alone moved three thresholds before a human saw a document. The
  practice is load-bearing, and session 6 adds a corollary: **the distribution tells you where the
  documents are, not which of them are good.** Every stage-5 threshold that survived the
  distribution still had to be moved by the sample. Session 8 adds a second corollary, from Finding
  G: **check that the instrument you are sampling with can measure the quantity you are asking
  for.** Every earlier stage measures a property of one document, which a sample estimates
  honestly; stage 6 measures a property of a *pair*, which a sample at rate *r* estimates at *r²*.
  The habit that had been right five stages running was silently wrong on the sixth, and it was
  caught by an implausible answer (zero duplicates) rather than by an error.
- ~~**`scripts/corpus_probe.py` is redundant with `scripts/stage3_probe.py`.**~~ **Resolved in
  session 6** — both deleted, replaced by `scripts/probe.py` covering stages 2→5. The consolidation
  is verified by reproducing Finding F's numbers exactly.
- ~~**The normalizer is validated on Wikipedia only.**~~ **Resolved in session 6** — the 200-sample
  set went through stage 4, 14.6% of FineWeb2 documents changed (against 13.7% over 20,000 in
  session 4), the Urdu-specific rules are the ones that fire, and no rule misfired on any of the
  200.
- ~~**⚠️ The code-switched budget is short.**~~ **Settled in session 12: 2.35×, measured.** The
  quantity moved four times and three of the moves were corrections to the *requirement* rather
  than new data — which is the honest summary of how much of this was arithmetic:

  | | available | required | |
  |---|---|---|---|
  | Session 10, against §6.1's ~10M figure | 7.00M | 10.00M | 0.70× |
  | Session 11, after Finding R corrected what U counts | 5.70M | 5.88M | 0.97× |
  | Session 12, after Finding U counted the held-out sets | 5.70M | 6.18M | 0.92× |
  | **Session 12, measured over both FineWeb2 shards** | **14.52M** | 6.18M | **2.35×** |

  Shard 000 beat its projection (~10.3M) for a reason the projection had wrong: it is **2.4× the
  size** of shard 001, not equal to it, and contributes 33.4M code-switched characters against
  17.4M — a factor of 1.92, marginally *less* dense than shard 001 while being far more material.
  A better answer than projected, from a projection that was wrong. Original note follows.
  The original worry measured this population against §6.1's ~10M-token figure and projected ~7M
  available. **Finding R establishes that 10M is a *pool* target and arm B's actual requirement is
  5.88M**, and session 11's two stage-9 passes measure the supply directly rather than by
  extrapolating a letter share: Wikipedia 4.4M characters (complete dump) + FineWeb2 17.4M
  (5% sample ×20) = 21.8M characters ≈ **5.7M tokens against 5.88M needed — 0.97×**.
  **Option (a) is now the recommendation rather than one of three**: fetch FineWeb2 train shard 000,
  which roughly doubles the FineWeb2 share at ~$0 and ~25 minutes and takes the population to
  ~10.3M. (b) "accept a smaller share and say so" costs a stated corpus-composition change and (c)
  "add a social-media source" costs a new licence-gate decision; neither is warranted for a 3% gap.
  **Do it before the freeze.** This is still the one population where more data is genuinely
  scarce — Finding B's "Urdu is not data-constrained" holds for *native* Urdu.
- ~~**Roman Urdu's 40M-token target is unverified after dedup.**~~ **Settled in session 8, and the
  worry was unfounded** — see Finding K′. The estimate that raised it applied the *Urdu*-column
  unique count to the *Roman* population and assumed 45 characters a sentence; measured, the Roman
  column has **3,478,770** distinct sentences averaging **74.2** characters ≈ 258M characters ≈
  52–63M tokens, comfortably over §6.1's ~40M. §6.1's Roman Urdu figure does **not** need the
  treatment the native figure got in v2.1. One number is still an estimate: the exact post-dedup
  character count needs a two-phase run rather than `--index-only`. Worth taking at freeze time,
  when it is a byproduct of the pass that writes the corpus anyway.

**Retry when convenient:** OpenReview `W5Ht05jF4c` — still behind the browser-verification wall as
of 2026-08-03 (both API v1 and v2 return `ChallengeRequiredError`). Lower stakes now that both arms
sit inside the fitted range.
