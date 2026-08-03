# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read the "Next session" section at the bottom
first.**

- **Started:** 2026-08-03 (Week 1 of 16)
- **Current phase:** Weeks 1–2 complete → Weeks 3–4, corpus freeze. Pipeline stages 1, 2, 3 and 4
  are built and validated on real text; next is stage 5 (quality filtering) and its 200-sample
  manual validation.
- **Gate G0:** ✅ **PASSED** 2026-08-03 — comparison confirmed unpublished. See
  [`reports/literature_review.md`](reports/literature_review.md).
- **Design decision:** ✅ **Option 2 (two-point law) chosen** 2026-08-03. U ∈ {25M, 100M}; 3 seeds
  at 25M, 1 at 100M. PRD amended to v2.1; preregistration committed.
- **Preregistration:** ✅ committed [`reports/preregistration.md`](reports/preregistration.md) —
  4 falsifiable predictions, before any training.
- **Spend to date:** $0.00 of $150 hard cap
- **Tests:** 233 passing (69 normalization · 57 encoding · 57 acquisition · 32 langid · 18 shards)

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
| Quality filtering (stage 5) + 200-sample manual validation | §6.3.5 | ⬜ |
| Exact dedup (stage 6) | §6.3.6 | ⬜ |
| MinHash near-dedup (stage 7) | §6.3.7 | ⬜ |
| Eval decontamination (stage 8) | §6.3.8 | ⬜ |
| Split creation (stage 9) | §6.3.9 | ⬜ |
| Tokenization + packing (stage 10) | §6.3.10 | ⬜ |
| PII regex pass (phones, emails) | §6.3 | ⬜ |
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

## Open questions for you

1. ~~**Config format.**~~ **Decided in session 4: JSON, for the whole data pipeline.** Three
   configs now exist (`normalization.json`, `encoding.json`, `sources.json`), all stdlib-parsed
   and all fingerprinted into the manifest. Revisit only if training configs get unwieldy in
   Week 6 — a YAML training config alongside JSON data configs is a fine outcome, and by then
   nothing in the pipeline has to change to get it.
2. **Compute account.** PRD §9 wants a provider spending limit set on day one and Kaggle used for
   all validation. Do you already have a Kaggle account and a spot-GPU provider (Vast/RunPod/
   Lambda) in mind? Nothing blocks until Week 6, but the $150 cap wants the limit set early.
3. **Annotators.** §8.4 needs 3 fluent Urdu speakers for ~2 hours each in Week 13, and §8.2 needs
   ~200 hand-written transliteration pairs. Both are favour-sized asks that take weeks of lead
   time. Worth lining up people now, not in Week 12.
4. **Hardware here.** Is there a local GPU on this machine for the tiny pilots, or is everything
   going to Kaggle? Changes how the Week 6–7 throughput work gets set up.

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

**Primary task: quality filtering, pipeline stage 5 (PRD §6.3.5) — with its 200-sample manual
validation.**

Stages 1, 2, 3 and 4 all exist now and all four have been pointed at real text. Stage 5 is the
next gate, and it is the one the PRD explicitly requires human validation for.

1. **`ravaan/data/quality.py`** — Urdu-script ratio, repetition, URL density, HTML residue,
   replacement-character frequency, per §6.3.5. Stage 3 already computes script ratios, so the
   Urdu-script rule should read them rather than recompute; the rest is new.
2. **The 200-sample manual validation is the deliverable, not the code.** §6.3.5 requires the
   rules to be validated against 200 manually inspected random samples. Draw them with
   `ShardReader(sample_rate=...)` so the sample is reproducible from a seed, and write them out
   in a form a person can actually read and mark up.
3. **Put the same 200 through the normalizer** — this closes session 4's carried-forward caveat
   that stage 4 has only been validated on Wikipedia, and it costs nothing extra once the sample
   exists.
4. **Then stage 6 (exact dedup).** It is cheap, and Finding F says it will be interesting:
   religious publishers republish the same texts across domains, so normalizing before hashing
   should surface cross-publisher duplicates that raw hashing would miss. Worth measuring both
   ways once, since the claim is now a prediction rather than an assumption.

**Do not start** tokenizer work or modelling. The tokenizer is timeboxed to Week 5.

**Carried forward**

- **The normalizer is validated on Wikipedia only.** Every rule fires (session 4, Measured), but
  Wikipedia is not representative. PRD §6.3.5 requires 200 manually inspected samples for the
  quality filter — put the same 200 through the normalizer and confirm no rule misfires on real
  **FineWeb2** Urdu before the freeze.
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
  Session 5 did this for stage 3 and it caught two population-level mislabels, so the practice is
  now load-bearing rather than aspirational.
- **⚠️ The code-switched budget may not be reachable from these sources.** PRD §6.1 asks for ~10M
  code-switched tokens. Measured share by letters: **0.54% of FineWeb2** and **2.6% of Urdu
  Wikipedia**. Extrapolated over shard 001 (~3.5G characters) plus the full Wikipedia dump
  (~324M), that is roughly **27M characters ≈ 7M tokens** — the right order of magnitude but
  *below* target and with no margin. Three ways out, in preference order: (a) fetch FineWeb2 train
  shard 000 as well, which roughly doubles it at ~$0 and ~25 minutes; (b) accept a smaller
  code-switched share and say so; (c) add a social-media source, which means a new licence-gate
  decision. **Decide before the freeze, not after.** Note this is the one population where more
  data is genuinely scarce — Finding B's "Urdu is not data-constrained" holds for *native* Urdu.
- **Roman Urdu's 40M-token target is unverified after dedup.** PRD §6.2 already warns that
  Roman-Urdu-Parl's 6.37M pairs collapse to ~1.09M unique Urdu sentences. At ~45 characters a
  sentence that is ~49M characters ≈ 12M tokens, well under the ~40M target. Stage 6 will settle
  it; if it holds, §6.1's Roman Urdu figure needs the same treatment §6.1's native figure got in
  v2.1.
- **`scripts/corpus_probe.py` is now redundant with `scripts/stage3_probe.py`.** The older script
  reads parquet ad hoc and predates the shard reader; the newer one runs stages 2→3 through it and
  covers the same ground plus langid. Fold the stage-4 reporting into `stage3_probe.py` and delete
  the old one, or keep it and port it to `ShardReader` — but not both, and not indefinitely.

**Retry when convenient:** OpenReview `W5Ht05jF4c` — still behind the browser-verification wall as
of 2026-08-03 (both API v1 and v2 return `ChallengeRequiredError`). Lower stakes now that both arms
sit inside the fitted range.
