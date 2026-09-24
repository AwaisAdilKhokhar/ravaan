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

> ## 🌐 THE CODE IS PUBLIC AND THE DEMO IS HOSTED, 2026-09-24 (session 35)
>
> **<https://github.com/AwaisAdilKhokhar/ravaan>** — public, Apache-2.0, 106 commits of history
> plus four from this session. **Session 34's two debts are paid**: the repository the model cards
> link to now exists, and everything from sessions 34 and 35 is committed.
>
> **<https://awaisadilkhokhar.github.io/ravaan/>** — the interactive decoder demo, on GitHub Pages
> via the `site/` + Actions workflow pattern `modelDNA` already uses. No sign-in, unlike the
> artifact host, which is why this is the link to put in a post.
>
> ✅ **Finding BP now has an artifact that *shows* it rather than stating it.** BP measured the
> diffusion arm sampling 17.9× faster and noted no artifact said so. `scripts/demo_trace.py`
> records, for every position, **which forward pass committed it**; the page replays both arms on
> one clock, one tick per forward pass, so diffusion visibly finishes at pass 8 while the AR arm
> is on token 8 of 32. `scripts/decoder_gif.py` renders the same trace as a 1200×628 GIF.
>
> ✅ **The traced loop is asserted equal to the shipped one, every run.** `sample_diffusion` has no
> hook for intermediate state, so `_trace_diffusion` re-implements its commit loop — and then
> checks its output token-for-token against the real sampler for the same seed, failing hard on a
> mismatch. This is Finding BQ's lesson applied before the fact rather than after it: a
> re-implementation verified by reading is not verified.
>
> ⚠️ **The demo's samples are selected, and the page says so in the page.** Best of 16 seeds per
> arm under one rule applied independently to both; all 320 draws ship in
> [`demo_trace_pool.json`](reports/demo_trace_pool.json) with the reason each was rejected. The
> prompts are **hand-written, not held-out** — short, because short sentences are readable, and
> chosen by someone who knows what the model does well. That is a selection effect and it is named
> on the page rather than absorbed.
>
> ✅ **CI ran for the first time in the project's life and was worth having** — see Finding BR. It
> was red on 28 ruff findings, **two of them real bugs**, and then red again for a different
> reason. Both workflows are green as of 2026-09-24.
>
> **New findings: BR (the gate that never ran), BS (§8.3's repetition rate is the wrong instrument
> at demo length), BT (byte fallback and Nastaliq both defeat per-token rendering).**
>
> ⚠️ **Spend unchanged at ~$1.90 — session 35 cost $0.** Everything ran on the idle 4060.

> ## 📦 IT IS PUBLISHED, 2026-09-23 (session 34)
>
> **Both models are public on the Hugging Face Hub, Apache-2.0, as a matched pair.**
>
> | | | held-out urdu bpb |
> |---|---|---|
> | [`AwaisAdilKhokhar/ravaan-diff-70m`](https://huggingface.co/AwaisAdilKhokhar/ravaan-diff-70m) | `ship-diff-b64`, 64 epochs | **0.7659 ± 0.0018** (K = 9) |
> | [`AwaisAdilKhokhar/ravaan-ar-70m`](https://huggingface.co/AwaisAdilKhokhar/ravaan-ar-70m) | `ship-ar-b/ar-s0_fp25`, **4 epochs** | 0.7774 exact |
>
> **Landing page:** <https://claude.ai/artifact/S6Pzi3VP9LWGdJniB8n5BL> — private until shared from
> the page's own share menu. Source is committed: `release_assets/landing.template.html` plus
> `scripts/landing.py`, which rebuilds `reports/landing.html` **byte-identical** to what was
> published. The page is not in the scratchpad and does not depend on a session.
>
> ✅ **The AR half is the 4-epoch checkpoint, deliberately, and its card says why** — it is
> Finding BF made legible. Releasing the arm at the rung where it was actually good, and
> explaining that 16 epochs made it *worse*, is what turns the baseline from a formality into the
> evidence for the crossover. It is the better of the two cards for that reason.
>
> ✅ **Neither released checkpoint memorizes** — [`overlap_release.json`](reports/eval/overlap_release.json),
> measured on the **released** checkpoints rather than inherited from `ship-diff-b`:
>
> | | 16-gram | 32-gram | 64-gram | 128-gram |
> |---|---|---|---|---|
> | released AR (`fp25`, 4 ep) | 0.000 | 0.000 | 0.000 | 0.000 |
> | released DIFF (`b64`, 64 ep) | 0.000 | 0.000 | 0.000 | 0.000 |
> | held-out Urdu (control) | 0.000 | 0.000 | 0.000 | 0.000 |
>
> ⚠️ **`--verify` had nothing to verify** — there were no n ≥ 16 matches to byte-check. The
> control row is what makes the zeros mean something rather than meaning the instrument is blind.
>
> **What shipped with the weights** (PRD §2's three requirements, all met): safetensors rather
> than a pickle; a vendored torch-only `ravaan_infer/` package because `RavaanDiffusion` is not a
> `transformers` architecture; a `generate.py` whose defaults are **8 steps / gumbel 2 /
> `--forbid-eos`**, each named in the card as measured rather than preferred (Findings BG, AR, AO);
> and a card carrying the ELBO-is-a-bound asymmetry, the single-seed caveat, Finding AE's 2.77%,
> Finding AW's undecontaminated `roman_urdu`, Finding T's ~4.4%, G3's unmet verdict, and the fact
> that **every Urdu judgement in this project is an LLM's** because G5's annotators were never
> recruited.
>
> ✅ ~~**Two debts this session created and did not pay.**~~ **Both paid in session 35.** The
> repository exists, is public, and carries every artifact of sessions 34 and 35; the cards' link
> resolves. See the 🌐 block above.
>
> ⚠️ **The HF write token was pasted into a chat transcript and must be rotated.** **Still open
> as of session 35** — the only debt from this session that is still outstanding.

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
>
> > ✅ **The diffusion column now carries an error bar, 2026-09-23 (session 33).** Nine seeded
> > draws of the full validation split at every rung (`scripts/elbo.py`,
> > [`elbo_diff_s0.json`](reports/eval/elbo_diff_s0.json)) — Finding BA is retired as a caveat on
> > this table and replaced by a number:
> >
> > | fraction | epochs | **Ravaan-DIFF, K = 9** | sem | single draw, as first reported |
> > |---|---|---|---|---|
> > | 1% | 4.3 | 1.1623 | 0.0009 | 1.1624 |
> > | 2% | 8.5 | 1.0370 | 0.0012 | 1.0350 |
> > | 5% | 21.3 | 0.9419 | 0.0013 | 0.9405 |
> > | 10% | 42.6 | 0.8950 | 0.0016 | 0.8956 |
> > | 25% | 106.6 | 0.8520 | 0.0017 | 0.8577 |
> > | 50% | 213.2 | 0.8239 | 0.0018 | 0.8181 |
> > | 100% | 426.5 | **0.8072** | 0.0017 | 0.8059 |
> >
> > **Every rung moves by less than 0.006 and the shape is untouched**, so the crossover stands
> > exactly as reported — the descent is monotone, it never regresses, and no rung's shift is
> > large enough to move the crossing. **The AR arm needs none of this**: its NLL is exact.
> > ⚠️ **The sem is the estimator's alone.** It says nothing about initialization (that is seed
> > 1's job) and nothing about the single-seed limitation, which v2.4's requirement to write the
> > endpoint as one paired comparison still governs.
> Curves: [`curve_ar_s0.json`](reports/eval/curve_ar_s0.json),
> [`curve_diff_s0.json`](reports/eval/curve_diff_s0.json), both by `scripts/curves.py`.

> ## 🚀 A releasable checkpoint exists, 2026-09-22
>
> **The core runs cannot be released — they are memorizers (Finding BD) — so a shippable model was
> trained on the data the experiment never used.** Arm B: **85,362,688 unique tokens**, 3.7× arm A and
> a cleaner mixture (74.27% native Urdu against 68.80%). Both arms, 16 epochs, **~$4.10** on a rented
> 5090. Held-out validation bpb on native Urdu at the seven fractions:
>
> | epochs | **Ravaan-AR** | **Ravaan-DIFF** |
> |---|---|---|
> | 0.16 | 1.4557 | 1.6144 |
> | 0.32 | 1.1946 | 1.5254 |
> | 0.80 | 0.9455 | 1.2217 |
> | 1.60 | 0.8325 | 1.0881 |
> | **4.00** | **0.7774** ← AR's best | 0.9637 |
> | 8.00 | 0.7887 | 0.8841 |
> | 16.00 | 0.8690 | **0.8320** ← DIFF's best |
>
> ✅ **Ship `ship-ar-b/ar-s0_fp25.pt`.** At **urdu bpb 0.7774** it is the best Urdu model the project
> has produced — against arm A's best 0.8311 and `core-ar-s0`'s final **3.6143** — and it reads as Urdu
> (repetition 0.013, longest repeat 2–7). The diffusion arm wins the *shared endpoint* at 16 epochs but
> **collapses into slot-looping when it generates** (repetition 0.124, `مہار مہار مہار`), so it is the
> better likelihood model and the worse generator. §8.3 and §4.5 disagree again, and this time on the
> same corpus.
>
> ✅ **Neither shippable checkpoint memorizes.** Verbatim overlap against the 85.4M-token arm-B stream,
> byte-verified, with real held-out Urdu as the control:
>
> | | 16-gram | 32-gram | 128-gram |
> |---|---|---|---|
> | `core-ar-s0` (arm A, 426 ep) | **0.251** | **0.249** | **0.111** |
> | ship AR `fp25` (arm B, 4 ep) | 0.000 | 0.000 | 0.000 |
> | ship DIFF `f1` (arm B, 16 ep) | 0.000 | 0.000 | 0.000 |
> | held-out Urdu (control) | 0.000 | 0.000 | 0.000 |
>
> ⚠️ **This is not the experiment, and it does not revive arm B.** PRD §0.3 dropped arm B because
> `roman_urdu` supply is 0.44× of its 23.53M requirement; the 85.4M stream on disk does **not** hold
> §6.1's 120:40:10 mixture, so **U is confounded with composition** — the exact confound §4.1 exists to
> forbid. §4.5's primary endpoint remains arm A's crossover and nothing here touches it. That the
> crossover reappears on arm B between 8 and 16 epochs is an observation, **not a bracket test of
> C_crit**, and the report must not write it as one.
>
> ⚠️ **The diffusion numbers are single-sample ELBO draws (Finding BA).** `evaluation.json` says 0.8247
> and the curve's own 100% point says 0.8320 — **1.06 sd apart on BA's 0.0069**, and `curves.py` refused
> to assert the two matched, naming BA rather than calling it a defect. The AR arm reproduces to 1e-4
> because its NLL is exact. **A bound still cannot establish an AR win**, which is the direction this
> table runs.
>
> > ✅ **Resolved 2026-09-23 (session 33). The 16-epoch diffusion number is 0.8322 ± 0.0018**, the
> > mean of **nine seeded draws** of the full validation split (`scripts/elbo.py`,
> > [`elbo_diff_b.json`](reports/eval/elbo_diff_b.json)). Single-draw sd on this checkpoint is
> > **0.0053**, so BA's 0.0069 was if anything pessimistic, and K = 9 delivers the ~0.002 it
> > predicted. **The disagreement resolves with a direction:** the curve's 0.8320 sits **0.04 sd**
> > from the mean and the run's own `evaluation.json` 0.8247 sits **1.41 sd** below it — the table
> > above was quoting the good draw and the run record holds the outlier. The endpoint gap is
> > therefore **0.8690 exact against 0.8322 ± 0.0018**, about 20 sem, and it is now a measurement
> > with a bar rather than a number with a caveat. ⚠️ **Only the 100% rung is averaged so far**;
> > the other six, and all of arm A's, are still single draws until the chained pass lands.
>
> ⚠️ **70M over 85.4M unique tokens is already Chinchilla-optimal** — 16 epochs is 1,365,803,008 tokens,
> and ÷20 is 68.3M against the model's 69.98M, within 2.5%. **Data is the ceiling, not compute or
> money**: a larger model over the same corpus buys more memorization capacity, not more Urdu. The only
> thing that raises this ceiling is more corpus.
>
> > ⚠️ **Amended 2026-09-23 (session 32). Both halves of that paragraph are AR's, and neither binds
> > the diffusion arm.** The Chinchilla arithmetic is a statement about a model that scores every
> > position; the diffusion objective scores only the masked ones, ~half of them on average, and
> > **Finding BG** measures the consequence — at 16 epochs AR had turned and DIFF was still descending
> > at −0.0520 bpb per doubling. And "the only thing that raises this ceiling is more corpus" is
> > wrong twice over: **Finding BH** shows more epochs raise it for ~$5, and the corpus is *already
> > on disk* — the frozen plan holds **12.14B characters** of native Urdu train band against arm B's
> > 247M drawn. What caps arm B is §6.1's fixed mixture, not the supply.
>
> ⚠️ **Every Urdu judgement here is Claude's**, as in every other report in this repository.
>
> Curves: [`curve_ar_b.json`](reports/eval/curve_ar_b.json),
> [`curve_diff_b.json`](reports/eval/curve_diff_b.json). Samples:
> [`ship_samples.md`](reports/ship_samples.md). Overlap: [`overlap_armb.json`](reports/eval/overlap_armb.json).

> ## 🥇 The shippable diffusion model exists, and it beats the AR arm, 2026-09-23
>
> **`ship-diff-b64` ran: 64 epochs, arm B, 5.46B tokens, 8.2 h on a rented 5090 for ~$4.60.**
> Held-out validation bits-per-byte on native Urdu, the seven rungs `checkpoint_fractions` wrote:
>
> | epochs | **urdu** | roman_urdu | code_switched | all |
> |---|---|---|---|---|
> | 0.64 | 1.2864 | 2.2916 | 1.8049 | 1.4752 |
> | 1.28 | 1.1188 | 2.0821 | 1.6095 | 1.2996 |
> | 3.20 | 0.9793 | 1.9227 | 1.3887 | 1.1540 |
> | 6.40 | 0.9232 | 1.8153 | 1.3072 | 1.0883 |
> | 16.00 | 0.8619 | 1.6967 | 1.1837 | 1.0152 |
> | 32.00 | 0.8032 | 1.6425 | 1.1336 | 0.9575 |
> | **64.00** | **0.7646** | **1.5648** | **1.0559** | **0.9110** |
>
> ✅ **The diffusion arm beats the AR arm's best on the same corpus: 0.7646 against 0.7774.**
> That is the comparison the project has never been able to make — until now the best AR
> checkpoint was arm B and the best diffusion was arm A, and every artefact had to disclose it.
> **Both released models are now on one corpus and the caveat is gone.**
>
> ✅ **Finding BH's fit held and was pessimistic.** It predicted ~0.777 at 64 epochs from three
> points; the measurement is **0.7646**. The realized per-doubling ratio is **0.66** against the
> fitted 0.65.
>
> ⚠️ **It still has not turned.** The last doubling bought **−0.0386** (0.8032 → 0.7646). AR
> turned at 4 epochs on this corpus and was being actively ruined by 16; this curve is still
> descending at 64. **More epochs would still buy**, and the same arithmetic that made this run
> worth $6 now points at 128 for ~$11.
>
> ✅ **The 16-epoch rung reads 0.8619 against `ship-diff-b`'s 0.8320, exactly as predicted.**
> The cosine anneals over `total_steps`, so at 64 epochs it has not finished at 16. Predicted
> before the run, confirmed after — it is the schedule, not a regression, and the two numbers are
> not comparable.
>
> ⚠️ ~~**These seven are single ELBO draws (Finding BA).** The 0.0128 margin over AR's exact
> 0.7774 is ~2.4 single-draw sd, so the win is real but wants `scripts/elbo.py` at K = 9 before it
> is written down as a result.~~
>
> > ✅ **DONE 2026-09-23 (session 34). The bar is on, and the result got slightly better.**
> > Nine seeded draws of the full validation split on `diff-s0_f1_weights.pt`
> > ([`elbo_diff_b64.json`](reports/eval/elbo_diff_b64.json)):
> >
> > | population | K = 9 | sem | sd | single draw, as first reported |
> > |---|---|---|---|---|
> > | **urdu** | **0.7659** | 0.0018 | 0.0054 | 0.7646 |
> > | roman_urdu | 1.5653 | 0.0047 | 0.0140 | 1.5648 |
> > | code_switched | 1.0796 | 0.0096 | 0.0288 | 1.0559 |
> > | all | 0.9128 | 0.0015 | 0.0045 | 0.9110 |
> >
> > **The endpoint is 0.7659 ± 0.0018 against AR's exact 0.7774 — a margin of +0.0115 bpb, which
> > is 6.4 sem.** Not 2.4 draws of noise; a measurement. ✅ **And the draw this file had been
> > quoting was honest**: 0.7646 sits **−0.24 sd** from the mean, so unlike Finding BJ's case
> > (where the run record held a 1.41 sd outlier) nothing here was being flattered by a lucky
> > sample. ⚠️ **The sem is still the estimator's alone** — one seed per arm, and v2.4's
> > requirement to write the endpoint as a single paired comparison is untouched.
> >
> > ✅ **Arm B's seven-rung curve is also averaged now** — `elbo_diff_b_curve.json`, 7 checkpoints
> > × 9 draws, finished 17:52. Arm A's is [`elbo_diff_s0.json`](reports/eval/elbo_diff_s0.json).
> > **Finding BA is fully retired for every diffusion number this project reports except the six
> > lost `ship-diff-b64` rungs**, which can never get one (Finding BM).
>
> ⚠️ **Six of the seven checkpoints died with the instance and only the 64-epoch one was saved.**
> The link ran at 19 KB/s direct and the run wrote 5.9 GB; what came back is
> `diff-s0_f1_weights.pt`, **optimizer state stripped** (839 MB → 280 MB, md5-verified, load-tested,
> 69,975,680 parameters). `curve.json` holds all seven rungs *scored*, so the curve above is
> complete — what is gone is the ability to put a bar on any rung but the last, or to resume
> training. Neither blocks the release; both are permanent. See Finding BM.
>
> Curve: [`curve_diff_b64.json`](reports/eval/curve_diff_b64.json) (copied into the repo, session 34 — the run dir on `D:` was its only home and it holds the six lost checkpoints' scores).
> Checkpoint: `D:/ravaan-runs/ship-diff-b64/diff-s0_f1_weights.pt`.


> ## ✅ ~~The shippable diffusion model is one ~$6 run away~~ — TAKEN, 2026-09-23
>
> **The run happened and the block above is the result. Kept because the reasoning is what
> justified the spend, and it was right: the fit predicted ~0.777 and the measurement came in
> at 0.7646.** What follows is the brief as it stood before the run.
>
> **The diffusion arm was stopped while it was still descending, and the reason it was stopped is
> the experiment's, not the model's.** §0.4 requires both arms to take the same budget, so both
> ended at 16 epochs — but at that point AR had turned two rungs earlier and DIFF had not turned at
> all:
>
> | epochs | **AR** | Δ | **DIFF** | Δ |
> |---|---|---|---|---|
> | 4.00 | **0.7774** | −0.0551 | 0.9637 | −0.1244 |
> | 8.00 | 0.7887 | **+0.0113** | 0.8841 | −0.0796 |
> | 16.00 | 0.8690 | **+0.0803** | **0.8320** | **−0.0520** |
>
> **DIFF's last doubling bought more than AR's best doubling ever did.** The near-proof that this
> continues is not extrapolation: `core-diff-s0` reached **0.8059 on arm A** — a corpus 3.7× smaller
> and a worse mixture — by running 426 epochs. Arm B's diffusion had strictly better data and was
> cut off at 16. Fitting the three deltas (ratio ≈0.65/doubling) puts **64 epochs at ~0.777**, level
> with AR's best, and 256 at ~0.754. ⚠️ **That column is a three-point log-linear fit, not a
> measurement** — arm A's own deltas wobble (−0.0379 then −0.0396) and the fit's own limit is only
> ~0.74, so the prize is a few hundredths of a bpb, not a transformation.
>
> **Cost, at the 5090's measured diffusion throughput (~175k tok/s) and $0.5647/h:**
>
> | epochs | tokens | wall clock | GPU | all-in |
> |---|---|---|---|---|
> | 32 | 2.73B | 4.3 h | $2.45 | ~$3 |
> | **64** | **5.46B** | **8.7 h** | **$4.90** | **~$6** |
> | 128 | 10.9B | 17.3 h | $9.79 | ~$11 |
> | 256 | 21.9B | 34.7 h | $19.59 | ~$22 |
>
> ✅ **Take 64, not 32 and not 256.** `checkpoint_fractions` writes seven checkpoints per run, so a
> 64-epoch run lands rungs at **0.64 / 1.3 / 3.2 / 6.4 / 16 / 32 / 64 epochs** — four new points past
> where the curve stopped. One run both produces the candidate checkpoint *and* answers whether
> epochs are still buying anything, which is the question that decides whether the $22 version or the
> corpus rebuild is worth doing. Going straight to 256 spends 4× to learn the same thing later.
>
> ⚠️ **You cannot resume `ship-diff-b` to get there, and this is the detail that will cost money if
> it is missed.** `RavaanTrainingConfig.lr_at` is cosine to 10% of peak over `total_steps`, so the
> existing checkpoint has already annealed. **64 epochs is a fresh run at the full price**, and its
> 16-epoch rung will read slightly *worse* than the current 0.8320 because the cosine has not
> finished there. That is expected, not a regression, and not a reason to stop the run.
>
> ✅ **A second thing the run buys, worth the $6 on its own: a matched-corpus release pair.** The
> demo currently has to disclose that AR is arm B and DIFF is arm A (session 32). A 64-epoch arm B
> diffusion run puts both released models on one corpus and that caveat disappears.
>
> **Everything needed is already on disk** — `vast/push.sh` ships the 169 MB arm-B corpus and the
> runbook is proven over 46 unattended GPU-hours. The edits are three lines; see "Next actions".

- **Started** 2026-08-03 (Week 1 of 16). **PRD v2.4** (2026-09-16). **Spend: first money went
  out 2026-09-20 — $40 loaded on Vast.ai, **~$28 committed to three runs** (the two core runs plus
  the second diffusion seed added 2026-09-21), of $150.**
  Everything before this was $0: the whole corpus freeze ran local, on Colab and on Kaggle.
  **Session 33 spent ~$7.90 of the ~$9.80 that remained** — ~$4.60 on `ship-diff-b64` itself,
  ~$1.85 on a finished box idling because nothing was watching (Finding BN), ~$0.75 on getting
  6 GB off a 19 KB/s link (Finding BM) and ~$0.40 on a shared-GPU dud and two false starts
  (Finding BL). **~$1.90 is left, which does not rent anything** — the 128-epoch continuation
  Finding BK points at needs a top-up, prepaid only, never automatic billing. **Both instances
  destroyed 2026-09-23; nothing is accruing.**
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
- **Git:** branch `stages-7-and-8`, **70 commits ahead of `main`** (main is at session 8 —
  fast-forward it when convenient). ⚠️ **Session 34's work is uncommitted.**
  ✅ **History was rewritten 2026-09-23 and the repository is now pushable.** `git-filter-repo`
  dropped session 17's **166 MB `removals_67_roman.txt`** and a stray 12 MB zip from every commit:
  **`.git` 54 MB → 15 MB, largest remaining blob 19.9 MB, all 106 commits preserved, and the HEAD
  tree hash is byte-identical before and after** (`d590db1a…`) — so nothing in the working tree
  changed, only history. **Pre-rewrite backup: `D:/ravaan-git-backup.git`**, keep until the first
  push is confirmed. There is still **no remote**, and both published model cards link to
  `github.com/AwaisAdilKhokhar/ravaan`, which does not yet exist.

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
| **Ablations A3/A4** — inference only | §4.4 | ✅ **s32** — swept at full scale over `ship-diff-b/diff-s0_f1.pt`, 300 generations → **Finding BG**. A3 runs backwards here too, so AP replicates at 70M/85.4M. ⚠️ Re-sweep on the 64-epoch checkpoint when it lands |
| ↳ ⚠️ **A2 measures §4.2's FIM layout, not "AR without FIM"** — MARIA reports the opposite | §4.4 | ⚠️ **A2 cut in v2.4** — Finding AT becomes a stated limitation; the report must say so |
| **The microbatch that reproduces session 23's runs is 32** — nothing recorded it | §4.1 | ✅ identified from `pad_tokens` 11039 |
| **`scripts/train.py --tokens / --epochs / --warmup-steps`** — `--steps` never moved the cosine | §4.3 | ✅ s23; every earlier short run trained at near-peak LR throughout |
| **`pin_utf8_streams()` reaches all sixteen drivers** — session 14's class fix, finished | — | ✅ s23 |
| **Core runs (W9–11, G4)** → eval (W12) → human eval (W13, **G5**) → demo (W14) → report (W15–16) | | ⬜ |

---

## Findings register

Seventy-one findings are referenced across this file, the PRD and the reports, and until now they
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
| AP | 22 | A3 runs backwards — 64 denoising steps repeat *more* than 8, monotonically on every axis | ~~⚠️ directional, one seed~~ → ✅ **replicated at full scale, s32 (Finding BG)**: 8 steps beat 160 on a 70M checkpoint over 85.4M tokens, same direction. **A3's table must not be written as "more steps, better"** |
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
| BD | 31 | **Ravaan-AR's fluency at 426 epochs is literal recitation, and §8.3's metrics cannot see it.** `core-ar-s0`'s final checkpoint reproduces **24.9% of its 32-token windows, 16.5% of its 64-token windows and 11.1% of its 128-token windows verbatim** from the arm-A training stream, byte-verified against the packed tokens. The control — real held-out Urdu the model never trained on — scores **0.000** at every n ≥ 16, which is what makes the AR figure a measurement rather than an anecdote. ⚠️ **§8.3's three metrics rank this checkpoint *above* the diffusion arm** (script 0.96, repetition 0.000): a reader of that table would conclude it writes the better Urdu. It is reciting the corpus, in one case a 128-token block of Quranic exegesis. **This is the mechanism behind Finding BC's 3.6143 bpb** — a confidently-wrong memorizer — and it is the number the report needs beside any generation-quality claim. `scripts/overlap.py`, [`overlap.json`](reports/eval/overlap.json) |
| BE | 31 | **The microbatch optimum is a property of the host, not the card, and must be re-measured on every box.** The core runs' RTX 5090 peaked at microbatch **16** (186,631 tok/s against 181,578 at 32). Session 31's RTX 5090 — same card, same model, same task mixture — peaks at **32**, and is **43% slower at 16**: 122,933 vs 175,821 tok/s, with 48 and 64 falling back to 166,685 and 157,753. Inheriting the previous box's setting would have cost ~2 GPU-hours on a 4-hour job. ⚠️ **`train.py throughput` could not measure this until session 31** — it hardcoded `arm="A"`, so a box holding only arm B's streams could not be measured at all. `--corpus-arm` added |
| BF | 31 | **On arm B the two arms have opposite curve shapes, and on neither is the best checkpoint the last one.** Held-out urdu bpb over 16 epochs of 85.4M unique tokens: **AR turns at 4.0 epochs** (1.4557 → 0.8325 → **0.7774** → 0.7887 → 0.8690) while **DIFF descends monotonically to 16** (1.6144 → … → **0.8320**) and has not turned. So AR's best is **0.7774 at 4 epochs** and DIFF's is **0.8320 at 16** — **AR ahead by 0.055 at their respective bests**, while at the *shared* 16-epoch endpoint DIFF leads 0.8320 to 0.8690. Both statements are true and they answer different questions. ⚠️ AR's turn at 4 epochs is where the repeated-data literature puts it; arm A's turn was at 8.5 epochs over 23.2M unique. ⚠️ **Not a bracket test of C_crit**: arm B's composition (74.3/20.4/5.4) differs from arm A's (68.8/26.1/5.1), so U is confounded with mixture — the exact confound §4.1 exists to forbid |
| BG | 32 | **A3's step count is the difference between a readable diffusion sample and a slot-looped one, and the sweep had never been run on a full-scale checkpoint.** Every diffusion sample in this repository before session 32 was decoded at **160 steps** — the one setting sessions 30 and 31 happened to use. Sweeping §4.4's grid over `ship-diff-b/diff-s0_f1.pt` (300 generations, `demo_sweep_diff.jsonl`) inverts the step axis on `lm/continue`: **8 steps → rep 0.016, 160 steps → 0.084, `confidence` at any step → 0.29–0.61**, and 64-step `confidence` unconditional generation averages **rep 0.852 with a longest repeated run of 66 words** over five prompts. ⚠️ **This is Finding AP at full scale** — "more steps, better" runs backwards at 70M over 85.4M tokens exactly as it did at 25M over 7.4M, so AP is no longer "directional, one seed". ⚠️ **The verdict it overturns is `progress.md`'s own**: the shippable block called DIFF "the better likelihood model and the worse generator" on the strength of `مہار مہار مہار` at rep 0.124 — which was a *decoder default*, not the checkpoint. **8 steps is 20× cheaper as well as better**, so this costs nothing to adopt | ✅ measured, both arms' pools shipped. **The released model card must name the step count beside the schedule** (Findings AO, AR already require the schedule and `--forbid-eos`) |
| BH | 32 | **The diffusion arm was stopped while still descending, and §0.4's equal-budget rule is why.** At the shared 16-epoch endpoint AR had turned at 4 epochs and was being actively ruined by more compute (+0.0803 on its last doubling) while DIFF was still gaining **−0.0520** — *more than AR's best doubling ever bought*. Both stopped there because the experiment requires the same budget; **a shippable checkpoint does not owe that constraint.** Corroboration rather than extrapolation: `core-diff-s0` reached **0.8059 on arm A**, a corpus 3.7× smaller at 426 epochs, and **0.000 verbatim overlap at n ≥ 16** — so heavy repetition is safe on this arm in a way Finding BD proves it is not on AR's. Fitted continuation: **64 epochs ≈ 0.777 for ~$6**, 256 ≈ 0.754 for ~$22 | ⚠️ **live and actionable — this is the next run.** The fit is three points and its own limit is ~0.74; treat the column as a range. ⚠️ **The cosine anneals over `total_steps`, so `ship-diff-b` cannot be resumed into it** — 64 epochs is a fresh run at full price |
| BI | 32 | **The ship corpus is capped by §6.1's mixture, not by the corpus.** `reports/freeze/plan.json` — the unsampled frozen plan — holds a native-Urdu train band of **12,136,015,091 characters**; arm B draws **246,984,881** of them, about **2%**. Arm B is not small because Urdu ran out (stage 9 measured the `urdu` margin at **146.8×**); it is small because the fixed 120:40:10 mixture chains native Urdu to the scarcest population, and `roman_urdu` is the one that failed G1 at 0.44×. `arm_tokens` is a free-form dict and arms are nested by construction, so a larger Urdu-heavy arm is a **config change, not code** | ⚠️ **live, and it carries a trap that makes it second, not first.** The held-out bands are carved *at the same mixture as the arms*, so changing `population_targets` can re-carve validation and test — and **every bpb number in this file stops being comparable**. The new held-out set must be verified byte-identical to the frozen one before a single GPU hour is spent. Corrects the shippable block's "the only thing that raises this ceiling is more corpus" |
| BJ | 33 | **Finding BA's estimator noise is now a bar rather than a caveat, and the draw that went into the run record was the outlier.** `Trainer.evaluate` called `model.loss` with `generator=None`, so Ravaan-DIFF's ELBO rode the global RNG and no diffusion number in this repository was reproducible as a named draw. `evaluate` now takes a seeded generator — `generator=None` is byte-for-byte the old path, so every committed `evaluation.json` is still reproducible by the code that wrote it — and `scripts/elbo.py` averages K of them. On `ship-diff-b/diff-s0_f1.pt`, nine draws of the full 4,874-sequence split give **urdu 0.8322 ± 0.0018** (single-draw sd **0.0053**, range 0.8237–0.8399), roman_urdu 1.6962 ± 0.0039, code_switched 1.1685 ± 0.0089, all 0.9909 ± 0.0015. **BA's 0.0069 was pessimistic and its K = 9 prediction of ~0.002 was right.** The 1.06 sd disagreement BA found resolves with a direction: `curve_diff_b`'s 0.8320 is **0.04 sd** from the mean and the run's own `evaluation.json` 0.8247 is **1.41 sd below** it — progress.md had been quoting the good draw and the run record holds the low one | ⚠️ **live until the curves land.** Only the 100% rung is averaged; the remaining six and all of arm A's are single draws, so the crossover tables still carry one-draw numbers at every other rung. Arm B's endpoint gap is **0.8690 exact against 0.8322 ± 0.0018**, ~20 sem, and BH's −0.0520 last doubling is ~10× the single-draw sd — both survive the bar comfortably. ⚠️ **The sem is the estimator's only**: it says nothing about initialization (that is seed 1's job) and nothing about the corpus |
| BK | 33 | **The diffusion arm beats the AR arm's best on the same corpus, given epochs the experiment could not spend.** `ship-diff-b64` — 64 epochs, arm B, 5.46B tokens, 8.2 h, ~$4.60 — reaches **urdu bpb 0.7646** against AR's best **0.7774** at 4 epochs on the identical 85.4M-token stream. Finding BH predicted ~0.777 from a three-point fit and was pessimistic; the realized per-doubling ratio is **0.66** against the fitted 0.65. The curve **has still not turned**: the last doubling bought −0.0386 (0.8032 → 0.7646) where AR turned at 4 epochs and was being ruined by 16. The 16-epoch rung reads **0.8619** against `ship-diff-b`'s 0.8320 — predicted before the run and confirmed after, because the cosine anneals over `total_steps` and has not finished at 16 in a 64-epoch schedule | ⚠️ **live.** The seven rungs are single ELBO draws and the 0.0128 margin is ~2.4 single-draw sd — **K = 9 before this is written as a result** (Findings BA, BJ). ✅ **The matched-corpus release pair exists**, so the cross-arm disclosure every artefact carried is gone. ⚠️ Still **not** a bracket test of C_crit and it does not touch §4.5's endpoint |
| BL | 33 | **A rented GPU can already be running someone else's job, and every symptom looks like a slow box.** The first 5090 rented this session measured throughput **flat and declining** across the sweep — 63,897 / 61,454 / 60,615 at microbatch 16/32/48 — which a GPU that wants a bigger batch does not do, then OOMed at 64 with the tell in the message: 31.36 GiB total, 17.89 GiB ours, 1.13 GiB free, so **~12.3 GiB belonged to nobody we could see**. Confirmed with nothing of ours running: **100% utilisation, 12,620 MiB resident, 2265 MHz against a 3105 MHz maximum, 525 W against a 525 W limit.** At ~62k tok/s the run would have been 23.7 h and **$13.38** against a $9.80 ceiling | ✅ `vast/push.sh` now refuses before shipping a byte. ⚠️ **The check is `memory.used` and `utilization.gpu`, NOT the process list** — `nvidia-smi --query-compute-apps` is **empty** in a Vast container even when the card is busy, because container isolation hides the other tenant's PID. Those two counters are the only signals that cross the boundary. A clean card reads ~0 MiB and 0% |
| BM | 33 | **Getting a finished run off a rented box is a harder constraint than training it, and the fix is to send less rather than to send it faster.** The instance's outbound ran at **19 KB/s direct** — measured raw, not inferred from the fetcher — while the 169 MB *upload* had been fine, so it is the host's egress and not the home link. One 839 MB checkpoint was **7 h and $3.92**; all seven were **48.6 h and $27.43** against ~$2.80 left. Two things made it affordable: **Vast's proxy route (`sshN.vast.ai`) ran 6.7× faster at 128 KB/s**, and **stripping the optimizer state cut the checkpoint 839 MB → 280 MB** — Adam's two moments are two thirds of the file and a released model needs none of it. Together: 7 h → 36 min, $3.92 → $0.34 | ⚠️ **live and it changes what a run should write.** Six of seven checkpoints were abandoned on the instance; `curve.json` holds all seven *scored*, so the curve survived and only the weights are gone. **Score on the box** (`launch.sh` does now) and **strip before transfer**, or plan the budget around 5.9 GB at a link speed nobody measures until it is too late. ⚠️ The stripped file **cannot resume training** — irrelevant here, the cosine had fully annealed |
| BN | 33 | **Two watchers, a fetcher and two `pkill`s all failed silently, and the box idled 3.3 h on a finished run.** The fetcher and both status watchers were killed under memory pressure or were never killed when they should have been, so when training ended at 10:47 nothing triggered the pull and it was found by the user asking — **~$1.85 of idle billing**. Three distinct mechanisms: (a) harness-tracked waiters die under memory pressure where `nohup` ones do not, for the **fourth** time (sessions 23, 28, 33×2); (b) **`pkill -f <pattern>` matches the killing command's own shell** when the pattern appears in its command line, so `pkill -f launch.sh` and `pkill -f pull.sh` both killed themselves and left the target running — one of them kept downloading 5.9 GB for two hours unnoticed; (c) `fetch.sh` had **not** died as assumed and woke to start a second, competing pull | ⚠️ **live.** `launch.sh`'s 8 h grace cap bounded the damage, which is the only reason it was $1.85 and not $40 — **bounded at eight hours is not the same as caught**. Kill by **PID**, never by a pattern naming the script. And a watcher is not a guarantee: the run's own artefacts on disk are the truth |

| BO | 34 | **G0's novelty verdict has a shelf life, and two of its sub-claims expired while nobody was looking.** The review was written 2026-08-03 and re-run 2026-09-23 across arXiv, ACL Anthology, OpenReview **and the Hugging Face Hub**. The Urdu claim survives — no masked diffusion LM for Urdu exists, and the only Urdu model on the Hub carrying a diffusion tag is a **text-to-speech** model. Two other things are now false: **Diffutron** (arXiv:2603.20466, a 0.3B masked diffusion LM for **Turkish**, March 2026) kills "first diffusion LM for a non-English language"; and **Ni et al., *Diffusion Language Models are Super Data Learners*** (arXiv:2511.03276, **November 2025**) makes the data-constrained crossover claim at 1–1.7B on English and Python — **it predates the G0 review by nine months and was not in it** | ⚠️ **live, and it changes the framing rather than the result.** The phenomenon is established prior art; **Ravaan's contribution is the axis nobody tested — a naturally low-resource, non-Latin-script natural language on noisy web text.** Both released cards state all three points explicitly, because the disclosure is what makes the surviving claim hold up when a reader checks it. **Carry the search date with the claim, always** — §8.1 of the review already required the hedge and this is why |
| BP | 34 | **The diffusion arm samples 17.9× faster and no artifact in this repository said so.** 160 tokens costs the AR arm **160 sequential forward passes**; the diffusion arm fills the same canvas in **8**. Measured over 12 matched `lm/continue` prompts on the 4060: median **0.37 s against 6.59 s**. The numbers were sitting in session 32's sweep and every session since, because `sample.py` has always written `seconds` and `forwards` into its JSONL | ✅ **used on the landing page and it is the most legible finding this project has for a non-specialist.** ⚠️ **It went unnoticed because every table in this repository scores likelihood and not one scored wall-clock at inference** — the project measured the thing it set out to measure and was blind to a free result beside it. Worth a line in the report: at 8 steps the better decode setting (Finding BG) is also the 20× cheaper one, which is not how these trade-offs usually run |
| BQ | 34 | **A vendored package verified by reading is not verified — third instance, after AX and BB.** `scripts/release.py` rewrites `from ravaan.` to `from ravaan_infer.` textually, and a textual rewrite works perfectly on the machine that built it because the real `ravaan` is importable there. `scripts/verify_release.py` runs each staged release in a **subprocess whose cwd is the release and whose `sys.path` has this repository stripped out**, then asserts parameter count, Arabic-script share and longest repeated run on real generated text. It caught **three** defects on first run: `SamplingConfig(top_k=None)` where the dataclass requires an int, `build_generator(seed, device=…)` against the real signature `(device, seed)`, and the **cp1252 console hole** on Urdu output — the same class `ravaan/console.py` closed for this repo and which a fresh subprocess re-opened | ✅ **the gate is now structural, not a habit.** `push_hf.py` refuses to upload anything absent from `release_verify.json` or failing it, and `cards.py` refuses to write a card when `elbo_diff_b64.json` is missing. **Every number that reaches a public page is gated on the artifact that produced it.** The lesson generalizes past releases: the check has to run where the stranger runs it, not where the author does |
| BR | 35 | **A CI gate that has never run is not a gate, and this one was hiding two real bugs.** `.github/workflows/tests.yml` was written in August and first executed on 2026-09-24, because until session 35 there was no remote to run it on. It came back red on **28 ruff findings, two of which were defects rather than style**: a literal `\n` inside the AR model card's H1 in `cards.py`, which would have shipped a broken title to the Hub on the next regeneration, and the same inside a rendered `<span>` in `landing.py`. Both were introduced earlier in session 35 by a bad multi-line edit and neither is visible from reading the diff. Then it was red a **second** time, for a different cause: the suite passed locally only off a **stale editable install**. `scripts/` is not a distributed package (`packages.find` ships `ravaan*` only) and `pytest`'s `pythonpath` was never set, so `test_substitutions` could not import its subject on a clean checkout; and five modules import `torch`/`numpy` at module scope, which errors during *collection* — not skipping — in the dependency-free job | ✅ **fixed and verified the way CI verifies it**: a venv with pytest and ruff only — **915 passed with torch present, 788 passed / 5 skipped without it**, ruff clean. `pythonpath = ["."]` makes the driver imports explicit rather than lucky, and the five modules now use `test_sampling.py`'s existing `importorskip` pattern. ⚠️ **The lesson generalises**: "it passes locally" was false for the whole life of the project and nothing could have told you |
| BS | 35 | **§8.3's repetition rate is the wrong instrument below ~30 words, and it fails silently in the direction that matters.** It is `1 - distinct-4` over whitespace words, so a 20-word continuation has 17 four-grams and the metric reads **0.000 for nearly every draw** — including draws that are unreadable. Measured while selecting demo samples: the worst diffusion draw in the pool scored repetition **0.000**, longest-repeat **1** and distinct-2 **1.000** while spraying one word (`کہیں، کہیں، کہیں`) across the canvas non-contiguously, which every n-gram order above 1 scores as clean. What separates draws at this length is **`longest_repeat`** and **distinct-1**, the type/token ratio: on a 160-draw pool the failing draws sit at **0.61** and everything kept starts at **0.74**, which is not a close call | ⚠️ **live for §8.3 generally, not just for demos.** The metric is sound at the canvas widths §8.3 was written for and misleading below them; anything scoring short generations must lead on `longest_repeat` + distinct-1. A fourth clause was also needed — three or more punctuation marks in a row — because `،،،،` attaches to whitespace tokens and makes them *look* distinct to every word-based metric. Selection rule and all 320 draws are in [`demo_trace_pool.json`](reports/demo_trace_pool.json) |
| BT | 35 | **Token-level truth and correct Urdu typography cannot be the same view, for two independent reasons.** (1) **§7's tokenizer has byte fallback**, so a character outside the 16k vocabulary arrives as two or three `<0xNN>` pieces occupying two or three *positions* — `…` is `<0xE2><0x80><0xA6>`. A diffusion decode commits positions in confidence order, so it can commit the middle byte of a character first, and a position-by-position rendering shows **U+FFFD** until the run completes. (2) **Nastaliq joins within a word** and a letter's shape depends on its neighbours, so splitting a word across `<span>`s to reveal its tokens separately produces text no Urdu reader would accept | ✅ **resolved by showing both, and labelling which is which**: the demo's cell canvas is per-token and exact (it is what shows diffusion committing position 19 before position 4), the prose is per-word and reveals a word when its **last** token commits. Byte-fallback draws are rejected from the demo pool outright rather than special-cased — on this checkpoint they are also the draws that had stopped writing Urdu. ⚠️ **Any future visualization of this model inherits both constraints** |

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
| 31 | 09-22 | **A releasable checkpoint exists.** Both arms trained on **arm B** — 85.4M unique tokens, 3.7× arm A and never trained on — 16 epochs, ~$4.10 on a rented 5090. **`ar-s0_fp25.pt` at 4 epochs is the best Urdu model the project has produced: urdu bpb 0.7774**, against arm A's best 0.8311 and `core-ar-s0`'s final 3.6143. **Memorization 0.000 at every n ≥ 16, equal to the held-out control.** `scripts/overlap.py` written and the recitation behind Finding BC measured | **BD, BE, BF** |
| 32 | 09-23 | **A demo exists, and the decode sweep it needed overturned a verdict in this file.** Five held-out prefixes continued by each arm's best checkpoint → [`demo.md`](reports/demo.md), [the page](https://claude.ai/artifact/Nq8PsaqFUkw9BPjqix4cuJ), `scripts/demo_page.py`. §4.4's A3/A4 grid run on a full-scale checkpoint for the first time (300 generations): **the diffusion arm's slot-looping was substantially a decoder default** — 8 steps, not 160. Arm A's diffusion found to be the better *generator* as well as the better bound, so the demo pairs `ship-ar-b/ar-s0_fp25.pt` with `core-diff-s1/diff-s1_f1.pt` across corpus arms, disclosed on the page. **Both verified non-reciting: 0.000 at n ≥ 16 against a 0.000 control.** And the curve re-read: **the diffusion arm was stopped while it was still descending** | **BG, BH, BI** |
| 33 | 09-23 | **The $6 run: `ship-diff-b64` at urdu bpb 0.7646, beating the AR arm's best 0.7774 on the same corpus** — the matched-corpus release pair exists. `scripts/elbo.py` and a seeded `Trainer.evaluate`; **arm A's whole curve now carries K = 9 error bars** and Finding BA is retired as a caveat there. `vast/` gained a shared-GPU pre-flight, a budget gate, a divisor check and on-box scoring | **BJ, BK, BL, BM, BN** |
| 34 | 09-23 | **Both models published on the Hugging Face Hub as a matched pair, Apache-2.0** — [`ravaan-diff-70m`](https://huggingface.co/AwaisAdilKhokhar/ravaan-diff-70m) at **0.7659 ± 0.0018** (K = 9) and [`ravaan-ar-70m`](https://huggingface.co/AwaisAdilKhokhar/ravaan-ar-70m) at 0.7774 exact, margin **6.4 sem**. Safetensors, a vendored torch-only `ravaan_infer/`, and cards carrying every caveat. **The AR half is released at 4 epochs deliberately** and its card says why — Finding BF made legible. Four drivers added that **refuse rather than warn**; `verify_release.py` runs the release where a stranger would run it. Memorization re-measured on the *released* checkpoints: 0.000 at every n, against a 0.000 held-out control. G0's novelty review re-run and two sub-claims found expired | **BO, BP, BQ** |
| 35 | 09-24 | **The code is public and the demo is hosted.** [`github.com/AwaisAdilKhokhar/ravaan`](https://github.com/AwaisAdilKhokhar/ravaan) created and pushed — **session 34's two debts paid**, the cards' 404 resolved, everything from both sessions committed. The interactive decoder demo is live at [awaisadilkhokhar.github.io/ravaan](https://awaisadilkhokhar.github.io/ravaan/) on Pages, with no sign-in wall. `scripts/demo_trace.py` records **which forward pass committed each position** and asserts its traced loop against the shipped sampler every run; `decoder_demo.py` and `decoder_gif.py` render it as a page and a 1200x628 GIF — **Finding BP, finally shown rather than stated**. CI executed for the first time in the project's life and was red twice before green | **BR, BS, BT** |

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
- ✅ ~~**CI is untested — there is no GitHub remote yet.**~~ **Resolved 2026-09-24 (session 35).**
  It ran, it was red twice, and it was worth having: see **Finding BR** for the two real bugs it
  caught and the stale-editable-install problem it exposed. Both workflows green; `pythonpath` and
  `importorskip` are the fixes. ⚠️ **What replaces this debt**: the suite is only green on a clean
  checkout *because* session 35 checked it on one — a dependency-free venv, `915 passed` with torch
  and `788 passed / 5 skipped` without. **Any new module importing `torch` or `numpy` at module
  scope re-breaks the dependency-free job**, and it will fail during collection, so the whole run
  exits 2 rather than skipping. Use `pytest.importorskip` at the top, as `test_sampling.py` does.
- ✅ ~~The 166 MB blob from session 17.~~ **Gone, and the figure was stale before the push.**
  Session 34 rewrote history with `git-filter-repo`; session 35 measured what actually shipped
  before pushing: **the largest blob in history is `reports/freeze/removals_8.txt` at 19.9 MB**
  (two versions) and **the whole pack is 11.22 MiB**. Nothing approaching GitHub's limits, and
  nothing expensive was made permanent by publishing.
- **Retry when convenient:** OpenReview `W5Ht05jF4c`, still behind browser verification. Low stakes
  now that both arms sit inside the fitted range.

---

## Next session

**START HERE. The models are published, the code is public, the demo is hosted. The remaining work
is writing and three people.** Six runs on local disk, **nothing is rented and nothing is
accruing** since 2026-09-23. Weeks 1–11 complete. **There is no GPU work left that anything
downstream is waiting on, and no engineering debt blocking anything.**

> 🌐 **Session 35 paid session 34's debts and hosted the demo.**
> **<https://github.com/AwaisAdilKhokhar/ravaan>** — public, both workflows green.
> **<https://awaisadilkhokhar.github.io/ravaan/>** — the interactive decoder demo, no sign-in.
> Findings BR, BS, BT are the new entries; the 🌐 block at the top of this file is the record.
>
> ⚠️ **Spend unchanged at ~$1.90 — session 35 cost $0.**

⚠️ **ONE DEBT IS STILL OPEN, AND IT IS A CREDENTIAL.**
1. **Rotate the Hugging Face write token.** It was pasted into a chat transcript on 2026-09-23 and
   **was still not rotated as of the end of session 35**. huggingface.co/settings/tokens — revoke,
   recreate. This is the oldest unpaid debt in the file and the only one with a security cost.

**Two things are done and should not be re-litigated.** The repository exists under the exact name
both model cards link to, and the demo is hosted somewhere that does not require a Claude account.
**Use the Pages URL in anything public** — the artifact at
<https://claude.ai/artifact/BRg2JkGzCZvZhu1L79AU2h> is the same page behind a sign-in wall, kept
only as a mirror.

⚠️ **Before touching `scripts/` or `tests/`, read Finding BR.** The suite passed locally for the
project's whole life off a stale editable install and nothing could have told you. It is now
verified the way CI verifies it, and **a new module importing `torch` or `numpy` at module scope
re-breaks the dependency-free job by failing collection, not by skipping**.

⚠️ **Before scoring any short generation, read Finding BS.** §8.3's repetition rate reads 0.000 for
nearly every draw under ~30 words, including unreadable ones. Lead on `longest_repeat` and
distinct-1 at that length. This applies to G3's coherence scoring as much as to demos.

**The demo is regenerated, never hand-edited** — the Urdu must come out of the sample file:

```bash
python scripts/demo_trace.py                  # sample both released models, recording commit order
python scripts/decoder_demo.py --site         # -> reports/decoder_demo.html AND site/index.html
python scripts/decoder_gif.py --og            # -> reports/decoder_demo.gif AND site/og.png
```

Pushing anything under `site/` redeploys Pages automatically. If the workflow ever needs a manual
kick, it has a `workflow_dispatch` trigger — the Actions tab, or the API.

> 📦 **Session 34 published the pair and put the bar on the headline.**
> [`ravaan-diff-70m`](https://huggingface.co/AwaisAdilKhokhar/ravaan-diff-70m) at
> **0.7659 ± 0.0018** and [`ravaan-ar-70m`](https://huggingface.co/AwaisAdilKhokhar/ravaan-ar-70m)
> at 0.7774 exact — margin **6.4 sem**, public, Apache-2.0, matched pair. Landing page at
> <https://claude.ai/artifact/S6Pzi3VP9LWGdJniB8n5BL>. Findings BO, BP, BQ are the new entries;
> the 📦 block at the top of this file is the record.
>
> ⚠️ **Spend unchanged at ~$1.90 — session 34 cost $0.** Everything it did ran on the idle 4060
> or on the Hub.

✅ ~~**PAY THESE FIRST. Session 34 created two debts.**~~ **Both paid in session 35.** The repo was
created under the exact name the cards link to and pushed (history had already been rewritten with
`git-filter-repo` in session 34 — **106 commits intact, HEAD tree hash byte-identical**), and
everything from both sessions is committed. **The staged release stays at `D:/ravaan-release/` and
is deliberately not in the repo** — 560 MB of weights that already live on the Hub. The pre-rewrite
backup at **`D:/ravaan-git-backup.git`** can now go: the push is confirmed and `origin/main` holds
the rewritten history.

⚠️ **The tooling session 34 added, and the one thing to understand about it.** Four drivers now
gate the release path, and **each refuses rather than warns**: `release.py` stages a repo,
`verify_release.py` runs it in a subprocess with this repository stripped from `sys.path`,
`cards.py` refuses to write a card if `elbo_diff_b64.json` is absent, and `push_hf.py` refuses to
upload anything missing from `release_verify.json` or failing it. **Finding BQ is why** — the
verifier caught three defects on its first run that reading the code had missed. If a future
session changes the inference path, **`verify_release.py` is the thing to re-run**, and it must
keep running the release where a stranger would run it rather than where the author does.

> 🥇 **Session 33 spent the $6 and it paid.** `ship-diff-b64` reaches **urdu bpb 0.7646** at
> 64 epochs, **beating the AR arm's best 0.7774 on the identical corpus**, and the curve has still
> not turned. The matched-corpus release pair exists and the cross-arm disclosure is gone. The
> 🥇 block at the top of this file is the result; Finding BK is the entry.
>
> ⚠️ **Spend: ~$7.90 of the $9.80, leaving ~$1.90. Everything below is $0 on the 4060.**
> ~$4.60 was the run; **~$1.85 was a finished box idling because nothing was watching** (Finding
> BN) and ~$0.40 was false starts. **There is not enough credit left to rent again** — the 128-epoch
> continuation Finding BK points at would need a top-up, prepaid only, never automatic billing.

⚠️ **Three debts session 33 created and did not pay. Read these before trusting the tooling.**
1. **`vast/pull.sh` reported "complete and md5-verified" having downloaded nothing.** The `ONLY`
   filter was passed `'a|b'`, but `case` parses alternation *before* variable expansion, so it
   became a literal pipe matching no file — and the script then declared success. **A fetcher that
   claims success on an empty transfer is the exact failure session 31's md5 check exists to
   prevent.** Fix the pattern *and* make an empty match an error, not a pass.
2. **`fetch.sh` starts a full-run pull that nothing bounds.** It woke on `evaluation.json` and began
   pulling 5.9 GB over a 19 KB/s link — 20+ hours of billing — while a second pull ran alongside it.
   It should strip and pull the scored-best checkpoint, not everything (Finding BM).
3. **Never `pkill -f <script-name>`**: the pattern matches the killing shell's own command line, so
   it kills itself and leaves the target running. Twice this session. **Kill by PID.**

⚠️ **This file used to say "more GPU cannot buy a better model; only more corpus can." That is
withdrawn.** Findings BH and BI: more epochs buy ~0.055 bpb on the diffusion arm for ~$5, and the
corpus is already on disk — 12.14B characters of native Urdu against arm B's 247M drawn.

```bash
ls -la /d/ravaan-runs/            # core-{ar,diff}-s0, core-diff-s1, ship-{ar,diff}-b, ship-diff-b64
git status --short                # clean through session 35; origin/main is current
git log --oneline -6              # sessions 34-35 are the top four commits
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
>
> ✅ **Session 31 removed one thing from their plate.** Whether `core-ar-s0`'s fluency was real no
> longer needs a native reader — Finding BD measures it as 24.9% verbatim recitation. The
> annotators are still required to separate the arms at their *honest* checkpoints, but the
> most embarrassing-looking result in the file is now settled by measurement.

**Next actions, in order. Nothing below costs money and nothing below needs a GPU.** ~$1.90 of
credit remains and no item requires it.

0. 🎯 **Pay session 34's three debts** — the GitHub repo, the commit, the token rotation. They are
   spelled out above. The first is a live 404 on a public page, so it is genuinely first.

1. **The write-up.** Deferred deliberately on 2026-09-23 ("I'll do the preprint later"), and it is
   now the only thing between this project and a citable result. **The material is all on disk**:
   `reports/preregistration.md` holds four falsifiable predictions committed before training, the
   findings register holds seventy-one numbered entries, and every curve and bar is a committed
   JSON. ⚠️ **Read Finding BO before writing a word of the novelty framing** — the phenomenon is
   prior art (Prabhudesai; **Ni et al., which the G0 review missed**), and the contribution is the
   language and script. The model cards already say this correctly and are the place to start.
   ⚠️ arXiv cs.CL needs an **endorsement** for a first-time submitter; that has weeks of lead time,
   like the annotators.

2. ⏳ **G5's annotators — still the critical path, and now the *only* one.** Three fluent Urdu
   speakers, ~2 h each. §8.3's three metrics score fluent prose and slot-looping clauses within a
   few hundredths of each other, so **they are the only instrument that can separate the arms on
   generation quality**. ⚠️ **Every Urdu judgement in this project, including on both published
   model cards, is an LLM's** — that is disclosed in public now, which raises the value of fixing
   it. [The annotation page](https://claude.ai/code/artifact/92e617de-5364-4273-8584-8ff1cc95dea2)
   renders all 243 samples in nastaliq. **The instrument exists; only the people are missing.**

3. **Re-run the A3/A4 sweep on the *released* checkpoint.** Finding BG's 8-step optimum was
   measured on `ship-diff-b` (16 epochs) and **the released model is `ship-diff-b64` (64 epochs)**
   — the step optimum is a property of a checkpoint, not a law, and `generate.py` ships 8 steps as
   its default to the public on the strength of the older measurement. ~25 min on the 4060, $0.
   If it moves, the model card and `release_assets/generate.py` both need the new number.

   ```bash
   python -u scripts/sample.py --checkpoint D:/ravaan-runs/ship-diff-b64/diff-s0_f1_weights.pt        --corpus data/packed --tokenizer data/tokenizer/ravaan-16k.model        --out reports/sweep_b64 --samples 5 --new-tokens 160 --forbid-eos always
   ```

4. **Week 12's remaining eval: infill exact-match and token-F1.** Never run by any session. §8.3's
   generation metrics are done for five checkpoint pairs; this is the preregistered conditional
   metric, scored under the truncation rule in `preregistration.md` §8.

5. **Seed 1's fraction curve**, ~35 min, $0 — confirms the *held-out* descent replicates rather
   than just the training trajectory:
   `python -u scripts/curves.py --run D:/ravaan-runs/core-diff-s1 --arm diff --seed 1 --corpus data/packed --corpus-arm A --out reports/eval/curve_diff_s1.json`

6. **The FIM framing** (open question 5, Finding AT) — still open, ~2.7 h on the 4060, $0.

7. **A live Hugging Face Space**, if the demo is wanted interactive. The static page is published
   and the inference path is proven to run **CPU-only with the source repo off `sys.path`**
   (Finding BQ), which is exactly what a free Space needs. `D:/ravaan-release/ravaan-diff-70m`
   is the folder to start from; a diffusion decode is **0.37 s at 8 steps** (Finding BP), so the
   free tier is genuinely enough.

8. ~~**The Urdu-heavy ship corpus**~~ (Finding BI) — **not worth it now.** It would invalidate
   every bpb number in this file by re-carving the held-out bands, and the published cards now
   quote those numbers. If it is ever revisited, the new held-out set must be verified
   byte-identical to the frozen one *before* a GPU hour is spent, and the release would have to be
   re-cut and re-pushed.

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

### 3. The runs — ✅ ALL SIX DONE (3 core on arm A, 3 shippable on arm B)

**Sixth run, session 33: `ship-diff-b64`** — 64 epochs, arm B, 5.46B tokens, 8.2 h, ~$4.60,
microbatch 32 on a clean 5090 at ~149k tok/s sustained. **urdu bpb 0.7646**, beating the AR
arm's best 0.7774 on the same corpus (Finding BK). Only the 64-epoch checkpoint came back —
stripped of optimizer state, 280 MB, md5-verified — because the box's egress ran at 19 KB/s
(Finding BM). `curve.json` holds all seven rungs scored.


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
# session 31's shippable runs — arm B, 16 epochs, ~2.5 h each on a 5090 at microbatch 32
python -u scripts/train.py run --arm ar --size 70M --seed 0 \
    --corpus data/packed --corpus-arm B --tokenizer data/tokenizer/ravaan-16k.model \
    --microbatch 32 --epochs 16 --evaluate --eval-split validation --eval-limit 0 \
    --out runs/ship-ar-b

# ⚠️ re-measure microbatch on EVERY host first (Finding BE) — 16 vs 32 was a 43% swing
python scripts/train.py throughput --arm ar --size 70M --microbatch 32 --steps 30 \
    --corpus-arm B --corpus data/packed --tokenizer data/tokenizer/ravaan-16k.model

# is a checkpoint reciting its corpus? (Finding BD) — the held-out control is what makes it readable
python scripts/overlap.py --samples reports/ship_samples.jsonl \
    --corpus data/packed --corpus-arm B --verify --out reports/eval/overlap_armb.json

# session 32's A3/A4 sweep — 20 settings x 3 tasks x 5 prompts, ~25 min on the 4060 (Finding BG)
python -u scripts/sample.py --checkpoint D:/ravaan-runs/ship-diff-b/diff-s0_f1.pt \
    --corpus data/packed --tokenizer data/tokenizer/ravaan-16k.model \
    --out reports/demo_sweep_diff --samples 5 --new-tokens 160 --forbid-eos always

# the demo itself: each arm's best checkpoint, same prefixes, at BG's step count
python -u scripts/sample.py --checkpoint D:/ravaan-runs/ship-ar-b/ar-s0_fp25.pt \
    --checkpoint D:/ravaan-runs/core-diff-s1/diff-s1_f1.pt \
    --corpus data/packed --tokenizer data/tokenizer/ravaan-16k.model \
    --out reports/demo_samples --samples 12 --new-tokens 160 \
    --forbid-eos always --steps 8 --schedule gumbel --gumbel 2
python scripts/demo_page.py --samples reports/demo_samples.jsonl --out reports/demo

# rent, ship, run, pull — vast/README.md is the runbook. pull.sh resumes and md5-verifies.
./vast/push.sh <host> <port>   &&   ./vast/pull.sh <host> <port> ship-ar-b
```

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

```bash
# session 33's 64-epoch shippable diffusion run, as it was actually launched
#   ssh -p <port> root@<host> 'cd /workspace/ravaan && \n#       MICROBATCH=32 FLOOR=120000 setsid nohup bash vast/launch.sh \n#       > /workspace/runs/chain.log 2>&1 < /dev/null &'
# MICROBATCH must divide 256 (16/32/64/128) - throughput measures any value, run refuses
# non-divisors. Pull over the PROXY host (sshN.vast.ai), never the direct one: 6.7x faster.
```

```bash
# an error bar on any diffusion number (Findings BA, BJ). K seeded draws, resumable per draw.
# ~130-200 s a pass on the 4060, so K=9 is ~25 min a checkpoint and ~3 h for a seven-rung curve.
python -u scripts/elbo.py --run D:/ravaan-runs/ship-diff-b --seed 0 --draws 9 \
    --corpus data/packed --corpus-arm B --check-denominators \
    --out reports/eval/elbo_diff_b_curve.json

# one checkpoint only, when it is a single number that has to carry the bar
python -u scripts/elbo.py --checkpoint D:/ravaan-runs/ship-diff-b/diff-s0_f1.pt --seed 0 \
    --draws 9 --corpus data/packed --corpus-arm B --out reports/eval/elbo_diff_b.json
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
- ⚠️ **Never pull a finished run with one `scp -r`.** Session 31 lost `ship-diff-b` to "Connection reset by peer" after ~2 GB of 6.3 GB, and because the fetcher ran under `set -e` it died *without* writing the watchdog's sentinel — so the instance billed idle for an hour with nobody watching. Per-file `scp` is not enough either: it restarts each **file** from zero, and on that link an 840 MB checkpoint never finished (1.5 MB, then 378 MB, then reset). `vast/pull.sh` resumes at a **byte offset** (`tail -c +N` appended to the partial) and **md5-verifies every file against the remote**. Git Bash has no `rsync`, which is the obvious tool.
- ⚠️ **`ssh` inside a `while read` loop eats the loop's stdin.** `pull.sh` processed exactly one file and then reported success. **`ssh -n`** is the fix, and the md5 check is what caught the false "complete" — a size check alone would also have passed, because the file it *did* fetch was correct.
- ⚠️ **Windows Python cannot open Git Bash `/d/…` paths.** `ls` and `find` resolve them and `open()` does not; use `D:/…`. Costs two confusing `FileNotFoundError`s on a file that demonstrably exists.
- ⚠️ **`Path.write_text()` on Windows writes CRLF**, so a Python-patched `.sh` fails on the instance with `set: pipefail: invalid option name`. Use `write_bytes`, and check with `file` before shipping a script.
