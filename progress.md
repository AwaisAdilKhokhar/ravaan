# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read the "Next session" section at the bottom
first.**

- **Started:** 2026-08-03 (Week 1 of 16)
- **Current phase:** Weeks 1–2 — literature review, corpus acquisition, language/script ID
- **Gate G0:** ✅ **PASSED** 2026-08-03 — comparison confirmed unpublished. See
  [`reports/literature_review.md`](reports/literature_review.md).
- **Design decision:** ✅ **Option 2 (two-point law) chosen** 2026-08-03. U ∈ {25M, 100M}; 3 seeds
  at 25M, 1 at 100M. PRD amended to v2.1; preregistration committed.
- **Preregistration:** ✅ committed [`reports/preregistration.md`](reports/preregistration.md) —
  4 falsifiable predictions, before any training.
- **Spend to date:** $0.00 of $150 hard cap
- **Tests:** 183 passing (69 normalization · 57 encoding · 57 acquisition)

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
| Language / script ID (stage 3) | §6.3.3 | ⬜ |

### Weeks 3–4 — corpus freeze (**G1**: clean corpus ≥ 100M tokens — PRD v2.1 §11; was 150M in v2.0)
| Item | PRD | Status |
|---|---|---|
| **Urdu normalization (stage 4)** | §6.3.4 | ✅ |
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

**Primary task: language / script identification, pipeline stage 3 (PRD §6.3.3).**

Stages 1, 2 and 4 exist and the corpus is on disk. Stage 3 is the gap between them, and it is the
one that decides what "Urdu" means for this project — which makes it the last stage where a wrong
default silently changes the corpus rather than the code.

1. **A streaming shard reader.** `scripts/corpus_probe.py` reads parquet ad hoc; stages 2→3→4 need
   a real iterator over a pinned shard that yields `(source, doc_id, text)` and can be resumed.
   This is the first thing that genuinely needs the `[data]` extra. Everything downstream
   (dedup, filtering, packing) consumes it, so build it once and properly.
2. **`ravaan/data/langid.py`** — document-level ID, sentence-level only for mixed documents, per
   §6.3.3. Three populations have to come out separately labelled, because §6.1 budgets them
   separately: native Urdu (~120M tokens), Roman Urdu (~40M), code-switched (~10M). A script-ratio
   classifier over Unicode blocks handles native-vs-Roman cheaply; the hard case is **Roman Urdu
   vs. English**, which share an alphabet and which no off-the-shelf langid separates well.
   Decide explicitly whether that needs a model or a word-list heuristic, and record the choice.
3. **Carry Finding E into the reader.** Document selection must be random across the shard, never
   a prefix or a contiguous block — otherwise arm A's 25M subsample is systematically older web
   text than arm B's 100M, confounding the primary endpoint with crawl date. The reader should
   make the biased option the one you have to ask for, as `corpus_probe.py` now does.
4. **Is Arabic-variant spelling site-correlated?** FineWeb2 changes only 13.7% of documents but
   averages 0.83 yeh substitutions across all of them, so a minority carries ~6 each. Check the
   `url` column at stage 3: if it is a per-publisher property, it interacts with near-dedup
   (stage 7) and with the arm A subsample.

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

**Retry when convenient:** OpenReview `W5Ht05jF4c` — still behind the browser-verification wall as
of 2026-08-03 (both API v1 and v2 return `ChallengeRequiredError`). Lower stakes now that both arms
sit inside the fitted range.
