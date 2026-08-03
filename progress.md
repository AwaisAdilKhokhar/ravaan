# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read the "Next session" section at the bottom
first.**

- **Started:** 2026-08-03 (Week 1 of 16)
- **Current phase:** Weeks 1–2 — literature review, corpus acquisition, language/script ID
- **Next gate:** **G0** (end of Week 2) — literature review must confirm the AR/DIFF comparison for
  Urdu is unpublished, *in writing*. Fail → reframe or stop.
- **Spend to date:** $0.00 of $150 hard cap
- **Tests:** 67 passing

---

## Status board

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⛔ blocked

### Weeks 1–2 — lit review + acquisition
| Item | PRD | Status |
|---|---|---|
| Repo scaffold, packaging, license, CI-able test suite | §13 | ✅ |
| Literature review → `reports/literature_review.md` (**G0**) | §11 | ⬜ |
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

**Primary task: literature review → `reports/literature_review.md` (Gate G0).**

This is the one item that can kill the project, it is due end of Week 2, and everything downstream
is wasted effort if it fails. It is also the only remaining Week 1–2 task that does not depend on
downloading anything.

Concretely:

1. Create `reports/literature_review.md` with a structure that can actually answer G0:
   - Masked diffusion LMs: MDLM, SEDD, LLaDA, and the diffusion-vs-AR scaling/data-constrained
     work that motivates the whole hypothesis (find the exact paper making the "diffusion wins
     when data-constrained, compute-abundant" claim, and pin down its crossover numbers so §4.3
     can state whether Urdu lands where English predicted).
   - Existing Urdu LMs and Urdu pretraining corpora.
   - Any existing diffusion LM for Urdu or a comparable low-resource language.
   - **Verdict section:** is this comparison unpublished? Written down, with citations, so §3's
     "no claim to be first until the literature review says so in writing" is satisfied.
2. Record the verdict and date in this file's status board, and flip G0 to pass/fail.

**Then, if G0 passes and time remains — start acquisition (stage 1):**

3. `ravaan/data/acquisition.py` + `configs/data/sources.json` — declarative source manifest
   (HF dataset id, revision/commit pin, license, expected size) with SHA-256 checksums written to
   `data/manifest.json`. Pin revisions: FineWeb2 and Wikipedia both move.
4. `ravaan/data/encoding.py` — stage 2 encoding validation (strict UTF-8 decode, replacement-char
   rate, mojibake detection), with tests.
5. Install the `data` extra (`pip install -e ".[data]"`) — nothing in the repo needs it yet.

**Do not start** normalization tuning, tokenizer work, or any modelling. Stage 4 is done and
frozen until real corpus text exists to validate it against; the tokenizer is explicitly timeboxed
to Week 5.

**One caveat to carry forward:** the normalizer's rules were validated against hand-written
fixtures, not real corpus text. PRD §6.3.5 requires 200 manually inspected samples for the
*quality filter* — take the same 200 samples through the normalizer at the same time and confirm
no rule is misfiring on real FineWeb2 Urdu before the corpus is frozen.
