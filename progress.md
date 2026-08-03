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
- **Tests:** 67 passing

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
| FineWeb2 `urd_Arab` acquisition + checksums | §6.2, §6.3.1 | ⬜ |
| Roman-Urdu-Parl acquisition + checksums | §6.2 | ⬜ |
| Urdu Wikipedia dump acquisition + checksums | §6.2 | ⬜ |
| Encoding validation (stage 2) | §6.3.2 | ⬜ |
| Language / script ID (stage 3) | §6.3.3 | ⬜ |

### Weeks 3–4 — corpus freeze (**G1**: clean corpus ≥ 150M tokens)
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
| Corpus manifest + statistics | §6.3 | ⬜ |

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

## Open questions for you

1. **Config format.** I used JSON (stdlib, no dependency). ML repos usually reach for YAML.
   Switching later means touching every config — worth deciding now. Recommendation: stay on JSON
   for data-pipeline configs, and only add YAML if training configs get unwieldy.
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
- **CI workflow.** `tests/` runs clean under `python -m pytest`; no GitHub Actions file yet.

---

## Next session

**Primary task: corpus acquisition, pipeline stage 1 (PRD §6.3.1).**

Week 1's planning work is complete — G0 passed, the design is decided, the PRD is amended, and the
preregistration is committed. Everything from here needs real corpus text on disk. The revised
target is **~120M unique clean tokens**, down from 300M, which shortens Weeks 3–4.

1. **`configs/data/sources.json` + `ravaan/data/acquisition.py`** — a declarative source manifest:
   HF dataset id, **pinned revision/commit SHA**, licence, expected size. FineWeb2 and Wikipedia
   both move; an unpinned revision makes the corpus irreproducible. Write SHA-256 checksums to
   `data/manifest.json`. Tests over a small fixture, not a live download.
2. **Evaluate UrduLM's corpus as a source** (arXiv:2601.17664 — 33 GB, ~5–6B tokens, "released
   openly"). **Check the licence first**: the arXiv listing shows CC BY-NC-ND, which would conflict
   with PRD §6.3's permissive-checkpoint policy. If NC, it can still serve as the §6.1
   "could-have-collected" citation and a tokenizer-fertility baseline without entering training.
3. **`ravaan/data/encoding.py`** — stage 2 encoding validation: strict UTF-8 decode, replacement-char
   rate, mojibake detection. With tests.
4. `pip install -e ".[data]"` — nothing in the repo needs it yet.

**Do not start** tokenizer work or modelling. The tokenizer is timeboxed to Week 5.

**Three caveats to carry forward**

- **Validate the normalizer on real text.** Its rules were checked against hand-written fixtures
  only. PRD §6.3.5 requires 200 manually inspected samples for the *quality filter* — put the same
  200 through the normalizer and confirm no rule misfires on real FineWeb2 Urdu before the freeze.
- **The infilling share is unresolved.** PRD §4.2 sets 10%; reported FIM practice is 50–90% with no
  left-to-right degradation (review §6). If 10% leaves Ravaan-AR genuinely bad at infilling, A2
  loses its meaning — the *fair* baseline would also be undertrained, and §4.1's whole fairness
  argument weakens. **Decide before the task mixture is frozen ahead of Stage C.** This is the last
  substantive open design question.
- **Hyperparameter provenance.** Preregistration §6 commits to taking the reference paper's config
  untuned, and to stating that it likely favours AR. Record the source when the training config is
  written in Week 6 — not retroactively.

**Retry when convenient:** OpenReview `W5Ht05jF4c` (browser-verification wall) for reviewer critique
of the `C_crit` fit. Lower stakes now that both arms sit inside the fitted range.
