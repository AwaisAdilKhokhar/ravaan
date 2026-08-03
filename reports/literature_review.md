# Literature review — Gate G0

**Date:** 2026-08-03
**Gate:** G0 (PRD §11) — *proceed if the literature review confirms the comparison is unpublished*
**Verdict:** ✅ **PASS on novelty** — with two findings that require the experimental design to change
before Stage C.

> PRD §3: "no claim to be the first Urdu diffusion model until the Week 1–2 literature review says
> so in writing." This document is that writing. The claim it supports is stated precisely in §7.

---

## 0. Executive summary

1. **The comparison is unpublished.** No masked diffusion language model for Urdu was found. No
   replication of the data-constrained diffusion result outside English was found. The specific
   question in PRD §1 appears open. **G0 passes.**

2. **⚠️ Finding A — the planned budget does not reach the predicted crossover.** Applying the
   reference paper's own fitted scaling law to Ravaan's specification (70M params, U = 300M unique
   tokens, 33 epochs) puts the run **≈125× below** the compute at which diffusion is predicted to
   overtake AR. Reaching the crossover at U = 300M would take ≈4,100 epochs. As specified, the
   headline experiment is predicted to return "no crossover" *before it is run* — a null result by
   construction, which is the same class of flaw v2 was written to remove from v1.

3. **⚠️ Finding B — the "naturally data-constrained" premise does not hold at 70M parameters.**
   UrduLM (January 2026) curated and openly released a 33 GB Urdu corpus of roughly 5–6B tokens.
   Chinchilla-optimal for a 70M-parameter model is ~1.4B tokens. Urdu therefore has **~4× more data
   than a 70M model can use**, and is not data-constrained at this scale. Capping at 300M — or at
   25M — is *artificial subsampling*, exactly what PRD §1 criticises the English result for.

Findings A and B are not fatal, and they point at the same fix. They are addressed in §8.

---

## 1. Method and limitations of this review

Searched 2026-08-03 via web search and direct retrieval: arXiv, ACL Anthology, OpenReview,
Hugging Face, and authors' project pages. Query families: masked diffusion LM foundations;
diffusion-vs-AR scaling and data-constrained training; diffusion LMs for low-resource, multilingual
and non-English settings; Urdu language models and corpora; AR infilling / FIM as a matched
baseline.

**Limitations, stated honestly:**

- Several quantitative values below were extracted by an automated reader from paper HTML, project
  pages, and the authors' blog, **not** read off the typeset PDF. Two sources disagreed on one
  number (§2.2). Everything marked ⚠️VERIFY must be checked against the source PDF before it enters
  the technical report.
- Absence of evidence is weak evidence. "No Urdu diffusion LM found" means seven query families
  surfaced none; it does not prove none exists. Non-English venues and Urdu-language publications
  (CLE Lahore, LREC regional tracks) are under-indexed by the tools used here.
- No paywalled or non-indexed venue was searched.

---

## 2. The motivating result

### 2.1 Prabhudesai, Wu, Zadeh, Fragkiadaki, Pathak — *Diffusion Beats Autoregressive in Data-Constrained Settings*

arXiv:2507.15857 (v1 July 2025, revised October 2025). CMU + Lambda. Code at
`github.com/wmn-231314/diffusion-data-constraint`. OpenReview `W5Ht05jF4c`.

This is the paper PRD §1 is arguing with, and the source of the crossover hypothesis.

| Property | Value |
|---|---|
| Models | 7M → 2.5B parameters |
| Unique-token budgets | U ∈ {25M, 50M, 100M} |
| Max epochs | 800 (80B tokens processed) |
| Dataset | **English C4**, GPT-2 BPE, 2048-token sequences |
| Objective | Masked diffusion vs. standard AR |

**Claim.** Masked diffusion outperforms AR when compute is abundant but unique data is scarce,
because random-order factorization acts as implicit data augmentation. AR overfits under heavy data
repetition; diffusion did not, within the budget explored.

### 2.2 The numbers that matter

**Data-reuse half-life** (epochs over which repeated data retains half its value):

| | Reported by authors' blog | Third-party extraction |
|---|---|---|
| Diffusion `R_D*` | ≈ **500** | 512.85 |
| AR `R_D*` | ≈ **15** | 31.93 |

⚠️VERIFY — the AR figure differs by ~2× between sources. The authors' own CMU blog says ≈15. The
direction and order of magnitude (diffusion tolerates repetition ~30× longer than AR) is consistent
across every source and is the load-bearing fact.

**Critical compute threshold.** The fitted relation, which is the useful form:

```
log10(U) = 0.460 · log10(C) − 7.052        U in millions of unique tokens, C in FLOPs
```

⚠️VERIFY against the paper's typeset equation. A closed form was also reported as
`C_crit(U) = 2.12 × 10^1.956 · U^2.174`, whose rendering is ambiguous; the log-linear fit above is
used throughout this document because it survives a unit check (§2.3).

### 2.3 Unit check — why the fit above can be trusted

The paper's own maximum budget is 100M parameters × 80B tokens = **4.80 × 10¹⁹ FLOPs** (at C = 6ND).
The fit predicts the crossover for their largest budget U = 100M at **4.77 × 10¹⁹ FLOPs**.

Ratio: **1.01×**. Their maximum compute lands essentially exactly on their own crossover, which is
what a paper reporting "diffusion overtakes AR at the top of our sweep" should look like. The units
are confirmed. Reproduce with `scripts/crossover.py`.

---

## 3. ⚠️ Finding A — Ravaan as specified sits far below the crossover

Applying the same fit to PRD §4.3 and §5:

| | Value |
|---|---|
| Parameters | 70M |
| Unique tokens U | 300M |
| Epochs | 33 → 9.9B tokens processed |
| Planned compute C = 6ND | **4.16 × 10¹⁸ FLOPs** |
| Predicted crossover C_crit(300M) | **5.19 × 10²⁰ FLOPs** |
| **Shortfall** | **125×** |
| Epochs needed to reach crossover at U = 300M | **≈ 4,120** |

Crucially, **U is free**. Total compute is set by parameters × tokens processed, so changing how
much *unique* data those 10B tokens are drawn from costs nothing. The reachability of the crossover
is purely a design choice:

| Unique U | Epochs to 10B | C_crit | Planned C / C_crit |
|---|---|---|---|
| 10M | 990 | 3.19 × 10¹⁷ | **13.0×** ✅ |
| 25M | 396 | 2.34 × 10¹⁸ | **1.78×** ✅ |
| 50M | 198 | 1.06 × 10¹⁹ | 0.39× ❌ |
| 100M | 99 | 4.77 × 10¹⁹ | 0.09× ❌ |
| 300M *(as specified)* | 33 | 5.19 × 10²⁰ | **0.01×** ❌ |

**Consequence.** PRD §12 offers "no crossover below 33 epochs at 70M params on Urdu" as a
publishable fallback. That fallback is much weaker than it looks: the English scaling law *already
predicts* no crossover there, by two orders of magnitude. Confirming a prediction that was never in
doubt is not a finding. The epoch sweep as specified measures the pre-crossover regime only.

PRD §4.3 asserts "epoch 33 is deep into the regime where the diffusion advantage is predicted to
appear." Against the reference paper's own fit at U = 300M, that assertion is **incorrect**. Epoch
33 is a factor of ~125 short.

---

## 4. ⚠️ Finding B — is Urdu actually data-constrained at 70M parameters?

PRD §1's framing rests on a contrast: the English result used *artificially subsampled* data, while
Urdu is *naturally* data-constrained. The literature does not support this at the chosen model size.

**UrduLM** (arXiv:2601.17664, 25 January 2026) — "A Resource-Efficient Monolingual Urdu Language
Model." Curates a **33 GB Urdu corpus, ~13M rows, estimated 5–6B tokens**; trains a 100M-parameter
decoder-only model with a custom BPE tokenizer. Corpus, tokenizer, weights and benchmarks
"released openly" (CC BY-NC-ND 4.0 on the arXiv listing — ⚠️VERIFY the corpus licence separately;
NC would matter for PRD §6.3's permissive-checkpoint policy).

| | Tokens |
|---|---|
| Urdu tokens demonstrably collectable | **~5–6B** (UrduLM) |
| Chinchilla-optimal for 70M params (20×) | ~1.4B |
| PRD target U | 0.3B |

At 70M parameters, Urdu has roughly **4× more data than the model can use**. It is not in the
data-constrained regime. Data scarcity would begin to bite for Urdu at roughly 250–300M parameters
and above.

This directly answers the question PRD §6.1 insists the report must be able to answer — *"we
capped deliberately" vs "that was all we could get."* The answer is now on the record: **capping is
deliberate**, because ~5–6B tokens exist. That is honest, but it also means Ravaan subsamples
artificially, precisely like the English study it set out to contrast itself against.

Note this also revisits a v1 decision: PRD §6.2 lists UrduLM among sources "dropped from v1." It
should be reconsidered — as a corpus, a tokenizer-fertility baseline, and the closest prior art for
a 100M-parameter Urdu LM.

---

## 5. Masked diffusion foundations

The methods the PRD builds on. No novelty claim is being made in this area; these are the
implementation references for Weeks 6–7.

| Work | Contribution | Relevance |
|---|---|---|
| **D3PM** (Austin et al., 2021) | Discrete diffusion with structured transition matrices; absorbing state | Origin of mask-as-absorbing-state |
| **SEDD** (Lou, Meng, Ermon, 2024) | Score entropy discrete diffusion | Main alternative parameterization |
| **MDLM** (Sahoo et al., NeurIPS 2024, arXiv:2406.07524) | SUBS parameterization reduces the absorbing-state ELBO to a **weighted average of MLM losses**; Rao-Blackwellized continuous-time objective; ELBO invariant to the noise schedule α_t | **The objective Ravaan-DIFF implements.** Code: `github.com/kuleshov-group/mdlm` |
| **LLaDA** (Nie et al., 2025) | First 8B diffusion LM trained from scratch; masks at ratio t ~ U[0,1] | Evidence the objective scales |

Two points that matter for implementation:

- MDLM reports diffusion approaching AR perplexity **within 15–25%** on standard benchmarks. That
  gap is the backdrop: at Chinchilla-optimal budgets AR wins comfortably, consistent with PRD §4.3's
  expectation that epoch 1 favours AR.
- MDLM's ELBO being invariant to α_t supports PRD §4.1's choice of a **time-agnostic** formulation
  (no timestep embedding), which is also what keeps parameter counts exactly matched.

---

## 6. Prior art on *fair* AR-vs-diffusion comparison

This is the area where PRD §4.1's contribution sits, and it is more contested than the PRD assumes.

- **MARIA** — *Enabling Autoregressive Models to Fill In Masked Tokens* (arXiv:2502.06901, Feb
  2025). Fuses AR and MLM hidden states through a learned linear head and reports **outperforming
  discrete diffusion baselines across all mask rates**. Direct prior art for the thesis that
  properly-equipped AR closes the infilling gap. Must be cited; the PRD's A2 ablation argument is
  strictly weaker without it.
- **FIM** (Bavarian et al., 2022). Standard AR infilling. Reported practice: a 50–90% FIM rate
  causes no left-to-right degradation — relevant to whether PRD §4.2's 10% infilling share is
  enough to make the AR baseline genuinely competent at infilling. **10% may be too low.**
- **Methodological subtlety:** FIM requires the infilled region to be a *contiguous block*, whereas
  masked infilling can fill *arbitrary* token subsets. PRD §4.1 pairs FIM against "mask the middle
  span," which is contiguous, so the infilling task is matched correctly. The plain-text task
  remains asymmetric by construction (left-to-right vs random-ratio) — that asymmetry *is* the
  independent variable, and the report should say so explicitly rather than leave it implicit.
- A controlled AR-vs-MDLM comparison on 50M tokens of TinyStories at matched compute was surfaced
  but could not be attributed to a peer-reviewed source. ⚠️VERIFY before citing.

---

## 7. Urdu language models — the landscape

| Work | Type | Notes |
|---|---|---|
| **UrduLM** (arXiv:2601.17664, Jan 2026) | 100M decoder-only, from scratch | 33 GB / ~5–6B-token corpus; custom BPE, 20–30% fertility gain over multilingual tokenizers. **Closest prior art.** |
| **Alif-1.0-8B-Instruct** (arXiv:2510.09051) | Llama-3.1-8B continued-pretrain + SFT | Instruction-tuned; not from scratch; out of scope but the visible "Urdu LLM" |
| **Instruction-Tuned Urdu LLMs** (LREC 2026, CLE) | Llama + LoRA | 800M-token continued pretraining, 432K instructions |
| RUBERT / Bilingual Roman Urdu LM | Roman-Urdu encoders | Relevant to transliteration eval, not pretraining |
| mBERT, XLM-R | Multilingual encoders | Baselines Urdu work is usually measured against |

**Diffusion for Urdu: nothing found.** **Diffusion for any naturally low-resource language, as a
data-constrained scaling study: nothing found.** The nearest neighbour is **XDLM** (arXiv:2307.13560,
2023), a cross-lingual diffusion LM for *machine translation* — different task, different question,
no scaling or data-repetition analysis.

---

## 8. Verdict and consequences

### 8.1 What may be claimed (G0)

**Supportable in writing, as of 2026-08-03:**

> To our knowledge, no masked diffusion language model has been trained for Urdu, and the
> data-constrained diffusion-vs-AR result of Prabhudesai et al. (2025) has not been replicated
> outside English.

**Not supportable, and must not be written:**

- "First Urdu diffusion model" *without* the "to our knowledge" hedge and a stated search date.
- Any claim that a fair FIM-matched AR-vs-diffusion comparison is itself novel — MARIA is prior art.
- Any claim that Urdu is *naturally* data-constrained at 70M parameters (§4).

### 8.2 The design problem, stated plainly

Findings A and B are the same problem seen twice. The PRD picked a model size at which (a) Urdu is
not data-constrained, and therefore (b) the unique-data budget that makes the crossover reachable
must be chosen artificially anyway. Since U is free and only *run count* costs money, the design
can be fixed at **zero additional compute**.

### 8.3 Options

| Option | Design | Reaches crossover? | Cost vs PRD |
|---|---|---|---|
| **0. Unchanged** | U = 300M, 33 epochs | No (0.01×) | Baseline |
| **1. Retarget U** | U = 25M, ~400 epochs, 3 seeds | Yes (1.78×) | Same — 6 core runs |
| **2. Two-point law** | U ∈ {25M, 100M}; 3 seeds at 25M, 1 seed at 100M | Yes at 25M; brackets it at 100M | 8 core runs vs 6 |
| **3. Scale model up** | ~300M params so Urdu is genuinely constrained | Yes | Far over the $150 cap |

**Recommendation: Option 2.** It preserves the PRD's 3-seed statistical protocol on the primary
endpoint, brackets the crossover from both sides so the *location* can be compared against the
English fit rather than just its sign, and costs two extra runs rather than more GPU-hours per run.
Option 3 is out of budget. Option 0 is predicted to be null before it starts.

Under Option 2 the research question sharpens from "does diffusion win for Urdu" to:

> **Does the data-constrained crossover between masked diffusion and autoregression occur where the
> English scaling law predicts, when the corpus is naturally noisy non-English Nastaliq-script web
> text rather than clean C4?**

That question is answerable on $150, is not answerable from the existing literature, and — unlike
Option 0 — has an informative outcome whichever way it resolves. It also keeps PRD §12's central
defence intact: the endpoint is the *curve*, not the winner.

### 8.4 Knock-on edits required if the design changes

- §1 research question — restate as above; drop "naturally data-constrained" as a premise.
- §4.3 — replace "epoch 33 is deep into the regime where the diffusion advantage is predicted to
  appear"; it is not.
- §4.5 — the preregistered primary endpoint must name the U values and the predicted C_crit *before*
  Stage C, so the prediction is falsifiable.
- §6.1 — corpus target changes; record the 5–6B-token availability figure as the §6.1 "could have
  collected" number.
- §6.2 — reconsider UrduLM as a source and as tokenizer-fertility prior art.
- §4.2 — reconsider the 10% infilling share against FIM practice of 50–90%.
- §11 — G4's "no signal by epoch 16" needs restating in epochs appropriate to a ~400-epoch sweep.

---

## 9. Bibliography

- Prabhudesai, M., Wu, M., Zadeh, A., Fragkiadaki, K., Pathak, D. (2025). *Diffusion Beats
  Autoregressive in Data-Constrained Settings.* arXiv:2507.15857. Code:
  https://github.com/wmn-231314/diffusion-data-constraint · https://diffusion-scaling.github.io/
- Sahoo, S. S., et al. (2024). *Simple and Effective Masked Diffusion Language Models.* NeurIPS
  2024. arXiv:2406.07524. Code: https://github.com/kuleshov-group/mdlm
- Lou, A., Meng, C., Ermon, S. (2024). *Discrete Diffusion Modeling by Estimating the Ratios of the
  Data Distribution (SEDD).*
- Austin, J., et al. (2021). *Structured Denoising Diffusion Models in Discrete State-Spaces
  (D3PM).*
- Nie, S., et al. (2025). *Large Language Diffusion Models (LLaDA).*
- *Enabling Autoregressive Models to Fill In Masked Tokens (MARIA).* arXiv:2502.06901.
- Bavarian, M., et al. (2022). *Efficient Training of Language Models to Fill in the Middle.*
- *UrduLM: A Resource-Efficient Monolingual Urdu Language Model.* arXiv:2601.17664.
- *Alif: Advancing Urdu Large Language Models via Multilingual Synthetic Data Distillation.*
  arXiv:2510.09051.
- *XDLM: Cross-lingual Diffusion Language Model for Machine Translation.* arXiv:2307.13560.
- FineWeb2. https://huggingface.co/datasets/HuggingFaceFW/fineweb-2

---

## 10. Open items

| # | Item | Blocking? |
|---|---|---|
| 1 | Verify `C_crit` equation and both `R_D*` values against the typeset PDF of arXiv:2507.15857 | Yes — §3 rests on it |
| 2 | Read OpenReview `W5Ht05jF4c` for reviewer critique of the scaling-law fit | Yes — same |
| 3 | Confirm UrduLM corpus licence and availability (NC would conflict with PRD §6.3) | Before corpus freeze |
| 4 | Confirm FineWeb2 `urd_Arab` token count — not published per-language; must be measured | Week 3 |
| 5 | Search Urdu-language and regional venues (CLE Lahore, LREC regional) not indexed here | Before publication |
| 6 | Attribute or drop the TinyStories AR-vs-MDLM comparison in §6 | Before publication |
