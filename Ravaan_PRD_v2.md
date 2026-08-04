# Ravaan v2: Does Masked Diffusion Pay Off for a Genuinely Low-Resource Language?

**Version:** 2.2
**Status:** Amended 2026-08-05 during the Weeks 3–4 corpus build, after stage 9 found §6.1 and §4.3 describing different corpora (Finding R). See §0.2. Previously amended 2026-08-03 after the Week 1 literature review (Gate G0 — passed); see §0.1.
**Supersedes:** v2.1 (August 3, 2026); v2.0 (August 3, 2026); v1.1 (August 2, 2026)
**Project type:** Open-source NLP research and portfolio project
**Development model:** Solo, part-time, rented spot GPUs
**Hard compute cap:** USD 150
**Target duration:** 16 weeks

---

## 0. What changed from v1.1, and why

| Area | v1.1 | v2.0 | Reason |
|---|---|---|---|
| Headline models | 3 (AR, vanilla MDLM, script-aware MDLM) | **2** (AR, DIFF) trained on identical tasks | v1's AR baseline never saw infilling or the corruption tasks, so any win was guaranteed by construction, not by architecture |
| Final model | ~205M params, 2–3B tokens | **~70M params, ~300M unique tokens × ~33 epochs** | 205M × 3B is ≈15 tokens/param — near Chinchilla-optimal, the exact regime where AR is expected to win. The diffusion hypothesis lives past the crossover, which requires many epochs over few tokens |
| Vocab | 32,768 | **16,384** | At 70M params, a 32k embedding table burns a third of the budget |
| Epoch sweep | Separate ablation line item ($150–400) | **Free — checkpoints inside one run** | Epochs 1/2/4/8/16/33 are evaluation points, not separate runs |
| Data sources | 8 | **3** (FineWeb2, Roman-Urdu-Parl, Urdu Wikipedia) | CulturaX/OSCAR/ROOTS/Makhzan/UrduLM/Bactrian-X each cost weeks and add little |
| Human benchmark | 5,000–10,000 examples | **400 paired A/B judgments** | 5–10k was unfunded and would have been silently dropped at month six |
| Frontend | "Ravaan Studio" (RTL editor, diffing, side-by-side, export) | **One HF Space with a denoising-step slider** | 4–6 weeks of frontend work that adds nothing to the research claim |
| Serving | REST API + WebSocket streaming | Cut | Same |
| Ablations | 7 required + 7 optional | **4** (2 need training, 2 are inference-only) | |
| Checkpoints | Open / Research / Experimental | **One permissive checkpoint** | With the NC-licensed sources dropped, the three-way split has nothing to separate |
| Statistics | "statistically significant" (unspecified) | **3 seeds, preregistered primary endpoint, Holm correction, paired bootstrap CIs** | v1 had no seeds, no n, no correction across six task comparisons |
| Timeline | None | **16 weeks with dated gates and kill criteria** | v1 costed GPU to the dollar and never estimated a single hour of human time |

---

## 0.1 What changed in v2.1, and why

The Week 1 literature review (`reports/literature_review.md`) passed Gate G0 on novelty but produced two findings that invalidated part of the v2.0 design. Both were verified against the typeset source paper on 2026-08-03.

| Area | v2.0 | v2.1 | Reason |
|---|---|---|---|
| Unique corpus U | 300M tokens, 33 epochs | **U ∈ {25M, 100M}**; ~396 and ~99 epochs | At 70M params, U = 300M sits **124× below** the compute at which the reference paper's own fitted law predicts a crossover. v2.0's headline experiment returned "no crossover" *predictably* — a null by construction. U costs nothing (compute = params × tokens processed), so this is fixed at zero extra GPU spend |
| Framing | Urdu is *naturally* data-constrained, unlike artificially subsampled English | **Does the English scaling law transfer to noisy non-English text?** | UrduLM (arXiv:2601.17664) released ~5–6B Urdu tokens. Chinchilla-optimal for 70M params is ~1.4B. Urdu is **not** data-constrained at this scale, so the v2.0 contrast does not hold |
| Core runs | 6 (2 models × 3 seeds) | **8** (3 seeds at U=25M, 1 seed at U=100M, both models) | Bracketing the crossover lets the *location* be tested, not just the sign. Same GPU-hours per run |
| §4.1 novelty claim | Implicit: FIM-matched comparison is the contribution | **Explicitly not novel** — MARIA (arXiv:2502.06901) is prior art | Must be cited. A2's argument is weaker without it |
| Preregistration | Named in §4.5, unwritten | **Written and committed** — `reports/preregistration.md` | Committed 2026-08-03, before any training |

**Unchanged:** the matched pair (§4.1), task mixture shares (§4.2, but see the open question on infilling share), model specification (§5), tokenizer (§7), evaluation (§8), the $150 cap (§9), and the definition of done (§14).

---

## 0.2 What changed in v2.2, and why

Building stage 9 (split creation) required deciding which documents constitute an arm, and that exposed a contradiction between two sections written at different times: **§6.1 and §4.3 did not describe the same corpus.** Nothing in the experimental design changes — v2.2 is a documentation correction to a load-bearing number, made before the corpus freeze rather than after. The full argument and its arithmetic are in `reports/splits.md` §1.

| Area | v2.1 | v2.2 | Reason |
|---|---|---|---|
| What **U** counts | Undefined. §6.1's per-component targets invited "U = the clean native Urdu component"; §4.3 assumed "U = the whole training set" | **U is an arm's total unique-token budget, summed across all three populations** | §4.3's own epoch arithmetic settles it: 396 × 25M = 9.9B and 99 × 100M = 9.9B, so epochs are counted over the whole training set — as they are in Prabhudesai et al.'s fitted law, where U *is* the set the model repeats over. Arm B's stated 0.09× of C_crit is only reproducible under this reading |
| §6.1's component table | Read as arm budgets | **Pool targets** — how much to collect — with the arm budgets stated separately | Under the other reading arm A is 25M + 40M + 10M = 75M unique tokens for 132 epochs, which is **6× short** of C_crit instead of 1.79× past it. That is Finding A's error a second time, on the arm carrying the primary endpoint. Reproduce both with `scripts/crossover.py` |
| Arm composition | Unstated | **Fixed population mixture, 120 : 40 : 10** — §6.1's targets in proportion. Arm B = 70.59M native + 23.53M Roman + 5.88M code-switched; arm A is a quarter of each | §4.1 requires the arms to differ in size and nothing else. Once there is more than one population that has no other meaning: scaling only the native component would confound U with source mix, the same failure §6.1 already forbids for crawl date |
| §6.1 headroom claim | "100M for arm B + ~20% headroom" | Pools total ~170M against arm B's 100M, so **every component carries 1.70× headroom** | Arm B's native share is 70.59M, not 100M. The ~120M native target was never 1.2× of anything |
| **G1** (§11) | Aggregate clean-token count only | Aggregate **and** per-population sufficiency at the arm mixture | The binding constraint is not the total. Code-switched supply currently measures ~0.97× of arm B's 5.88M while the aggregate sits at 15× margin, so G1 as written could pass on a corpus from which arm B cannot be assembled |
| Held-out eval (§6.1, §8.2) | One decontaminated split, ~5K sequences | **Two** — validation and test, ~5K sequences each, carved at the arm mixture | G4 (§11) reads arm A's validation curves at mid-W10 and may cut arm B on what it sees. That is a decision taken on validation data, so §8.2's reported held-out number cannot come from the same set. Costs 5K sequences from a pool with 15× margin. Carving both at the arm mixture is required because §8.3 reports validation BPB *by script*: a held-out mixture differing from the training mixture would make aggregate BPB move with the mixture rather than with the model |

**Unchanged:** every number in §4.3, §4.5, §5, §9 and §12. Stage 9 was built to the corrected reading before this amendment was written, so no code changes either — `reports/splits.md` and `ravaan/data/splits.py` already implement it.

---

## 1. Research question

**Primary.** Does the data-constrained crossover between masked diffusion and autoregression occur where the English scaling law predicts, when the training corpus is naturally noisy non-English Nastaliq-script web text rather than clean C4?

The motivating claim from the literature is that masked diffusion outperforms AR when compute is abundant but unique data is scarce, because random-order factorization acts as implicit data augmentation. Prabhudesai et al. (arXiv:2507.15857) measured this on English C4 at U ∈ {25, 50, 100}M and fitted a critical-compute threshold `log10(U) = 0.460·log10(C) − 1.050`.

Urdu corpora are noisier, more duplicated, and more domain-skewed than a C4 subsample, and the script, morphology and tokenizer fertility all differ. Whether a law fitted on clean English holds on that material is open. **Both Ravaan arms sit inside the reference paper's fitted range of U**, so no claim here depends on extrapolating their law.

> **Corrected in v2.1.** v2.0 argued Urdu is *naturally* data-constrained while English was *artificially* subsampled. That contrast does not survive: ~5–6B Urdu tokens are collectable and a 70M model can use ~1.4B. Ravaan subsamples deliberately, exactly as the English study did. This is stated plainly rather than defended — see `literature_review.md` §4.

**Secondary.** Does adding script-aware corruption training (transliteration, OCR restoration, spacing repair, code-switch normalization) help both parameterizations equally, or does one absorb it better?

**Explicitly not the question.** Whether Ravaan is a good Urdu chat model. It will not be one.

---

## 2. Deliverables

1. **Ravaan-DIFF** — masked diffusion LM, ~70M params, released checkpoint
2. **Ravaan-AR** — compute-matched autoregressive baseline, released checkpoint
3. **The epoch-crossover curve** — validation bits-per-byte vs. compute for both models at U ∈ {25M, 100M}; 3 seeds in arm A, 1 in arm B
4. **Urdu corpus pipeline** — code, manifest, checksums, statistics (no raw text redistribution)
5. **Urdu SentencePiece tokenizer** — 16k, with a fertility benchmark across native/Roman/mixed script
6. **Evaluation suite** — including a hand-corrected real-OCR test set and a human-written transliteration set
7. **HF Space demo** — text box, mask spans, denoising-step slider, step-by-step replay
8. **Technical report** — with negative results and failure cases

---

## 3. Non-goals

Unchanged from v1, plus: no billion-parameter model, no production API, no RTL editor, no instruction tuning, no chat interface, no claim to be the first Urdu diffusion model until the Week 1–2 literature review says so in writing.

---

## 4. Experimental design

This section is the project. Everything else is scaffolding to make it credible.

### 4.1 The matched pair

Both models share: the same corpus, the same tokenizer, the same parameter count (within 2%), the same context length, the same optimizer and schedule, the same number of tokens processed, the same seeds, and **the same training tasks**.

They differ in exactly one thing: the factorization.

| | Ravaan-AR | Ravaan-DIFF |
|---|---|---|
| Attention | Causal | Bidirectional |
| Objective | Next-token prediction | Masked diffusion (MDLM-style, time-agnostic) |
| Plain text | Standard LM | Random-ratio masking, loss on masked positions |
| Infilling | **FIM** — prefix/suffix/middle reordering | Mask the middle span |
| Transliteration | `<src> <sep> <tgt>` sequence, loss on target | Condition on unmasked source, diffuse the target |
| Restoration / code-switch | Same seq2seq framing | Same conditional framing |

The FIM row is the fix for v1's central flaw. AR models have done infilling since 2022; comparing a diffusion model trained on infilling against an AR model that was not is not an architecture result.

Use **time-agnostic MDLM** (no timestep embedding) rather than DiT-style adaLN conditioning. It keeps parameter counts exactly matched and is simpler to get right.

### 4.2 Task mixture (identical for both models)

| Objective | Share |
|---|---|
| Plain-text denoising / LM | 65% |
| Span infilling | 10% |
| Roman ↔ native transliteration | 10% |
| OCR and spacing restoration | 8% |
| Code-switch normalization | 7% |

Corruptions are generated dynamically at training time from clean text, with the generator version and seed recorded. These shares are a hypothesis, frozen before Stage C and not tuned afterwards.

### 4.3 The epoch sweep

Two arms, both processing ~9.9B tokens, differing only in how much unique data those tokens are drawn from:

| Arm | Unique U | Epochs | Seeds | Predicted position |
|---|---|---|---|---|
| **A** (primary) | 25M | ~396 | 3 | **1.79× past** C_crit = 2.32 × 10¹⁸ FLOPs |
| **B** (bracket) | 100M | ~99 | 1 | **0.09× of** C_crit = 4.72 × 10¹⁹ FLOPs |

**U is the arm's *total* unique-token budget** — native Urdu, Roman Urdu and code-switched text summed — not any one component. That is what the epoch counts above divide 9.9B by, and it is what U means in the fitted law: the training set the model repeats over. §6.1 gives the composition. *(Stated explicitly in v2.2; see §0.2.)*

Checkpoint at **1, 2, 5, 10, 25, 50, 100% of tokens processed** — identical fractions for both models and both arms, so the curves share a compute x-axis. Evaluate every checkpoint.

This is the primary experiment and it costs one run per model per arm per seed (8 total). Arm A is predicted to *cross*; arm B is predicted *not* to. The paired outcome is the result: it tests the crossover's **location** against the English fit, not merely its sign.

> **Corrected in v2.1.** v2.0 fixed U ≈ 300M and asserted "epoch 33 is deep into the regime where the diffusion advantage is predicted to appear." Against the reference paper's own fitted law that is wrong by two orders of magnitude — U = 300M at 70M params for 33 epochs is **124× below** C_crit and would need ~4,080 epochs. The authors corroborate this themselves: at U = 500M they required a 2.3B-parameter model and saw no convergence at 130 epochs. Reproduce with `scripts/crossover.py`.

**Why this costs nothing.** Compute is parameters × tokens processed. How much *unique* data those tokens are drawn from is free. Only the number of runs changed (6 → 8).

**Methodological note that must appear in the report:** the diffusion objective yields an *upper bound* (ELBO) on likelihood, not exact NLL. Comparing a diffusion ELBO against exact AR NLL is conservative — it disadvantages diffusion. Report both, state the bound explicitly, and treat downstream task metrics (which are directly comparable) as the tiebreaker.

Report **bits-per-byte**, not bits-per-token, so the comparison is tokenizer-independent.

### 4.4 Ablations

| # | Ablation | Cost |
|---|---|---|
| A1 | DIFF without script-aware corruptions | 1 training run |
| A2 | AR without FIM — i.e. v1's original baseline | 1 training run |
| A3 | Denoising steps: 8 / 16 / 32 / 64 | Inference only |
| A4 | Unmasking schedule: random vs. confidence-based | Inference only |

A2 is included deliberately. Running the broken baseline alongside the fair one lets you quantify exactly how much the unfair comparison would have inflated the result — which is a more interesting paragraph than the result itself.

**Prior art, and a scope correction.** The FIM-matched comparison in §4.1 is *methodologically necessary but not novel*. MARIA (arXiv:2502.06901) already reports that a properly-equipped AR model outperforms discrete diffusion baselines at infilling across all mask rates. It must be cited, and A2 must be framed as quantifying the inflation on **Urdu**, not as discovering that the unfair baseline inflates results.

### 4.5 Statistical protocol

- **3 seeds** per core config (AR, DIFF) in **arm A**; 1 seed in arm B, reported as directional. Ablations get 1 seed and are reported as directional.
- **Primary endpoint, preregistered:** the sign and compute-location of the AR/DIFF crossover in validation BPB across arm A's sweep. **Committed 2026-08-03 in `reports/preregistration.md`, before any training** — including four falsifiable predictions (P1–P4) and a committed reading for every outcome combination.
- **Secondary endpoints (3, Holm-corrected):** transliteration chrF on the human-written set, infill exact-match, OCR CER reduction on the real-OCR set.
- Paired bootstrap confidence intervals on all task metrics. If a CI includes zero, say so in the abstract.
- No metric is added to the results table after seeing results.

---

## 5. Model specification

| Property | Value |
|---|---|
| Parameters | ~70M (≈59.5M non-embedding) |
| Layers | 12 |
| Hidden dimension | 640 |
| Heads | 10 (head dim 64) |
| FFN (SwiGLU) | 1,728 |
| Context length | 512 |
| Vocabulary | 16,384, tied embeddings |
| Positional encoding | RoPE |
| Normalization | RMSNorm |
| Precision | BF16 |
| Attention | PyTorch SDPA |

Exact parameter counts must be computed programmatically and asserted equal within 2% across configs in CI.

**Fallback ladder if the corpus comes in small:** 70M → 40M (10 layers, d=512) → 25M (8 layers, d=384). Shrink the model, never the epoch count — the epoch count is the experiment.

---

## 6. Corpus

### 6.1 Targets

**Pool targets — how much to collect.** These are not arm budgets; see the next table.

| Component | Pool target |
|---|---|
| Clean native Urdu | **~120M unique tokens** |
| Roman Urdu | ~40M tokens |
| Code-switched | ~10M tokens |
| **Pool total** | **~170M unique tokens** |
| Parallel script pairs | ~500K deduplicated pairs |
| Held-out eval | ~5K sequences each for validation and test, decontaminated |

**Arm budgets — how much to train on.** An arm's U (§4.3) is its *total* across the three populations, drawn from the pools at a **fixed mixture: the pool targets in proportion, 120 : 40 : 10.**

| Population | Share | Arm A (U = 25M) | Arm B (U = 100M) | Pool | Headroom |
|---|---|---|---|---|---|
| Native Urdu | 70.59% | 17.65M | **70.59M** | ~120M | 1.70× |
| Roman Urdu | 23.53% | 5.88M | **23.53M** | ~40M | 1.70× |
| Code-switched | 5.88% | 1.47M | **5.88M** | ~10M | 1.70× |
| **Total (U)** | 100% | **25M** | **100M** | ~170M | 1.70× |

Holding the mixture fixed across arms is what §4.1's "differ in size and nothing else" means once there is more than one population. Scaling only the native component would confound U with source mix — the same failure this section already forbids for crawl date.

Arm A's 25M-token corpus is a **deterministic, seeded subsample** of arm B's 100M — not a separate collection. Stage 9 makes this structural rather than maintained: a document's split and arm are one integer, a keyed hash of its id, and arm A is a *prefix* of arm B's bucket range, so the containment cannot be violated by a later pass. The plan is checksummed and committed.

**How much clean data could we have collected?** ~5–6B tokens. UrduLM (arXiv:2601.17664, Jan 2026) curated and released 33 GB / ~5–6B tokens of Urdu. **Capping is therefore a deliberate design decision, not a limitation**, and the report must say so in exactly those terms. v2.0 asked this question; v2.1 records the answer. (Qualification recorded in `configs/data/sources.json`: the 33 GB artifact is not actually public, and of what is described, 5.5 GB is machine-translated English and 19.4 GB is CommonCrawl overlapping our own primary source. The conclusion survives the discount; the report must quote the number with the caveat rather than flat.)

> **Corrected in v2.1.** Native target reduced from ~300M to ~120M. See §0.1 and §4.3 — at U = 300M the primary experiment cannot reach the crossover it exists to measure. This shortens Weeks 3–4.

> **Corrected in v2.2.** v2.1's component table read as arm budgets, and its native line said "100M for arm B + ~20% headroom for filtering losses". Both are wrong. Arm B's native share is **70.59M**, the pools total ~170M against its U of 100M, and the headroom is **1.70×** on every component. Taken at face value, the old wording made arm A a 75M-token / 132-epoch run sitting **6× short** of the crossover it exists to measure, instead of 1.79× past it — Finding A's error a second time, on the arm carrying the primary endpoint. See §0.2 and `reports/splits.md` §1; reproduce with `python scripts/crossover.py --params 70e6 --unique 75e6 --epochs 132`.

### 6.2 Sources

| Source | License | Role |
|---|---|---|
| FineWeb2 `urd_Arab` | ODC-By 1.0 | Primary native Urdu |
| Roman-Urdu-Parl | Apache 2.0 | Parallel script pairs |
| Urdu Wikipedia | CC BY-SA | Clean supplementary + eval |

**Dropped from v1:** CulturaX, OSCAR, ROOTS, Makhzan, UrduLM, Bactrian-X.

**Warning carried forward.** Roman-Urdu-Parl is substantially machine-produced — the source work crawled Urdu sentences and passed them through an automatic transliteration portal, with crowdsourcing added for spelling variation. Its ~6.37M pairs collapse to roughly 1.09M unique Urdu sentences. Two consequences: (a) dedup the native side hard before mixing it into pretraining, and (b) any transliteration claim evaluated only on this corpus means "matches that transliterator," not "transliterates well." The human-written test set in §8.2 exists solely to close this gap.

### 6.3 Pipeline

Ten stages, down from twenty:

1. Acquisition + checksums
2. Encoding validation
3. Language and script identification (document level; sentence level only for mixed docs)
4. Urdu normalization — Arabic/Persian Yeh and Kaf variants, presentation forms, tatweel, zero-width characters, directionality marks, digit variants. Preserve original text, normalized text, and a transformation log. **Never apply NFKC blindly.**
5. Quality filtering — Urdu-script ratio, repetition, URL density, HTML residue, replacement-character frequency. Rules validated against 200 manually inspected random samples.
6. Exact deduplication (raw and normalized hashes, document and paragraph level)
7. MinHash near-deduplication
8. Evaluation decontamination (hash + fuzzy match against all test sets)
9. Split creation
10. Tokenization and sequence packing

Minimal PII handling: one regex pass for phone numbers and emails. Do not build a PII system.

**Release policy:** code, manifest, checksums, and statistics only. No raw text redistribution. One permissive checkpoint.

---

## 7. Tokenizer

SentencePiece Unigram, 16,384, byte fallback, minimal destructive normalization, stable offset mappings.

Benchmark on a fixed suite (clean native, informal native, Roman, mixed-script, numerals, names, URLs, OCR-corrupted, literary): report tokens-per-word by script, byte-fallback rate, compression ratio, and 95th-percentile sequence length.

**Timeboxed to one week.** Pick, freeze, checksum, move on. The same tokenizer serves every model in the comparison — this is non-negotiable for the design.

---

## 8. Evaluation

### 8.1 Engineering invariants — CI, not results

These are unit tests and never appear in a results table: valid UTF-8 output, locked-token preservation, checkpoint resumability, bit-identical determinism under fixed seed, parameter-count parity across configs.

v1 listed the first two as success metrics at 100%. Locked-token preservation at 100% is an architectural invariant — you simply don't unmask those positions — and valid UTF-8 follows from byte fallback. Reporting them as results is measuring the thermometer.

### 8.2 Test sets

| Set | Size | Construction |
|---|---|---|
| Held-out native Urdu | 5K sequences | Decontaminated **test** split — see §6.1. The separate 5K validation split is what G4 and the §8.3 curves read; the number reported here comes only from the test split |
| Transliteration (reference) | Official split | Roman-Urdu-Parl test |
| **Transliteration (human)** | ~200 pairs | Hand-written by native speakers — the only set that can support a real transliteration claim |
| **Real OCR** | ~300 lines | Tesseract Urdu over scanned public-domain Nastaliq, gold hand-corrected (~8 hours of work) |
| Infilling | 500 items | Random spans masked from held-out text |

The real-OCR set is mandatory. Training on synthetic OCR noise and testing on synthetic OCR noise measures only whether the model learned your own noise generator.

### 8.3 Automatic metrics

Validation BPB by epoch and by script; transliteration CER/WER/chrF with named-entity and number preservation; restoration CER reduction, punctuation F1, whitespace F1, hallucinated-token rate; infill exact-match and token-F1 with locked-span preservation; generation script consistency, distinct-n, repetition rate.

### 8.4 Human evaluation

**400 paired A/B judgments**, model identities hidden, 3 fluent Urdu speakers, covering transliteration, infilling, restoration, and open generation. Roughly two hours per annotator — a favour-sized ask, not a funded task. Report Fleiss' kappa; if agreement is poor, report that instead of the preference score.

---

## 9. Compute and budget

| Item | GPU-hours | Cost |
|---|---|---|
| Debug and tiny pilots | Kaggle free tier | $0 |
| Throughput tuning | 20 | $7 |
| 8 core runs (arm A: 2 models × 3 seeds; arm B: 2 models × 1 seed) | 187 | $66 |
| 2 ablation runs (A1, A2) | 45 | $16 |
| Evaluation sampling | 25 | $9 |
| Failed runs and restarts | 60 | $21 |
| Storage | — | $15 |
| **Total** | **~337** | **~$134** |

Per-run cost is unchanged from v2.0 — every run processes the same ~9.9B tokens. Only the run count rose, 6 → 8, funded by trimming the failed-run contingency from 80 to 60 GPU-hours. **If that contingency proves tight, drop arm B's seed to a shared-seed pair or cut ablation A1 — never cut arm A's 3 seeds**, which carry the primary endpoint.

**Hard cap: $150.** Assumes RTX 4090-class spot instances at ~$0.35/hr. Verify against live marketplace pricing in Week 6 before committing.

Cost controls: provider spending limit set on day one; every configuration validated on Kaggle before it touches a paid instance; checkpoint every 500 steps with resume tested before any paid run (spot instances get preempted); cost recorded per experiment; no hyperparameter sweeps.

---

## 10. Schedule

Roughly 250–320 person-hours across 16 weeks, or about 16–20 hrs/week.

| Weeks | Work | Output |
|---|---|---|
| 1–2 | Literature review; corpus acquisition; language/script ID | ✅ Lit review + **preregistration** committed W1; raw corpus on disk |
| 3–4 | Normalization, dedup, quality filter, decontamination | **Frozen corpus v1** (~170M-token pool, §6.1) + arm B's 100M and arm A's seeded 25M + manifest + statistics |
| 5 | Tokenizer training and benchmark | **Frozen tokenizer** + checksum |
| 6–7 | Shared backbone, AR head, MDLM objective, tiny-model validation, throughput measurement | **Gate 1** |
| 8 | Pilot runs at 20M params, all 4 configs, 1 seed | **Gate 2** |
| 9–11 | 6 core runs + 2 ablation runs | **Gate 3** at midpoint |
| 12 | Build test sets incl. real-OCR; run automatic evaluation | Results tables |
| 13 | Human evaluation | Preference scores + kappa |
| 14 | HF Space demo | Public demo |
| 15–16 | Technical report, repo cleanup, release | **Ship** |

**If only ~10 hrs/week are available:** this becomes 6–7 months. The minimum viable cut, in order of what to drop: HF Space → human evaluation → ablations A1/A2 → seeds 2 and 3. The epoch sweep on a single seed for both models is the irreducible core; below that there is no project.

---

## 11. Gates and kill criteria

Every gate below can actually fail. v1's Gate D ("script-aware improves at least one primary task") could not — with six tasks and no multiple-comparison correction, something always improves by chance.

| Gate | When | Proceed if | Kill / fallback |
|---|---|---|---|
| **G0** | End W2 | Literature review confirms the comparison is unpublished | Reframe or stop |
| **G1** | End W4 | Clean corpus ≥ **100M** tokens **and** every population at or above arm B's share of it (§6.1: 70.59M / 23.53M / 5.88M) | 25–100M → run arm A only, report single-arm. Below 25M → stop. **A population short at the mixture is its own failure** — the aggregate can clear 100M several times over while arm B cannot be assembled |
| **G2** | End W7 | Measured throughput implies 8 core runs ≤ $90 | Shrink model, never epoch count |
| **G3** | End W8 | 20M pilot DIFF produces coherent Urdu after 50 epochs; both models resume from checkpoint correctly | Implementation bug — debug, do not scale |
| **G4** | Mid W10 | Arm A curves are separating or converging in a legible way **by 50% of tokens processed** | No signal by then → complete arm A's 3 seeds, cut arm B, report the flat result as the primary finding per preregistration §7 |
| **G5** | W13 hard date | Automatic results are in hand | Cut human eval and demo, ship the report |

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| No crossover appears within budget | The primary endpoint is the *curve*, not the winner. Because arm A is placed **1.79× past** the predicted C_crit, "no crossover where the English law predicts one" is now a genuine falsification of transfer — a publishable, citable result. **This defence did not hold in v2.0**, where the design sat 124× short and the English law itself already predicted no crossover; confirming that would have been no finding at all |
| Roman-Urdu-Parl is machine-generated | Human-written test set; scope the claim explicitly if it disagrees with the reference set |
| Seed variance swamps the effect | 3 seeds, paired bootstrap CIs, report intervals not point estimates |
| Diffusion ELBO vs. AR exact NLL not directly comparable | Report both, state the bound, lead with downstream metrics |
| Corpus smaller than expected after filtering | Model-size ladder in §5 |
| Spot instance preemption | Checkpoint every 500 steps; resume tested before any paid run |
| Annotators unavailable or disagree | Kappa reported honestly; automatic metrics carry the paper if human eval fails |
| Scope creep back toward v1 | Anything not in §2 requires deleting something else from §2 |

---

## 13. Repository

```
ravaan/
├── README.md
├── LICENSE
├── pyproject.toml
├── configs/           # data, tokenizer, model, training, sampling, eval
├── ravaan/
│   ├── data/          # acquisition, normalization, langid, dedup, quality, corruption, packing
│   ├── tokenization/
│   ├── models/        # common backbone, ar/, diffusion/
│   ├── training/
│   ├── sampling/
│   └── evaluation/
├── tests/             # engineering invariants from §8.1
├── scripts/
├── demo/              # HF Space
└── reports/
    ├── preregistration.md   # committed before Stage C, timestamped
    ├── literature_review.md
    └── technical_report.md
```

---

## 14. Definition of done

**Ship criteria** — all must hold:

- Both models trained from random initialization on identical data, tasks, and compute
- Epoch sweep complete: 3 seeds per model in arm A (U=25M), 1 seed per model in arm B (U=100M)
- Preregistration committed before results were seen, and honoured
- Real-OCR and human-written transliteration test sets built and used
- Human evaluation completed or its absence explained
- All §8.1 invariants passing in CI
- Total spend under $150, with per-experiment costs recorded
- Technical report includes negative results, failure examples, and the A2 comparison showing what the unfair baseline would have claimed

**Explicitly not a ship criterion:** that Ravaan-DIFF wins.

The project succeeds if the comparison is fair and the result is reported honestly. A clean negative result on whether diffusion transfers to naturally low-resource languages is a better artifact than an inflated positive one, and it is the version that survives someone reading the methods section.
