# Ravaan v2: Does Masked Diffusion Pay Off for a Genuinely Low-Resource Language?

**Version:** 2.0
**Status:** Proposed
**Supersedes:** v1.1 (August 2, 2026)
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

## 1. Research question

**Primary.** Holding unique data and training tasks fixed, at what compute budget — if ever — does a masked diffusion parameterization overtake an autoregressive one for Urdu, and does that crossover sit where the English result predicts?

The motivating claim from the literature is that masked diffusion outperforms AR when compute is abundant but unique data is scarce, because random-order factorization acts as implicit data augmentation. That result was measured on *artificially subsampled* English. Urdu is *naturally* data-constrained, and its corpora are noisier, more duplicated, and more domain-skewed than a C4 subsample. Whether the finding survives contact with a real low-resource language is open.

**Secondary.** Does adding script-aware corruption training (transliteration, OCR restoration, spacing repair, code-switch normalization) help both parameterizations equally, or does one absorb it better?

**Explicitly not the question.** Whether Ravaan is a good Urdu chat model. It will not be one.

---

## 2. Deliverables

1. **Ravaan-DIFF** — masked diffusion LM, ~70M params, released checkpoint
2. **Ravaan-AR** — compute-matched autoregressive baseline, released checkpoint
3. **The epoch-crossover curve** — validation bits-per-byte vs. epochs for both, 3 seeds each
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

Fix a unique corpus **U ≈ 300M tokens**. Train each model to ~33 epochs (~10B tokens processed). Checkpoint at epochs **1, 2, 4, 8, 16, 33** and evaluate every checkpoint.

This is the primary experiment and it costs one run per model per seed. Epoch 1 sits near the Chinchilla-optimal point where AR is expected to lead; epoch 33 is deep into the regime where the diffusion advantage is predicted to appear. The question is whether the curves cross, and where.

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

### 4.5 Statistical protocol

- **3 seeds** per core config (AR, DIFF). Ablations get 1 seed and are reported as directional.
- **Primary endpoint, preregistered:** the sign and location of the AR/DIFF crossover in validation BPB across the epoch sweep. Committed to the repo with a timestamp before Stage C begins.
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

| Component | Target |
|---|---|
| Clean native Urdu | ~300M unique tokens |
| Roman Urdu | ~40M tokens |
| Code-switched | ~10M tokens |
| Parallel script pairs | ~500K deduplicated pairs |
| Held-out eval | ~5K sequences, decontaminated |

**Record separately how much clean data you *could* have collected.** "We deliberately capped at 300M to sit in the data-constrained regime" is a design decision; "300M was all we could get" is a limitation. The report must be able to tell the reader which.

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
| Held-out native Urdu | 5K sequences | Decontaminated split |
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
| 6 core runs (2 models × 3 seeds) | 140 | $50 |
| 2 ablation runs (A1, A2) | 45 | $16 |
| Evaluation sampling | 25 | $9 |
| Failed runs and restarts | 80 | $28 |
| Storage | — | $15 |
| **Total** | **~310** | **~$125** |

**Hard cap: $150.** Assumes RTX 4090-class spot instances at ~$0.35/hr. Verify against live marketplace pricing in Week 6 before committing.

Cost controls: provider spending limit set on day one; every configuration validated on Kaggle before it touches a paid instance; checkpoint every 500 steps with resume tested before any paid run (spot instances get preempted); cost recorded per experiment; no hyperparameter sweeps.

---

## 10. Schedule

Roughly 250–320 person-hours across 16 weeks, or about 16–20 hrs/week.

| Weeks | Work | Output |
|---|---|---|
| 1–2 | Literature review; corpus acquisition; language/script ID | Lit review settling the novelty question in writing; raw corpus on disk |
| 3–4 | Normalization, dedup, quality filter, decontamination | **Frozen corpus v1** + manifest + statistics |
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
| **G1** | End W4 | Clean corpus ≥ 150M tokens | 50–150M → drop to 40M params. Below 50M → stop |
| **G2** | End W7 | Measured throughput implies core runs ≤ $80 | Shrink model, never epoch count |
| **G3** | End W8 | 20M pilot DIFF produces coherent Urdu after 50 epochs; both models resume from checkpoint correctly | Implementation bug — debug, do not scale |
| **G4** | Mid W10 | Epoch curves are separating or converging in a legible way | No signal by epoch 16 → stop at 3 seeds, report the flat result |
| **G5** | W13 hard date | Automatic results are in hand | Cut human eval and demo, ship the report |

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| No crossover appears within budget | The primary endpoint is the *curve*, not the winner. "No crossover below 33 epochs at 70M params on Urdu" is a publishable, citable result |
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
- Epoch sweep complete at 3 seeds per core config
- Preregistration committed before results were seen, and honoured
- Real-OCR and human-written transliteration test sets built and used
- Human evaluation completed or its absence explained
- All §8.1 invariants passing in CI
- Total spend under $150, with per-experiment costs recorded
- Technical report includes negative results, failure examples, and the A2 comparison showing what the unfair baseline would have claimed

**Explicitly not a ship criterion:** that Ravaan-DIFF wins.

The project succeeds if the comparison is fair and the result is reported honestly. A clean negative result on whether diffusion transfers to naturally low-resource languages is a better artifact than an inflated positive one, and it is the version that survives someone reading the methods section.
