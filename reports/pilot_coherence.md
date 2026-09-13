# G3's coherence half — the pilot checkpoints, read

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
| **G3** | **The coherence half does not pass.** The resume half does. |

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

**Decide before Week 9.** This is the second item on that list, after the infilling *share*
(open question 5), and the two are the same conversation: both are about whether Ravaan-AR is a
fair FIM baseline or a straw one, which is §4.1's entire argument.

---

## 8. Reproducing this

```bash
python scripts/sample.py \
    --checkpoint runs/pilot/pilot-ar/ar_f1.pt \
    --checkpoint runs/pilot/pilot-diff/diff_f1.pt \
    --corpus data/packed-pilot --out reports/pilot_samples \
    --samples 6 --new-tokens 160
```

~8 minutes of decoding on the 4060 (7.5 min summed over the 306 generations). The AR
arm is the slow half at 5.9 s a sample against the diffusion arm's 1.2 s: there is no
KV cache, deliberately — `ravaan/sampling/ar.py` records why, and the short version is that a
second attention path is too high a price for inference speed in a project whose matched pair is
held together by there being only one.
