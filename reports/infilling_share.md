# Open question 5 — the infilling share, measured

**Question (PRD §4.2, open since session 4).** §4.2 sets the infilling share at 10%. Reported FIM
practice is 50–90% with no left-to-right degradation. If 10% leaves Ravaan-AR genuinely bad at
infilling, ablation **A2 ("AR without FIM") loses its meaning** — the *fair* baseline would also be
undertrained, and §4.1's whole fairness argument weakens.

**Answer: keep §4.2's 10%.** Raising the share to 50% costs measurable left-to-right quality, buys
a small infill improvement, and **does not address the reason the AR arm is bad at infilling** —
which is not a data-budget shortfall at all. That is the substantive finding here and it is bigger
than the question.

---

## 0. What was run

Two Ravaan-AR runs, matched in everything but the share. Same 25M rung, same seed, same optimizer,
same **367,919,104 tokens processed** over **186,931,200 unique tokens at 2 epochs**, same §4.2
corruption fingerprint `dcaafa28a181`, same tokenizer `2855877c8ecd38c9`. The only difference in
either `config.json` outside `tasks.shares` is `log_every` (10 against 25), a logging cadence.

| | lm | infill | translit | restore | codeswitch |
|---|---|---|---|---|---|
| `runs/urdu-ar` (§4.2) | 0.65 | **0.10** | 0.10 | 0.08 | 0.07 |
| `runs/urdu-ar-fim50` | 0.25 | **0.50** | 0.10 | 0.08 | 0.07 |

The residual comes out of `lm` alone, so exactly one thing moves. Spreading it over the unpinned
tasks would have moved four and a difference in infill quality could then be any of them.
Realized mixture, from the run's own log: `lm 25.00% [25%] · infill 50.00% [50%] · translit
10.00% [10%] · restore 8.01% [8%] · codeswitch 6.99% [7%]`.

**The control, first.** Both arms are read on a held-out split, so recall has to be ruled out
before anything else is read. `scripts/memorization.py`, 384 sequences per split:

| checkpoint | train | held-out | gap |
|---|---|---|---|
| `urdu-ar/ar-s0_f1` (infill 10%) | 3.7340 | 3.7808 | **+0.0469** |
| `urdu-ar-fim50/ar-s0_f1` (infill 50%) | 3.8836 | 3.9263 | **+0.0427** |
| `urdu-diff/diff-s0_f1` (infill 10%) | 4.3435 | 4.4076 | **+0.0641** |

All three sit in the ~0.05 band session 23 measured on this corpus. Nothing here is reciting, so
every number below is about the framing and the share.

---

## 1. What 50% costs

Held-out plain-LM bits-per-byte, native Urdu, 2,000 sequences:

| Ravaan-AR | held-out bpb |
|---|---|
| infill 10% | **0.8154** |
| infill 50% | **0.8528** |

**+0.0374 bpb, 4.6% relative.** §4.3's token budget is fixed, so the forty points came out of `lm`
and the model saw 40% less plain-LM text; this is the price of the trade rather than a surprise.
It is worth saying plainly that this does **not** contradict the review's "50–90% with no
left-to-right degradation": that literature is document-level FIM at far larger scale, not 50% of a
five-task mixture at 20M parameters.

---

## 2. What 50% buys

`scripts/infill_eval.py`, 64 validation sequences a span, greedy, scored under preregistration §8's
truncation rule (the AR arm's generation cut to the gold span's token length).

**Token-F1:**

| span | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| AR infill 10% | 0.000 | 0.055 | 0.059 | 0.112 | 0.148 | 0.150 | 0.152 |
| AR infill 50% | 0.031 | 0.016 | 0.098 | 0.102 | **0.174** | **0.174** | **0.174** |
| DIFF confidence | **0.516** | **0.359** | **0.301** | **0.184** | 0.219 | 0.189 | 0.172 |
| DIFF gumbel 2 | **0.516** | 0.336 | 0.305 | 0.189 | 0.202 | 0.200 | 0.195 |

**Exact-match — §4.5's named secondary endpoint:**

| span | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| AR infill 10% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AR infill 50% | 0.031 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| DIFF confidence | 0.516 | 0.234 | 0.078 | 0.000 | 0.000 | 0.000 | 0.000 |

So 50% buys roughly **+0.02 to +0.04 token-F1** at the spans where the metric moves at all. Against
0.037 bpb of left-to-right quality, that is a poor trade on its own terms — and §3 is why it is a
worse trade than it looks.

⚠️ **Exact-match is zero almost everywhere, and that is a fact about the endpoint.** §4.5 makes
infill exact-match one of three Holm-corrected secondary endpoints. For the AR arm it is **0.000 at
every span measured except one**, so at this scale it cannot separate two AR checkpoints at all and
token-F1 is carrying the entire signal. Week 12 should know this before it preregisters the decode
settings the endpoint will be scored under.

---

## 3. Why the AR arm is bad at infilling, which is not the share

The first reading of §2 was that greedy decoding had collapsed the AR arm: at span 1 it emitted
`کے` on **32 of 64** items, a high-frequency genitive marker, regardless of context. That reading
is **wrong**, and `scripts/infill_probe.py` is what shows it — teacher-forced, one forward pass per
item, the rank and probability of the *gold* token under the model's own distribution. No decoder
is involved, so none can be blamed.

### 3.1 The same token, asked two ways

Same checkpoint, same sequence, same position, same gold token:

| `urdu-ar/ar-s0_f1`, span 4 | median rank | P(gold) | top-1 |
|---|---|---|---|
| under `<lm>` — plain left-to-right | **2** | 0.373 | 0.484 |
| under `<fim_middle>` — §4.2's FIM | **74** | 0.007 | 0.031 |

The arm knows this token. Asked for it through the FIM framing — which hands it **strictly more**
information, since it also gets the suffix — it collapses by a factor of ~37 in rank and ~50 in
probability. **The deficit is not the model's Urdu and not the decoder.**

### 3.2 It is not the span distribution either

`_frame_infill` trains on middles of 5–50% of the content, so small holes are off-distribution for
the AR arm and that was the next live explanation. It is not the explanation — the rank does not
recover anywhere in `_frame_infill`'s own range:

| span | 1 | 2 | 4 | 16 | 64 | 128 | 200 |
|---|---|---|---|---|---|---|---|
| AR 10% — FIM rank | 89 | 101 | 74 | 172 | 117 | 284 | 79 |
| AR 10% — plain-LM rank | 2 | 3 | 2 | 3 | 3 | 3.5 | 2 |
| AR 50% — FIM rank | 49 | 108 | 47 | 95 | 78 | 218 | 53 |
| **DIFF — FIM rank** | **1** | **3.5** | **2** | **6** | **6** | **6** | **6.5** |

### 3.3 The damage is one position wide

Median rank of the middle's *k*-th token, teacher-forced with the gold middle prefixed back in, at
span 64:

| depth into middle | d0 | d1 | d2 | d4 | d8 | d16 | d32 |
|---|---|---|---|---|---|---|---|
| AR infill 10% | **117.0** | 11.0 | 6.5 | 3.5 | 2.5 | 4.0 | 4.0 |
| AR infill 50% | **77.5** | 6.5 | 5.5 | 3.5 | 3.5 | 4.0 | 4.0 |

**The AR arm infills perfectly competently from the second token onward** — rank 3–6, which is its
own plain-LM rank. Everything that is wrong with it is concentrated on the single token immediately
after `<fim_middle>`.

**The mechanism that fits all three tables.** To predict `middle[0]` the arm has to reach back past
the *entire suffix* to where the prefix ended — hundreds of tokens — and at 20M parameters it does
not; it emits a high-frequency token instead. To predict `middle[1]` it has `middle[0]` adjacent.
The diffusion arm never faces this: its canvas keeps the hole **in place**, both neighbours
adjacent, attention bidirectional. That is why it sits at rank 1–6 at every span.

**This is the same framing Finding AQ is about.** AQ established that §4.2's FIM layout has no
terminator after the middle, so the arm was never taught where an infill *ends*. This establishes
that it barely learns where one *begins*. Both are properties of the layout, not of masked
diffusion and not of the backbone — and 5× the training share moves d0 from 117 to 78 while leaving
it 20× worse than d1, which is the clearest statement available that **the share is not the
variable that governs this**.

---

## 4. What this obliges

1. **§4.2's 10% stands.** Recorded as decided rather than assumed, with the numbers above. The
   question's premise — "if 10% leaves AR bad at infilling, A2 loses meaning" — resolves as: AR
   *is* bad at infilling, and raising the share is not the remedy.

2. **⚠️ A2 does not measure what its name says, and the report must say so.** A2 is "AR without
   FIM". Given §3, A2 compares a framing that is crippled at one position against no framing at
   all. Whatever A2 returns, it is a statement about §4.2's FIM layout rather than about whether an
   AR model can be equipped for infilling. **MARIA (arXiv:2502.06901), flagged as prior art in
   session 2, reports properly-equipped AR beating discrete diffusion at infilling.** This result
   is the opposite, and the honest reading is that our AR arm is *not* properly equipped — which is
   exactly the hazard §4.1's fairness argument exists to guard against.

3. **§4.5's infill exact-match is a near-constant zero for the AR arm.** It is a preregistered
   secondary endpoint and it cannot separate AR checkpoints at this scale. The preregistered
   truncation rule is not the cause — it cuts to gold length, and the first token is the broken one
   either way.

4. **⚠️ This is new evidence bearing on a decision already taken.** On 2026-09-13 Finding AQ was
   decided *not fixed*: the framing keeps its missing terminator and the cost moves to scoring. That
   decision was taken knowing the framing had no **end** marker. It was not known that the same
   framing loses ~37× in rank at its **start**. A terminator does not fix the start, so this is not
   simply AQ's decision returning — but it is a second, larger defect in the same layout, and
   whether §4.2's FIM framing is fit for the core runs is now a live question rather than a settled
   one. **It is the user's call and it is cheap today**: a framing change costs one re-pilot now and
   six core runs once Week 9 has started.

---

## 5. What this is not

- **One seed**, at the 25M rung, 368M tokens processed. Directional evidence for a design decision,
  not a result for a table.
- **The corpus is `data/packed-urdu`, which is urdu-only and is not the freeze.** Its manifest says
  so. No number here belongs in a results table, and the `roman_urdu` and `code_switched`
  populations are absent entirely.
- **The cold start may close with scale.** §4.3's run is 70M parameters over 9.9B tokens — 27× the
  tokens and 3.5× the parameters. The reach-past-the-suffix operation is exactly the kind of thing
  that improves with capacity, so this is a finding about this rung, and §5's ladder is where it
  would be retested.
- **Every judgement about the Urdu text is Claude's**, in the same words `quality_validation.md`
  uses. The rank tables do not need a reader; §2's generations do.

---

## 6. Reproducing

```bash
# the matched run (2.72 h on a 4060)
python -u scripts/train.py run --arm ar --size 25M --seed 0 \
    --corpus data/packed-urdu --corpus-arm A --out runs/urdu-ar-fim50 \
    --tokenizer data/tokenizer/ravaan-16k.model \
    --microbatch 32 --tokens-per-step 65536 --tokens 367919104 --warmup-steps 100 \
    --task-share infill=0.50 --evaluate

# the control
python -u scripts/memorization.py --corpus data/packed-urdu --corpus-arm A --sequences 384 \
    --checkpoint runs/urdu-ar/ar-s0_f1.pt --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \
    --checkpoint runs/urdu-diff/diff-s0_f1.pt \
    --out reports/eval/memorization_infill_share.json

# §2's scored grid (~25 min)
python -u scripts/infill_eval.py --corpus data/packed-urdu --items 64 --spans 1 2 4 8 16 32 64 \
    --checkpoint runs/urdu-ar/ar-s0_f1.pt --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \
    --checkpoint runs/urdu-diff/diff-s0_f1.pt --out reports/infill_share

# §3's framing probe (~2 min)
python -u scripts/infill_probe.py --corpus data/packed-urdu \
    --checkpoint runs/urdu-ar/ar-s0_f1.pt --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \
    --checkpoint runs/urdu-diff/diff-s0_f1.pt --out reports/eval/infill_framing_probe.json
```

**Artefacts.** `reports/infill_share.{jsonl,scores.json,md}` are §2, 1,792 generations with their
text. `reports/eval/infill_framing_probe.json` is §3. `reports/eval/memorization_infill_share.json`
is §0's control.
