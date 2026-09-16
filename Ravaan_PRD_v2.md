# Ravaan v2: Does Masked Diffusion Pay Off for a Genuinely Low-Resource Language?

**Version:** 2.4
**Status:** Amended 2026-09-16 on a schedule decision: the project ships **two training runs — one AR, one diffusion**. Seeds 2–3 and ablations A1/A2 are dropped. This is §10's own "minimum viable cut", taken deliberately rather than forced by a measurement. See §0.4. Previously amended 2026-09-10 at the corpus freeze (Gate **G1 failed on the `roman_urdu` population**, arm B dropped for a single-arm design; see §0.3), 2026-08-05 (Finding R; see §0.2) and 2026-08-03 after the Week 1 literature review (Gate G0 — passed; see §0.1).
**Supersedes:** v2.3 (September 10, 2026); v2.2 (August 5, 2026); v2.1 (August 3, 2026); v2.0 (August 3, 2026); v1.1 (August 2, 2026)
**Project type:** Open-source NLP research and portfolio project
**Development model:** Solo, part-time, rented spot GPUs
**Hard compute cap:** USD 150
**Target duration:** 16 weeks
**Priority (v2.4):** **time to a reported result.** Where a choice trades breadth against wall-clock, breadth loses. This is a stated priority, not a discovered constraint, and §0.4 records what it costs.

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

## 0.3 What changed in v2.3, and why

**Arm B is dropped. Ravaan is a single-arm study.** This is Gate G1's pre-committed fallback (§11)
taken on the condition v2.2 added to it, and it is forced by a measurement made at the corpus freeze
**before any model was trained**. The preregistration's deviation log records it; its text is
unedited.

The complete stage 6+7 pass over Roman-Urdu-Parl (2026-09-10, unsampled, 1.38 h) removed **82.4% of
its characters** — 465,303,750 in, 81,791,735 out — as 42.3% exact duplicates followed by half the
remainder as near-duplicates. Roman-Urdu-Parl is the *only* source feeding the `roman_urdu`
population; FineWeb2 contributes zero. At §6.1's fixed 120 : 40 : 10 mixture that leaves the
population at **0.44× of arm B's requirement**, so arm B cannot be assembled at any seed count.

| Area | v2.2 | v2.3 | Reason |
|---|---|---|---|
| Arms | **A** (U=25M, 3 seeds) and **B** (U=100M, 1 seed) | **A only** — U=25M, ~396 epochs, 3 seeds | `roman_urdu` supply is 0.44× of arm B's need. §11's fallback names this outcome and this response |
| Core runs | 8 | **6** (2 models × 3 seeds) | Two arm-B runs are unfunded because they are unbuildable, not because of budget |
| What the primary endpoint tests | The crossover's **sign and location**, by bracketing C_crit | The crossover's **sign at one U**, 1.79× past predicted C_crit | The bracket needed two arms. §4.5's primary endpoint was always arm A alone and is unchanged |
| Preregistration | P1–P4 | **P2 withdrawn**, P1/P3/P4 unaffected | P2 is a statement about arm B. It is withdrawn rather than restated; the §3 outcome table collapses to its two arm-A rows |
| Budget | ~$134 | **~$118** | Two fewer core runs, ~47 GPU-hours |

**Why the gate worked.** v2.2 tightened G1 from an aggregate token count to *aggregate **and**
per-population sufficiency at the arm mixture*, on the argument that "the gate as written could pass
on a corpus from which arm B cannot be assembled". That is exactly the corpus that arrived: the
aggregate clears 100M many times over — `urdu` sits at 46.66× — while `roman_urdu` cannot fund arm
B. The condition added in v2.2 is the one that caught it.

**What survives, and it is the load-bearing part.** Arm A sits **1.79× past** the predicted
C_crit = 2.32 × 10¹⁸ FLOPs, and `scripts/crossover.py` puts the predicted crossover at U = 33M for
this compute against arm A's 25M. So §12's central defence is untouched: "no crossover where the
English law predicts one" remains a genuine falsification of transfer rather than a null by
construction. What is lost is the ability to test the crossover's *location* by bracketing it —
the report must claim the sign at one U and must not imply more.

> **A narrower arm B was available and was declined.** The largest arm B this corpus can build is
> U ≈ 40M, which does sit above the 33M pivot. It was rejected because a 25M-vs-40M bracket around
> a 33M pivot is inside the fitted law's own uncertainty, and a bracket that cannot fail is the
> error v2.0 was amended to remove. Recorded here so the option is not rediscovered as an oversight.

**Unchanged:** the matched pair (§4.1), task mixture (§4.2), arm A's specification and epoch count
(§4.3), the primary endpoint and its 3 seeds (§4.5), model specification (§5), corpus targets and
mixture (§6.1), tokenizer (§7), evaluation (§8), the $150 cap (§9), and the definition of done
(§14) except for its arm-B clause.

---

## 0.4 What changed in v2.4, and why

**The project ships two training runs: one AR, one diffusion, one seed each.** Seeds 2 and 3 are
dropped and ablations **A1 and A2** are dropped with them. Unlike v2.1–v2.3, this is **not forced by
a measurement** — the corpus supports the six runs v2.3 planned. It is a schedule decision, taken
with the stated priority of reaching a reported result as fast as possible, and it is exactly the cut
§10 pre-committed to: *"the minimum viable cut, in order of what to drop: HF Space → human evaluation
→ ablations A1/A2 → seeds 2 and 3. The epoch sweep on a single seed for both models is the
irreducible core; below that there is no project."*

| Area | v2.3 | v2.4 | Reason |
|---|---|---|---|
| Core runs | 6 (2 models × 3 seeds) | **2** (2 models × **1 seed**) | Schedule. §10 names seeds 2–3 as the last thing to drop, and this is that cut |
| Ablation **runs** | A1, A2 — 1 training run each | **dropped** | §10's order puts ablations *ahead* of seeds; cutting seeds while keeping these would invert the project's own priority |
| Ablations A3, A4 | inference-only | **unchanged** | They decode the trained diffusion checkpoint and cost no run |
| What the primary endpoint supports | crossover **sign** at one U, seed-averaged | crossover **sign** at one U, **a single paired comparison** | One run per arm carries no estimate of initialization variance |
| Budget | ~$118 | **~$55** | Four fewer training runs |
| Binding constraint | cost | **wall-clock** | $150 against two runs is no longer tight; time is |
| `roman_urdu` Finding AE rows | undecided | **not filtered — rate disclosed** | Filtering is shallow without a native-speaker pass; disclosure is honest and costs no time |
| §6.2's Roman-Urdu-Parl warning | "machine-produced", a *style* mismatch | **a wrong lexicon, rate named** | Finding AE. Open question 6 resolved as its option (b) — the wording amendment is free now the version is bumping anyway |

**What this costs, stated plainly and once.** §4.5's paired bootstrap still runs, but it resamples
**eval items, not seeds**. With one run per arm there is no estimate of seed-to-seed variance, so a
measured AR/DIFF gap in validation BPB **cannot be separated from a single initialization draw**.
The report must present the primary endpoint as *one paired comparison* and must not describe it as
a seed-averaged effect, quote a between-seed interval, or imply the sign was replicated. §10 already
judged this survivable and that judgement — not a new one — is what is being relied on.

**Losing A2 has a consequence worth naming.** §4.4 called it *"a more interesting paragraph than the
result itself"*: it quantified how much the un-equipped AR baseline would have inflated the claim, on
Urdu. Without it the report must cite MARIA (arXiv:2502.06901) for the effect's existence and state
plainly that **Ravaan did not measure it**. §14's ship criterion naming A2 is amended to match, and
Finding AT's concern — that our AR arm may not be properly equipped for infilling — now goes into the
report as a stated limitation rather than a measured quantity.

**Three smaller decisions taken with it, all in the same direction.** (a) **Finding AE's rows are
not filtered** — §6.2 now names the wrong-lexicon rate (2.77% of rows after dedup, inside 23.53% of
arm A's tokens) and the report discloses it instead of the corpus being edited to hide it; filtering
only the eight confirmed words cannot reach the unscreened tail without a native-speaker pass.
(b) **§6.2 and §8.2 gain the wording amendment** that open question 6 offered as its option (b),
since the argument for deferring it was "do not bump the version for wording" and the version is
bumping. (c) **The stage-10 fertility re-verification is skipped** — `pack.py --measure-only
--resolve-plan` would cost a full corpus pass, and stage 10 reports measured fertility as it packs,
so a bad `code_switched` ratio is visible after the fact and re-packable; that population is 5.88% of
the mixture, so a 20% error moves arm A by ~1%.

**The cheapest thing that partly restores the seed argument, if it is ever wanted:** re-run the
*diffusion* arm alone at a second seed, one run, and report the within-arm spread beside the
between-arm gap. It does not make the endpoint seed-averaged, but it bounds the noise the single
comparison is exposed to. Recorded here so it is a known option rather than a rediscovery.

**Open, and due before Week 12.** §10's cut order runs HF Space → human evaluation → ablations →
seeds. Taking the seed cut implies the first two are already gone. They are **not** cut in this
amendment, because that is a separate decision (G5 has a hard date in §11). Until it is taken the
plan is internally inconsistent about its own stated priorities.

**Unchanged, and this is the load-bearing part:** everything that makes the comparison *fair*. The
matched pair (§4.1), the task mixture (§4.2), arm A's U and epoch count (§4.3), both objectives, the
frozen corpus and its decontamination, the tokenizer (§7), the ELBO caveat, the preregistration's
P1/P3/P4, the §8.1 invariants, and the $150 cap (§9). **Cutting seeds reduces what the result can
support; it does not make the comparison unfair.**

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
3. **The epoch-crossover curve** — validation bits-per-byte vs. compute for both models at U = 25M, 3 seeds *(v2.3: arm B dropped, §0.3)*
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

One arm, processing ~9.9B tokens:

| Arm | Unique U | Epochs | Seeds | Predicted position |
|---|---|---|---|---|
| **A** (primary) | 25M | ~396 | **1** *(v2.4: was 3 — §0.4)* | **1.79× past** C_crit = 2.32 × 10¹⁸ FLOPs |
| ~~**B** (bracket)~~ | ~~100M~~ | ~~99~~ | ~~1~~ | **Dropped in v2.3** — `roman_urdu` supply is 0.44× of its requirement. See §0.3 |

At this compute the fitted law puts the crossover at **U = 33M**, so arm A's 25M sits on the side
where a crossover is predicted. Reproduce with `python scripts/crossover.py --params 70e6
--unique 25e6 --epochs 396`.

**U is the arm's *total* unique-token budget** — native Urdu, Roman Urdu and code-switched text summed — not any one component. That is what the epoch counts above divide 9.9B by, and it is what U means in the fitted law: the training set the model repeats over. §6.1 gives the composition. *(Stated explicitly in v2.2; see §0.2.)*

Checkpoint at **1, 2, 5, 10, 25, 50, 100% of tokens processed** — identical fractions for both models and both arms, so the curves share a compute x-axis. Evaluate every checkpoint.

This is the primary experiment and it costs one run per model per seed (**2 total** — v2.4, §0.4;
was 6). Arm A is predicted to *cross*.

> **v2.4: one seed per arm, so this is a single paired comparison.** The checkpoint fractions, the
> token budget, U, the epoch count and both objectives are unchanged — what is gone is replication.
> There is no between-seed interval to quote and no way to show the sign is not one initialization's
> draw. **State this beside the result, not in a limitations paragraph at the end.**

> **v2.3: this tests the sign, not the location.** With both arms it tested the crossover's location
> against the English fit, because a cross in A paired with no cross in B brackets C_crit. Arm B is
> unbuildable from the frozen corpus (§0.3), so the claim available is whether a crossover occurs at
> U = 25M, 1.79× past where the English law predicts one. **The report must not imply the location
> was measured.**

> **Corrected in v2.1.** v2.0 fixed U ≈ 300M and asserted "epoch 33 is deep into the regime where the diffusion advantage is predicted to appear." Against the reference paper's own fitted law that is wrong by two orders of magnitude — U = 300M at 70M params for 33 epochs is **124× below** C_crit and would need ~4,080 epochs. The authors corroborate this themselves: at U = 500M they required a 2.3B-parameter model and saw no convergence at 130 epochs. Reproduce with `scripts/crossover.py`.

**Why this costs nothing.** Compute is parameters × tokens processed. How much *unique* data those tokens are drawn from is free. Only the number of runs changed (6 → 8).

**Methodological note that must appear in the report:** the diffusion objective yields an *upper bound* (ELBO) on likelihood, not exact NLL. Comparing a diffusion ELBO against exact AR NLL is conservative — it disadvantages diffusion. Report both, state the bound explicitly, and treat downstream task metrics (which are directly comparable) as the tiebreaker.

Report **bits-per-byte**, not bits-per-token, so the comparison is tokenizer-independent.

### 4.4 Ablations

| # | Ablation | Cost |
|---|---|---|
| ~~A1~~ | ~~DIFF without script-aware corruptions~~ | ~~1 training run~~ — **dropped in v2.4 (§0.4)** |
| ~~A2~~ | ~~AR without FIM — i.e. v1's original baseline~~ | ~~1 training run~~ — **dropped in v2.4 (§0.4)** |
| A3 | Denoising steps: 8 / 16 / 32 / 64 | Inference only |
| A4 | Unmasking schedule: random vs. confidence-based | Inference only |

> **A3 and A4 were both extended on 2026-09-14, inference-only, and the deviation is logged in `reports/preregistration.md` §8.** A4's two settings turned out to be the two *limits* of one dial — ranking by `log p(chosen) + s·Gumbel(0,1)` with *s* annealed to zero — and both limits fail while the interior does not; A3's 64-step ceiling still commits 2–3 positions per step from independent marginals on a 160-position canvas, so the grid never contained one-position-per-step. Both rows above are still measured and reported. See `reports/pilot_coherence.md` §10.

~~A2 is included deliberately. Running the broken baseline alongside the fair one lets you quantify exactly how much the unfair comparison would have inflated the result — which is a more interesting paragraph than the result itself.~~

> **v2.4: A1 and A2 are dropped and the paragraph above is what is lost.** Both cost a training run
> and the project now ships two. The report must therefore cite MARIA (below) for the *existence* of
> the inflation and state that **Ravaan did not measure its size on Urdu** — the claim A2 existed to
> make is withdrawn, not weakened. Finding AT's concern (our AR arm may be under-equipped for
> infilling by §4.2's FIM layout) becomes a **stated limitation** rather than a measured quantity.
> A3 and A4 are unaffected: they decode the trained diffusion checkpoint and cost no run.

**Prior art, and a scope correction.** The FIM-matched comparison in §4.1 is *methodologically necessary but not novel*. MARIA (arXiv:2502.06901) already reports that a properly-equipped AR model outperforms discrete diffusion baselines at infilling across all mask rates. It must be cited, and A2 must be framed as quantifying the inflation on **Urdu**, not as discovering that the unfair baseline inflates results.

### 4.5 Statistical protocol

- **1 seed** per core config (AR, DIFF) in **arm A**, which is the only arm (§0.3). *(v2.4: was 3 — §0.4. Two training runs total.)* Ablations A1/A2 are dropped; A3/A4 are inference-only and still reported as directional.
- **Primary endpoint, preregistered:** the sign and compute-location of the AR/DIFF crossover in validation BPB across arm A's sweep. **Committed 2026-08-03 in `reports/preregistration.md`, before any training** — including four falsifiable predictions (P1–P4) and a committed reading for every outcome combination. *(v2.3: **P2 withdrawn** with arm B; P1, P3 and P4 stand. The withdrawal is in the deviation log, §8 — the preregistration's text above it is unedited, and no model had been trained when it was written.)*
- **Secondary endpoints (3, Holm-corrected):** transliteration chrF on the human-written set, infill exact-match, OCR CER reduction on the real-OCR set.
- Paired bootstrap confidence intervals on all task metrics. If a CI includes zero, say so in the abstract. ⚠️ **v2.4: these resample *eval items*, not seeds.** With one run per arm there is **no estimate of initialization variance**, so an item-level CI that excludes zero still does not establish that the sign would survive a different seed. Report the CI, name what it does and does not cover, and never present the primary endpoint as seed-averaged.
- ⚠️ **The paired bootstrap must resample *sentences*, not rows**, on the transliteration reference set: its 16,241 rows are 4,500 distinct sentences (effective *n* = 2,978), so resampling rows would treat ~5.4 duplicates of one sentence as independent draws and narrow every interval. *(v2.4; not a wording question — it holds regardless of how §6.2 is worded.)*
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

> **Measured at the freeze, 2026-09-10 (v2.3).** These are *pre-dedup* pools. Stages 6 and 7 removed
> **82.4%** of Roman-Urdu-Parl's characters, and it is the only source of `roman_urdu` — taking that
> population to **0.44×** of arm B's 23.53M and **~1.53×** of arm A's 5.88M. `urdu` (46.66×) and
> `code_switched` (2.35×) are effectively untouched: FineWeb2's self-similarity measured 9 clusters
> in 193,666 documents. **Arm B is therefore dropped (§0.3); the arm B column below is retained as
> the record of what was budgeted.** Arm A's margin is not yet through stage 8.

Holding the mixture fixed across arms is what §4.1's "differ in size and nothing else" means once there is more than one population. Scaling only the native component would confound U with source mix — the same failure this section already forbids for crawl date.

Arm A's 25M-token corpus is a **deterministic, seeded subsample** — not a separate collection. Stage 9 makes this structural rather than maintained: a document's split and arm are one integer, a keyed hash of its id, and arm A is a *prefix* of the bucket range, so the containment cannot be violated by a later pass. The plan is checksummed and committed. *(v2.3: arm B is dropped (§0.3). The mechanism is unchanged — arm A was always the prefix — so nothing in stage 9 changes; the bucket range above arm A's cut is simply unused.)*

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

> **v2.4 — the mismatch is narrower and worse than "machine-produced" suggests (Finding AE).**
> Measured unsampled over the corpus: the transliterator renders **eight common Urdu words as fixed,
> *unrelated* words** — کرتے → `baghaawat`, بس → `dehli`, گھر → `mamu` — at 52–93% of their
> occurrences, with specificity 0.87–0.99. This is a **wrong lexicon**, not a style or spelling
> variant, and it affects **3.95% of rows (2.77% after dedup)**, which sit inside **23.53% of arm A's
> tokens**. **Decision, 2026-09-16: do not filter — train on the corpus as it is and state the rate
> in the technical report.** Filtering the eight confirmed words is shallow (it cannot reach the
> unscreened tail without a native-speaker pass over the 225-candidate list) and the priority is time
> to a result; the honest alternative is disclosure, and the rate is small enough to disclose.
> Consequence to carry: any transliteration claim resting on this corpus is weaker than §6.2's
> original wording implies, and the human-written set in §8.2 is the only instrument that can support
> one.

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
| Transliteration (reference) | Official split | Roman-Urdu-Parl test — *(v2.4)* **4,500 distinct sentences across 16,241 rows, effective *n* = 2,978**; see `reports/eval/transliteration_reference_set.md`. Contains the Finding AE lexicon (§6.2) |
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
| **2 core runs** (arm A: 2 models × 1 seed) *(v2.4: was 6 — §0.4)* | 47 | $17 |
| ~~2 ablation runs (A1, A2)~~ — **dropped in v2.4** | ~~45~~ 0 | ~~$16~~ $0 |
| Evaluation sampling | 25 | $9 |
| Failed runs and restarts | 20 | $7 |
| Storage | — | $15 |
| **Total** | **~112** | **~$55** |

Per-run cost is unchanged from v2.0 — every run processes the same ~9.9B tokens. The count went 6 → 8
in v2.1, back to **6** in v2.3 when arm B turned out to be unbuildable (§0.3), and to **2** in v2.4 on
a schedule decision (§0.4).

⚠️ **There is nothing left to cut.** v2.3's advice ("cut ablation A1, never cut the seeds") is spent:
A1 and A2 are gone and the seeds went with them. §10's ladder is down to its last rung — the two runs
*are* the irreducible core, and dropping either ends the project rather than shrinking it. If the
budget binds, the response is a cheaper instance or a smaller model (G2's lever), **never a run**.

⚠️ **v2.4: cost is no longer the binding constraint — wall-clock is.** Two runs against the $150 cap
leaves roughly 3× headroom, which inverts how the instance should be chosen: pick for **throughput,
not price**, because the cheapest card that clears G2 is no longer the right pick when the priority
is time to a result. At the G2 target of 64,162 tok/s two runs are ~86 GPU-hours (~3.6 days, ~$30);
on this project's own RTX 4060 at ~14,200 tok/s they are ~387 hours (~16 days, $0). **The rule that
does not change: throughput is measured on the instance before the budget is committed** — a spec
sheet has never been accepted here and is not accepted now.

**Hard cap: $150.** Pricing assumption was RTX 4090-class spot at ~$0.35/hr; with the constraint now
on time rather than money, verify live marketplace pricing *and* measured throughput together before
committing.

Cost controls: provider spending limit set on day one; every configuration validated on Kaggle before it touches a paid instance; checkpoint every 500 steps with resume tested before any paid run (spot instances get preempted); cost recorded per experiment; no hyperparameter sweeps.

---

## 10. Schedule

Roughly 250–320 person-hours across 16 weeks, or about 16–20 hrs/week.

| Weeks | Work | Output |
|---|---|---|
| 1–2 | Literature review; corpus acquisition; language/script ID | ✅ Lit review + **preregistration** committed W1; raw corpus on disk |
| 3–4 | Normalization, dedup, quality filter, decontamination | **Frozen corpus v1** (~170M-token pool, §6.1) + arm A's seeded 25M + manifest + statistics *(v2.3: arm B dropped at the freeze — §0.3)* |
| 5 | Tokenizer training and benchmark | **Frozen tokenizer** + checksum |
| 6–7 | Shared backbone, AR head, MDLM objective, tiny-model validation, throughput measurement | **Gate 1** |
| 8 | Pilot runs at 20M params, all 4 configs, 1 seed | **Gate 2** |
| 9–11 | **2 core runs** (1 AR, 1 DIFF) *(v2.4: was 6 core + 2 ablations — §0.4)* | **Gate 3** at midpoint |
| 12 | Build test sets incl. real-OCR; run automatic evaluation | Results tables |
| 13 | Human evaluation | Preference scores + kappa |
| 14 | HF Space demo | Public demo |
| 15–16 | Technical report, repo cleanup, release | **Ship** |

**If only ~10 hrs/week are available:** this becomes 6–7 months. The minimum viable cut, in order of what to drop: HF Space → human evaluation → ablations A1/A2 → seeds 2 and 3. The epoch sweep on a single seed for both models is the irreducible core; below that there is no project.

> **v2.4: the last two rungs of that ladder have been taken** — ablations A1/A2 and seeds 2–3 are
> dropped (§0.4). ⚠️ **The first two have not**, so the ladder is currently being climbed out of
> order: HF Space and human evaluation sit above the rungs already spent. That is an open decision,
> due before Week 12, and until it is taken this schedule does not match its own priority.

---

## 11. Gates and kill criteria

Every gate below can actually fail. v1's Gate D ("script-aware improves at least one primary task") could not — with six tasks and no multiple-comparison correction, something always improves by chance.

| Gate | When | Proceed if | Kill / fallback |
|---|---|---|---|
| **G0** | End W2 | Literature review confirms the comparison is unpublished | Reframe or stop |
| **G1** | End W4 | Clean corpus ≥ **100M** tokens **and** every population at or above arm B's share of it (§6.1: 70.59M / 23.53M / 5.88M) | 25–100M → run arm A only, report single-arm. Below 25M → stop. **A population short at the mixture is its own failure** — the aggregate can clear 100M several times over while arm B cannot be assembled |
| ↳ **verdict, 2026-09-10** | | **FAILED on `roman_urdu` at 0.44×** — the aggregate cleared easily (`urdu` 46.66×) and the population did not, which is the case this row was rewritten for in v2.2 | **Fallback taken: arm A only, single-arm (§0.3).** Arm A's own `roman_urdu` margin is ~1.53× and has not yet been through stage 8 — **re-check this gate after decontamination** |
| **G2** | End W7 | Measured throughput implies **2** core runs ≤ $90 *(v2.4: was 6; v2.3: was 8)* — at $0.35/hr that is ~21,400 tok/s, against v2.3's 64,162 | Shrink model, never epoch count. ⚠️ **v2.4 inverts this gate's use:** at two runs almost any rentable card passes on cost, so the question it now answers is *how long will this take*, not *can I afford it*. Measure on the instance regardless |
| **G3** | End W8 | 20M pilot DIFF produces coherent Urdu after 50 epochs; both models resume from checkpoint correctly | Implementation bug — debug, do not scale |
| ↳ **verdict, 2026-09-13** | | **SPLIT.** Resume: **PASS** on both arms — 5,614 steps, 367,919,104 tokens each, reload asserted parameter-identical. Coherence: **FAIL** — Ravaan-AR is fluent, Ravaan-DIFF is not, under any of 16 decoder settings (`reports/pilot_coherence.md`, 306 generations). **Narrowed 2026-09-14:** the sixteen were §4.4's grid, and the grid was wrong at both of its diffusion edges — a setting outside it (`gumbel` 2, one position per step) gets real Urdu words in grammatical clauses from the same checkpoint. Still a FAIL on the gate's own wording, because the arm is topic-locked and drifts to Roman Urdu unprompted; but "exhausted the decoder" was not true when it was written | **Decision taken 2026-09-13: the gate is recorded unmet on its own terms and W9 proceeds.** This row's kill reads "implementation bug", and no implementation bug was found: both arms train, checkpoint, resume exactly and decode, and three separate decoder defects were found *and fixed* without moving the verdict (a fourth, on 2026-09-14, moved it further than any of the three — so this clause is weaker support than it read as). The control offered on 2026-09-13 was that **Ravaan-AR is fluent on the same corpus, the same loop and the same code**, so a defect in anything shared would show in both arms. ⚠️ **Corrected 2026-09-14: that control does not hold either, and the first version of this row leaned on it after the other support had already been weakened.** Finding AS measured the pilot AR arm's train-versus-held-out gap at **+4.94 nats** against the diffusion arm's **+0.17** — at 50 epochs over 7.36M unique tokens it was reciting the corpus, so the two arms were not doing the same thing and its fluency is not evidence the shared code is sound. **What the decision rests on instead is stronger**: session 23's matched pair at 186.9M unique tokens × 2 epochs, where both memorization gaps are ~0.05, no diffusion-specific defect appears, and the arms separate in the direction §4.3 predicts ([`reports/diffusion_scale.md`](reports/diffusion_scale.md)). The pilot is 25M parameters at 368M training tokens over a 7.36M-token corpus, which is plausibly below the scale at which "coherent Urdu" is reachable at all, so the gate's premise is judged wrong rather than the code. **The technical report must carry this verdict, this reasoning *and this correction*** — a G3 section that quotes the original control without saying it was reciting the corpus is what a methods reviewer finds — and must not describe G3 as passed |
| **G4** | Mid W10 | Arm A curves are separating or converging in a legible way **by 50% of tokens processed** | No signal by then → complete both runs and report the flat result as the primary finding per preregistration §7. *(v2.3: "cut arm B" is spent — it was cut at G1. **v2.4: "complete arm A's 3 seeds" is spent too** — there is one seed per arm, so this gate has **no lever on the run list at all** and acts only on the write-up. It is also now the project's sole early warning for a diffusion-only defect, since G3 was recorded unmet and the six runs that would have averaged out a bad draw no longer exist — read it with that in mind.)* |
| **G5** | W13 hard date | Automatic results are in hand | Cut human eval and demo, ship the report |

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| No crossover appears within budget | The primary endpoint is the *curve*, not the winner. Because arm A is placed **1.79× past** the predicted C_crit, "no crossover where the English law predicts one" is now a genuine falsification of transfer — a publishable, citable result. **This defence did not hold in v2.0**, where the design sat 124× short and the English law itself already predicted no crossover; confirming that would have been no finding at all |
| Roman-Urdu-Parl is machine-generated | Human-written test set; scope the claim explicitly if it disagrees with the reference set |
| Seed variance swamps the effect | ~~3 seeds,~~ paired bootstrap CIs, report intervals not point estimates. ⚠️ **v2.4 removed this row's main mitigation and did not replace it.** With one run per arm the risk is **accepted, not mitigated**: a measured AR/DIFF gap cannot be separated from a single initialization draw, the surviving CIs resample *eval items* rather than seeds, and the report must say so beside the primary result (§0.4, §4.5). The cheapest partial restoration is one extra seed on the diffusion arm (~43 GPU-h, ~$15) |
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
- Epoch sweep complete: **1 seed per model** in arm A (U=25M) *(v2.4: was 3 seeds — §0.4; v2.3: arm B dropped — §0.3. Both absences are explained in the report, not omitted)*
- Preregistration committed before results were seen, and honoured
- Real-OCR and human-written transliteration test sets built and used
- Human evaluation completed or its absence explained
- All §8.1 invariants passing in CI
- Total spend under $150, with per-experiment costs recorded
- Technical report includes negative results and failure examples ~~and the A2 comparison showing what the unfair baseline would have claimed~~ *(v2.4: A2 is dropped — the report cites MARIA for the effect and states that Ravaan did not measure its size on Urdu; §0.4)*
- **The primary endpoint is stated as a single paired comparison**, with no between-seed interval quoted and no implication that the sign was replicated (v2.4, §0.4)

**Explicitly not a ship criterion:** that Ravaan-DIFF wins.

The project succeeds if the comparison is fair and the result is reported honestly. A clean negative result on whether diffusion transfers to naturally low-resource languages is a better artifact than an inflated positive one, and it is the version that survives someone reading the methods section.
