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
| 2026-09-10 | **Arm B is dropped. The project reports a single arm (A, U = 25M, 3 seeds).** P2 becomes unresolvable and is withdrawn, not restated. The outcome table in §3 collapses to its two arm-A rows: *cross* → the crossover occurs where the English law predicts at this U; *no cross* → it does not, and §7's first bullet governs the write-up. P1, P3 and P4 are unaffected, and §4's primary endpoint — arm A, 3 seeds — is unchanged. | Corpus availability, measured at the freeze and **before any training run**. Roman-Urdu-Parl loses 82.4% of its characters to stages 6 and 7 (465,303,750 → 81,791,735), and it is the only source feeding the `roman_urdu` population. That leaves it at **0.44× of arm B's requirement** at the fixed 120:40:10 mixture, so arm B cannot be assembled at any seed count. This is Gate G1's pre-committed fallback (PRD §11, "run arm A only, report single-arm") taken on the condition v2.2 added to it for precisely this case. The deletion was verified as genuine near-duplication by reading the text, not inferred from the rate — see progress.md session 17, Findings AA and AB. **No model has been trained and no result has been seen**; this deviation is forced by the data that exists, and is recorded here rather than in the text above because §8 is the only place a preregistration may change. |
| 2026-09-13 | **Infill exact-match is scored against a truncation rule, fixed here before any result exists: the AR arm's generation is cut to the gold span's token length.** §4.5's secondary endpoint is otherwise not computable for that arm. No other endpoint moves; P1, P3 and P4 are unaffected. | §4.2's FIM framing for the AR arm places the middle at the end of the sequence with **no terminator after it**, so the model was never given a signal for where an infill ends. Measured on the pilot: over 12 prompts with a 32-token hole it stopped on 5, and its median generation was the 200-token budget rather than a choice (progress.md session 22, Finding AQ). Truncating to the gold length is the *symmetric* repair, not a generous one — the diffusion arm is already given that length, because an absorbing-state canvas has a fixed width from its first forward pass. Scoring AR without it would compare a bounded answer against an unbounded one and inflate **toward diffusion**, which is the opposite of the bias §6 warns about and the opposite of what ablation A2 exists to quantify. The framing itself is left unchanged by decision on 2026-09-13, the cost being that both arms are told the answer's length; the alternative was a training-side terminator token and a re-pilot. **No model in the reported experiment has been trained and no result has been seen.** |


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
