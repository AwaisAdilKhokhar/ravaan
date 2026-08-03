# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read the "Next session" section at the bottom
first.**

- **Started:** 2026-08-03 (Week 1 of 16)
- **Current phase:** Weeks 1–2 — literature review, corpus acquisition, language/script ID
- **Gate G0:** ✅ **PASSED** 2026-08-03 — comparison confirmed unpublished. See
  [`reports/literature_review.md`](reports/literature_review.md).
- **⚠️ Blocking decision open:** G0 passed on novelty but surfaced two findings that require the
  experimental design to change before Stage C. See "Decision required" below.
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
| Act on lit-review Findings A & B — revise PRD §1/§4.3/§6.1 | — | ⛔ needs your call |
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

## ⛔ Decision required before Weeks 3–11

Findings A and B are one problem seen twice: the PRD picked a model size at which Urdu is not
data-constrained, so the unique-data budget must be chosen artificially regardless. Because U costs
nothing, this is fixable at **zero additional GPU spend** — only run *count* changes.

| Option | Design | Reaches crossover? | Cost |
|---|---|---|---|
| 0. Unchanged | U = 300M, 33 epochs | No (0.01×) | 6 core runs |
| 1. Retarget U | U = 25M, ~400 epochs, 3 seeds | Yes (1.78×) | 6 core runs |
| **2. Two-point law** *(recommended)* | U ∈ {25M, 100M}; 3 seeds at 25M, 1 at 100M | Yes at 25M, brackets at 100M | 8 core runs |
| 3. Scale model up | ~300M params | Yes | Far over $150 |

Option 2 keeps the 3-seed protocol on the primary endpoint and brackets the crossover so its
*location* — not just its sign — can be tested against the English fit. Full reasoning and the list
of PRD edits each option implies: review §8.

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

**Primary task: verify the two numbers Finding A rests on, then act on the design decision.**

Finding A is currently strong enough to redirect the project and *not* strong enough to bet the
project on — its constants came from automated extraction of HTML and a blog post, not the typeset
paper, and two sources disagreed by ~2× on the AR half-life. Verify before anything is rebuilt
around it.

1. **Verify against the PDF of arXiv:2507.15857** (open items 1–2 in the review):
   - the closed-form `C_crit(U)` equation and the `log10(U) = 0.460·log10(C) − 7.052` fit;
   - both `R_D*` half-lives (blog says ~500 / ~15; a third-party extraction said 512.85 / 31.93);
   - read OpenReview `W5Ht05jF4c` for reviewer critique of the scaling-law fit specifically. If
     reviewers doubted its extrapolation, Finding A weakens and Option 0 gets more defensible.
   - `pip install pymupdf` or use the arXiv HTML v7 — the automated PDF reader failed on this file.
   - Update `scripts/crossover.py` constants and re-run; the review's numbers must still hold.

2. **Apply the design decision** once you've chosen an option (review §8.3). If Option 2:
   - write `reports/preregistration.md` — U values, predicted `C_crit` per arm, primary endpoint,
     and the falsifiable prediction, committed and timestamped **before** Stage C (PRD §4.5);
   - make the §8.4 edits to the PRD (§1, §4.3, §6.1, §4.2, §11 G4) — that list is the changelog;
   - corpus target drops from 300M to ~100M unique tokens, which shortens Weeks 3–4.

3. **Then start acquisition (stage 1)** — unchanged by the decision, since over-collecting is free
   and you can always subsample down to the chosen U:
   - `ravaan/data/acquisition.py` + `configs/data/sources.json` — declarative manifest (HF dataset
     id, **pinned revision**, license, expected size) writing SHA-256 checksums to
     `data/manifest.json`. FineWeb2 and Wikipedia both move; pin them.
   - Add **UrduLM's corpus** to the candidate sources (review §4) — but check its licence first,
     since CC BY-NC-ND would conflict with PRD §6.3's permissive-checkpoint policy.
   - `ravaan/data/encoding.py` — stage 2 encoding validation (strict UTF-8, replacement-char rate,
     mojibake detection), with tests.
   - `pip install -e ".[data]"` — nothing in the repo needs it yet.

**Do not start** tokenizer work or any modelling. The tokenizer is timeboxed to Week 5 and its
vocab-size choice may interact with the revised corpus size.

**Two caveats to carry forward**

- The normalizer's rules were validated against hand-written fixtures, not real corpus text. PRD
  §6.3.5 requires 200 manually inspected samples for the *quality filter* — put the same 200
  through the normalizer and confirm no rule misfires on real FineWeb2 Urdu before the freeze.
- PRD §4.2 sets the infilling share at 10%. Reported FIM practice is 50–90% with no left-to-right
  degradation (review §6). If 10% leaves Ravaan-AR bad at infilling, the A2 "unfair baseline"
  comparison loses its meaning — the fair baseline would also be undertrained. Decide before the
  task mixture is frozen ahead of Stage C.
