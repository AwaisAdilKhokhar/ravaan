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

- **Started** 2026-08-03 (Week 1 of 16). **PRD v2.3** (2026-09-10). **Spend $0.00 of $150.**
- **Weeks 1–2 complete. Weeks 5–8 complete ahead of them.** §7's tokenizer, §5's model, both
  objectives, the training loop, §4.2's five-task generator, §8's decoders, and both halves of G3.
- **Weeks 3–4 — stage 6+7 is finished for all three sources** (2026-09-16, on Kaggle, **$0**).
  The pass that had been blocked since session 17 ran in 6.94 h. What remains of the freeze is
  **stages 9 → 8 → 10**, all local and all cheap, and the **G1 re-check** that falls out of stage 8.
- **Two live design questions**, both yours, both due before Week 9: **the FIM framing**
  (open question 5, reopened by Finding AT) and **whether to filter `roman_urdu` on Finding AE**
  (waits on stage 8's numbers, with the G1 re-check).

### Gates

| Gate | PRD | Status |
|---|---|---|
| **G0** — comparison unpublished | §11 | ✅ **PASS** 2026-08-03 — [`literature_review.md`](reports/literature_review.md) |
| **G1** — clean corpus ≥ 100M tokens, per-population | §11 | ⛔ **FAIL on `roman_urdu` (0.44×)** → arm B dropped, single-arm. **Re-check due after stage 8** |
| **G2** — throughput implies 6 runs ≤ $90 | §11 | 🟡 requirement known (**64,162 tok/s** at 70M); the *rented* card decides it |
| **G3** — 20M pilot, both arms, resume | §11 | 🟡 resume **PASS**; coherence **FAIL**, recorded unmet on its own terms, Week 9 proceeds |
| **G4** — arm A's curves at 50% of tokens | §11 | ⬜ Week 9–11 |
| **G5** — human evaluation | §11 | ⬜ Week 13, and the annotators are not lined up |

### Record

- **Design decision** ✅ Option 2 (two-point law) chosen 2026-08-03 — U ∈ {25M, 100M}, 3 seeds at
  25M, 1 at 100M; PRD v2.1. **Superseded 2026-09-10 by v2.3**: arm B is unbuildable, so the design
  that shipped is effectively option 1 — **U = 25M, ~396 epochs, 3 seeds, 6 core runs, ~$118**,
  with P2 withdrawn in the preregistration's deviation log and its text above unedited.
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
| One unsampled stage-9 pass over **all** sources together | §6.3.9 | ⬜ deferred to freeze |
| Stage 8 complete (not sampled) over FineWeb2 | §6.3.8 | ⬜ deferred to freeze — Finding T makes it load-bearing |
| Stage 10's writing pass | §6.3.10 | ⬜ after the stage-9 re-solve |
| **G1 re-check after stage 8** — arm A's `roman_urdu` margin is ~1.53× *pre*-stage-8 | §11 | ⬜ **load-bearing**; the remaining fallback is "below 25M → stop" |
| **Stage-9 re-solve against measured fertility** — one command, before the corpus is *written* | §6.3.9, §7 | ⬜ |
| **Finding AE decision** — filter `roman_urdu`'s 2.77% wrong-lexicon rows, or train as-is and state the rate | §6.1 | ⬜ decide with the G1 re-check |
| Native-speaker pass: stage 5's 29 disagreements, stage 7's sampled pairs, the PII ambiguous match, the 225-candidate substitution screen | §6.3.5 | ⬜ one sitting, ~1–2 h, **never lined up** |
| Corpus manifest + per-stage statistics | §6.3 | 🟡 acquisition manifest done; stage stats pending |
| `neardedup.py` resumability | §6.3.7 | ⬜ not needed if FineWeb2 runs on a rented box |

**Closed, and not to be re-opened:** the Colab path for FineWeb2 (refused on both time and
memory); arm B (Findings AA/AB, PRD v2.3); stage 7's threshold at 0.80.

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
| ↳ ⚠️ `code_switched`'s figure is the least-supported — that population filled to only 43.4% of its share | §7 | ⚠️ re-measure when stage 10 runs for real |
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
| **G2** — measured on a local 4060; the **rented** card decides it | §11 | 🟡 requirement: **64,162 tok/s** at 70M, against 14,128 (AR) / 14,438 (DIFF) here |
| ↳ the ladder: 70M **4.54×** short · 40M **2.78×** · 25M **1.72×** (37,236 tok/s) | §11 | ✅ s21 — check a spec sheet against this *before* renting |
| ↳ Finding AM — both arms cost the same per token, within 2.2% | §4.1 | ✅ and it is the half that transfers to another card |
| ↳ §4.2's generator is ~180 ms of CPU per 256-sequence step, so `throughput` builds tasks by default | §11 | ✅ ~13% of throughput, and the cheapest evidence the tasks are running |
| ↳ ⚠️ the binding *local* constraint is **VRAM, not speed** — 25M at microbatch 32 sits at 7.8 GB of 8.19 | §9 | ✅ every G2 figure above is at microbatch 16 |
| **G3** — 20M pilot, both arms | §11 | 🟡 resume **PASS**; coherence **FAIL**, gate recorded unmet, Week 9 proceeds |
| ↳ 50-epoch run complete, both arms, §4.3's seven fraction checkpoints written | §4.3 | ✅ the curve infrastructure works end to end |
| ↳ 306 generations read → [`pilot_coherence.md`](reports/pilot_coherence.md), text in [`pilot_samples.md`](reports/pilot_samples.md) | §11 | ✅ **both halves of its headline were narrowed on 2026-09-14 — Findings AR and AS** |
| ↳ **G3's record corrected** — PRD §11, `pilot_coherence.md` §9/§11, and §12 written | §11 | ✅ s24; session 23's handoff said this was done, and it was not |
| **Ablations A3/A4** — inference only | §4.4 | 🟡 pilot-scale sweep done; the core-run sweep is Week 12 |
| ↳ ⚠️ **A2 measures §4.2's FIM layout, not "AR without FIM"** — MARIA reports the opposite | §4.4 | ⚠️ the report must say so |
| **The microbatch that reproduces session 23's runs is 32** — nothing recorded it | §4.1 | ✅ identified from `pad_tokens` 11039 |
| **`scripts/train.py --tokens / --epochs / --warmup-steps`** — `--steps` never moved the cosine | §4.3 | ✅ s23; every earlier short run trained at near-peak LR throughout |
| **`pin_utf8_streams()` reaches all sixteen drivers** — session 14's class fix, finished | — | ✅ s23 |
| **Core runs (W9–11, G4)** → eval (W12) → human eval (W13, **G5**) → demo (W14) → report (W15–16) | | ⬜ |

---

## Findings register

Forty-eight findings are referenced across this file, the PRD and the reports, and until now they
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
| AU | 25 | The Kaggle CLI's **access-token** auth path takes the username from the *server's* token introspection, which answers `del=c0b94e0932cd8e95` for this account — so uploads refuse after sending the bytes and pushed kernels land unreachable | ✅ `authenticate()` tries access token → legacy key → OAuth creds, and only the third reads `credentials.json`'s correct slug. **Delete `~/.kaggle/access_token`** and the CLI falls through to it |
| AT | 24 | The AR FIM framing loses **~37× in rank at the middle's first token** — `<lm>` ranks gold **2**, `<fim_middle>` ranks it **74**, same checkpoint and position — and the damage is **one position wide** | ⚠️ **live — it reopens the framing call AQ closed.** Not the decoder, span distribution, window, memorization or share |

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
| 25 | 09-15/16 | **The corpus freeze is finished.** Kaggle reopened (Z′, AL retired); AU and AV found and fixed; kernel 00's trial **FITS** at 8.96 h; **kernel 01 ran FineWeb2 stage 6+7 in 6.94 h for $0** — 4,318 ids, largest cluster 8 | **AU, AV** |

### The two results worth keeping in front of you

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

**2. Compute account — 🟡 no longer blocking the freeze; still open for Week 9's GPU.**

- **Kaggle is open** (`awaisbinadil`, phone verified 2026-09-15) and the freeze is running there.
  Notebooks have internet, `kaggle quota` reports GPU 30 h / TPU 20 h, and the code dataset
  uploads. Getting there cost Finding AU, not code.
- **A rented 32 GB Linux CPU box is now the fallback, not the blocker.** It is what happens if
  kernel 00's trial projects FineWeb2's pass past the ~12 h cap. ~14 h, **~$2–4**. Any provider
  does — Hetzner CX42-class, Vast, DigitalOcean — and `colab/freeze_colab.py` runs unmodified on it
  (`/proc/meminfo`, not a Colab API).
- **Set the provider spending limit when the account is created**, which is what PRD §9 wanted on
  day one, and the same account then answers the spot-GPU question for Week 9.
- **Budget context:** $0 of $150 spent, and v2.3 dropped two core runs, so the plan is ~$118. This
  box is a rounding error against it.

**3. Annotators — ⚠️ has not moved in four sessions, and it is now load-bearing in four places.**

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

**6. Does PRD §6.2's Roman-Urdu-Parl warning get amended for Finding AE?** *Your call.* Nothing in
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
and it holds regardless.

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

**START HERE. The next task is stage 9**, then 8, then 10 — all local, all cheap, and all under
step 1 below. **Stage 6+7 finished on 2026-09-16 and nothing about the corpus is blocked on you any
more**; the G1 re-check that follows it is blocked on a command, not on a decision. The modelling
work that could be done without the corpus had already been done — Weeks 5–8 are complete, both
halves of G3 are answered, session 23 ran the first matched pair this project has that is
*actually* matched, and session 24 closed the infilling share.

> **⚠️ Two decisions are yours, they are now the only things waiting on you, and both get more
> expensive once Week 9 starts.**
> **(a) The FIM framing** — open question 5, reopened by Finding AT. A re-pilot costs 2.7 h and $0
> today, against six core runs later.
> **(b) The publishable-checkpoint fork** — below, under step 2.

### 1. Finish the corpus

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


**Then stages 9 → 8 → 10, all local, all cheap:**

```
9   split.py --source ALL --limit 0 --measure-only --exclude <each 6+7 list>
              --plan-out reports/freeze/plan.json --heldout-out data/freeze/heldout.jsonl
8   decontaminate.py --source ALL --limit 0 --exclude <each 6+7 list>
              --removals reports/freeze/removals_8.txt
10  pack.py --source ALL --limit 0 --plan-in plan_resolved.json
              --exclude <each 6+7 list> --exclude removals_8.txt --out data/packed
```

- **Stage 9 must come after 7**, or the held-out split can contain near-duplicates of training
  documents. Stage 8 catches the cross-source case and structurally cannot catch that one.
- **Stage 8 must run complete, not sampled** (Finding T).
- **Only step 10's *writing* pass is blocked on the re-solve.** Stages 9 and 8 can complete first.

**Three things fall out, in this order:**

1. **⚠️ The G1 re-check, and it is load-bearing.** Arm A's `roman_urdu` margin is **~1.53×** and
   that is a *pre*-stage-8 number. Stage 8 will remove more, including matches against
   Roman-Urdu-Parl's own test split. If it eats a third of that margin arm A gets tight, and G1's
   remaining fallback is **"below 25M → stop."** Re-run the gate the moment stage 8's numbers
   exist; it is flagged in PRD §11's verdict row. Not a worry yet — a number to look at early.

2. **The stage-9 re-solve**, one command, and it must land **before the corpus is written**:

   ```
   ravaan-splits <plan.json> --chars-per-token urdu=3.8935 roman_urdu=4.1928 code_switched=3.2758
   ```

   The worst move against `configs/data/splits.json` is 11%, not the factor of two an earlier note
   feared, and `roman_urdu` — the thinnest margin — was already right. ⚠️ `code_switched`'s 3.2758
   is the least-supported of the three; re-measure it when stage 10 runs for real.

3. **The Finding AE decision** (open question 6's sibling) — filter, or train as-is and state the
   rate. Same number, second in line after the G1 re-check.

**⚠️ Disk here is tight** — 8 GB free on C:, with `data/raw` at 7.8 GB. Stages 9 and 8 are
read-only with small outputs; packed arm A is ~200 MB. It fits, with no room for a second copy of
anything.

### 2. Then compute

§4.3's run is 70M params × 9.9B tokens. **6 runs in $90 at $0.35/hr is 42.9 h/run, which is
64,162 tok/s at the 70M rung.** This 4060 does ~14,100–14,400 — **4.5× short** — which is exactly
why `throughput`'s own docstring says to measure on the instance you intend to rent *before*
renting it. A 4090-class spot is the assumption; **verify it against the ladder, do not trust the
spec sheet.** Set the provider spending limit when the account is created; the same account answers
step 1's rented-CPU question.

> **⚠️ A planning fork to settle before Week 9: the crossover experiment and a publishable
> checkpoint want opposite things from U.** Arm A caps U at 25M unique tokens and ~396 epochs *on
> purpose* — that is what puts it 1.79× past C_crit and it is the whole point of §4.3. It also
> makes a poor model to hand anyone. A checkpoint meant for §2's deliverable 1 should be trained on
> the whole ~170M-token pool (or more — §6.1 records that 5–6B tokens of Urdu exist and that
> capping is a *design decision*). Same code, same budget, different U; one extra run.
>
> ⚠️ Session 23 measured the tempting version of this argument and only half of it held. Going
> 7.36M → 186.9M unique tokens **fixed the script collapse** (Arabic-script share 0.250 → 1.000
> unprompted) and **did not fix the slot-looping**. The fork survives on the weaker and sufficient
> argument: **arm A's U is capped to land past C_crit, which is a property nobody downloading a
> model wants.** Decide deliberately, and **make sure the report and the model card say which
> checkpoint is which** — the paper's artifact and the hub's artifact should not silently be the
> same file.
>
> **Three things a release needs that the PRD does not yet cover.** (a) **Inference code ships with
> the weights** — `RavaanDiffusion` is not a `transformers` architecture, and from outside the
> model the schedule, the step count and forbidding `</s>` *are* the model (Findings AO, AR).
> (b) **The model card carries the ELBO-is-a-bound caveat, G3's verdict and the failure modes**, in
> the same words §4.3 and §11 require of the report. (c) **Urdu Wikipedia is CC-BY-SA** and
> `data/manifest.json` flags it in `share_alike_sources`; whether share-alike reaches model weights
> is worth settling *before* publishing. §2.4's "no raw text redistribution" means the corpus ships
> as code, manifest and checksums either way.

### 3. Then the runs

6 core (2 arms × 3 seeds) plus A1 and A2 at 1 seed each. Resume is proven exact on both arms, so
spot preemption is survivable and §9's checkpoint-every-500-steps control is already in the loop.

**⚠️ The cheap run that is now obvious, and it is not in §10's schedule.** Session 23's two regimes
are two different *corpora*, so repetition is confounded with composition. Once the freeze lands the
clean version costs **one extra run and no new data**: arm A at its 25M unique tokens is already the
repeat regime, so train one diffusion arm on **the same frozen corpus at the same 9.9B budget drawn
from the full ~170M-token pool**, and the pair brackets the crossover on one corpus with one
variable moved. **Do not let it displace arm A's three seeds** — §9 is explicit that those carry the
primary endpoint alone — but it is worth ~$8 of the contingency, and it is the same run that
answers the publishable-checkpoint fork.

### What the core runs and the eval are obliged to carry

- **G3 is recorded unmet on its own terms, and the report must not describe it as passed.** The
  gate's kill criterion reads "implementation bug — debug, do not scale", and no implementation bug
  was found; a 25M model at 368M training tokens over a 7.36M-token corpus is judged plausibly
  below the scale at which coherent Urdu is reachable at all, so the gate's *premise* is judged
  wrong rather than the code. **The accepted risk, named rather than filed away:** if there is a
  diffusion-only defect it now surfaces after six core runs are paid for. The cheapest early warning
  is **G4** — arm A's curves at 50% of tokens — which should be read with this in mind and not only
  for the crossover. ⚠️ And the report must carry the **correction**, not just the conclusion: the
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
- **A2 measures §4.2's FIM layout, not "AR without FIM"** (Finding AT), and MARIA
  (arXiv:2502.06901) reports the opposite result. The honest reading is that our AR arm is not
  properly equipped — the exact hazard §4.1's fairness argument exists to guard against.
- **§8.3's three generation metrics are a floor.** They catch a sample that stopped being Urdu and
  one that is four phrases on a loop, and they are blind to what actually separates the arms.

### Re-running things

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
```

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
