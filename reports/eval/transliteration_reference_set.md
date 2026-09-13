# The reference transliteration set — what it actually measures

**Instrument:** Roman-Urdu-Parl official test split (PRD §8.2, "Transliteration (reference)")
**Written:** 2026-09-10, session 18, while the corpus freeze waits on its last pass
**Verdict:** the split is **4,500 sentences wearing 16,241 rows**, and — separately — **its Roman
column substitutes fixed wrong words for common Urdu words.** The second defect is corpus-wide,
not split-local, so it is a **corpus** finding that happened to be found in an eval set.
**Evidence, all in this directory:** `neardedup_testsplit_roman.json`,
`neardedup_testsplit_urdu.json`, `pairs_testsplit_*.jsonl`, `substitutions_train.json`,
`substitutions_test_confirmed.json`, `substitutions_after_freeze.json`,
`substitutions_screen.json`, `substitutions_screen_test.json`.

---

## 1. Why this pass exists

`progress.md` has carried this since session 11:

> The reference transliteration split contains internal near-duplicates, and that is an instrument
> defect independent of contamination. Nine test rows (`test_set.csv:1:606`–`1:614`) are spelling
> variants of one sentence with an *identical* Urdu column. **Not yet measured at the whole-split
> level** — the obvious check is stage 7 pointed at the test split alone, which is one cheap pass.

It is one cheap pass, and this is it. It answered the question it was asked in §2–§4 and then
answered a larger one nobody had asked, which is §5.

Stage 7 is configured exactly as the freeze ran it on this source — Jaccard ≥ 0.80 over **char**
5-grams, `min_shingles` 8 — so the numbers below sit beside `reports/freeze/neardedup_roman.json`
without conversion. `--no-quality` is deliberate: the published split *is* the instrument, so
nothing is filtered out of it before it is measured.

---

## 2. The split is 4,500 sentences wearing 16,241 rows

Counted directly off the CSV before any normalization, and reproduced independently by stage 6:

| | test_set.csv | validation_set.csv |
|---|---|---|
| rows | 16,241 | 16,219 |
| **distinct Urdu sentences** | **4,500 (27.7%)** | **4,500 (27.7%)** |
| distinct Roman sentences | 11,036 (68.0%) | 11,037 (68.0%) |
| distinct (Urdu, Roman) pairs | 11,036 | 11,037 |
| **rows byte-identical to another row** | **5,205 (32.0%)** | 5,182 (32.0%) |
| largest Urdu group | 10 | 10 |
| mean rows per Urdu sentence | 3.61 | 3.60 |

Urdu-side group sizes in the test split — a third of the sentences appear once, and 106 appear ten
times:

| rows per sentence | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| sentences | 1,500 | 472 | 460 | 497 | 498 | 357 | 284 | 185 | 141 | 106 |

**The two splits are disjoint** — 0 shared Urdu sentences, 0 shared Roman sentences, 0 shared pairs.
So the split *boundary* was drawn correctly, at the sentence. What was not done is the step after
it: each held-out sentence was expanded into all of its crowdsourced Roman variants, and the rows
were shipped as though they were independent items. PRD §6.2's warning — "its ~6.37M pairs collapse
to roughly 1.09M unique Urdu sentences" — is written about the *training* corpus. It is equally
true of the evaluation split, at 3.61 : 1, and that had never been checked.

**5,205 rows carry no information whatever.** Both columns are byte-identical to another row.

---

## 3. What that does to a number computed over rows

A per-row mean weights each sentence by its multiplicity *m* rather than equally. With perfect
within-sentence correlation the effective sample size is `N² / Σmᵢ²`:

| | test | validation |
|---|---|---|
| nominal *N* | 16,241 | 16,219 |
| Σmᵢ² | 88,559 | 87,835 |
| **effective *n*** | **2,978** | **2,995** |
| share of nominal | 18.3% | 18.5% |

Two consequences, of different sizes:

1. **The point estimate is a multiplicity-weighted average.** The 106 ten-variant sentences
   contribute as much as 1,060 of the 1,500 singletons. Nothing fixes this except scoring by
   sentence.
2. **A paired bootstrap resampled by row reports an interval ≈ √(16241/2978) = 2.34× too narrow.**
   PRD §4.5 and preregistration §4 put paired bootstrap CIs on all task metrics. Resampling has to
   be over the **4,500 sentences**, not the rows, or the CI is wrong by a factor the reader cannot
   see. This is a statement about how the metric is computed, not about which metric it is, so it
   costs nothing to honour.

The preregistered secondary endpoint is chrF on the **human-written** set (preregistration §4), not
on this one, so no preregistered number moves. The reference-set number is a PRD §8.3 reported
metric and it is the one that needs the caveat.

---

## 4. Stage 7 on top of that

| | Roman column | Urdu column |
|---|---|---|
| rows in | 16,241 | 16,241 |
| after stage 6 (exact, normalized) | 10,410 (64.1%) | **4,500 (27.7%)** |
| after stage 7 (near, J ≥ 0.80) | **7,477 (46.0%)** | 4,492 (27.7%) |
| characters retained end to end | 37.0% | 21.7% |
| largest cluster | 14 | 3 |

The Urdu column is *clean* once exact duplicates are gone: stage 7 removes 8 more documents out of
4,500. So the 4,500 really are 4,500 distinct sentences, and every bit of the duplication is the
one-sentence-many-spellings structure. The Roman column keeps collapsing because its variants
differ by a letter.

**Read across the cut, 0.80 is conservative here too** — the same verdict Finding AB reached on the
training side, reached again on a different split by the same method. The pairs stage 7 *keeps* are
still one sentence:

| J | fate at 0.80 | pair |
|---|---|---|
| 0.750 | kept | `Iqbal ne usay kabhi arzoo…` / `Iqbal ne ise kabhi arzoo…` |
| 0.773 | kept | `mein tou kuch aur hi samajh…` / `mein to kuch aur hi samajh…` |
| 0.789 | kept | `…magar is qader kahan` / `…magar US qader kahan` |
| 0.828 | removed | `woh iss liye ke aaj meri 61 win saalgirah…` / `wo is liye ke aaj meri…` |
| 0.977 | removed | `aalam deen bhi ensaan hotay heen…` / `alam deen bhi ensaan hotay heen…` |

So **46.0% retained is an upper bound on the split's distinct content**, and 4,500 — the Urdu-side
count — is the honest denominator.

---

## 5. Finding AE — the Roman column substitutes wrong words, and the training corpus has it too

Reading the largest groups to check the duplication was what it looked like turned up something
else. The ten Roman variants of one Urdu sentence do not differ only in spelling:

```
Urdu:  جی کال سنٹر والے سارا دن سوتے ہیں رات کو کام کرتے ہیں
       (…they sleep all day and *work* at night)

1943   jee cal center walay sara din sotay hain raat ko kaam baghaawat hain
1944   ji  cal center walay sara din sotay hain raat ko kaam baghaawat hain
       … seven more, all "baghaawat" …
1952   jee cal center walay sara din sotay hain raat ko kaam karty     hain   ← the only correct one
```

`baghaawat` means **rebellion**. کرتے (`kartay`, "do/work") has been replaced by it, and **nine of
the ten references are wrong while the correct one is the minority** — so majority vote returns the
wrong answer.

It is not a one-off. Measured over the **complete 6,333,218-row training split**, unsampled:

| Urdu word | rendered as | rows with the word | rendered wrongly | correct form present | substitute elsewhere | specificity |
|---|---|---|---|---|---|---|
| بس (`bas`, "just") | `dehli` | 93,307 | 79,594 (85.3%) | 11,833 (12.7%) | 3,107 | 0.962 |
| کرتے (`kartay`, "do") | `baghaawat` | 129,423 | 86,437 (66.8%) | 39,876 (30.8%) | 2,774 | 0.969 |
| گھر (`ghar`, "house") | `mamu` | 61,005 | 54,101 (88.7%) | 6,866 (11.3%) | 1,554 | 0.972 |
| مت (`mat`, "don't") | `sukh` | 12,864 | 11,649 (90.6%) | 1,258 (9.8%) | 1,065 | 0.916 |
| چکر (`chakkar`) | `post` | 10,007 | 8,922 (89.2%) | 1,072 (10.7%) | 1,354 | 0.868 |
| کھلاڑی (`khilari`, "player") | `rgbi` | 9,716 | 6,823 (70.2%) | 2,828 (29.1%) | 134 | 0.981 |
| لائبریری (`library`) | `tromin` | 6,647 | 6,200 (93.3%) | 447 (6.7%) | 57 | 0.991 |
| انقلاب (`inqilab`, "revolution") | `khatima` ("end") | 6,121 | 3,206 (52.4%) | 2,895 (47.3%) | 12 | 0.996 |
| یہ (`yeh`, "this") | `ki` | 783,079 | 671,685 (85.8%) | 177,460 (22.7%) | 1,614,911 | 0.294 |

**Specificity** is P(the Urdu word is present | the substitute is present), and it is the column
that carries the argument. For eight of the nine it is 0.87–0.99: `dehli`, `baghaawat`, `mamu`,
`rgbi`, `tromin` essentially do not occur in this corpus **except** as the rendering of one specific
Urdu word they do not mean. That is a fixed wrong entry in a lexicon — not noise, not crowdsourced
spelling variation, and not a defensible transliteration choice. On the test split alone all eight
measure specificity **1.000**.

یہ→`ki` is listed because its rate is the same, but its specificity is low for a legitimate reason
— `ki` is also the correct rendering of کی and کہ — so it is held out of the conservative count.

**Reach over the full training split:**

| | rows | share of rows | share of Roman characters |
|---|---|---|---|
| carrying ≥1 of the **eight high-specificity** substitutions | **250,249** | **3.95%** | 5.26% |
| including یہ→`ki` | 885,711 | 13.99% | — |

**Both are floors**, from eight words hand-read out of a 225-candidate screen (§7) over a 1/16
sample that contained 36,531 distinct Urdu word types.

### 5.1 Words are deleted as well as replaced

The nine rows the carried-forward note actually named carry both defects at once, which is why the
second went unseen for seven sessions:

```
Urdu:  لائیبریری کا نیا پراجیکٹ … میں بھی فائدہ حاصل کرکے دعائیں دوں گا
       (…so that I too may *benefit*, and give blessings)

1:606  layibriri ka naya project … mein bhi        se haasil karkay duayen dun ga
1:612  layibriri ka naya project … mein bhi faaida haasil karkay duayen dun ga   ← the only complete one
```

Eight of the nine drop فائدہ (`faaida`, "benefit") entirely. The note read these rows as spelling
variants and stopped there — which is what an aggregate does to you when the aggregate you computed
was the right one for a different question.

### 5.2 Stage 6+7 does not remove it

The obvious hope is that the substituted rows are the templated duplicates the freeze already
deletes. They are not. Against the freeze's own removal list
(`reports/freeze/removals_67_roman.txt`, 4,307,848 ids):

| | rows | carrying a confirmed substitution | share |
|---|---|---|---|
| before stage 6+7 | 6,333,218 | 250,249 | 3.95% |
| **after stage 6+7** | 2,025,370 | **56,165** | **2.77%** (3.67% of characters) |

Deduplication removes 68% of the corpus and about a third of the substitution rate with it. The
defect survives at roughly two thirds of its original density, so it is a property of the source,
not of its duplication. (2,025,370 is an upper bound on the frozen set by ~300k rows: rows dropped
by stages 2–5 never reach a removal list. The freeze's own `documents_kept` is 1,724,751.)

### 5.3 What it means for the project

PRD §6.2 already says Roman-Urdu-Parl "is substantially machine-produced" and that a transliteration
claim evaluated on it means "matches that transliterator," not "transliterates well."
**That warning is correct and it is not strong enough.** It describes a *style* mismatch. What is
measured here is that the transliterator emits an unrelated word for at least eight common Urdu
words, at 52–93% of their occurrences, and that the crowdsourcing step PRD §6.2 credits with
spelling variation propagated the error into every variant instead of correcting it.

1. **Evaluation.** The reference-set transliteration number is weaker again. It was already
   discounted for contamination (Finding Q: 16.8% of its Urdu side is in Urdu Wikipedia) and now
   for the 3.61 : 1 row inflation of §2. This is a third, independent discount and it is the
   largest of the three: a model that transliterates کرتے *correctly* is penalised on two thirds of
   the rows containing it. §8.2's human-written set is now carrying essentially the whole
   transliteration claim, and §8.4's human A/B is the only other instrument that can see this.
2. **The corpus.** Roman-Urdu-Parl is the **only** source feeding the `roman_urdu` population
   (PRD §0.3), which is **23.53% of arm A's tokens**. So this is not confined to an eval set: the
   pretraining text for nearly a quarter of the arm contains a fixed set of wrong words at a
   measured rate that survives the freeze. It is not a decontamination problem — stage 8 removes
   training rows matching *test* items, and these rows match nothing.

---

## 6. What this does **not** change

- **No preregistered endpoint moves.** The preregistered transliteration endpoint is the
  human-written set (preregistration §4); this is a PRD §8.3 reported metric. Nothing here is a
  deviation and nothing needs to be logged as one.
- **No gate moves.** G1 counts tokens; corrupted tokens are still tokens.
- **The AR/DIFF comparison is not biased in direction.** PRD §4.1 gives both models the identical
  corpus, so a shared lexical corruption is shared. It raises the floor under both and narrows
  what the corpus can teach; it does not favour a factorization.

---

## 7. What a native speaker has to settle, and what the screen is worth

The eight words in §5 are adjudicated **by machine, not by a fluent speaker** — the same posture
`quality_validation.md` takes for stage 5 and `neardedup_threshold.md` takes for stage 7, and the
technical report must use those words. They were kept because the substitute is a common word with
an unambiguous meaning and its specificity is ≥ 0.87. That is a strong argument. It is not a native
speaker.

The screen that produced them is a **candidate generator with low precision, and it is reported as
one.** It flags an Urdu word type when some Roman token with no plausible sound-correspondence to
it appears in ≥30% of its rows and occurs ≥85% of the time beside it. Over a 1/16 sample of the
training split (395,827 rows) it returns **714 suspect types** and **225 candidates**, of which
perhaps a quarter survive reading. The rest are its own false positives, because the crude
Urdu→Latin skeleton it screens with cannot match English loanwords (`فروری`→`feb`, `کلک`→`click`,
`ویب`→`website`, `اوورز`→`overs`) or `h`/`w`/`y`-heavy words (`ہوئے`→`hue`, `دونوں`→`dono`,
`خوش`→`khush`). Its first draft stripped `h`, `w` and `y` as vowels and flagged `ہے`→`hai` as a
substitution, which is the whole failure mode in one line.

**So: the phenomenon is established beyond doubt and its extent is not.** The floor is 3.95% of
rows from eight words. `substitutions_screen.json` is the list to hand a native speaker, ranked by
row count; it is an hour of work, and it is the same sitting that already owes stage 5 its 29
disagreements, stage 7 its sampled pairs, and the PII pass its one ambiguous Wikipedia match.

**The decision that follows is not this report's to take.** Whether to filter the `roman_urdu`
population on a confirmed substitution list — and pay for it out of arm A's ~1.53× margin — or to
train on the corpus as it is and state the rate in the report, is a corpus-composition change
against a margin that has not been through stage 8. It should be taken with the stage 8 numbers in
hand, not before them.

---

## 8. Reproducing

```bash
# §2, §4 — the split's internal duplication
python scripts/neardedup.py --source roman-urdu-parl --split test --limit 0 \
    --shingle-unit char --no-quality --sweep 0.70 0.75 0.80 0.85 0.90 0.95 \
    --pairs-out reports/eval/pairs_testsplit_roman.jsonl \
    --json reports/eval/neardedup_testsplit_roman.json
#   … add --urdu-side for the Urdu column

# §5 — the substitution table, complete corpus, unsampled
python scripts/substitutions.py confirmed --json reports/eval/substitutions_train.json
python scripts/substitutions.py confirmed --split test --json reports/eval/substitutions_test_confirmed.json

# §5.2 — against the freeze's own removals
python scripts/substitutions.py survivors --removals reports/freeze/removals_67_roman.txt \
    --json reports/eval/substitutions_after_freeze.json

# §7 — the candidate list for a native speaker
python scripts/substitutions.py screen --step 16 --json reports/eval/substitutions_screen.json
```

§3's effective sample sizes are `N²/Σmᵢ²` over the Urdu-side group sizes in §2 and need no pass —
the group-size table is the whole input.
