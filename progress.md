# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read the "Next session" section at the bottom
first.**

- **Started:** 2026-08-03 (Week 1 of 16)
- **Current phase:** Weeks 1–2 complete → Weeks 3–4, corpus freeze. Pipeline stages 1–6 are built
  and validated on real text; stage 5's 200-sample validation is adjudicated, scored and written up
  ([`reports/quality_validation.md`](reports/quality_validation.md)), and stage 6 has run **complete
  passes over every source** — Urdu Wikipedia, both columns of Roman-Urdu-Parl, and FineWeb2 against
  Wikipedia. Next is stage 7 (MinHash near-dedup), which session 8 hands a measured acceptance test,
  a measured expectation of near-inertness on the primary source, and the one population where it
  demonstrably has real work to do.
- **Gate G0:** ✅ **PASSED** 2026-08-03 — comparison confirmed unpublished. See
  [`reports/literature_review.md`](reports/literature_review.md).
- **Design decision:** ✅ **Option 2 (two-point law) chosen** 2026-08-03. U ∈ {25M, 100M}; 3 seeds
  at 25M, 1 at 100M. PRD amended to v2.1; preregistration committed.
- **Preregistration:** ✅ committed [`reports/preregistration.md`](reports/preregistration.md) —
  4 falsifiable predictions, before any training.
- **Spend to date:** $0.00 of $150 hard cap
- **Tests:** 317 passing (69 normalization · 57 encoding · 57 acquisition · 43 quality · 41 dedup
  · 32 langid · 18 shards)
- **Committed** through session 7. Sessions 6 and 7 are one commit — stage 5, its 200-sample
  validation and the write-up are one deliverable.

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

**Stage 6 is done, all six full passes landed, and every prediction carried into it has been
answered** — three of them negatively, which is the useful direction. The one number still carrying
an assumption is the exact post-dedup character volume of Roman-Urdu-Parl (Finding K′), which comes
free from the two-phase pass at freeze time.

1. **Stage 7 (MinHash near-dedup)** — and session 8 hands it four things it should not have to
   rediscover:
   - **The one population where near-dedup has real work to do**, from Finding L: Urdu Wikipedia
     articles that also exist inside FineWeb2 as crawled HTML. 2,388 documents in shard 001 come
     from wiki hosts and **not one** is byte-identical to its counterpart in the `wikimedia`
     dump — processed wikitext against a rendered page. If stage 7 does not cluster those, it is
     not doing the job stage 8 needs it to have done. This is the acceptance test that replaces
     the one Finding I retired.
   - **A measured acceptance test, written before the code.** Finding I: `urdu-wikipedia:122264`,
     `:122214`, `:363641`, `:122110` and the geo-stub farm around them top out at Jaccard **0.677**
     at n=2 and **0.423** at n=5. A stage 7 built at the conventional 0.8 threshold will not touch
     them, and that is the *expected* result, not a bug to chase. Session 7's note that near-dedup
     "should not miss" them is superseded.
   - **A measured expectation of near-inertness on the primary source.** Finding H: FineWeb2
     already removed 31.02% of `urd_Arab` by MinHash. Stage 7 should be reported as an assertion
     on FineWeb2 unless it demonstrably is not, and the thing to check is whether it fires on
     Finding F's cross-publisher republication, which is long, verbatim, and exactly what a
     near-dedup is for.
   - **A threshold decision that must be made on measured pairs, not inherited.** Every stage-5
     threshold that survived the distribution still had to be moved by the 200-sample; the same
     discipline applies to a similarity threshold. Draw candidate pairs at several thresholds and
     read them before picking one.
2. **Stage 8 (eval decontamination) has a requirement now, not a preference.** Finding L: for the
   most likely contamination path in this project — §8.2's held-out evaluation text drawn from Urdu
   Wikipedia while the same articles sit in training data as crawled HTML — **hashing returns a
   confident zero and fuzzy matching is the entire mechanism**. §6.3.8's "hash + fuzzy match" must
   not be implemented as "hash, and fuzzy match if there is time". A stage 8 reporting zero
   contamination from hashes alone is reporting the artefact Finding L measured.
3. **Then stages 9 (splits) and 10 (tokenization + packing)**, plus the PII regex pass and the
   corpus manifest/statistics rollup — the remaining Weeks 3–4 items. Stage 9 inherits Finding G's
   lesson directly: a split assignment is a per-document property and samples fine, but any
   *pairwise* check over the splits does not.

**Do not start** tokenizer work or modelling. The tokenizer is timeboxed to Week 5.

**A note on running long passes here.** Stage 6 is the first stage that must read a source *whole*
— Finding G — and tracked background jobs in this environment were killed three times at somewhere
under 14 minutes. Foreground calls cap at 10 minutes. What worked was `nohup … &` as a detached
process. Stages 7 and 9 have the same shape, so budget for it.

**Carried forward**

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
  were booked as "the stub farm, which is stage 7's" — **and session 8's Finding I retires that
  booking.** No stub pair reaches Jaccard 0.7 at any shingle size, so all four are residue that
  survives the whole pipeline. `reports/quality_validation.md`'s error budget needs the sentence
  corrected the next time it is touched: stage 5's false-accept rate is the filter's, not a debt
  owed to a later stage.
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
- **⚠️ The code-switched budget may not be reachable from these sources.** PRD §6.1 asks for ~10M
  code-switched tokens. Measured share by letters: **0.54% of FineWeb2** and **2.6% of Urdu
  Wikipedia**. Extrapolated over shard 001 (~3.5G characters) plus the full Wikipedia dump
  (~324M), that is roughly **27M characters ≈ 7M tokens** — the right order of magnitude but
  *below* target and with no margin. Three ways out, in preference order: (a) fetch FineWeb2 train
  shard 000 as well, which roughly doubles it at ~$0 and ~25 minutes; (b) accept a smaller
  code-switched share and say so; (c) add a social-media source, which means a new licence-gate
  decision. **Decide before the freeze, not after.** Note this is the one population where more
  data is genuinely scarce — Finding B's "Urdu is not data-constrained" holds for *native* Urdu.
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
