# G3's coherence half — the pilot checkpoints, read

> **⚠️ Amended 2026-09-14 (session 23). §0's verdict is narrower than it was written.**
> "Does not produce coherent Urdu under any of the 16 decoder settings measured" is still true of
> those sixteen settings, and the sixteen were **the wrong grid**: §4.4's A3 stops at 64 steps,
> and A4 offers only the two endpoints of what is really a one-parameter family. A setting outside
> the grid — the `gumbel` schedule at scale 2, 160 steps — gets **real Urdu words in
> grammatical clauses** out of this same checkpoint. §10 is the measurement and §11 is what
> it costs the reasoning in §9. **Nothing about the model changed; this is a decoder result.**

**Gate G3 (PRD §11):** *"20M pilot DIFF produces coherent Urdu after 50 epochs; both models resume
from checkpoint correctly."*

The resume half passed in session 21. This is the other half, and it could not be attempted until
session 22 because nothing in the repository could turn a checkpoint into a sentence —
`ravaan/sampling/` was a one-line docstring. The samples are
[`pilot_samples.md`](pilot_samples.md) (for reading) and
[`pilot_samples.jsonl`](pilot_samples.jsonl) (for the tables below); this file is what they mean.

---

## 0. The verdict, and how much of it is mine to give

| | |
|---|---|
| **Ravaan-AR** | Fluent, grammatical, script-consistent Urdu. Locally coherent over a sentence or two; no long-range sense, which is expected at this scale. |
| **Ravaan-DIFF** | **Does not produce coherent Urdu under any of the 16 decoder settings measured.** Two distinct failures, depending on the schedule — a repetition collapse (confidence) or word-shaped noise (random). |
| **G3** | **The coherence half does not pass.** The resume half does. **Decided 2026-09-13: the gate is recorded unmet on its own terms and Week 9 proceeds** — see §9. |

**Adjudicated by Claude, not by a native speaker** — the same caveat
[`quality_validation.md`](quality_validation.md) carries, in the same words, for the same reason.
What a speaker is being asked is whether `رکھتا ہوتی تھی۔ س۔ اس کے سامنے دہلی میں ایسا سیاہ زمانہ
تھا نہ تھا` is Urdu prose or Urdu-shaped noise, and that is a fluent reader's judgement.
`pilot_samples.md` is laid out to be marked up by one; the AR/DIFF contrast is stark enough that
the verdict is unlikely to move, but the *degree* is not mine to state.

**What this is not evidence about.** This is the 25M rung at 50 epochs over 7.36M tokens — the
pilot corpus, not the frozen one. G3 is a go/no-go on the *pipeline*, and §4.3's crossover is what
the experiment is actually for. A diffusion arm that is incoherent at 368M tokens of training is
not a finding about masked diffusion; it is a finding about 368M tokens. The findings below that
*do* generalise are the three decoder ones, because they are properties of the decoding procedure
rather than of this checkpoint.

---

## 1. Method

- **Checkpoints:** `runs/pilot/pilot-{ar,diff}/{ar,diff}_f1.pt` — fraction 1.0, step 5,614,
  367,919,104 tokens each, 8L/384d (§5's 25M rung), tokenizer `2855877c8ecd38c9`.
- **Decoder:** temperature 0.9, top-p 0.95, no top-k. Seed 0 + prompt index, so the six prompts in
  a set are six samples rather than one repeated (the first run of this driver had a fixed seed
  and produced six identical unconditional samples — visible only because the metrics matched to
  16 decimal places).
- **Prompts:** 6 per set, from the **validation** split of the `urdu` population, evenly spaced
  rather than taken from the head.
- **Sets:** `lm/free` (`<lm>` alone), `lm/continue` (`<lm>` + a 48-token real prefix), `infill`
  (a 32-token hole in a real sequence).
- **Axes:** §4.4's A3 (8/16/32/64 steps) × A4 (confidence/random) × whether `</s>` may be
  committed. 306 generations: 18 AR, 288 DIFF.
- **Metrics:** §8.3's three, from `ravaan.evaluation.generation`. `script` is the Arabic-script
  share of letters, `rep` is 1 − distinct-4, `run` is the longest repeated word run.

---

## 2. The AR arm

| set | script | distinct-1 | rep | run |
|---|---|---|---|---|
| `lm/free` | 0.987 | 0.729 | 0.002 | 2.5 |
| `lm/continue` | 0.995 | 0.770 | 0.001 | 2.5 |
| `infill` | 0.966 | 0.686 | 0.011 | 3.3 |

Reads as Urdu. Real words, agreement and case marking mostly right, quotation and sentence
punctuation used the way the corpus uses it, and no repetition to speak of. It drifts in topic
within a paragraph and invents plausible-looking names and numbers, which is what a 25M model
trained for 50 epochs on 7.4M tokens should do.

---

## 3. Finding AO — `</s>` is a trap on a context-free canvas, and it cost the whole script

A diffusion canvas has a width the *caller* chose. "The document ends here" is therefore not a
question the model is being asked — and asked anyway, it answers loudly. Instrumenting the
unconditional 512-token canvas at 64 steps, confidence schedule:

| | first 128 committed tokens |
|---|---|
| **confidence** | **60 × `</s>` (47%)**, then 42 × `▁hai`, 24 × `▁nahi` |
| **random** | content words in both scripts — 73% Arabic at step 0, 99% Arabic in the finished sample |

The mechanism is not subtle once measured. At an all-mask canvas the sharpest marginal the model
has is "this is the end", so a confidence-first schedule spends its first steps scattering `</s>`
across the canvas. The first *content* token to clear the confidence bar after that is a
Roman-Urdu function word — `hai`, `nahi`, `ki` are short, and `roman_urdu` is 23.53% of arm A — and
because attention is bidirectional, a handful of Roman tokens conditions the entire remaining
canvas on Roman. The sample comes out in Roman Urdu:

```
ki nahi hai aap ki tou ki baat nahi hai is liye aap ki baat nahi hai ki aap ki aap ki baat nahi hai
```

Arabic-script share **0.000**, at both 32 and 64 steps. Forbidding `</s>` takes the same setting to
**1.000**:

| `lm/free`, confidence | 8 | 16 | 32 | 64 |
|---|---|---|---|---|
| script, `</s>` allowed | 0.924 | 0.666 | **0.000** | **0.000** |
| script, `</s>` forbidden | 0.984 | 0.996 | **1.000** | 0.998 |

**The effect is confined to the context-free set**, which is the check that the explanation is
right rather than merely consistent: on `lm/continue` and `infill`, where a real prefix is pinned,
forbidding `</s>` moves nothing (0.947 → 0.947, 1.000 → 1.000). `</s>` wins only when there is
nothing else to condition on.

**What follows.** `</s>` belongs in the diffusion decoder's forbidden set whenever the canvas width
was chosen by the caller, alongside `<mask>` and `<pad>` and for the same reason: it is a token
that means nothing under this framing. It is **not** hard-coded — `ravaan.sampling.diffusion`
forces only `<mask>`, and `scripts/sample.py` sweeps the rest — because `</s>` *is* in the training
distribution as stage 10's document separator, so silently removing it would change a distribution
rather than fix a framing. The flag is `--forbid-eos`, the number that argues for `always` is in
the table above, and the decision belongs in the report rather than in a default.

---

## 4. Finding AP — A3 runs backwards: more denoising steps make the confidence schedule worse

§4.4 sweeps 8/16/32/64 expecting quality to buy time. On the unconditional set, with `</s>`
forbidden so the script collapse of §3 is out of the way:

| `lm/free`, confidence, `</s>` forbidden | 8 | 16 | 32 | 64 |
|---|---|---|---|---|
| distinct-1 | 0.244 | 0.242 | 0.141 | **0.069** |
| rep (1 − distinct-4) | 0.082 | 0.123 | 0.450 | **0.687** |
| longest repeated run | 5.7 | 5.8 | 13.0 | **21.0** |

Every axis degrades monotonically in the direction §4.4 expected to be an improvement. At 64 steps
the sample is one clause on a loop:

```
کے لئے ان کو حاصل کرنے کے لئے ان کی مہارت کو حاصل کرنے کے لئے حاصل کرنے کے لئے ان کو حاصل کرنے کے لئے
```

`lm/continue` shows the same shape more mildly (rep 0.061 → 0.450 from 8 to 64 steps), and `infill`
— a 32-token hole with both sides pinned — shows none of it (rep ≤ 0.023 everywhere). So the effect
scales with how much of the canvas is unconstrained.

**The reading is that confidence-first unmasking is self-reinforcing, and more steps give it more
chances to reinforce.** Committing the most-certain position first means committing the most
predictable token first; each such commit makes its neighbours more predictable in the same
direction; with 64 opportunities the canvas converges on the corpus's most probable clause. Eight
steps commits 64 positions at once and cannot chase itself the same way. This is a *directional*
result at one model scale with one seed per prompt, and it is the opposite of the default
assumption, so the ablation table for A3 must not be written as "more steps, better output" and
then measured.

---

## 5. A4 — random beats confidence on every measure here

| `lm/free`, `</s>` forbidden | schedule | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|
| distinct-1 | confidence | 0.244 | 0.242 | 0.141 | 0.069 |
| | **random** | **0.746** | **0.725** | **0.676** | **0.666** |
| rep | confidence | 0.082 | 0.123 | 0.450 | 0.687 |
| | **random** | **0.000** | 0.001 | **0.000** | **0.000** |
| longest run | confidence | 5.7 | 5.8 | 13.0 | 21.0 |
| | **random** | 1.8 | 2.2 | 2.3 | 2.2 |

And random is flat in the step count, which is the other half of §4's reading: without the
self-reinforcement, more steps neither help nor hurt.

**This does not make random's output good.** It makes it *not repetitive*, which is a different
claim, and §6 is about the difference.

---

## 6. What §8.3's generation metrics cannot do

Side by side, one prompt, 64 steps:

| | script | distinct-1 | rep | run |
|---|---|---|---|---|
| AR, `lm/continue` | 0.995 | 0.770 | 0.001 | 2.5 |
| DIFF, `lm/continue`, random | 0.979 | 0.680 | 0.001 | 2.3 |

Those are nearly the same numbers. They are not nearly the same text. The AR sample is Urdu prose;
the diffusion sample under the random schedule is script-consistent, non-repetitive, correctly
punctuated and made substantially of **non-words** — `چارائیانہ`, `وبشہیاب`, `کہفالرخانہ` are not
Urdu, and §7's byte fallback will spell anything you ask it to.

So: **§8.3's three generation metrics are a floor, not a measure of quality.** They catch the two
failures that are cheap to miss across a hundred samples — a sample that stopped being Urdu, and a
sample that is four phrases on a loop — and they are blind to the failure that actually separates
these two arms today. §8.4's human evaluation is not a nicety here; it is the only instrument in
the plan that can tell these two rows apart. Worth knowing now, because §8.4's three annotators are
open question 3 and have weeks of lead time.

---

## 7. Finding AQ — §4.2's FIM framing never taught the AR arm where a middle ends

`_frame_infill`'s AR branch builds

```
<infill> <fim_prefix> prefix <fim_suffix> suffix <fim_middle> middle
```

and the middle runs to the end of the 512-token sequence. **There is no terminator after it.**
Published FIM puts one there precisely so the model learns to stop; this framing does not, so the
AR arm has no signal for the length of the span it is filling.

Measured, over 12 infill prompts with a 32-token hole and `</s>` allowed as a stop:

| | |
|---|---|
| stopped at `</s>` | **5 / 12** |
| median tokens generated | **200** (the budget — i.e. it did not stop) |
| lengths when it did stop | 33, 86, 124, 127, 152 — against a 32-token hole |

The 5/12 is not the model ending a middle; it is stage 10's document separator turning up at
roughly its corpus rate — the same 4/12 appears on `lm/free`, which has no middle at all.

**Three things follow.**

1. **§8.3's "infill exact-match" is not computable for the AR arm as trained.** Any stopping rule
   is imposed after the fact by whoever computes the metric.
2. **It compounds the length asymmetry** that `ravaan.sampling` documents: the diffusion arm is
   *given* the span width because its canvas is fixed, and the AR arm has to infer one it was
   never taught. A2 ("AR without FIM") is supposed to quantify the inflation from an unfair
   baseline; an infill metric scored this way inflates in the other direction, toward diffusion.
3. **The fix is a training-side change and it is cheap exactly now.** Add a terminator token after
   the middle in `_frame_infill`'s AR branch — §7's vocabulary already carries twelve framing
   pieces and both arms embed all of them, so reusing one costs no parameters and breaks no §4.1
   matching. It costs a pilot re-run. After the core runs start it costs six.

### Decided 2026-09-13 — the framing is not changed, and the cost moves to scoring

The terminator is **not** being added and the pilot is **not** being re-run. Infill exact-match is
instead scored against a truncation rule, fixed before any result exists and logged in
[`preregistration.md`](preregistration.md) §8: **the AR arm's generation is cut to the gold span's
token length.**

That is the *symmetric* repair, not a generous one — the diffusion arm is already given the gold
length, because an absorbing-state canvas has a fixed width from its first forward pass. Scoring AR
unbounded would compare a bounded answer against an unbounded one and inflate toward diffusion,
which is the opposite of the bias preregistration §6 warns about.

**What the report must state, and it is not a footnote:** under this rule **both arms are told how
long the answer is**, so §8.3's infill exact-match measures content and not length, for either of
them. The claim "Ravaan-AR can infill" is therefore weaker than it looks — the model has not
demonstrated that it knows where to stop, because it was never taught, and the metric no longer
asks. §8.4's human evaluation covers infilling and is the only place that gap can show up.

Open question 5 — the infilling *share* — is unaffected and still open. It was bundled with this
only because one re-pilot would have covered both.

---

## 10. Finding AR — A4's two schedules are the endpoints of a family, and the middle is readable

§3 to §6 above measure `confidence` and `random` and find that both fail. They fail in
**opposite** directions, which is the part that was worth another look:

| | what it commits | what comes out |
|---|---|---|
| `confidence` | the position it is most sure of | real words, one clause on a loop (rep up to 0.69) |
| `random` | a uniformly-drawn position | no repetition at all (rep 0.000), and **non-words** |

Committing the most-certain position first means committing the most *predictable* token first, and
each such commit makes its neighbours more predictable in the same direction. Committing a
uniformly-drawn position means committing a token the model had no opinion about, and every position
decoded afterwards is conditioned on that scaffolding — bidirectionally, so there is no part of
the canvas it does not reach.

Neither is a choice between two options. They are the two limits of ranking by

```
log p(chosen token)  +  s · Gumbel(0, 1)        s annealed linearly to 0 over the decode
```

which is MaskGIT's schedule. At `s = 0` the ranking is `confidence` **exactly** — `log` is
monotone, and `tests/test_sampling.py` asserts the two produce bit-identical output at both
temperatures rather than taking it on trust. As `s → ∞` the noise swamps the
log-probability and the ranking is `random`. A4 measured the two ends of a dial and reported that
neither end works.

**What the middle produces**, from `runs/pilot/pilot-diff/diff_f1.pt` — the same checkpoint
§0 calls incoherent — at `gumbel` 2, 160 steps, `</s>` forbidden, temperature 0.9,
top-p 0.95. Unconditional:

```
کیا جاتا ہے، اس منشیات کو استعمال کیا جاتا ہے، منشیات کے خلاف منشیات کو منشیات کے استعمال سے متاثر ہونے کا خطرہ ہوتا ہے، تاہم، اس کے برعکس اس منشیات کے جسم میں بہت زیادہ ہوتا ہے
```

and continuing a real validation prefix:

```
امر کی ہے کہ وہ قرآن اور اس کی زبان میں بیان کرتا ہے ۔ اور اس نے اس جرہن میں بیان کی ہے ۔ اس کے بارے میں اس کی بات ہے ۔ امام ابن بثی نے فرمایا ہے کہ ان میں سے ایک چیز ہے ۔
```

These are Urdu words in Urdu clauses. They are topic-locked and thin, which is what a 20M model at
368M training tokens should be. They are **not** §6's `چارائیانہ` /
`وبشہیاب` / `کہفالرخانہ`, and they are not §4's one clause
repeated twenty-one times.

### A3's ceiling was doing as much work as A3's contents

The same shape of problem, one axis over. §4.4 sweeps 8/16/32/64 steps. On a 160-position canvas
64 steps still commits 2–3 positions per step **from independent marginals**, and on the
512-wide canvas the arm trained at it commits 8. The natural reference point — one position per
step, which is the exact any-order ancestral sampler for this chain — is 160 steps, outside the
grid. Under `random` at 160 steps this checkpoint produces substantially real Urdu where at 64 it
produced non-words, and **§8.3's three metrics register almost none of that difference**,
exactly as §6 says they would not. A3's flat `random` row from 8 to 64 was read as "steps do not
matter for this schedule"; it is better read as "the metrics cannot see what changed".

`scripts/sample.py` now sweeps 160 alongside §4.4's four rungs, and `--schedule gumbel --gumbel
S`. Nothing above the masked-position count does anything — those steps commit nothing and the
loop skips them — so 160 is the top of the axis for a 160-token canvas rather than an arbitrary
number.

### What generalises, and what does not

This is a **decoding** result, and decoding results are the class §0 says carries forward: a
property of the procedure rather than of this checkpoint. Three qualifications belong with it.

1. **The scale is a hyperparameter and it is not tuned here.** 1 and 2 were swept and 2 is better on
   this checkpoint. §4.4's ablations are preregistered and this is a third arm of A4, so it is
   reported as one rather than quietly adopted as the default the other two are compared against.
2. **It does not make the pilot diffusion arm good.** The unconditional samples still fall into
   Roman Urdu — `roman_urdu` is 23.53% of arm A and on a context-free canvas nothing holds the
   script — and the Urdu that does come out is topic-locked. §12 is a separate run about that.
3. **§6 still stands and is now the load-bearing paragraph in this file.** The metrics did not
   separate `random` at 64 steps from `random` at 160, and they do not separate `gumbel` 2 from
   `random` on script or repetition either. Every judgement in this section is a reader's.
   §8.4's three annotators are the instrument, and they are still open question 3.

---

## 11. What this costs §9's reasoning

§9 records G3's coherence half as unmet and lets Week 9 proceed, on the argument that the gate's
premise was wrong rather than the code — that 368M training tokens over a 7.36M-token corpus is
below the scale at which coherent Urdu is reachable. **That argument survives. One of its supports
does not.**

The support that fails: *"three separate decoder defects were found and fixed without moving the
verdict"* was offered as evidence that the decoder had been exhausted. It had not been. A fourth
decoder change moved the verdict further than any of the three.

What this does **not** change: the AR control still holds — same corpus, same loop, same code,
fluent — so there is still no evidence of a defect in anything the two arms share. And the
decoder change does not make the pilot diffusion arm coherent, only legible.

What it adds is a caution for §4.4. **An ablation grid can be wrong at its edges as well as in
its interior**, and both of §4.4's diffusion axes were. A3's top rung and A4's two schedules were
each chosen before anything had been decoded, which is what preregistration is for and is also why
they could not have been informed by output. The honest handling is the one this file already uses
for `</s>`: sweep past the edge, report the number, and put the decision in the report rather than
in a default.

---

## 8. Reproducing this

```bash
python scripts/sample.py \
    --checkpoint runs/pilot/pilot-ar/ar_f1.pt \
    --checkpoint runs/pilot/pilot-diff/diff_f1.pt \
    --corpus data/packed-pilot --out reports/pilot_samples \
    --samples 6 --new-tokens 160
```

§0 to §7 are that command as it stood in session 22 — A3's four rungs, A4's two schedules,
both `</s>` settings. §10's sweep adds the third schedule and the 160-step rung, and forbids
`</s>`, which §3 settled:

```bash
python scripts/sample.py \
    --checkpoint runs/pilot/pilot-ar/ar_f1.pt \
    --checkpoint runs/pilot/pilot-diff/diff_f1.pt \
    --corpus data/packed-pilot --out reports/pilot_samples \
    --samples 6 --new-tokens 160 --forbid-eos always
```

~8 minutes of decoding on the 4060 (7.5 min summed over the 306 generations). The AR
arm is the slow half at 5.9 s a sample against the diffusion arm's 1.2 s: there is no
KV cache, deliberately — `ravaan/sampling/ar.py` records why, and the short version is that a
second attention path is too high a price for inference speed in a project whose matched pair is
held together by there being only one.

---

## 9. What was decided, 2026-09-13

**G3 is recorded unmet, and the core runs proceed.** The gate's kill criterion is "implementation
bug — debug, do not scale", and no implementation bug was found. The control is §2: Ravaan-AR is
fluent on the same corpus, through the same loop, in the same code, so a defect in anything the
arms share would show in both. Three decoder defects *were* found and fixed during this session and
none of them moved the verdict. The judgement is that a 25M model at 368M training tokens over a
7.36M-token pilot corpus is below the scale at which coherent Urdu is reachable at all — the gate's
premise is wrong rather than the code.

The alternative considered and declined was a re-pilot at the 40M rung (~8 h on the 4060, at a
reduced microbatch because 8.19 GB is tight), which would have converted the judgement into a
measurement.

**The risk that was accepted, named rather than filed.** If a diffusion-only defect does exist, it
now surfaces after the six core runs are paid for. The cheapest early warning is **G4** — arm A's
curves at 50% of tokens processed — which is already a gate and should be read with this in mind
rather than only for the crossover.

**The technical report must carry the verdict and this reasoning, and must not describe G3 as
passed.**
