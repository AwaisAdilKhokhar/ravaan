# The same budget, spread two ways — what repetition does to each arm

**Session 23, 2026-09-14.** Two pairs of 20M-parameter models, each processing **exactly
367,919,104 tokens**, differing in how many unique tokens those were drawn from:

| | unique tokens | epochs | corpus |
|---|---|---|---|
| **repeated** | 7,358,976 | 50 | `data/packed-pilot` — §6.1's three populations, G3's pilot |
| **plentiful** | 186,931,200 | 2 | `data/packed-urdu` — native Urdu only, built this session |

This file exists because [`pilot_coherence.md`](pilot_coherence.md) §0 recorded a verdict — *AR is
fluent, DIFF is not, on the same corpus and the same code* — whose control turns out not to have
been doing the same thing as the arm it controlled for.

> **None of these numbers goes in a results table.** Neither corpus is the freeze: stage 8 has not
> run on either, FineWeb2's stage 6+7 has not run, and neither split is stage 9's. The `plentiful`
> corpus is additionally **urdu-only**, so it is not arm A's mixture. This is a diagnostic about a
> *mechanism*, at one seed and one rung, and §4.3 is the experiment.

---

## 1. The finding: at 50 epochs the AR arm is reciting the corpus

`scripts/memorization.py` runs `Trainer.evaluate`'s plain-LM scoring twice — once over a spaced
sample of the split the model trained on, once over held-out. Same objective, same denominator,
same code path, 384 sequences per split, so the difference between the two numbers is
generalization gap and not framing.

| corpus | checkpoint | epochs seen | arm | train | held-out | **gap** |
|---|---|---|---|---|---|---|
| repeated | `ar_fp25` | 12.5 | AR | 3.406 | 4.502 | **+1.096** |
| repeated | `ar_f1` | 50 | AR | 1.705 | 6.641 | **+4.935** |
| repeated | `diff_fp25` | 12.5 | DIFF | 5.547 | 5.608 | **+0.062** |
| repeated | `diff_f1` | 50 | DIFF | 4.796 | 4.966 | **+0.170** |
| plentiful | `ar-s0_f1` | 2 | AR | 3.734 | 3.781 | **+0.047** |
| plentiful | `diff-s0_f1` | 2 | DIFF | 4.344 | 4.408 | **+0.064** |

Nats per token. Each arm is compared **only to itself on two splits** — an ELBO and an exact
likelihood cannot be compared to each other, and this table never does.

**It is a curve, not a point.** Over the second half of the repeated run the AR arm's gap goes
**+1.10 → +4.93** while the diffusion arm's goes **+0.06 → +0.17**. The AR arm spends its
generalization progressively as the epochs accumulate; the diffusion arm barely moves. On the
plentiful corpus, where two passes make memorization impossible, **both gaps are ~0.05** — which is
the control that says the instrument measures what it claims to.

**Why the objectives differ here is not mysterious.** The AR arm sees the same factorization on
every pass, so the same text presents the same prediction problem 50 times. MDLM draws a fresh
masking rate *and* a fresh mask per sequence, so the same text presents an effectively
non-repeating task distribution. The diffusion arm's resistance to repetition may be a property of
the objective rather than of its capacity — and §4.3 is the experiment that would say.

---

## 2. What that does to G3's verdict

§9 of `pilot_coherence.md` reads: *"The control is that **Ravaan-AR is fluent on the same corpus,
the same loop and the same code** — a defect in anything shared would show in both arms."*

The first clause is intact: a defect in anything shared would indeed show in both arms, and none
did. **The second is not the comparison it reads as.** At 50 epochs over 7.36M tokens the two arms
were not doing the same thing — one memorized the corpus and looked fluent, and the other did not
memorize, which at that data scale means not having enough Urdu to learn Urdu from. "AR is fluent
and DIFF is not" was never evidence that DIFF was broken.

---

## 3. So the comparison was run again where neither arm can cheat

Same 25M rung, same §4.2 mixture, same optimizer, same 367,919,104-token budget, same seed —
186.9M unique tokens at 2 epochs. Both gaps come out ~0.05 (§1), so this is the first matched pair
this project has that is actually matched.

### Held-out bits-per-byte, native Urdu

| data regime | Ravaan-AR (exact NLL) | Ravaan-DIFF (ELBO) | ahead |
|---|---|---|---|
| 7.36M unique × 50 epochs | 1.4200 | **≤ 1.0737** | **diffusion, provably** |
| 186.9M unique × 2 epochs | **0.8154** | ≤ 0.9703 | AR, on the bound |

**The asymmetry in that table is the point and it must survive into the report.** §4.3 already
requires the diffusion figure to be stated as a bound; the consequence, which is easy to lose, is
that **the bound can prove a diffusion win and can never prove an AR one.** Row one is therefore a
result: the diffusion arm's upper bound is 0.35 bpb below the AR arm's exact likelihood, and its
true value is lower still. Row two is *consistent with* an AR win and does not establish one —
Ravaan-DIFF's true NLL could sit anywhere at or below 0.9703, including below 0.8154. What carries
row two is the text, not the number.

### The text

At 2 epochs, `lm/free`, the AR arm writes connected Urdu news prose:

> ...تو یہ کیا کہنا کہ عمران خان کو کیوں ڈرایا گیا اس نے اعلان کیا تھا کہ نواز شریف نے عدالت کے
> باہر مولانا فضل الرحمٰن اور ان کی جماعت کو دو سو فیصد سے زیادہ رشوت دیدی

and the diffusion arm, at its best decoder setting (`gumbel` 2, 160 steps, `</s>` forbidden),
writes well-formed Urdu clauses that loop on a slot:

> آپ کی مصنوعات کو بھی محسوس کر رہا ہے، آپ ایک دوسرے کو تلاش کرتے ہیں اور اپنے آپ کے تجربے کو تلاش
> کرتے ہیں... اس کے ساتھ آپ کی معلومات حاصل کرنے کے لئے استعمال کر رہے ہیں

Both are real Urdu words in grammatical order. They are not the same thing to read, and **§8.3's
three metrics score them within a few hundredths of each other** — the blindness
`pilot_coherence.md` §6 identified, showing up again on a different pair of checkpoints. Adjudicated
by Claude; [the annotation page](https://claude.ai/code/artifact/92e617de-5364-4273-8584-8ff1cc95dea2)
exists so a fluent reader can overrule this paragraph.

### What the extra data did fix

Going from 7.36M to 186.9M unique tokens removed **the script collapse** — the repeated corpus's
unconditional samples fall into Roman Urdu (Arabic-script share 0.250 at fraction 1.0), the
plentiful corpus's do not (0.999–1.000). That is a mixture effect as much as a scale one, since the
plentiful corpus is urdu-only, and it is the one improvement here that has a second explanation.

---

## 4. The sign flips, and it flips the way the experiment predicts

Diffusion ahead where data is repeated; AR ahead where data is plentiful. That is **§4.5's primary
endpoint — the sign of the AR/DIFF crossover** — appearing at pilot scale, on this pipeline, before
anything has been rented. Arm A's whole design is to sit in the repeat regime (25M unique tokens,
~396 epochs) precisely because that is where the crossover is predicted.

**Four reasons this is corroboration and not a result.**

1. **The two regimes are two different *corpora*, not one corpus at two budgets.** Composition is
   confounded with repetition: `repeated` carries §6.1's three populations and `plentiful` is
   native Urdu alone. The clean design is one corpus and two epoch counts, and the frozen corpus is
   what makes it affordable.
2. **The ELBO is one-directional evidence** (§3). Half the table is a bound that cannot decide the
   direction it points.
3. **One seed, one rung, 20M parameters** at 368M training tokens — two orders of magnitude below
   §4.3's 9.9B.
4. **Neither corpus has been through stage 8**, so both held-out splits carry unmeasured
   contamination. Finding T projects ~4.4%, which flatters *both* held-out figures and therefore
   *understates* the AR arm's memorization gap in §1 — the conservative direction for the claim
   this file makes.

**What it earns is a cheaper early warning than G4.** Session 22 accepted, on the record, the risk
that a diffusion-only defect would surface only after six core runs were paid for. No defect was
found here; what was found is the diffusion arm behaving the way the hypothesis says it should,
under the one variable the hypothesis is about.

---

## 5. Reproducing this

```bash
# the plentiful corpus — ~25 min, urdu only, and NOT the freeze
python scripts/tokenizer.py sample --source urdu-wikipedia --split train --limit 0 \
    --exclude reports/freeze/removals_67_wikipedia.txt --chars 500000000 \
    --population-chars roman_urdu=0 --population-chars code_switched=0 --out data/urdu-sample
python scripts/tokenizer.py sample --source fineweb2-urd_Arab --split train --limit 0 \
    --chars 500000000 --population-chars urdu=360000000 \
    --population-chars roman_urdu=0 --population-chars code_switched=0 --out data/fw2-sample
cat data/fw2-sample/sample_urdu.txt >> data/urdu-sample/sample_urdu.txt
python scripts/pack_pilot.py --sample data/urdu-sample --out data/packed-urdu \
    --tokenizer data/tokenizer/ravaan-16k.model --purpose "session 23 diagnostic"

# each arm — ~2.7 h on a 4060, 39k tok/s
python scripts/train.py run --arm diff --size 25M --seed 0 --corpus data/packed-urdu \
    --tokenizer data/tokenizer/ravaan-16k.model --tokens 367919104 \
    --tokens-per-step 65536 --microbatch 32 --warmup-steps 100 --log-every 25 \
    --out runs/urdu-diff --evaluate            # --arm ar --out runs/urdu-ar for the control

# the gap
python scripts/memorization.py --corpus data/packed-pilot --sequences 384 \
    --checkpoint runs/pilot/pilot-ar/ar_fp25.pt --checkpoint runs/pilot/pilot-ar/ar_f1.pt \
    --checkpoint runs/pilot/pilot-diff/diff_fp25.pt --checkpoint runs/pilot/pilot-diff/diff_f1.pt \
    --out reports/eval/memorization_pilot.json
```

**Artifacts.** `reports/eval/memorization_{pilot,urdu,urdu_pair}.json` are §1's table.
`reports/urdu_pair_samples.*` is the matched pair at 2 epochs; `reports/urdu_samples.*` is the full
decoder grid over the pilot's two arms and the plentiful diffusion arm (594 generations);
`reports/diffusion_scale_samples.*` is one decoder setting across four fraction checkpoints of each
diffusion run. Checkpoints are under `runs/`, which is git-ignored — 3.8 GB.
