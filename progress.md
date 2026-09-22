# Ravaan — Progress

Working log for the project specified in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md).
Spec is the PRD; this file is the state of play. **Read "Next session" at the bottom first.**

> **Condensed 2026-09-15.** Sessions 1–24 were logged at length (4,654 lines). The full prose —
> every session log, every finding's derivation, every superseded note — is in git history at
> commit `8cecdfd` and its ancestors: `git show 8cecdfd:progress.md`. What is kept here is what a
> later session needs to act: current state, the findings register, the decisions that must not be
> re-opened, the live questions, and the plan. Detail that lives in `reports/*.md` is pointed at
> rather than restated.

## State of play

> ## 🏁 The primary endpoint has an answer, 2026-09-21
>
> **§4.5's crossover is measured, at full scale, on the frozen corpus.** Both arms, one seed each,
> 70M parameters, 9.9B tokens over 23,214,080 unique — held-out validation bits-per-byte on
> native Urdu, at §4.3's seven fractions:
>
> | fraction | epochs | **Ravaan-AR** | **Ravaan-DIFF** | ahead |
> |---|---|---|---|---|
> | 1% | 4.3 | **0.9018** | 1.1624 | AR |
> | 2% | 8.5 | **0.8311** ← AR's best | 1.0350 | AR |
> | 5% | 21.3 | 0.9753 | **0.9405** | DIFF |
> | 10% | 42.6 | 1.2062 | **0.8956** | DIFF |
> | 25% | 106.6 | 1.6885 | **0.8577** | DIFF |
> | **50%** | 213.2 | 2.4416 | **0.8181** | DIFF |
> | 100% | 426.5 | 3.6143 | **0.8059** ← DIFF's best | DIFF |
>
> **The arms cross between 8.5 and 21 epochs.** AR leads the first two rungs, the curves cross,
> and past the crossing AR turns up into memorization while diffusion descends monotonically for
> all 426 epochs and never regresses. ⚠️ **This is a *crossover*, not a level difference, and that
> is the claim to make** — §4.3 predicted the shape and the shape is what was measured.
>
> ⚠️ **Three framings are all true and they are not equally honest. The report takes the third.**
> "Diffusion beats AR **4.5×**" compares AR's most-overfit point to diffusion's best. "AR's best
> 0.8311 against diffusion's best 0.8052" is a **3% gap** and inside nothing significant at one
> seed. **What was actually measured is the crossing, and where it sits.**
>
> ✅ **A bound wins, which is the direction that can be established.** DIFF's number is an ELBO —
> an upper bound — and it still beats AR's exact NLL. §4.3's standing caveat is that a bound can
> prove a diffusion win and never an AR one; **here that asymmetry works for the result.**
>
> ✅ **The diffusion side is replicated, 2026-09-22.** `core-diff-s1` finished at urdu bpb
> **0.8024** against seed 0's **0.8052** — a difference of 0.0028 where the sd of a difference of
> two single draws is √2 × 0.0069 = 0.0098, so **0.29σ. Indistinguishable.** Both seeds land at
> ~0.80 against AR's 3.6143, so **no initialization story explains the 4.5×.**
>
> | population | seed 0 | seed 1 | Δ | sd(diff) | σ |
> |---|---|---|---|---|---|
> | **urdu** | 0.8052 | 0.8024 | 0.0028 | 0.0098 | **0.29** |
> | roman_urdu | 1.5937 | 1.6213 | 0.0276 | 0.0126 | **2.19** |
> | code_switched | 1.1340 | 1.1126 | 0.0214 | 0.0434 | 0.49 |
> | all | 0.9508 | 0.9526 | 0.0018 | 0.0057 | 0.32 |
>
> ⚠️ **`roman_urdu` at 2.19σ is the one population where the seeds differ by more than noise
> comfortably allows.** One of four comparisons at ~2σ is unsurprising, and it is also the
> population Finding AW says was **never decontaminated by stage 8**. Worth a line in the report;
> **not** worth a conclusion. Averaging draws (Finding BA) is what would settle it.
>
> ⚠️ **AR is still one seed, so §4.5's endpoint is still a single paired comparison.** What is now
> replicated is the diffusion arm's own number, not the gap. v2.4's requirement to write the
> endpoint as one comparison, with no between-seed interval, is unchanged.
>
> Curves: [`curve_ar_s0.json`](reports/eval/curve_ar_s0.json),
> [`curve_diff_s0.json`](reports/eval/curve_diff_s0.json), both by `scripts/curves.py`.

- **Started** 2026-08-03 (Week 1 of 16). **PRD v2.4** (2026-09-16). **Spend: first money went
  out 2026-09-20 — $40 loaded on Vast.ai, **~$28 committed to three runs** (the two core runs plus
  the second diffusion seed added 2026-09-21), of $150.**
  Everything before this was $0: the whole corpus freeze ran local, on Colab and on Kaggle.
- **⏱ Priority, set 2026-09-16 and it governs every choice below: time to a reported result.**
  The project ships **two training runs — one AR, one diffusion, one seed each** (PRD §0.4).
  Seeds 2–3 and ablations **A1/A2 are dropped**; A3/A4 are inference-only and survive. Budget
  ~$118 → **~$55**, and **cost stops being the binding constraint — wall-clock is.** What it costs
  is one thing and the report must carry it: **the primary endpoint is a single paired comparison
  with no estimate of seed variance**, so a measured AR/DIFF gap cannot be separated from one
  initialization draw. This is PRD §10's own pre-committed minimum viable cut, taken deliberately.
- **Weeks 1–2 complete. Weeks 5–8 complete ahead of them.** §7's tokenizer, §5's model, both
  objectives, the training loop, §4.2's five-task generator, §8's decoders, and both halves of G3.
- **✅ Weeks 3–4 are COMPLETE. The corpus freeze is finished, 2026-09-20, all local, $0.**
  `data/packed` — 20 shards, 218 MB, manifest with per-shard checksums committed, shards not.
  All twelve streams exist (three populations × train/A, train/B, validation, test).
  **Arm A: 23,214,080 tokens. Held-out: validation 4,874 sequences, test 5,072** against §6.1's
  ~5K each. **G1 re-check: PASS** — stage 8 removed only **592** roman-urdu-parl rows, so the
  population that killed arm B never threatened arm A.
- ⚠️ **U is 23.21M, not 25M, and the mixture is 68.8 / 26.1 / 5.1 against §6.1's 70.6 / 23.5 / 5.9.**
  Accepted 2026-09-20 and logged in the preregistration's deviation log. Arm A's cut is a fixed
  bucket range solved on stage 9's *pre*-stage-8 histogram and stage 8 then took 13.5% of the
  characters inside it. **It strengthens the design rather than weakening it** — less unique data at
  the same 9.9B tokens means arm A sits **2.11× past C_crit** where the plan put it at 1.79×, and
  the crossover is still predicted at U = 33M. Epochs ~426, not ~396. **The report quotes the
  realized numbers, not the planned ones.**
- 🟢 **Ravaan-DIFF seed 0 is COMPLETE, 2026-09-21 — the project's first core result.** Vast.ai
  RTX 5090, instance **51739847**, $0.5647/h. 75,531 steps, 9.9B tokens, **15.17 h at 181,288
  tok/s**, and **6.3 GB of checkpoints are on local disk at `/d/ravaan-runs/core-diff-s0`**.
  Held-out validation over the full 4,874 sequences: **urdu bpb 0.8052**, roman_urdu 1.5937,
  code_switched 1.1340, all 0.9508. ⚠️ **Every one of those is an ELBO — read it as ≤ — and it is
  a *single draw*, not a fixed quantity (Finding BA).**
- 🟢 **Ravaan-AR seed 0 is COMPLETE, 2026-09-21** — 75,531 steps, 15.45 h at 178,002 tok/s, all
  checkpoints and `evaluation.json` on local disk (6.3 GB). Held-out validation: **urdu bpb
  3.6143**, roman_urdu 6.2295, code_switched 5.0055, all 4.1070. ⚠️ **Those are memorization
  numbers, not a broken run — see Finding BC**, which is the single most important thing in this
  file to read before quoting any of them.
- 🟢 **Ravaan-DIFF seed 1 is COMPLETE, 2026-09-22** — 15.20 h, **urdu bpb 0.8024**, replicating
  seed 0 at **0.29σ**. The no-second-seed decision of 2026-09-21 was reversed the same day, and
  it was worth it: it is what makes the diffusion result defensible against the first objection a
  reader raises at one seed.
- ✅ **THE COMPUTE PHASE IS OVER. The instance is destroyed, 2026-09-22.** All three runs are on
  local disk at `/d/ravaan-runs` — **6.3 GB each, 8 checkpoints and `evaluation.json` apiece,
  18.9 GB total**, every artifact off the box before it went. Total **~$28 of the $40 loaded**,
  against G2's $90 ceiling and a $150 project budget. **Nothing is rented and nothing is
  accruing.** Weeks 9–11 complete.
- ⚠️ **The critical path is now the annotators, and it has been since the corpus froze.** Nothing
  left in the plan is blocked on compute or money; **G5 is blocked on three people who have never
  been approached.** See "Next session".
- ⚠️ **Two blockers were found by launching, not by reading, and both are fixed (Findings AX, AY).**
  **`data/packed` could not build §4.2's task generator at all** — `pack.py` never wrote §7's twelve
  framing pieces into the manifest, so *both* arms exited on arrival. It would have failed on the
  rented box five minutes in. A third defect (AZ, `--eval-limit`) is **not** fixed and is worked
  around on the command line.
- **One live design question left, and it is yours: the FIM framing** (open question 5, Finding AT).
  ✅ **Finding AE is decided 2026-09-16 — do not filter, disclose the rate**; open question 6 is
  folded into PRD v2.4 as a §6.2/§8.2 wording amendment.

### Gates

| Gate | PRD | Status |
|---|---|---|
| **G0** — comparison unpublished | §11 | ✅ **PASS** 2026-08-03 — [`literature_review.md`](reports/literature_review.md) |
| **G1** — clean corpus ≥ 100M tokens, per-population | §11 | ⛔ **FAIL on `roman_urdu` (0.44×)** → arm B dropped, single-arm. **Stage 9 measured arm A's own margin 2026-09-16: `roman_urdu` 2.55×** (not the ~1.53× this file carried), `code_switched` 9.40×, `urdu` 146.8×. Stage 8 must remove **>60.8%** of the `roman_urdu` pool to break arm A. **Re-check still due when stage 8 lands** |
| **G2** — throughput implies **2** runs ≤ $90 | §11 | ✅ **PASS 2026-09-20, measured on the rented instance** as the gate always required. RTX 5090 at microbatch 16: **DIFF 186,631 / AR 183,149 tok/s** against a bar of ~21,400 — **8.5× over**. Two runs = **30.6 h = $17.30** against the $90 ceiling. The 4060's 15,350 tok/s (re-measured on the frozen corpus, up from the 14,200 this file carried) was never the answer — it was the requirement |
| **G3** — 20M pilot, both arms, resume | §11 | 🟡 resume **PASS**; coherence **FAIL**, recorded unmet on its own terms, Week 9 proceeds |
| **G4** — arm A's curves at 50% of tokens | §11 | ✅ **PASS 2026-09-21, on its own terms.** The gate asks whether arm A's curves are "separating or converging in a legible way by 50% of tokens". At 50% (213.2 epochs): **AR 2.4416, DIFF 0.8181** — a **3× separation**, monotone on both sides, with the crossover already behind it. Its fallback branch ("no signal by then → report the flat result as the primary finding") is **not live**, and it did its job as an *early warning*: no diffusion-only defect. First gate to pass on its own terms since G2. ⚠️ **v2.4 left it no lever on the run list** — "complete arm A's 3 seeds" is spent along with "cut arm B" — so it acts only on the write-up, and it was the project's sole early warning for a diffusion-only defect. [`curve_ar_s0.json`](reports/eval/curve_ar_s0.json), [`curve_diff_s0.json`](reports/eval/curve_diff_s0.json) |
| **G5** — human evaluation | §11 | ⬜ Week 13, and the annotators are not lined up. ⚠️ **PRD §10's cut order puts human evaluation *above* the seeds already dropped** — so the ladder is currently being climbed out of order. Open decision, due before Week 12 (PRD §0.4) |

### Record

- **Design decision** ✅ Option 2 (two-point law) chosen 2026-08-03 — U ∈ {25M, 100M}, 3 seeds at
  25M, 1 at 100M; PRD v2.1. **Superseded 2026-09-10 by v2.3**: arm B is unbuildable, so the design
  that shipped is effectively option 1 — U = 25M, ~396 epochs, 3 seeds, 6 core runs, ~$118,
  with P2 withdrawn in the preregistration's deviation log and its text above unedited.
  **Superseded again 2026-09-16 by v2.4 — U = 25M, ~396 epochs, *1 seed per arm*, 2 core runs,
  ~$55.** ⚠️ **This one is different in kind from every amendment before it: it is a schedule
  decision, not a measurement.** v2.1–v2.3 were forced by data; this is a deliberate trade of
  statistical support for wall-clock, logged in the preregistration on 2026-09-16 **before the
  training corpus existed** — stage 10 had not packed it — so it cannot have been informed by any
  result. P1/P3/P4 stand as written; what changed is the evidence that will resolve them.
  **Ablations A1 and A2 are withdrawn with the seeds; A3/A4 are inference-only and stand.**
- **Preregistration** ✅ [`reports/preregistration.md`](reports/preregistration.md) — 4 falsifiable
  predictions, committed before any training. §8 carries the deviation log: the infill truncation
  rule (2026-09-13), A4's third arm and A3's fifth rung (2026-09-14).
- **Tests: 910 collected** across 23 files (verified 2026-09-15). ⚠️ The counts this file carried
  were never reconciled — the old per-file breakdown summed to 847, session 21 reported 792 green,
  session 22 reported 886. Trust the runner, not the log.
- **Git:** branch `stages-7-and-8`, working tree clean, **70 commits ahead of `main`** (main is at
  session 8 — fast-forward it when convenient). There is still **no remote**.

---

## Status board

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⛔ blocked

### Weeks 1–2 — lit review + acquisition — ✅ complete

Repo scaffold and CI-able suite (§13); literature review and G0 (§11); Findings A & B acted on via
PRD v2.1; preregistration (§4.5); source manifest, acquisition and the executing licence gate
(§6.2, §6.3.1) with all three sources fetched and checksummed; encoding validation (§6.3.2);
streaming shard reader; language/script ID (§6.3.3).

### Weeks 3–4 — corpus freeze (**G1**: clean corpus ≥ 100M tokens, PRD v2.1 §11)

**Built and validated — stages 4 through 10, plus the PII pass.** Each carries its own decision
record: stage 5's 200-sample validation ([`quality_validation.md`](reports/quality_validation.md)),
stage 7's threshold ([`neardedup_threshold.md`](reports/neardedup_threshold.md)), stage 8's
instrument ([`decontamination.md`](reports/decontamination.md)), stage 9
([`splits.md`](reports/splits.md)), stage 10 ([`packing.md`](reports/packing.md)), PII
([`pii.md`](reports/pii.md)). `ravaan/data/exclusions.py` chains them (Finding W); removal lists
carry the read plan they were computed over and refuse a mismatch. `ravaan/console.py` closed the
cp1252 hole as a class, and all sixteen drivers now call `pin_utf8_streams()`.

**Freeze runs — ✅ all three sources complete as of 2026-09-16:**

| source | stage 6+7 | evidence |
|---|---|---|
| Urdu Wikipedia | ✅ session 14 | `reports/freeze/removals_67_wikipedia.txt` — 188 ids, 118 clusters |
| Roman-Urdu-Parl | ✅ session 17, on Colab | `removals_67_roman.txt` — 4,307,848 ids, 1.38 h, peak 5.60 GB |
| FineWeb2 (both shards) | ✅ **session 25, on Kaggle** | `removals_67_fineweb2.txt` — 4,318 ids, 4,153 clusters, **largest 8**, 6.94 h, peak 6.65 GB |

| Remaining item | PRD | Status |
|---|---|---|
| **Freeze run: stage 6+7, FineWeb2 both shards** | §6.3.7 | ✅ **done 2026-09-16 on Kaggle, $0.** All three sources are now frozen through stage 7 |
| One unsampled stage-9 pass over **all** sources together | §6.3.9 | ✅ **done 2026-09-16, local, $0.** Phase 1 (measure) + phase 2 (assign) with the re-solve between them. 6,463,060 documents measured, 6,242,081 assigned, 220,979 outside the budgeted populations. `reports/freeze/split9_{measure,assign}.json`, `plan{,_resolved}.json`, `configs/data/splits_resolved.json` |
| Stage 8 complete (not sampled) over all three sources | §6.3.8 | 🟡 **restarted 2026-09-17 with a narrower eval index — see Finding AW.** Unsampled, `--both-columns`, **38,266 items / 3,067,145 shingles / 57,022 indexed lines**: `heldout_urdu` (5,400, word, 0.80), `heldout_code_switched` (384, word, 0.80), and **both columns** of `roman-urdu-parl:test` (16,241 each, char, 0.90). ⚠️ **`heldout_roman_urdu` (100,411 items) is excluded** — the first attempt carried it and was abandoned at 26.9% after 28.7 h. Finding T is still fully covered: it is about held-out *native Urdu* inside FineWeb2, which is `heldout_urdu` |
| Stage 10's writing pass | §6.3.10 | 🟡 **chained behind stage 8**, runs unattended. `--plan-in plan_resolved.json` (pack.py takes the splits config from the plan, so it needs no `--splits-config`) |
| **G1 re-check after stage 8** — arm A's `roman_urdu` margin is **2.55×** *pre*-stage-8 | §11 | 🟡 **much safer than this file feared.** Stage 9 measured it at 2.55×, not ~1.53×: supply 18.10M against arm A's 7.09M (5.88M corpus + 1.20M held-out). **Stage 8 would have to remove >60.8% of the pool** before the "below 25M → stop" fallback is live. Re-run the arithmetic when stage 8's removals land |
| **Stage-9 re-solve against measured fertility** | §6.3.9, §7 | ✅ **done 2026-09-16, and it had to land *before* the held-out split was written, not after stage 8** — `chars_per_token` sets `heldout_chars`, which sets `test_from`/`validation_from`, so the plan this file sketched would have put documents in train that the eval set also contains. Measured fertility came in close: urdu 4.71 chars/word → 1.21 tok/word, roman_urdu 4.92 → 1.17, code_switched 5.04 → 1.54 |
| **Finding AE decision** | §6.1 | ✅ **decided 2026-09-16: do not filter.** Train on the corpus as it is and state the 2.77% wrong-lexicon rate (3.95% pre-dedup, inside 23.53% of arm A's tokens) in the report. Filtering the eight confirmed words cannot reach the unscreened tail without a native-speaker pass, and disclosure costs no time. **PRD v2.4 amends §6.2 and §8.2 accordingly** — open question 6 resolved as its option (b) |
| Native-speaker pass: stage 5's 29 disagreements, stage 7's sampled pairs, the PII ambiguous match, the 225-candidate substitution screen | §6.3.5 | ⬜ **downgraded 2026-09-16 — not a training blocker.** One sitting, ~1–2 h, never lined up. It can happen while the runs are in flight, or not at all; nothing in the freeze or either run waits on it. ⚠️ It *is* still what the Finding AE filter would have needed, and Finding AE is now disclosed rather than filtered, so this is the pass that would let the disclosure be narrowed |
| Corpus manifest + per-stage statistics | §6.3 | 🟡 acquisition manifest done; stage stats pending |
| `neardedup.py` resumability | §6.3.7 | ⬜ not needed if FineWeb2 runs on a rented box |

**Closed, and not to be re-opened:** the Colab path for FineWeb2 (refused on both time and
memory); arm B (Findings AA/AB, PRD v2.3); stage 7's threshold at 0.80; **the stage-10 fertility
re-verification** (`pack.py --measure-only --resolve-plan`) — skipped 2026-09-16 because it costs a
full corpus pass and stage 10 reports measured fertility *as it packs*, so a bad `code_switched`
ratio is visible after the fact and re-packable; that population is 5.88% of the mixture, so a 20%
error moves arm A by ~1%. **Premise, written next to the verdict** per the Kaggle lesson below: this
holds only while the priority is wall-clock and while stage 10's reported fertility stays close to
3.8935 / 4.1928 / 3.2758. If stage 10 reports a large move, re-open it.

> **⚠️ The Kaggle entry used to sit in that list and has been removed, because its premise was an
> account property rather than a fact.** Phone verification was done 2026-09-15 and it lifted both
> halves at once — notebooks have DNS (Z′) and `kaggle quota` reports GPU 30 h / TPU 20 h (AL).
> A second credential bug then had to be found before anything would upload (Finding AU). The
> lesson to carry: **"closed, do not re-open" is only as durable as the premise under it** — write
> the premise down next to the verdict, so a later session can check the premise instead of
> obeying the verdict.

### Weeks 5–16

| Item | PRD | Status |
|---|---|---|
| **Tokenizer** — SentencePiece Unigram 16k, byte fallback, 12 framing tokens inside the vocabulary | §7 | ✅ s19, fingerprint `2855877c8ecd38c9` |
| ↳ fertility measured, retiring stage 9's estimate | §7 | ✅ urdu **3.8935** / roman_urdu **4.1928** / code_switched **3.2758** (separator-inclusive) |
| ↳ `code_switched`'s figure was the least-supported — that population filled to only 43.4% of its share | §7 | ✅ **discharged 2026-09-20.** Stage 10 measured **3.117** against the 3.2758 estimate — low by 4.8%, the same direction and order as urdu (3.739 vs 3.8935, −4.0%) and roman_urdu (4.066 vs 4.1928, −3.0%) |
| **Shared backbone** — RoPE, RMSNorm, SwiGLU, SDPA, tied embeddings; one flag switches the arm | §5 | ✅ s19, both arms at **69,975,680** params, identical |
| **AR objective** · **MDLM objective** (time-agnostic) · **training loop** | §4.1, §4.3, §9 | ✅ s19; resume tested exact on both arms |
| **§4.2's five-task corruption generator** | §4.2 | ✅ s20, both arms train on all five |
| ↳ restoration damage is stage 4 inverted; half of it (dot confusions) deliberately is not | §6.3.4, §8.2 | ✅ `normalize_text(corrupt) == clean` asserted over 40 seeds at a 50% edit rate |
| ↳ the three conditional tasks are byte-identical across arms | §4.1 | ✅ asserted on the tensor |
| **`ravaan/sampling/`** — both decoders, §4.2's framings, §4.4's A3/A4, §8.1's invariants | §8, §4.4 | ✅ s22 |
| **§8.3's generation metrics** — script consistency, distinct-n, repetition | §8.3 | ✅ `ravaan/evaluation/generation.py` |
| ↳ ⚠️ they **cannot separate fluent Urdu from Urdu-shaped noise** — scores land within a few hundredths on two different checkpoint pairs | §8.4 | ⚠️ §8.4's annotators are the only instrument that can |
| **§8.3's infill exact-match + token-F1** | §8.3, §4.5 | ✅ s24, `ravaan/evaluation/infill.py` |
| ↳ ⚠️ exact-match is **0.000 at every span but one** for the AR arm — see Finding AT | §4.5 | ⚠️ a secondary endpoint that cannot separate AR checkpoints |
| **`scripts/memorization.py`** — plain-LM scoring on both splits, same code path | §4.3 | ✅ s23; nothing measured this before |
| **The first matched pair that is actually matched** — both arms, 186.9M unique × 2 epochs | §4.1 | ✅ s23, [`diffusion_scale.md`](reports/diffusion_scale.md) |
| ↳ **the AR/DIFF sign flips between the two regimes** — §4.5's primary endpoint, at pilot scale | §4.5 | ✅ and Finding AS is why the pair is readable |
| ↳ ⚠️ a bound can prove a *diffusion* win and never an AR one — half the table is one-directional | §4.3 | ⚠️ the report must carry this beside the table |
| ↳ ⚠️ two regimes are two *corpora*, so composition is confounded with repetition | §6.1 | ⚠️ the clean version is one extra run after the freeze |
| ↳ ⚠️ `data/packed-urdu` is **urdu-only** and **not the freeze** — its manifest says so | §6.1 | ⚠️ no number from it goes in a results table |
| **Open question 5 answered — keep §4.2's 10% infilling share** | §4.2 | ✅ s24, [`infilling_share.md`](reports/infilling_share.md) |
| ↳ 50% costs **+0.0374 held-out bpb** and buys **+0.02–0.04 token-F1**; memorization gaps ~0.04 | §4.2 | ✅ matched pair, one variable |
| ↳ ⚠️ but it found **Finding AT**, and the *framing* call is live again | §4.2, §4.4 | ⬜ **open question 5 — and it is yours** |
| **`--task-share`** — §4.2's table stays frozen; the override lands in `config.json` | §4.2 | ✅ residual out of `lm` alone |
| **G2** — the **rented** card decides it, and it did | §11 | ✅ **PASS 2026-09-20 on the instance**, which is what the gate always required. RTX 5090 at microbatch 16: **181,288 tok/s sustained** against a v2.4 bar of ~21,400 — **8.5× over**. The 4060's 15,350 was never the answer, it was the requirement. Three runs came in at **~46 GPU-h / ~$28** against the $90 ceiling |
| ↳ the ladder: 70M **4.54×** short · 40M **2.78×** · 25M **1.72×** (37,236 tok/s) | §11 | ✅ s21 — check a spec sheet against this *before* renting |
| ↳ Finding AM — both arms cost the same per token, within 2.2% | §4.1 | ✅ and it is the half that transfers to another card |
| ↳ §4.2's generator is ~180 ms of CPU per 256-sequence step, so `throughput` builds tasks by default | §11 | ✅ ~13% of throughput, and the cheapest evidence the tasks are running |
| ↳ ⚠️ the binding *local* constraint is **VRAM, not speed** — 25M at microbatch 32 sits at 7.8 GB of 8.19 | §9 | ✅ every G2 figure above is at microbatch 16 |
| **G3** — 20M pilot, both arms | §11 | 🟡 resume **PASS**; coherence **FAIL**, gate recorded unmet, Week 9 proceeds |
| ↳ 50-epoch run complete, both arms, §4.3's seven fraction checkpoints written | §4.3 | ✅ the curve infrastructure works end to end |
| ↳ 306 generations read → [`pilot_coherence.md`](reports/pilot_coherence.md), text in [`pilot_samples.md`](reports/pilot_samples.md) | §11 | ✅ **both halves of its headline were narrowed on 2026-09-14 — Findings AR and AS** |
| ↳ **G3's record corrected** — PRD §11, `pilot_coherence.md` §9/§11, and §12 written | §11 | ✅ s24; session 23's handoff said this was done, and it was not |
| **Ablations A3/A4** — inference only | §4.4 | 🟡 pilot-scale sweep done; the core-run sweep is Week 12 |
| ↳ ⚠️ **A2 measures §4.2's FIM layout, not "AR without FIM"** — MARIA reports the opposite | §4.4 | ⚠️ **A2 cut in v2.4** — Finding AT becomes a stated limitation; the report must say so |
| **The microbatch that reproduces session 23's runs is 32** — nothing recorded it | §4.1 | ✅ identified from `pad_tokens` 11039 |
| **`scripts/train.py --tokens / --epochs / --warmup-steps`** — `--steps` never moved the cosine | §4.3 | ✅ s23; every earlier short run trained at near-peak LR throughout |
| **`pin_utf8_streams()` reaches all sixteen drivers** — session 14's class fix, finished | — | ✅ s23 |
| **Core runs (W9–11, G4)** → eval (W12) → human eval (W13, **G5**) → demo (W14) → report (W15–16) | | ⬜ |

---

## Findings register

Fifty-seven findings are referenced across this file, the PRD and the reports, and until now they
were only defined inside the session that raised them. One line each, with the session that owns
the derivation — `git show 8cecdfd:progress.md` has the full text of every one.

⚠️ marks a finding that is still live: it constrains a decision, a run, or something the report
must say.

| # | s | Finding | Status |
|---|---|---|---|
| A | 2–3 | The planned budget was ~124× below the predicted crossover; U is free, so retarget it | ✅ PRD v2.1; both arms placed inside the reference law's fitted range |
| B | 2 | "Naturally data-constrained" fails at 70M — Urdu has ~5–6B collectable tokens against a ~1.4B Chinchilla budget | ✅ capping is a deliberate design decision, on the record |
| C | 4 | UrduLM's 33 GB corpus is not a public artifact; 5.5 GB of it is machine-translated English | ✅ in `sources.json` under `rejected`; qualifies B's headline number |
| D | 4 | The first mojibake detector would have silently deleted 3% of a *clean* corpus — 57 unit tests passed on it | ✅ the round trip is the detector, not a character class; 97.03% → 99.99% |
| E | 4 | A prefix of a FineWeb2 shard is not a sample of it — there is block-level structure | ✅ probes spread across row groups; **stage 9 and arm A's subsample must sample randomly** |
| F | 5 | Arabic-variant spelling is a property of publishers, not of the language | ✅ answered |
| G | 8 | A duplicate rate cannot be measured on a sample — a pair survives at *r*², not *r* | ✅ linear-detection design; the first run reported zero and was meaningless |
| H | 8 | FineWeb2 removed **31.02%** of `urd_Arab` as near-duplicates before we ever saw it | ✅ explains the near-nil exact-duplicate rate, and it is a fact about the *source* |
| I | 8–9 | Session 7's four stage-5 false accepts are caught by neither stage 6 nor stage 7 | ✅ confirmed against the shipped stage 7 — they are residue that survives the pipeline |
| J | 8 | 99.6% of the apparent dedup win on Wikipedia is stage 5's length floor, counted twice | ✅ measure dedup yield *after* stage 5 |
| K | 8 | Roman-Urdu-Parl collapses harder than PRD §6.2's own warning | ✅ first stage-6 result that removed anything |
| K′ | 8 | §6.1's 40M-token Roman budget survives — 3,478,770 distinct sentences at ~74.2 chars | ✅ reproduced **exactly** by session 17's Colab pass, on a different code path |
| L | 8 | Wikipedia *is* inside FineWeb2 and exact hashing finds none of it | ✅ this is the requirement stage 8 exists for |
| M | 9 | Stage 7 finds 633 cross-source clusters where exact dedup finds 1 | ✅ session 8's acceptance test, written before the code, passes |
| N | 10 | The instrument session 9 specified cannot measure the quantity it was specified for | ✅ the exact answer turned out to be affordable |
| O | 10 | Stage 8's first run over real text was wrong by **59×**, and only reading the hits showed it | ✅ fixed |
| P | 10 | A retention floor carried across a unit change would have failed the freeze nine tenths through | ✅ caught by watching RSS, not by reasoning |
| Q | 10 | **16.8%** of the reference transliteration split's Urdu side sits in Urdu Wikipedia | ⚠️ stage 8 must run against the eval sets; the report must state it and discount that number |
| R | 11 | PRD §6.1 and §4.3 do not describe the same corpus — the reading §6.1 invites is fatal to the primary endpoint | ✅ PRD v2.2; pool targets separated from arm budgets |
| S | 11 | A sampled pass reported Gate G1 **twenty times** too low, and the two wrong numbers agreed | ✅ fixed |
| T | 11 | ~**4.4%** of the held-out split is likely inside FineWeb2 (0.22% measured at a 5% sample) | ⚠️ **the freeze's stage 8 must run complete, not sampled**, and the report must carry the number |
| U | 12 | Gate G1 returned `pass` on a corpus from which arm B could not be assembled | ✅ G1 now checks per-population sufficiency, not just the total |
| V | 13 | 11 of the PII pass's first 13 phone matches on Wikipedia were **ISBNs** | ✅ fixed and re-measured; recall-side gaps are stated in `pii.md` §6 rather than fixed |
| W | 14 | The freeze order was not runnable — stages 9 and 10 could not read a removal list | ✅ `ravaan/data/exclusions.py`, `--exclude`, 17 tests. **The bugs live at the seams** |
| X | 14 | Stage 7's index costs **2×** what the module documents | ✅ the freeze moved off this machine; a projection from a docstring is not a measurement |
| Y | 16 | A Kaggle kernel's address comes from its **title**, not the slug in `id` | ✅ derived and asserted |
| Z | 16 | The Kaggle mount is `/kaggle/input/datasets/<owner>/<slug>/`, two levels below the docs | ✅ settled by a kernel that printed the tree |
| Z′ | 16 | `enable_internet: True` is recorded, returned by the API, and **not a network** | ✅ the flag is still not evidence of a network. Its *premise* retired 2026-09-15 — phone verification done, notebooks have DNS (see AU) |
| AA | 17 | Roman-Urdu-Parl's 82.4% character loss is **genuine** near-duplication, not a chaining artifact | ✅ read, not inferred — the five largest clusters are geo-stub templates with the numbers stripped |
| AB | 17 | 0.80 is if anything too conservative there, so **no threshold move recovers budget** | ✅ do not re-litigate |
| AC | 17 | The sweep is not recoverable after the fact and the run carried no `--sweep` | ✅ both passes carry it now, with the floor asserted |
| AD | 17–18 | A `.gitignore` negation cannot re-include a file under an excluded parent — **six instances** | ✅ fixed as a class: `!/reports/**/*.jsonl` |
| AE | 18 | Roman-Urdu-Parl renders eight common Urdu words as fixed *unrelated* words (کرتے→`baghaawat`, بس→`dehli`, گھر→`mamu`) at 52–93% of occurrences, specificity 0.87–0.99 | ⚠️ **3.95% of rows, 2.77% after dedup, in 23.53% of arm A's tokens** — live decision, below |
| AF | 19 | The corpus was not the critical path, and had not been for a while | ✅ Weeks 5–8 were built instead of waiting |
| AG | 19 | The diffusion arm's per-step loss is a far noisier estimator than AR's | ⚠️ standing caution: **a flat early diffusion curve is not evidence of anything** — matters for G4 |
| AH | 19 | CPU bf16 autocast is ~10× slower than fp32 here; CPU throughput ~600 tok/s | ✅ CPU paths stay fp32; 9.9B tokens on CPU would be ~200 days |
| AI | 20 | The first romanizer emitted vowel-less Roman at **1.80** tokens per native token | ✅ inherent-vowel epenthesis → **1.54**; the residual gap is vowel quality, which an abjad does not record |
| AJ | 20 | Fixed-tie-break apportionment **starved 3 of 5 tasks to 0.00%** at every microbatch a host actually fits | ✅ systematic sampling; unbiased at any batch size. Found by reading the realized mixture, not the loss |
| AK | 20 | `evaluate` rescaled the two arms' BPB by different amounts (AR inflated by L/(L−1)) | ✅ `LossOutput.scored`; it matters far more with §4.2's framings in the path |
| AL | 21 | Kaggle's phone verification gates **accelerators**, not only the network | ✅ true, and **retired 2026-09-15**: verification done, `kaggle quota` reports GPU 30 h / TPU 20 h. Kernel 10's host-agnostic branch is now usable rather than kept |
| AM | 21 | AR and DIFF cost the same per token, within **2.2%** | ✅ neither arm can buy an advantage by being cheaper at a fixed token budget |
| AN | 21 | Kernel 10 **trained the bare objective** and the loss curve looked fine | ✅ `build_tasks` moved into the library; 3 tests. Second instance of "the bugs live at the seams" |
| AO | 22 | `</s>` on a context-free diffusion canvas — 47% of first commits; Arabic-script share 0.000 → **1.000** when forbidden | ✅ `--forbid-eos always`, swept and reported. Deliberately **not** defaulted |
| AP | 22 | A3 runs backwards — 64 denoising steps repeat *more* than 8, monotonically on every axis | ⚠️ directional, one seed. **A3's table must not be written as "more steps, better"** |
| AQ | 22 | §4.2's AR FIM framing has **no terminator after the middle** — it stopped on 5/12 prompts, median length = the budget | ✅ **decided 2026-09-13: not fixed.** Cost moves to scoring; truncation rule preregistered |
| AR | 23 | A4's two schedules are the *limits* of one family, not the family | ✅ `gumbel` added, `s=0` == `confidence` bit-for-bit; the **interior** gets real Urdu clauses out of the "incoherent" checkpoint |
| AS | 23 | The pilot **AR arm memorized the corpus, and it is G3's control** — AR gap **+4.94 nats**, DIFF **+0.17**; on the plentiful corpus both are ~0.05 | ⚠️ G3's reasoning is qualified in place; the report must carry the correction, not just the conclusion |
| AV | 25 | Kernel 00's `read_plan` searched **stdout**, but `neardedup.py` writes `reading <source>: plan <hex>` to **stderr** — stdout carries only the JSON config | ✅ cost one kernel, with the fetch and verify already passed and the right corpus on disk. Searches both streams now, and the fix was validated locally before re-pushing |
| AW | 26 | Stage 8's cost is dominated by **posting-list length, not index size**: adding `heldout_roman_urdu` (100,411 short sentences, char 5-grams) grew distinct shingles only 3,067,145 → 3,203,208 (+4.4%) but **indexed lines 57,022 → 115,109** and made the pass **3.3× slower** (measured: 2m24s vs 43.8s over 1,500 identical Wikipedia documents, same top findings) | ⚠️ the first freeze attempt was abandoned at **26.9% after 28.7 h**; restarted without that set. `for_sentences()`'s docstring predicted this shape for char shingles on short sets and set `retain_hits_above` 0.50 → 0.80 for it — the residue it did not cover is the **fan-out**, which no config knob bounds |
| AU | 25 | The Kaggle CLI's **access-token** auth path takes the username from the *server's* token introspection, which answers `del=c0b94e0932cd8e95` for this account — so uploads refuse after sending the bytes and pushed kernels land unreachable | ✅ `authenticate()` tries access token → legacy key → OAuth creds, and only the third reads `credentials.json`'s correct slug. **Delete `~/.kaggle/access_token`** and the CLI falls through to it |
| AT | 24 | The AR FIM framing loses **~37× in rank at the middle's first token** — `<lm>` ranks gold **2**, `<fim_middle>` ranks it **74**, same checkpoint and position — and the damage is **one position wide** | ⚠️ **live — it reopens the framing call AQ closed.** Not the decoder, span distribution, window, memorization or share |
| AX | 27 | **`scripts/pack.py` never wrote §7's twelve framing pieces into stage 10's manifest, so the frozen corpus could not build §4.2's task generator and *neither arm would start*** — `FramingTokens.from_manifest` refuses a partial set. `pack_pilot.py` patched the manifest after stage 10; `pack.py` did not, and the freeze ran through `pack.py` | ✅ fixed in `pack.py` (`_with_framing_pieces`); `data/packed/manifest.json` patched in place — piece ids are a property of the **tokenizer**, not the packing, so **no re-pack**: model sha256 matches the manifest's `2855877c8ecd38c9`, nothing outside the `tokenizer` block moved, **all 20 shard checksums still verify**. Findings W/AN a third time — *and this one lived in the half of the seam the pilot never crossed* |
| AY | 27 | **`Trainer.train` clobbered the `wall_seconds` it had just restored** (`started = time.time()`), while `state.tokens` carried over — so after any preemption `tokens_per_second` divided every token the run had *ever* processed by seconds since resume | ✅ one line, `loop.py:179`. Logging only, no effect on the science — but it is the number that says whether a rented instance is on budget, and §9 makes resume a first-class path precisely because spot instances get preempted |
| AZ | 27 | **`--eval-limit` truncates in shard order, not by sampling.** Populations concatenate `code_switched → roman_urdu → urdu`, so the default 2,000 scores the primary endpoint on the **first 592 of 3,466** urdu validation sequences and weights the `all` row 10/61/30 instead of 4/25/71 | ⚠️ **not fixed — pass `--eval-limit 0`**, which falls through to the full split for ~2 min. Finding E's shape ("a prefix of a shard is not a sample of it") applied to the eval set. Both core runs launched with `0` |
| BA | 28 | **The diffusion arm's held-out bpb is a single-sample Monte Carlo estimate, not a fixed property of the checkpoint.** `RavaanDiffusion.loss` draws one masking rate `t` and one mask **per sequence**, and `Trainer.evaluate` calls it with `generator=None`, so the reported number moves with the global RNG state. Measured over **6 independent draws on the frozen `f1` checkpoint**, full validation split: **urdu sd 0.0069** (range 0.7995–0.8170), roman_urdu 0.0089, **code_switched 0.0307** — noisiest where the population is smallest at 196 sequences — and `all` 0.0040 | ⚠️ **live, and it reaches the primary endpoint.** The AR arm's NLL is exact, so §4.5 compares a noiseless number against one carrying **sd ≈ 0.007 bpb on native Urdu**; the gap must be reported against that error bar, **beside the result**. It also bounds what G4 can resolve — see the gate. Found by asserting a recomputed 100% point against the run's own committed `evaluation.json` (**0.9564 against 0.9508**, same checkpoint, same code path), not by reading the code. ⚠️ **Compounds the single-seed decision**: no replication *and* an unquantified estimator term would have been two unknowns stacked. **Averaging K draws shrinks it by √K** — K = 9 puts urdu near 0.002 for ~15 min of an idle 4060, and needs no rented GPU |
| BB | 28 | **The AX fix did not parse.** `scripts/pack.py` as it sat in the working tree carried two string literals containing **real newlines where `\n` was intended**; `ast.parse` refused it at line 437. It survived review because hand-patching the manifest meant `pack.py`'s write path was never re-run after the fix was written — the fix was verified by reading it | ✅ repaired 2026-09-21, and `_with_framing_pieces` then verified to reproduce the patched manifest **exactly** (12 pieces, `<mask>` = 4). **No effect on either run** — nothing in `ravaan/` or `train.py` imports `pack.py`. The lesson is this register's oldest one aimed at a *fix* rather than at a stage: **a fix verified by reading is not verified.** The suite would have caught it and was not run |
| BC | 29 | **Ravaan-AR's held-out loss collapses past ~8.5 epochs, and at 426 epochs it is *worse than uniform random*.** Held-out urdu bpb runs 0.9018 → **0.8311 at 8.5 epochs** → 0.9753 → 1.2062 → 1.6885 → 2.4416 → **3.6143**, while train bpt falls monotonically 5.614 → **0.201**. At 100% the model is at **23.98 bits/token against a uniform baseline of 14.00 over the 16,384 vocabulary** — 9.98 bits *worse than knowing nothing* | ⚠️ **live, and it is the result, not a defect.** Three independent checks say so: **(1)** the `fp01` checkpoint at 4.3 epochs scores a healthy **0.9018**, so the AR scoring path is sound; **(2)** the collapse is **monotone and identical in all three populations** (urdu, roman_urdu, code_switched) which have different shingle units, lengths and scripts — a scoring defect does not do that; **(3)** the 100% point **reproduces the run's own `evaluation.json` to 6.6e-6 relative** on a second code path. It is Finding AS at full scale: at pilot, 50 epochs over 7.36M tokens gave an AR gap of +4.94 nats; here 426 epochs over 23.21M gives **+16.48 nats**. **A confidently-wrong memorizer can be arbitrarily worse than chance** — train loss 0.139 nats means near-total confidence, misapplied off-distribution. ⚠️ **The report must state that AR's *best* held-out checkpoint is 0.8311 at 8.5 epochs, not only its final 3.6143** — quoting the endpoint alone against diffusion's best overstates the effect ~4.5× where the honest comparison is the crossing |

> ⚠️ **One number in this table was carried wrong.** The status board reported Finding AS as
> "AR gap +4.46 nats, DIFF +0.03" from session 23 through session 24. Session 23's measurement
> table gives `ar_f1` **1.705 train / 6.641 held-out = +4.935** and `diff_f1` **4.796 / 4.966 =
> +0.170**, which is what the session text quotes as "+4.94 against +0.17". The table's figures are
> the measured ones and are used above.

---

## Session log

One line per session: what it delivered, and what it raised. The findings are in the register
above; the derivations are in git at `8cecdfd`. Dates are 2026.

| s | date | Delivered | Raised |
|---|---|---|---|
| 1 | 08-03 | Repo scaffold (§13); **stage 4, Urdu normalization** — the component every later stage reads through | — |
| 2 | 08-03 | Initial commit; **literature review, G0 PASS**; `scripts/crossover.py` | **A, B** |
| 3 | 08-03 | Finding A verified against the typeset PDF (124× short); **PRD v2.1**; **preregistration committed** | — |
| 4 | 08-03 | **Stage 1 acquisition** with an executing licence gate; **stage 2 encoding**; first real corpus on disk | **C, D, E** |
| 5 | 08-04 | Streaming shard reader; **stage 3 langid** | **F** |
| 6 | 08-04 | **Stage 5 quality filtering** + the 200-sample validation; `scripts/probe.py` (stages 2→5) | — |
| 7 | 08-04 | [`quality_validation.md`](reports/quality_validation.md) written; sessions 6–7 committed as one deliverable | — |
| 8 | 08-04 | **Stage 6 exact dedup**, six full-source passes | **G, H, I, J, K, K′, L** |
| 9 | 08-04 | **Stage 7 MinHash near-dedup**; threshold chosen from measured pairs → [`neardedup_threshold.md`](reports/neardedup_threshold.md) | **M** |
| 10 | 08-04 | **Stage 8 decontamination** → [`decontamination.md`](reports/decontamination.md) | **N, O, P, Q** |
| 11 | 08-04/05 | **Stage 9 splits** → [`splits.md`](reports/splits.md); the second stage-8 run | **R, S, T** |
| 12 | 08-05 | **PRD v2.2** for Finding R; G1 checks the mixture; **stage 10 packing** → [`packing.md`](reports/packing.md); FineWeb2 shard 000 fetched (4.84 GB) | **U** |
| 13 | 08-05 | **PII pass** → [`pii.md`](reports/pii.md) — the last unbuilt thing in §6.3 | **V** |
| 14 | 08-05 | **`exclusions.py`** — the missing hand between stages; Urdu Wikipedia frozen through stage 7 (188 ids); cp1252 closed as a class | **W, X** |
| 15 | 08-06 | Kaggle runners written (committed later, in 16) | — |
| 16 | 09-10 | Three reasons the Kaggle side had never worked; **phone verification unavailable → Kaggle closed**; freeze re-hosted on **Colab** with a memory gate | **Y, Z, Z′** |
| 17 | 09-10 | Colab ran it: FineWeb2 refused, **Roman-Urdu-Parl complete in 1.38 h** — 82.4% of characters removed → `roman_urdu` 0.44× → **arm B dropped, PRD v2.3** | **AA, AB, AC, AD** |
| 18 | 09-10 | The reference transliteration split measured: **4,500 sentences in 16,241 rows**, effective *n* **2,978** → [`transliteration_reference_set.md`](reports/eval/transliteration_reference_set.md) | **AE** |
| 19 | 09-13 | **Weeks 5–7 built instead of waiting**: §7's tokenizer (`2855877c8ecd38c9`), §5's model at 69,975,680 both arms, both objectives, the training loop, resume exact | **AF, AG, AH** |
| 20 | 09-13 | **§4.2's five-task corruption generator** — both arms train on all five | **AI, AJ, AK** |
| 21 | 09-13 | Sessions 18–20 committed; **a local RTX 4060 found behind a CPU-only torch wheel**; **G2 measured**; **G3's resume half PASSES** | **AL, AM, AN** |
| 22 | 09-13 | **`ravaan/sampling/`** — both decoders, §8.1's invariants asserted for the first time; **G3's coherence half answered: FAIL** → [`pilot_coherence.md`](reports/pilot_coherence.md) | **AO, AP, AQ** |
| 23 | 09-14 | **The first matched pair that is actually matched** — 186.9M unique × 2 epochs, both arms → [`diffusion_scale.md`](reports/diffusion_scale.md); `memorization.py`; `--tokens/--epochs` | **AR, AS** |
| 24 | 09-14 | **Open question 5 answered — keep 10%** → [`infilling_share.md`](reports/infilling_share.md); §8.3's infill metrics; G3's record actually corrected | **AT** |
| 25 | 09-15/16 | **Stage 6+7 finished for all three sources.** Kaggle reopened (Z′, AL retired); AU and AV found and fixed; kernel 00's trial **FITS** at 8.96 h; **kernel 01 ran FineWeb2 stage 6+7 in 6.94 h for $0** — 4,318 ids, largest cluster 8 | **AU, AV** |
| 26 | 09-17/20 | **The corpus freeze is finished.** Stage 8 restarted on a narrower eval index and completed; **stage 10 packed 20 shards, all 12 streams**; U measured at **23.21M** and accepted into the deviation log; Weeks 3–4 closed | **AW** |
| 27 | 09-20 | **The core runs are launched.** Two blockers found *by running the thing* — AX would have stopped both arms on the rented box; AY would have made the budget read as nonsense after the first preemption. **G2 PASSES on a rented 5090 at 181,600 tok/s.** Ravaan-DIFF s0 training, Ravaan-AR s0 chained, auto-stop watchdog installed | **AX, AY, AZ** |
| 28 | 09-21 | **Ravaan-DIFF s0 is complete — the project's first core result**, 15.17 h, urdu bpb ≤ 0.8052 over the full validation split, 6.3 GB on local disk. AR s0 training. **The second diffusion seed was declined and then added back the same day**, which required rearming the watchdog and renaming the sentinel. **G4's diffusion half read** through `scripts/curves.py` — §4.3's "evaluate every checkpoint" had no driver and the gate's own curve could not be produced. AX's committed fix found not to parse | **BA, BB** |
| 29 | 09-21/22 | **Ravaan-AR s0 complete, and §4.5's primary endpoint has an answer.** **G4 PASSES** — the crossover is measured between 8.5 and 21 epochs, AR degrading to 3.6143 held-out urdu bpb against diffusion's 0.8059. AR's collapse verified as memorization and not a defect by three independent checks. `curves.py`'s reproduction tolerance corrected from an unreasonable 1e-9 to 1e-4 relative — which is itself what separated AR's float noise (6.6e-6) from DIFF's genuine ELBO sampling (5.9e-3, 207× larger) | **BC** |
| 30 | 09-22 | **The compute phase is over.** DIFF s1 complete at urdu bpb **0.8024**, replicating seed 0's 0.8052 at **0.29σ** — the diffusion result is not one initialization's draw. All three runs downloaded (18.9 GB), **instance destroyed**, **~$28 of $40**. ⚠️ `roman_urdu` is the one population where the seeds differ by more than noise allows (2.19σ) and it is also the one stage 8 never decontaminated (AW) — a line in the report, not a conclusion. **The critical path is now the annotators** | — |

### The results worth keeping in front of you

**0. THE RESULT — the crossover is measured at full scale on the frozen corpus (session 29).**
The table is at the top of this file. AR leads to ~8.5 epochs, the arms cross between 8.5 and 21,
and past the crossing AR degrades to **3.6143** held-out urdu bpb while diffusion descends
monotonically to **0.8059**. §4.5's primary endpoint, answered, in the direction a bound can
establish. ⚠️ One seed per arm: the crossing's *existence* is well supported, its *location* is
one draw. ⚠️ And read **Finding BC** before quoting the endpoint — AR's *best* is 0.8311, not
3.6143, and the 4.5× ratio is the least honest of the three available framings.

**The two below are now corroboration rather than the headline, and they held up.** Both were
measured at pilot scale before the corpus existed, and both predicted what session 29 measured —
which is the strongest thing that can be said for them.

**1. The sign of the crossover already flipped, at pilot scale, on a matched pair (session 23).**
Same rung, mixture, optimizer, seed and **367,919,104 tokens processed**; both memorization gaps
~0.05, so neither arm could cheat. Held-out bits-per-byte on native Urdu:

| data regime | Ravaan-AR (exact NLL) | Ravaan-DIFF (ELBO) | ahead |
|---|---|---|---|
| 7.36M unique × 50 epochs | 1.4200 | **≤ 1.0737** | **diffusion, provably** |
| 186.9M unique × 2 epochs | **0.8154** | ≤ 0.9703 | AR, on the bound |

Diffusion ahead where data is repeated, AR ahead where it is plentiful — which is §4.5's primary
endpoint and the whole reason arm A caps U at 25M. ⚠️ **Corroboration, not a result**: two regimes
are two *corpora*, so composition is confounded with repetition; the corpus is not the freeze; one
seed. And **a bound can prove a diffusion win and can never prove an AR one** — row one is a
result, row two is *consistent with* an AR win.

**2. The AR arm memorizes and the diffusion arm does not, and that is the mechanism §4.3 is about
(Finding AS).** At 50 epochs over 7.36M unique tokens the AR gap runs +1.10 → **+4.94** nats while
the diffusion gap runs +0.06 → **+0.17**, on identical data, parameters, epochs, loop and code.
AR sees the same factorization every epoch; MDLM draws a fresh rate and mask, so the same text is
an effectively non-repeating task distribution. Arm A repeats 25M unique tokens ~396 times.

---

## Settled — do not re-open

Each of these cost a session to establish and has an argument behind it, not just a preference.

**Corpus and thresholds**

- **Roman-Urdu-Parl's 82.4% loss is genuine** (s17). A 10,757-document component and an average
  pair degree of 1.38 both said "chaining artifact"; both were wrong, and twenty-four sentences
  settled it. Read across the cut, the pairs 0.80 *keeps* are still spelling variants of one
  sentence. **No threshold move recovers budget.**
- **Arm B is dropped; PRD is v2.3; P2 is withdrawn** with its text above unedited. The narrower
  arm B at U ≈ 40M was considered and declined on the record (§0.3): a 25M-vs-40M bracket around a
  33M pivot sits inside the fitted law's own uncertainty, and a bracket that cannot fail is the
  error v2.0 was amended to remove.
- **The reference transliteration split is 4,500 sentences, not 16,241 items**, and the bootstrap
  unit is the sentence. Nothing here needs re-measuring.
- **Finding AE is not a threshold question and not a dedup question.** Measured unsampled over the
  whole training split and again against the freeze's removal list; the rate survives at 2.77%.
  **Do not re-derive the rate — extend the word list, and only with a native speaker.**
- **The substitution screen's precision is low on purpose and is documented.** Its false positives
  are English loanwords and `h`/`w`/`y`-heavy words the crude skeleton cannot match;
  `tests/test_substitutions.py` pins four so a later "improvement" has to notice it is
  invalidating the report's precision paragraph. **Do not filter on the screen unadjudicated** —
  it would delete `فروری`→`feb` along with `کرتے`→`baghaawat`.
- **Paragraph-level dedup is implemented, measured, and deliberately off** — 0.89% of line
  characters on Urdu Wikipedia. Dropping a line rewrites a document and invalidates the
  400-character floor stage 5 applied one stage earlier.
- **Chaining is bounded by measurement, not by design.** `largest_cluster` is the number to watch
  on any new source; capping it would be a second threshold nobody swept.

**Modelling and decoding**

- **The transliteration task is synthesized by a rule, not drawn from Roman-Urdu-Parl's pairs**,
  and that was a decision: §4.2 requires dynamic generation from clean text, and Finding AE
  measured that column as known-corrupt supervision. **Extend the caveat; do not re-derive it.**
- **The romanizer's residual 1.54-vs-0.93 fertility gap is vowel quality and no rule closes it.**
  It belongs in the report, not in another pass at the map.
- **The mixture is checked in the counters, not in a batch.** §4.2's shares hold in expectation at
  every microbatch; a per-batch count that does not match the table is not a defect.
- **The diffusion collapse is not a canvas-width artefact** (s22). Measured at 512 the collapse is
  *worse* (repetition 0.68 against 0.33). Ruling this out is what made Finding AO findable.
- **`</s>` is not hard-coded out of the diffusion decoder, and that is the decision.** It is
  genuinely in the training distribution as stage 10's document separator, so forcing it out would
  change a distribution rather than fix a framing. `sample_diffusion` forces only its own `<mask>`;
  everything else is `scripts/sample.py --forbid-eos`, swept and reported.
- **A4's schedules commit the same number of positions per step.** Drawing the count as well would
  make the schedules differ in two things at once and the ablation would not measure what it names.
  The cost — `random` is a fixed-count approximation rather than the process itself — is stated.
- **There is no KV cache in the AR decoder and there should not be one yet.** It would add an
  inference path through `Attention` that the diffusion arm cannot use and training never
  exercises, and §4.1's matched pair is held together by there being exactly one attention
  implementation. Revisit only if §8.4 needs thousands of generations — and then test for
  bit-identical logits before believing anything it produces.

**Hosting**

- **Kaggle is open again as of 2026-09-15** and is where the freeze is running. Phone
  verification retired both closures (Z′, AL) and Finding AU cleared the credential bug that made
  every upload fail. ⚠️ **Do not paste a Kaggle API token into `~/.kaggle/access_token`** — the
  Settings page tells you to, and it restores the broken auth path. `credentials.json` from
  `auth login` is what carries the right username.
- **This machine is the pilot host** — RTX 4060 Laptop, 8.19 GB, Ada, native bf16. It is a **proxy
  for the rented card, never a substitute**; what it establishes is the requirement.
- **Free RAM here is ~2 GB of 16 GB**, so this machine cannot stage a large intermediate and is
  **not** a candidate for the freeze's 32 GB CPU pass.

**The method lessons that kept paying**

- **Test the stages against a noisy source before trusting their thresholds** (Finding D, seven
  times over). Fixture tests prove a rule does what it says; only real text shows whether it fires
  on the right things. Corollary (s6): the distribution tells you where the documents are, not
  which are good. Corollary (Finding G): check the instrument can measure the quantity you are
  asking it for — a per-document statistic survives a sample and a per-*pair* one does not.
- **An aggregate can only say where to look** (s17) — and reading is not a check you run on a
  number, it is a different instrument (s18).
- **The bugs live at the seams** (Findings W, AN). Every stage's library is tested to pinned
  hashes; what fails is the code that *composes* them.
- **Read what the driver actually did, not what it was asked to do** (Findings AJ, AN, and session
  23's Wikipedia-only corpus). The realized mixture is where three of these became visible; the
  loss curve showed none of them.

---

## Open questions for you

**1. Config format** — ✅ decided in session 4: JSON for the whole data pipeline, stdlib-parsed and
fingerprinted into the manifest. Revisit only if training configs get unwieldy.

**4. Hardware here** — ✅ answered in session 21: an RTX 4060 Laptop, 8.19 GB, Ada (8.9), native
bf16, which had been behind a CPU-only torch wheel all along. `torch==2.13.0+cu126` is the version
the suite was written against, so only the backend changed. See "Settled → Hosting".

**2. Compute account — ⚠️ as of 2026-09-16 this is THE blocker. Nothing else is.** The freeze
finishes itself overnight; after that the only thing between here and a result is a rented GPU.

- **Kaggle is open** (`awaisbinadil`, phone verified 2026-09-15) and the freeze is running there.
  Notebooks have internet, `kaggle quota` reports GPU 30 h / TPU 20 h, and the code dataset
  uploads. Getting there cost Finding AU, not code.
- **A rented 32 GB Linux CPU box is now the fallback, not the blocker.** It is what happens if
  kernel 00's trial projects FineWeb2's pass past the ~12 h cap. ~14 h, **~$2–4**. Any provider
  does — Hetzner CX42-class, Vast, DigitalOcean — and `colab/freeze_colab.py` runs unmodified on it
  (`/proc/meminfo`, not a Colab API).
- **Set the provider spending limit when the account is created**, which is what PRD §9 wanted on
  day one, and the same account then answers the spot-GPU question for Week 9.
- **Budget context, rewritten by v2.4:** $0 of $150 spent and the plan is now **~$55**, so there is
  roughly 3× headroom. ⚠️ **This inverts how to pick the instance: choose for throughput, not
  price.** Two runs at the old 64,162 tok/s target are ~86 GPU-hours — **~3.6 days, ~$30**. The same
  two runs on this 4060 at ~14,200 tok/s are ~387 hours — **~16 days, $0**. Renting is the answer
  while the priority is time, and a *faster* card than a 4090-class one is now affordable where it
  was not at six runs. **The rule that does not change: measure throughput on the instance before
  committing the budget** (`scripts/train.py throughput`), which is exactly why G2 exists.

**3. Annotators — 🟡 downgraded 2026-09-16: not a training blocker, and its fate is an open
decision.** Nothing in the freeze or either run waits on a native speaker. But PRD §10's cut order
puts **human evaluation above the seeds that v2.4 already dropped**, so keeping §8.4 while cutting
seeds climbs the ladder out of order — that is the decision due before Week 12 (PRD §0.4). What
follows is what is at stake if it is kept.

§8.4 needs 3 fluent Urdu speakers for ~2 hours each in Week 13, and §8.2 needs ~200 hand-written
transliteration pairs. Both are favour-sized asks with weeks of lead time. What now rests on a
fluent reader who has not been lined up:

1. **§8.4's human evaluation is the only instrument in the plan that can separate the two arms.**
   §8.3's three metrics score fluent prose and slot-looping clauses within a few hundredths of each
   other — twice now, on two different pairs of checkpoints.
2. Stage 5's **29 disagreements** in `reports/quality_validation.json` (~20 minutes, and the
   highest-value single thing a native speaker could do).
3. The **225-candidate substitution screen**, `reports/eval/substitutions_screen.json`, ranked (~1 hour) —
   without it the Finding AE filter cannot be widened past eight confirmed words.
4. Stage 7's sampled pairs, and the PII pass's one ambiguous match.

Every Urdu judgement in `quality_validation.md`, `pilot_coherence.md` and `diffusion_scale.md` is
Claude's, and each report says so in those words.
[The annotation page](https://claude.ai/code/artifact/92e617de-5364-4273-8584-8ff1cc95dea2) renders
all 243 samples in nastaliq and records a verdict per sample per annotator — **the instrument
exists and only the people are missing.**

**5. The FIM framing — ⚠️ the share is answered; the framing is live, and it is the last
substantive open design question.**

*The share, closed 2026-09-14:* **keep §4.2's 10%**
([`infilling_share.md`](reports/infilling_share.md)). A matched Ravaan-AR pair at 50% against 10%,
one variable, both memorization gaps ~0.04: **50% costs +0.0374 held-out bpb (4.6%) and buys
+0.02–0.04 token-F1.** A poor trade on its own terms, and §3 of that report is why it is worse than
it looks.

*The framing, open:* **Finding AT** says the AR arm's infill deficit is not a data-budget
shortfall. Under `<lm>` it ranks the gold token **2**; under `<fim_middle>` — same checkpoint, same
position, strictly *more* information — it ranks it **74**, and the damage is **one position wide**
(d0 117, d1 11, d4 3.5, which is its own plain-LM rank). 5× the share moves d0 from 117 to 78 and
leaves it 20× worse than d1. To predict `middle[0]` the arm must reach back past the entire suffix
to where the prefix ended, and at 20M parameters it does not. The diffusion arm never faces this —
its canvas keeps the hole in place — and sits at rank 1–6 at every span.

**This is new evidence on a decision already taken.** Finding AQ was closed *not fixed* on
2026-09-13 knowing the layout had no **end** marker; it was not known that the same layout barely
learns the **start**, and a terminator does not fix the start. Three options, and the cost of all
of them rises steeply once Week 9 begins:

- **(a) Change nothing.** Defensible: the report states the defect and A2 is read as a statement
  about §4.2's FIM layout rather than about AR infilling in general. Costs nothing now, and costs
  the paper a weaker A2.
- **(b) Re-pilot one framing change** — ~2.7 h on the 4060, **$0**. A middle terminator, or the SPM
  ordering, which puts the middle adjacent to the prefix and directly addresses a
  reach-past-the-suffix failure. One run says whether it closes d0.
- **(c) Decide it is out of scope** and cut A2 from §4.4 rather than report an ablation whose name
  overclaims what it measured.

> **⚠️ v2.4 took half of (c) for an unrelated reason, so this question has changed shape.** A2 is
> **cut** — it cost a training run and the project now ships two — but it was cut on schedule
> grounds, not because the ablation was judged to overclaim. So the naming problem (c) worried about
> is moot, and what is left is a straight (a)-vs-(b) choice about the *arm itself*:
> **(a)** ship the AR arm on §4.2's layout as-is and carry Finding AT as a stated limitation — the
> report says our AR arm may be under-equipped for infilling and that MARIA measured the effect
> elsewhere; **(b)** spend ~2.7 h on the 4060, **$0**, to re-pilot one framing change (a middle
> terminator, or SPM ordering) before Week 9 and find out whether d0 closes.
> ⚠️ **(b) is cheap in money and is the last thing that can still delay the runs.** Under the
> wall-clock priority (a) is the consistent answer; (b) is the answer if the infill secondary
> endpoint is the one you care about. **This is the only open design question left.**

**6. Does PRD §6.2's Roman-Urdu-Parl warning get amended for Finding AE? — ✅ RESOLVED 2026-09-16
as option (b).** The argument for (a) was "do not bump the version for wording"; v2.4 bumps it
anyway for the run-count change, so (b) became free and was taken. §6.2 now names the wrong lexicon,
the eight words, the 52–93% occurrence rates and the **3.95% / 2.77%-after-dedup** figures; §8.2's
reference row gains "4,500 distinct sentences across 16,241 rows, effective *n* = 2,978". The
sibling decision — **filter or disclose** — was taken the same day: **disclose, do not filter.**
Original text kept below for the record.

Nothing in
the design changes and no number in the PRD moves, which is why session 18 did not bump the version
on its own. But §6.2 currently describes a *style* mismatch, and what was measured is a **wrong
lexicon** at 3.95% of rows.

- **(a) Leave the PRD at v2.3** and carry Finding AE in the technical report and in
  `reports/eval/transliteration_reference_set.md`. Cheapest, and §6.2's warning is directionally
  right.
- **(b) v2.4 — a wording amendment to §6.2 and §8.2 only.** §6.2's warning gains a sentence with
  the rate and the specificity; §8.2's "Transliteration (reference)" row gains "4,500 distinct
  sentences; see `reports/eval/`". Same class of change v2.2 was, with the same argument: the next
  person to read §6.2 will otherwise under-weight the human-written set exactly as this project did
  until session 18.

Either way, **§4.5's bootstrap must resample sentences, not rows** — that is not a wording question
and it holds regardless. ✅ **Now written into PRD §4.5 as a v2.4 bullet**, with the effective *n*.

---

## Open debts

Live only. Resolved notes have been dropped; they are in git at `8cecdfd`.

**Blocking the freeze's downstream steps**

- **⚠️ ~4.4% of the held-out split is likely inside FineWeb2 (Finding T)**, measured at 0.22% on a
  5% sample. §8.2's held-out native set is the primary endpoint's own instrument, so the freeze
  must run stage 8 **complete**, not sampled, and the report must state the measured number.
- **⚠️ 16.8% of the reference transliteration split's Urdu side is in Urdu Wikipedia (Finding Q)**,
  and Wikipedia is a training source. Stage 8 removes the contaminated *training* documents, which
  is correct and does **not** repair the metric — the test items remain compromised for any model
  trained on a corpus assembled before this ran. The report must state the 16.8% and say the
  reference-set transliteration number is weaker evidence than §8.2's human-written set.
- **⚠️ Finding AE's decision** — filter `roman_urdu` on the eight confirmed words (cheap, shallow,
  2.77% of surviving rows) or train as-is and state the rate. **Take it with the G1 re-check**, in
  that order: is arm A still fundable, and only then, what does filtering cost its margin.

**Things the report must say**

- ⚠️ **Every diffusion bits-per-byte figure carries an estimator error bar, and the AR ones do
  not** (Finding BA). The ELBO is a single-sample Monte Carlo estimate — one masking rate and one
  mask per sequence — measured at **sd 0.0069 on native Urdu** and **0.0307 on code-switched**
  over 6 draws on a frozen checkpoint. §4.5's primary endpoint therefore compares an exact NLL
  against a noisy bound, and **the AR/DIFF gap must be quoted against that sd, beside the result**,
  in the same place v2.4 already requires the single-seed caveat. The honest presentation averages
  K draws and says K; reporting one draw as if it were the checkpoint's bpb overstates precision.
- **Stage 5's 200-sample validation was adjudicated by Claude, not a native speaker.** The report
  must describe it as machine-adjudicated, in those words, until that changes.
- **Stage 8's precision is 0.73 and its errors are one named family** — bylines whose year differs.
  Session 11 added a second family, shared quotations, at precision 0.87. Both left in
  deliberately; the report states precision rather than implying the removals are all genuine.
- **The PII pass's recall gaps are stated rather than fixed** — Indian mobile formats, dot-separated
  numbers and `[at]` obfuscation are all measured in the FineWeb2 sample and all uncaught, because
  catching bare ten-digit runs is precisely what Finding V removed. `reports/pii.md` §6 is the list.
- **`script_ratio` is stage 5's weak rule**, precision 0.50, and **no threshold in the usable range
  beats 0.56** while the affected count moves 16×. The honest options are to drop it (stage 3
  already made the language decision on better evidence) or to replace Latin *share* with a test of
  whether the Latin is quoted material. Tuning the number is not an option. **Decide before the
  freeze.**
- **The duplicate-n-gram rules are near-inert** — 4 documents in 19,999 on Wikipedia, 0 on FineWeb2.
  Keep as a backstop with that stated, or drop. And the honest sentence about repetition is not
  "this corpus has little of it" but "**it had a great deal and FineWeb2 removed it before we saw
  the data**" (Finding H) — a statement about the source, not about Urdu.
- **Wiki markup is not HTML.** `{{Infobox}}` dumps clear `max_html_ratio` at any usable threshold;
  the fix belongs in Wikipedia-specific preprocessing ahead of stage 5, not in the threshold.
  `quality_validation.md`'s error budget needs one sentence corrected the next time it is touched:
  stage 5's false-accept rate is the filter's own, not a debt owed to a later stage (Finding I).
- **Stage 7's threshold is validated against clusters and pairs, not against read documents.**
  `reports/minhash_pairs_*.jsonl` is built to be read by a fluent speaker.
- **Hyperparameter provenance.** Preregistration §6 commits to taking the reference paper's config
  untuned and to stating that it likely favours AR. Record the source when the training config is
  finalised — not retroactively.

**Small and mechanical**

- ⚠️ **`--eval-limit` is a prefix, not a sample (Finding AZ)** — unfixed by choice, worked around
  with `--eval-limit 0`. The honest fix is to make `Trainer.evaluate` sample across populations, or
  to make the flag per-population; until then any *other* caller of `evaluate` has the same defect.
- **`RavaanDiffusion`'s `mask_id` is not in the run's `config.json`** — `ModelConfig.to_dict()` does
  not carry it, so a run record cannot say which absorbing token it trained against. Harmless while
  it resolves from the manifest; worth closing when the model card is written.
- **Two of §8.2's five test sets do not exist yet** — the ~200 human-written transliteration pairs
  and the ~300 real-OCR lines. Both are sentence/line unit; neither has been through stage 8.
- **`scripts/` has ~2,900 lines and thin test coverage, and Findings W and AN both lived there.**
  The properties worth covering are the ones where a driver *composes* stages: that
  `neardedup.py` writes stage 6's removals as well as stage 7's, that `decontaminate.py`'s removals
  are row ids rather than column variants, and that every driver applies stage 4 → stage 5 → PII
  before whatever it owns.
- **`reports/pilot_samples.md` still carries session 22's decoder grid.** `pilot_coherence.md` §10
  points at the new settings and `pilot_samples_v2.*` holds a three-prompt sweep; the full
  six-prompt regeneration is waiting on a free card.
- **`scripts/memorization.py`'s console table prints checkpoint basenames**, so two runs whose
  files are both `ar-s0_f1.pt` are indistinguishable in it. The JSON carries full paths.
- **Parquet shards are not resumable across a schema change** — a `.part` from a different pinned
  revision is only caught by the final digest check. Acceptable: revisions change rarely and the
  failure is loud.
- **Parallelizing normalization** — single-threaded is fast enough for one pass over 1.5 GB.
- **CI is untested — there is no GitHub remote yet.** `.github/workflows/tests.yml` runs ruff +
  pytest on 3.11 and 3.13 (two versions because Urdu handling depends on Unicode data, which moves
  between releases). It will run on the first push. Also: session 17 committed a 166 MB removal
  list and a download bundle by `git add -A`; **the blob is still in history and there is no remote
  yet**, so removing it is cheap now and will not be later.
- **Retry when convenient:** OpenReview `W5Ht05jF4c`, still behind browser verification. Low stakes
  now that both arms sit inside the fitted range.

---

## Next session

**START HERE. The compute phase is over and §4.5's primary endpoint is answered — the result is
the first thing in this file.** All three runs are on local disk, the instance is destroyed,
nothing is rented and nothing is accruing. Weeks 1–11 complete. **Nothing is blocked on compute
or money.**

```bash
ls -la /d/ravaan-runs/core-*/          # 3 runs, 6.3 GB each, 8 checkpoints + evaluation.json
git log --oneline -8                   # the result is committed
```

> ### ⚠️ The critical path is the annotators, and it is the only thing with lead time
>
> **G5 needs 3 fluent Urdu speakers for ~2 h each, and nobody has been approached.** §8.4 is the
> only instrument in the plan that can separate the two arms on generation quality — §8.3's three
> metrics score fluent prose and slot-looping clauses within a few hundredths of each other, twice
> now, on two different checkpoint pairs. §8.2 also needs **~200 hand-written transliteration
> pairs** and **~300 real-OCR lines** (~8 h of hand-correction); neither set exists and neither has
> been through stage 8. These are favour-sized asks with weeks of lead time and every other task
> below can be done alone. ⚠️ **PRD §10's cut order puts human evaluation *above* the seeds v2.4
> already dropped**, so keeping §8.4 while having cut seeds climbs the ladder out of order — that
> decision is due before Week 12 (PRD §0.4) and is still open.
> [The annotation page](https://claude.ai/code/artifact/92e617de-5364-4273-8584-8ff1cc95dea2)
> renders all 243 samples in nastaliq and records a verdict per sample per annotator.
> **The instrument exists and only the people are missing.**

**Next actions, in order. Everything here is $0 and runs on the idle 4060.**

1. **Average K = 9 draws for every diffusion number** (Finding BA), ~15 min. Takes urdu's sd from
   0.0069 to ~0.002 and is what lets the crossover table carry a real error bar instead of a
   caveat. It is also the only thing that settles whether `roman_urdu`'s 2.19σ seed difference is
   real. The scratch driver that measured the sd is the starting point; promote it to `scripts/`.
2. **Seed 1's fraction curve**, ~35 min:
   `python -u scripts/curves.py --run D:/ravaan-runs/core-diff-s1 --arm diff --seed 1 --corpus data/packed --corpus-arm A --out reports/eval/curve_diff_s1.json`
   Confirms the *held-out* descent replicates, not just the training trajectory — the training
   curves already agree to 0.007–0.06 bpt at every fraction.
3. **Week 12's eval**: §8.3's generation metrics, §8.3's infill exact-match and token-F1, and
   A3/A4's core-run sweep over the trained diffusion checkpoint. All built, all inference-only.
4. **The FIM framing** (open question 5, Finding AT) — still open, ~2.7 h on the 4060, $0. Under
   the wall-clock priority (a) "change nothing and state the limitation" was the consistent answer;
   the card is idle now, so (b) is cheaper than it was when the question was framed.
5. **`git remote`** — there still is not one, and session 17's **166 MB blob is in history**.
   Removing it is cheap now and expensive after the first push. CI has never run.

---

### The rented-box record — history, not a task. Kept for the lessons only.

Vast.ai RTX 5090, instance `51739847`, $0.5647/h, 2026-09-20 11:32 UTC → 2026-09-22, **destroyed**.
Three runs, **~46 GPU-h, ~$28** of the $40 loaded, against G2's $90 ceiling. Sustained **181,288
tok/s with no drift across 15.17 h**, and AR within 1.9% of it (Finding AM, reproduced on a rented
card). The chain ran unattended for 46 hours and needed no intervention.

- ⚠️ **The watchdog's trigger must be the *last* run in the chain.** It was armed on AR; adding a
  seed behind AR would have stopped the box two hours into it. **Premise next to the verdict:**
  add a fourth run and the watchdog must be rearmed again.
- ⚠️ **A sentinel is part of the trigger.** `.downloaded` → `.downloaded_all` was renamed because
  the two-run fetcher touches the old one the moment AR lands, which would have ended the new
  run's download grace before that run existed. **One added run cost three coordinated changes.**
- ⚠️ **The watchdog only ever *stops*, deliberately**, so the disk survives a failed download.
  Stop halts the GPU charge; **only destroy halts the $0.75/day storage.**
- ⚠️ **Wait on a file the producer writes, never a process name.** Git Bash has no `pgrep`, so
  `until ! pgrep -f foo.py` returns *immediately*. Session 23 hit this; session 28 hit it again.
- ⚠️ **Harness-tracked waiters get killed under memory pressure; `nohup`'d work does not.** Three
  waiters died in sessions 28–29 without the jobs they watched being touched.
- **Cost control as installed, and it held:** prepaid credit is a hard ceiling (**never enable
  Vast's automatic billing** — that removes it), the watchdog stops on the last run's own
  completion artifact using the instance's scoped `CONTAINER_API_KEY`, and the fetcher's sentinel
  ends the grace early.


**What DIFF s0 produced**, and the numbers the report starts from:

| | urdu | roman_urdu | code_switched | all |
|---|---|---|---|---|
| **bpb** (validation, 4,874 seqs) | **0.8052** | 1.5937 | 1.1340 | 0.9508 |
| **sd over 6 draws** (Finding BA) | ±0.0069 | ±0.0089 | ±0.0307 | ±0.0040 |

⚠️ **Both rows matter.** The first is an ELBO, so read it as **≤**. The second says it is one draw
from a distribution, not the checkpoint's bpb — see Finding BA before quoting any of it.

**G4's diffusion half, read 2026-09-21** — held-out validation bpb at §4.3's seven fractions,
`reports/eval/curve_diff_s0.json`, produced by `scripts/curves.py`:

| fraction | tokens | urdu | roman_urdu | code_switched | all |
|---|---|---|---|---|---|
| 10% | 0.99B | 0.8956 | 1.7351 | 1.2554 | 1.0509 |
| 25% | 2.47B | 0.8577 | 1.6577 | 1.1717 | 1.0048 |
| **50%** | **4.95B** | **0.8181** | 1.6375 | 1.1528 | 0.9691 |
| 100% | 9.90B | 0.8059 | 1.6220 | 1.1405 | 0.9564 |

**Legible and still descending at 50%, no plateau, no diffusion-only defect** — so G4's "no signal
by then" branch is not live on this half. ⚠️ **But most of the movement is spent by 50%**: on urdu,
10%→50% is **0.0775 ≈ 11 sd** of Finding BA's noise and is real, while 50%→100% is **0.0122 ≈
1.8 sd** on one draw per point and **is not separable from the estimator**. Do not describe the
second half's gain as measured without averaging draws first. AR's half of the gate lands with AR.

⚠️ **`scripts/curves.py` is new, and it exists because §4.3's "Evaluate every checkpoint" had no
driver** — `train.py run --evaluate` scores only the final model, so the seven checkpoints every
run writes had no reader and the curve G4 is *defined on* could not be produced. It scores
**validation, never test** (PRD §8.2 reserves test for the reported number, and G4 may act on what
it sees), calls `Trainer.evaluate` directly so the 100% point is comparable with the run's own
`evaluation.json` rather than merely similar to it, and **asserts exactly that at the end** — which
is how Finding BA was found rather than assumed.

**What the runs were launched with**, and the header to check any rerun against:

```bash
python -u scripts/train.py run --arm diff --size 70M --seed 0     --corpus data/packed --corpus-arm A     --tokenizer data/tokenizer/ravaan-16k.model --microbatch 16     --evaluate --eval-split validation --eval-limit 0     --out /workspace/runs/core-diff-s0
# corpus 45,340 sequences — 23,214,080 tokens · urdu 68.80 / roman_urdu 26.11 / code_switched 5.09
# Ravaan-DIFF at 70M: 69,975,680 parameters · 9.9e9 tokens over 75,531 steps · epochs 426.5
# tasks lm 65% infill 10% translit 10% restore 8% codeswitch 7%
```

⚠️ **`--eval-limit 0` is load-bearing** (Finding AZ) and **microbatch 16 is the measured optimum**
on the 5090 — 186,631 tok/s against 181,578 at 32 and 168,734 at 8. `--mask-id` is no longer
needed: the patched manifest carries `<mask>` = 4, which is the path the code intended.

### 1. ~~Finish the corpus~~ — ✅ DONE 2026-09-20. Kept as the record of how, not as a task

**✅ Stage 6+7 is done for all three sources.** FineWeb2's pass ran on **Kaggle** on 2026-09-16 in
**6.94 h for $0** — kernel 01, unsampled, `--single-pass`, sweep at 0.7/0.8/0.9. The rented 32 GB
box was never needed. What it produced is `reports/freeze/removals_67_fineweb2.txt`, **4,318 ids**
(4,182 near-duplicate + 136 exact), and all three lists load through `read_exclusions` with their
plan fingerprints matching the pinned corpus.

| | measured | had been projected |
|---|---|---|
| wall clock | **6.94 h** | 8.96 h (kernel 00's trial) |
| peak child RSS | **6.65 GB** | 14.5 GB |
| documents | **4,649,209** | 4,980,000 (`FINEWEB2_DOCUMENTS`) |
| kept | **99.91% of documents, 99.92% of characters** | "almost nothing removed" (Finding H) |

**⚠️ `largest_cluster` is 8, and that is the number this pass existed to produce.** Nothing caps a
component's size and the only prior evidence that 0.80 does not chain was Wikipedia's 23. The
sweep bounds it on both sides — 0.70 gives 30,783 removed with largest **50**, 0.90 gives 226 with
largest **2** — so **0.80 transfers to FineWeb2 and stage 7's threshold is settled on evidence from
every source.**

Two projection errors worth carrying, both in the safe direction and both the same shape as
Finding X: memory was over-projected by **2.2×**, and `FINEWEB2_DOCUMENTS` was **6.6% high**. A
projection from a 200k-document prefix was pessimistic, not optimistic — the per-document rate
*improved* as the index filled rather than degrading, which is the opposite of the worry that
justified the headroom.

**If a stage 6+7 pass ever has to run again**, the route is `kaggle/README.md` plus these:
`python kaggle/push.py code` (rebuild `ravaan-code.zip` from HEAD first), `push 00`, read its
verdict, `push 01`, `pull 01`. ⚠️ Kernel 00's output is the corpus mount for 01, so 00 must stay.
⚠️ `pull` writes the files nested at `reports/freeze/reports/freeze/` — move them up.
⚠️ If `kaggle config view` shows `username: del=…`, read Finding AU before doing anything else:
`mv ~/.kaggle/access_token ~/.kaggle/access_token.unused`, and do **not** paste a fresh API token
into that file, which is exactly what Kaggle's Settings page tells you to do.


**Stages 9 → 8 → 10 — 9 is done, 8 is running, 10 is chained.** The freeze finishes itself.

**✅ Stage 9, 2026-09-16, local, $0.** It is *two* passes, not one, and five things in the sketch
this file used to carry would each have failed. Recorded so they are not rediscovered:

```bash
# phase 1 — measure.  ~4.6 h
python -u scripts/split.py --source urdu-wikipedia --source fineweb2-urd_Arab \
    --source roman-urdu-parl --split train --limit 0 --measure-only \
    --exclude reports/freeze/removals_67_{wikipedia,fineweb2,roman}.txt \
    --plan-out reports/freeze/plan.json --json reports/freeze/split9_measure.json
# re-solve — 1 s.  the flag REPEATS; it is action="append", not nargs="+"
python -u -m ravaan.data.splits reports/freeze/plan.json \
    --chars-per-token urdu=3.8935 --chars-per-token roman_urdu=4.1928 \
    --chars-per-token code_switched=3.2758 -o reports/freeze/plan_resolved.json
# phase 2 — assign + write the held-out split.  ~4.3 h
python -u scripts/split.py --source … --split train --limit 0 \
    --config configs/data/splits_resolved.json --plan-in reports/freeze/plan_resolved.json \
    --exclude … --heldout-out data/freeze/heldout.jsonl --json reports/freeze/split9_assign.json
```

1. ⚠️ **`--split train` is mandatory.** The stage 6+7 lists were computed under it and their
   read-plan fingerprints only match under it — `roman-urdu-parl` is `db3a15522463a364` restricted
   against `3bcab08f4248f2fa` unrestricted, `fineweb2-urd_Arab` `54b744f92e3949f8` against
   `28e188b3d1cad629`. Without the flag stage 9 exits 1 on arrival. Wikipedia's fingerprint is
   identical either way, which is why a wikipedia-only test never caught it.
2. ⚠️ **`--measure-only` and `--heldout-out` cannot be combined** — `main()` returns after phase 1,
   so the held-out file is silently never written.
3. ⚠️ **The re-solve must precede the held-out write, not follow stage 8.** `chars_per_token` feeds
   `heldout_chars` → `test_from`/`validation_from`. urdu 3.5 → 3.8935 widens the held-out band ~11%,
   and documents in that sliver are *train* under the old bands and *held-out* under the new ones —
   so writing held-out first would hand stage 8 the wrong eval set and leave stage 10 training on
   documents that eval set contains.
4. ⚠️ **`--chars-per-token` is `action="append"`.** The one-liner with three values is an argparse
   error.
5. ⚠️ **`--plan-in` alone aborts phase 2.** `SplitAssigner.load_plan` refuses a config-fingerprint
   mismatch and `split.py` builds its assigner from `SplitConfig()` unless `--config` is given —
   default `23df13e0dfc3` against the re-solved `0f18ff46d95b`. The re-solved config is now written
   to **`configs/data/splits_resolved.json`** and handed to phase 2. This one surfaces ~4 h in.

**What stage 9 produced.** 6,463,060 documents measured, 6,242,081 assigned, 220,979 outside the
budgeted populations. **Arm A: 24.97M of 25M tokens, every population on target** — urdu
17.63M/17.65M, roman_urdu 5.88M/5.88M, code_switched 1.46M/1.47M. `data/freeze/heldout.jsonl`,
**106,195 documents, 46.5 MB**, counts verified against the log. Measured fertility landed close to
the ratios it was solved with: urdu 4.71 chars/word → 1.21 tok/word, roman_urdu 4.92 → 1.17,
code_switched 5.04 → 1.54.

**The G1 re-check is in much better shape than this file feared.** The gate line stage 9 prints is
against *arm B*; arm A's is computed separately and is what matters:

| population | supply | arm A needs | margin | stage 8 could remove |
|---|---|---|---|---|
| urdu | 3120.21M | 21.26M | 146.8× | 99.3% |
| **roman_urdu** | **18.10M** | **7.09M** | **2.55×** | **60.8%** |
| code_switched | 16.65M | 1.77M | 9.40× | 89.4% |

This file carried ~1.53× for `roman_urdu`. It is **2.55×**, so stage 8 must eat 61% of the pool
before "below 25M → stop" is live. Still pre-stage-8 — **re-run this table when stage 8 lands.**

**🟡 Stage 8, running.** Unsampled, `--both-columns`, 138,677 eval items / 3,203,208 distinct
shingles / 20,883 below `min_shingles` (exact-only). ⚠️ **The held-out file is split by population
before indexing, because the shingle unit is per test set**: `roman_urdu`'s items are median **42
chars with 94% under 100**, so word-unit shingling would have dropped nearly all of them — they get
`sentences` (char 5-grams, floor 25, 0.90) while `urdu` and `code_switched` (median ~1,300–1,450
chars) get word unit at 0.80. Both columns of `roman-urdu-parl:test` are indexed, which is the
cross-source case `decontamination.md` §7 says had never been measured. ✅ Verified before launch:
`--both-columns` checks exclusions on the **bare row id** ahead of `_variants`, so the stage 6+7 list
still applies, and `removals_8.txt` is written as row ids with the suffix stripped.

**🟡 Stage 10, chained behind it**, unattended. `pack.py` takes its splits config from `--plan-in`
(`pack.py:278`), so unlike `split.py` it needs no `--splits-config` and cannot hit defect 5 above.
It writes only what the arms and the held-out split draw — not the 3.1B-token train pool — so the
output is ~250 MB, not gigabytes.

**Disk is fine now** — 20 GB free on C:, not the 8 GB this file used to warn about.

### 2. ~~Then compute~~ — ✅ DONE 2026-09-20: Vast.ai RTX 5090, G2 PASS at 181,600 tok/s

§4.3's run is 70M params × 9.9B tokens, and **v2.4 makes it two runs, not six.**

| | tok/s needed | GPU-hours, 2 runs | wall clock | cost |
|---|---|---|---|---|
| **G2's bar at 2 runs ≤ $90** | **~21,400** | 257 | 10.7 d | $90 (the *ceiling*, not the plan) |
| v2.3's old bar at 6 runs | 64,162 | — | — | — |
| a 4090-class spot at 64,162 | — | **86** | **~3.6 d** | **~$30** |
| **this 4060**, measured ~14,200 | — | 387 | **~16 d** | **$0** |

> ✅ **Settled 2026-09-20 and the estimates below were all pessimistic.** A rented **RTX 5090**
> at **$0.5647/h** measured **181,600 tok/s** — 2× the "4090-class at 64,162" row this table hoped
> for and 8.5× G2's bar — so two runs are **30.6 h for $17.30**, not 86 h for $30. Two lessons
> worth keeping: **cost per token is nearly flat across consumer cards** (a 4090 at $0.27 and a
> 5090 at $0.45 land within a few dollars of each other on the whole job), so "pick for throughput,
> not price" is right for wall-clock and wrong for cost; and **datacenter cards are strictly worse
> here** — a 70M model cannot fill an A100 or H100, so they cost 2–3× more for the same 9.9B
> tokens. The rule that held: the measurement, not the spec sheet, decided it.

**Renting is the answer while the priority is time**, and the interesting change is that at two runs
the $150 cap has ~3× headroom — so **pick the instance for throughput, not price.** A card faster
than a 4090-class one is affordable now in a way it was not at six runs, and every hour it saves is
a day off the project. ⚠️ **What does not change: measure throughput on the instance before
committing the budget** (`scripts/train.py throughput`, which has §4.2's CPU cost in it). That rule
is the entire reason G2 exists, and a spec sheet has never been accepted here. Set the provider
spending limit when the account is created.

> **✅ The planning fork about U is resolved by v2.4, and not in the way it hoped.** The fork asked
> whether to add a run trained on the full ~170M-token pool, because arm A caps U at 25M and ~396
> epochs *on purpose* — that is what puts it 1.79× past C_crit and it is the whole point of §4.3 —
> while also making a poor model to hand anyone. **v2.4 ships two runs and no extras, so there is no
> separate publishable checkpoint.** The consequence must be stated rather than quietly absorbed:
> **what gets released is arm A's checkpoint, and arm A is deliberately deep into the repeat
> regime.** The model card must say so in plain words — this is a research artifact trained ~396
> times over 25M tokens to sit past C_crit, not a general Urdu model — and must not be presented as
> the best Urdu model the corpus could produce. Session 23 is the evidence for why that matters:
> going 7.36M → 186.9M unique tokens **fixed the script collapse** (Arabic-script share 0.250 →
> 1.000 unprompted) and **did not fix the slot-looping**.
>
> **Three things a release needs that the PRD does not yet cover.** (a) **Inference code ships with
> the weights** — `RavaanDiffusion` is not a `transformers` architecture, and from outside the
> model the schedule, the step count and forbidding `</s>` *are* the model (Findings AO, AR).
> (b) **The model card carries the ELBO-is-a-bound caveat, G3's verdict and the failure modes**, in
> the same words §4.3 and §11 require of the report — plus, new in v2.4, **the single-seed caveat**
> and **Finding AE's 2.77% rate**. (c) **Urdu Wikipedia is CC-BY-SA** and `data/manifest.json` flags
> it in `share_alike_sources`; whether share-alike reaches model weights is worth settling *before*
> publishing. §2.4's "no raw text redistribution" means the corpus ships as code, manifest and
> checksums either way.

### 3. The runs — 🟢 DIFF s0 DONE · AR s0 RUNNING · DIFF s1 CHAINED

**One AR, one diffusion, one seed each, same corpus, same budget, same tasks** (PRD §0.4) —
**plus a second diffusion seed, added back 2026-09-21.**
Resume is proven exact on both arms, so spot preemption is survivable and §9's
checkpoint-every-500-steps control is already in the loop.

**What v2.4 cut, and it is not coming back quietly:**

- **Seeds 2 and 3** — the primary endpoint is now a single paired comparison. See the state of play.
- **Ablations A1 and A2** — each cost a training run. A3 and A4 are inference-only, decode the
  trained diffusion checkpoint, and **survive unchanged**.
- ~~**The cheap crossover run**~~ — dropped 2026-09-16. It would have cost one extra run and no new
  data to de-confound session 23's repetition-versus-composition comparison by training a second
  diffusion arm on the *same* frozen corpus at the full ~170M-token pool. Worth ~$8 and a couple of
  days; **cut because it is not the primary endpoint and the priority is time.** ⚠️ Recorded rather
  than deleted: this is also the run that would have answered the publishable-checkpoint fork above,
  so cutting it is what makes the model-card wording in §2 load-bearing.
- ~~**A separate publishable checkpoint**~~ — same run, same decision.

✅ **The one add-back was taken, 2026-09-21: a second seed on the *diffusion* arm.** Declined and
then reversed the same day, and the reversal is the record — it is chained as `core-diff-s1`,
15.1 h and **$8.55**, bringing the plan to ~$28 of the $40 loaded. **What it buys and what it does
not:** it bounds the initialization noise the diffusion side is exposed to, which is the first
objection a reader raises at one seed. It does **not** make §4.5's endpoint seed-averaged — there
is still one AR seed, so the AR/DIFF gap remains a single paired comparison and v2.4's requirement
to write it as one is unchanged. What becomes sayable is whether the *diffusion* arm's own result
is stable across a draw.

⚠️ **Read it together with Finding BA.** Seed 1 bounds *initialization* noise; BA measured a
separate *estimator* noise of sd 0.0069 bpb on native Urdu that is present in every diffusion
number including seed 0's. Two different error terms, and a seed-to-seed difference smaller than
BA's sd says nothing about initialization at all.

### What the core runs and the eval are obliged to carry

- **G3 is recorded unmet on its own terms, and the report must not describe it as passed.** The
  gate's kill criterion reads "implementation bug — debug, do not scale", and no implementation bug
  was found; a 25M model at 368M training tokens over a 7.36M-token corpus is judged plausibly
  below the scale at which coherent Urdu is reachable at all, so the gate's *premise* is judged
  wrong rather than the code. **The accepted risk, named rather than filed away:** if there is a
  diffusion-only defect it surfaces only after the core runs are paid for. ⚠️ **v2.4 moves this risk
  in both directions at once** — two runs to lose instead of six, so discovery is cheaper; but **no
  seed replication**, so a bad diffusion run is harder to *diagnose* when it appears. The cheapest
  early warning is **G4** — arm A's curves at 50% of tokens — which should be read with this in mind
  and not only for the crossover, and which v2.4 leaves with no lever except the write-up. ⚠️ And the report must carry the **correction**, not just the conclusion: the
  original verdict rested on "AR is fluent on the same corpus", and Finding AS measured that control
  arm at +4.94 nats of memorization. A G3 section that quotes the original control without saying it
  was reciting the corpus is what a methods reviewer finds.
- **Infill exact-match is scored under a preregistered truncation rule** — the AR arm's generation
  cut to the gold span's token length (`preregistration.md` §8, 2026-09-13). It is the *symmetric*
  repair, because the diffusion arm is already given that length. The residue the report must state:
  **both arms are now told how long the answer is**, so the metric measures content, not length.
- **`</s>` must be forbidden when the diffusion arm decodes a fixed-width canvas** —
  `scripts/sample.py --forbid-eos always` (Finding AO). Stated in the report, not hidden in a
  default.
- **A3's table must not be written as "more steps, better"** (Finding AP), and **A4 has three arms
  and A3 a fifth rung**, logged as deviations (Finding AR). `gumbel=0` is `confidence` bit-for-bit,
  so the family contains its own limit and both preregistered settings are still measured and
  reported.
- **The diffusion ELBO is one-directional evidence.** §4.3 already requires the word "bound"; the
  consequence to state *beside every table* is that a bound can establish a diffusion win and can
  never establish an AR one.
- ~~**A2 measures §4.2's FIM layout, not "AR without FIM"**~~ — **A2 is cut in v2.4.** Finding AT
  stands and now enters the report as a **stated limitation rather than a measured quantity**: our AR
  arm may not be properly equipped for infilling under §4.2's layout — the exact hazard §4.1's
  fairness argument exists to guard against — and **MARIA (arXiv:2502.06901) reports the opposite
  result** on a properly-equipped AR model. Cite MARIA for the effect's existence and say plainly
  that **Ravaan did not measure its size on Urdu.**
- **The primary endpoint is one paired comparison and must be written as one** (v2.4). No
  between-seed interval, no claim that the sign was replicated, and the paired bootstrap's intervals
  labelled as resampling **eval items, not seeds**. Beside the result, not in a closing limitations
  paragraph.
- **Finding AE's 2.77% wrong-lexicon rate is disclosed, not filtered** (2026-09-16, PRD §6.2). Any
  transliteration claim resting on the reference set is weaker than §6.2's original wording implied,
  and the human-written set is the only instrument that can support one. **§4.5's bootstrap resamples
  sentences, not rows**, on that set — effective *n* = 2,978, not 16,241.
- ⚠️ **The `roman_urdu` held-out split was not decontaminated by stage 8** (Finding AW, 2026-09-17). It carries stage 7's within-source dedup only — which removed 82.4% of Roman-Urdu-Parl's characters before the split existed — and no containment pass. **The report must state this**, and state the reason it was judged tolerable: contamination there inflates held-out BPB for **both arms equally**, so the AR/DIFF crossover (the primary endpoint) is largely robust to it. What it does weaken is the **absolute** BPB figure and any transliteration claim resting on held-out Roman Urdu. The reference transliteration set (`roman-urdu-parl:test`, both columns) **is** fully decontaminated, so §4.5's secondary transliteration endpoint is unaffected.
- **§8.3's three generation metrics are a floor.** They catch a sample that stopped being Urdu and
  one that is four phrases on a loop, and they are blind to what actually separates the arms.

### Re-running things

```bash
# the two core runs, as launched on the 5090 (s27). --arm and --out are the only differences
python -u scripts/train.py run --arm diff --size 70M --seed 0 --corpus data/packed     --corpus-arm A --tokenizer data/tokenizer/ravaan-16k.model --microbatch 16     --evaluate --eval-split validation --eval-limit 0 --out runs/core-diff-s0
```

```bash
# G3's samples, ~8 min on the 4060
python scripts/sample.py --checkpoint runs/pilot/pilot-ar/ar_f1.pt \
    --checkpoint runs/pilot/pilot-diff/diff_f1.pt \
    --corpus data/packed-pilot --out reports/pilot_samples --samples 6 --new-tokens 160

# the pilot itself, ~5.5 h both arms
RAVAAN_EPOCHS=50 RAVAAN_SIZE=25M python -u kaggle/train_10_pilot.py

# the pipeline
python scripts/tokenizer.py sample|train|bench    # §7 — done, 2855877c8ecd38c9
python scripts/pack_pilot.py                      # G3's corpus
python scripts/train.py spec                      # §5's parameter assertion, both arms
python scripts/train.py throughput --corpus …     # G2, with §4.2's CPU cost in it
python scripts/train.py run --arm ar|diff …       # a run; §4.2 on by default, --no-tasks for a smoke test
python scripts/curves.py --run … --arm diff …     # §4.3/G4: score all seven fraction checkpoints
```

```bash
# G4's curve for a finished run. ~5 min per checkpoint on the 4060, resumable, validation only.
python -u scripts/curves.py --run "D:\ravaan-runs\core-diff-s0" --arm diff --seed 0 \
    --corpus data/packed --corpus-arm A --out reports/eval/curve_diff_s0.json
```

⚠️ **Wait on a file the producer writes, never on a process name.** `pgrep` does not exist in Git
Bash, so `until ! pgrep -f foo.py` returns *immediately* and a chained step starts against a job
that is still running — session 23 hit this with `pgrep` and session 28 hit it again the same way.
And ⚠️ **harness-tracked waiters still get killed under memory pressure while the `nohup`'d work
survives** — both happened in session 28, to the same job, without touching it.

`python -u` matters — the early prints have no `flush=True` and a redirected run looks hung.
**Read the realized mixture the driver prints, not the loss**: Finding AJ's starved mixture showed
up there and nowhere else, and Finding AN's bare objective showed up in neither.

⚠️ Finding AG applies hardest here: **the diffusion arm's per-step loss is a far noisier estimator
than AR's** — inside the noise at 300 steps of four sequences, clear at 1,200. A flat diffusion
curve in a short pilot is not evidence of anything.

### Running long passes on this machine

- Harness-tracked background jobs were killed three times under ~14 minutes; foreground calls cap
  at 10. **`nohup … &` as a detached process works** — sessions 9, 10, 11 and 23 confirm it.
- ⚠️ **Harness-tracked background waiters get killed under memory pressure and `nohup` ones do
  not.** Session 23 lost three pollers to "system is running low on memory" while a 2.7 h training
  run and its three chained successors ran to completion untouched. **Chain the work itself; poll
  it as little as possible.** It is the bash `sleep` loop that dies; the Python does not.
- ⚠️ **Chain on a condition the producer actually writes.** Session 23's first chain used `pgrep`,
  which Git Bash does not have, so the wait fell through and packing started on a half-written
  corpus. The form that worked:
  `until grep -q "<the producer's own completion line>" <log>; do sleep 15; done`
- Two concurrent passes over the *same* parquet file took ~50 minutes where either alone is ~20.
  Parallel passes are free in cores and are not free when they contend on one file.
- The pip cache reached 6.2 GB against 2.2 GB free once. `python -m pip cache purge` reclaims it.
