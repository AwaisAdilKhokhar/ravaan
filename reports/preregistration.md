# Preregistration — Ravaan AR vs. masked diffusion on Urdu

**Committed:** 2026-08-03 (Week 1). **Status:** OPEN — no model has been trained; no results exist.
**Required by:** PRD §4.5. **Binding until:** results are reported.

> This document exists to make the project falsifiable. It is committed to git before Stage C, and
> the commit timestamp is the evidence. Anything not written here before training started cannot be
> presented afterwards as a planned finding. If a deviation becomes necessary, it is recorded in
> §8 below with its date and reason — **the original text is never edited**.

---

## 1. Question

> Does the data-constrained crossover between masked diffusion and autoregression occur where the
> English scaling law of Prabhudesai et al. (arXiv:2507.15857) predicts, when the training corpus is
> naturally noisy non-English Nastaliq-script web text rather than clean C4?

This supersedes PRD v2 §1's framing. The reason is recorded in `literature_review.md` §4: Urdu is
**not** data-constrained at 70M parameters (~5–6B Urdu tokens are demonstrably collectable versus
~1.4B Chinchilla-optimal), so the unique-data budget is a design variable in this study exactly as
it was in the English one. The honest question is therefore about **transfer of the scaling law**,
not about natural data scarcity.

## 2. Design

Two models — **Ravaan-AR** and **Ravaan-DIFF** — identical in corpus, tokenizer, parameter count
(within 2%), context length, optimizer, schedule, tokens processed, seeds, and training tasks.
They differ **only** in factorization (PRD §4.1). Both arms process ~9.9B tokens.

| Arm | Unique tokens U | Epochs | Seeds | Role |
|---|---|---|---|---|
| **A** | 25M | ~396 | **3** | Primary. Predicted to sit **1.79× past** C_crit |
| **B** | 100M | ~99 | 1 | Bracket. Predicted to sit **0.09× of** C_crit (i.e. before it) |

Both U values lie inside the reference paper's fitted range of U ∈ {25, 50, 100}M. No result in
this study depends on extrapolating their law beyond where they estimated it.

Checkpoints for evaluation are taken at **fixed fractions of tokens processed**, identically for
both models and both arms, so curves are comparable on the x-axis of compute:
**1, 2, 5, 10, 25, 50, 100% of 9.9B tokens.**

## 3. Predictions, stated before any run

These are the falsifiable commitments. Derived with `scripts/crossover.py` from the reference fit
`log10(U) = 0.460·log10(C) − 1.050`.

| # | Prediction | Resolves as WRONG if |
|---|---|---|
| **P1** | In **arm A**, validation BPB curves for AR and DIFF **cross**, with DIFF lower at the final checkpoint | No crossing by 9.9B tokens, or DIFF is higher at the end |
| **P2** | In **arm B**, the curves **do not cross**; AR is lower at the final checkpoint | They cross in arm B |
| **P3** | The arm-A crossover occurs at compute within **one order of magnitude** of C_crit(25M) = 2.32 × 10¹⁸ FLOPs | Observed crossover is outside [2.3 × 10¹⁷, 2.3 × 10¹⁹] FLOPs |
| **P4** | AR's fitted data-reuse half-life on Urdu is **lower** than DIFF's | DIFF's is lower or they are within CI |

**P1 and P2 together are the primary endpoint.** The interesting outcome is the *pair*: a crossover
in A and none in B reproduces the English law's shape on Urdu. Any other combination does not.

**What each outcome means, committed in advance:**

| A | B | Reading |
|---|---|---|
| cross | no cross | Scaling law **transfers** to Urdu. P1–P2 confirmed. |
| cross | cross | Crossover occurs **earlier** on Urdu than English predicts — diffusion advantage is *larger* on noisy non-English text. |
| no cross | no cross | Crossover is **later** on Urdu than predicted, or absent. A real negative result about transfer. |
| no cross | cross | Incoherent with the law; indicates a bug. Debug, do not report as a finding. |

## 4. Endpoints

**Primary (one, preregistered):** the sign and compute-location of the AR/DIFF crossover in
validation **bits-per-byte** across the token-processed sweep, in arm A, aggregated over 3 seeds.
BPB — not bits-per-token — so the comparison is tokenizer-independent.

**Secondary (three, Holm-corrected across the family):**
1. Transliteration chrF on the **human-written** test set (PRD §8.2)
2. Infill exact-match
3. OCR CER reduction on the **real-OCR** test set

**Statistics.** Paired bootstrap confidence intervals on all task metrics. If a CI includes zero,
it is stated in the abstract. Ablations get 1 seed and are reported as directional only.

**No metric is added to the results table after results are seen.** Metrics computed but not listed
here may appear only in an appendix explicitly labelled exploratory.

## 5. The ELBO caveat, acknowledged in advance

The diffusion objective yields an **upper bound (ELBO)** on likelihood, not exact NLL. Comparing a
diffusion ELBO against exact AR NLL is **conservative — it disadvantages diffusion.** Both are
reported, the bound is stated explicitly, and downstream task metrics (directly comparable) are the
tiebreaker. This is carried forward unchanged from PRD §4.3.

## 6. Known bias toward AR

The reference paper adopts Muennighoff et al.'s hyperparameters and notes they "may provide a slight
advantage to autoregressive models." Ravaan inherits this. **Commitment:** hyperparameters are
chosen once, from the reference paper's configuration, and are **not tuned for either model**. The
report states whose defaults they are and acknowledges the direction of the bias. No
hyperparameter sweep will be run for either arm (this is also a PRD §9 cost control).

## 7. What would make this project report a negative result

Committed in advance, so that a null cannot be quietly reframed later:

- If P1 fails (no crossover in arm A at 1.79× past predicted C_crit), the finding is
  **"the English data-constrained crossover does not transfer to Urdu at 70M parameters"** and that
  is the headline. It is reported as the primary result, not buried.
- If seed variance swamps the effect (paired CIs spanning zero at every checkpoint), the finding is
  **"the effect is smaller than seed noise at this scale"** and the intervals are reported instead
  of point estimates.
- **Ravaan-DIFF winning is not a ship criterion** (PRD §14).

## 8. Deviation log

*Any change after this file's first commit is appended here with date and reason. Text above is
never edited.*

| Date | Change | Reason |
|---|---|---|
| — | *(none yet)* | |

---

## Appendix — parameters fixed at preregistration

| | |
|---|---|
| Model | ~70M params (≈59.5M non-embedding), 12 layers, d=640, 10 heads, head dim 64, SwiGLU FFN 1728 |
| Context | 512 |
| Vocabulary | 16,384 SentencePiece Unigram, tied embeddings, byte fallback |
| Positional / norm / precision | RoPE / RMSNorm / BF16 |
| Diffusion objective | Time-agnostic MDLM (no timestep embedding), loss on masked positions |
| AR objective | Next-token prediction + FIM |
| Task mixture | Frozen before Stage C per PRD §4.2 — **the infilling share is under review** (lit review §6: reported FIM practice is 50–90%, PRD specifies 10%) |
| Compute per arm | C = 6ND ≈ 4.16 × 10¹⁸ FLOPs |
| C_crit(25M) | 2.32 × 10¹⁸ FLOPs |
| C_crit(100M) | 4.72 × 10¹⁹ FLOPs |
| Reference fit | `log10(U) = 0.460·log10(C) − 1.050`, arXiv:2507.15857 Fig. 6, verified against PDF 2026-08-03 |
