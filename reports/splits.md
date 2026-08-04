# Stage 9 — the partition, and what U actually counts

**Stage:** Split creation (PRD §6.3.9)
**Written:** 2026-08-04/05, session 11, before the corpus freeze
**Decision:** a document's split and arm membership are **one integer** — a blake2b bucket of its
id — and every boundary is an integer bucket index. Arm A is a *prefix* of arm B, so §6.1's
"deterministic, seeded subsample of the frozen 100M corpus" is a property the construction cannot
violate rather than one a second pass maintains.
**Correction:** **U is the total unique-token budget of an arm, not its native-Urdu component.**
PRD §6.1 and §4.3 disagree; §4.3's own epoch arithmetic settles it, and the reading §6.1 invites
puts arm A **6× short** of the crossover instead of 1.79× past it. See §1.
**Evidence:** `reports/stage9/split_wikipedia.json` and `plan_wikipedia.json` (a **complete** pass
over the Urdu Wikipedia dump), `split_fineweb2_5pct.json` (FineWeb2 at 5%),
`decon_heldout_vs_fineweb2.json` and `hits_heldout_vs_fineweb2.jsonl` (the second stage-8 run,
which stage 9 unblocked).

---

## 1. Finding R — §6.1 and §4.3 do not describe the same corpus, and one reading is fatal

This is the largest result of the session and it is a design correction, not a measurement.

PRD §6.1 lists per-component collection targets:

| Component | Target |
|---|---|
| Clean native Urdu | ~120M unique tokens (**"100M for arm B** + ~20% headroom") |
| Roman Urdu | ~40M tokens |
| Code-switched | ~10M tokens |

PRD §4.3 fixes the arms at U ∈ {25M, 100M} for ~396 and ~99 epochs. **Assembling an arm by taking
each population's target gives arm A 25M + 40M + 10M = 75M unique tokens, not 25M.** Both readings
cannot be right.

**§4.3's own arithmetic settles it.** 396 × 25M = 9.9B and 99 × 100M = 9.9B, so epochs are counted
over the *whole training set*. So is the U in Prabhudesai et al.'s fitted law — it is the size of
the training set the model repeats over, which is what makes the law a statement about data
constraint at all.

**The cost of the other reading is the same class of error as Finding A, on the arm carrying the
primary endpoint.** At 70M parameters and the same 9.9B tokens processed:

| Reading | Arm A's true U | Epochs | C / C_crit | |
|---|---|---|---|---|
| U = total unique tokens (**taken**) | 25M | 396 | **1.79× past** | reproduces §4.3's table exactly |
| U = native component only | 75M | 132 | **6× short** | needs ~802 epochs to reach it |

```
python scripts/crossover.py --params 70e6 --unique 75e6 --epochs 132
```

Arm B is the check that this is the intended reading and not a convenient one: at U = 100M total
and 99 epochs the arithmetic gives 0.09× of C_crit, which is **exactly** the figure PRD §4.3's
table already states. The table is only reproducible under the total-U reading, so §6.1's component
list is the part that misleads — its figures are **pool** targets (how much to collect), not arm
budgets (how much to train on).

**What stage 9 therefore does.** The arms are assembled from the pools at a fixed mixture: §6.1's
targets in proportion, 120 : 40 : 10.

| Population | Share | Arm A (U = 25M) | Arm B (U = 100M) |
|---|---|---|---|
| Native Urdu | 70.59% | 17.65M tokens | 70.59M tokens |
| Roman Urdu | 23.53% | 5.88M | 23.53M |
| Code-switched | 5.88% | 1.47M | 5.88M |

Holding the mixture fixed across arms is what "differ in size and nothing else" (§4.1) means once
there is more than one population. Scaling only the native component would confound U with source
mix — the same failure §6.1 already forbids for crawl date.

**Two consequences that outlive this session.**

1. **The PRD needs amending at §6.1**, the way §4.3 and §6.1 were amended in v2.1 for Finding A.
   The component figures should be labelled as pool targets and the arm mixture stated.
2. **The code-switched shortfall shrinks by 41%.** The carried-forward ⚠️ was written against
   §6.1's 10M figure. Arm B needs **5.88M**, not 10M. §6 measures whether that is reachable.

---

## 2. The partition is one integer

A document's entire fate at stage 9 is `bucket_of(doc_id)` — blake2b of the id, keyed to this
stage, quantized to `[0, 100000)` — and every split and arm is a *range* of buckets:

```
0                                    arm A        arm B     train_to  val_from        100000
|--------------------------------------|------------|----------|---------|-------------|
|<-------------- arm A --------------->|
|<--------------------- arm B ---------------------->|
|<------------------------- train ----------------------------->|validation|    test
```

Five properties follow, and each is a PRD requirement:

| Property | Why it is not merely a nicety |
|---|---|
| **Arm A is a prefix of arm B** | §6.1's "subsample of, not a separate collection", for *any* budgets, with no membership list to drift |
| **Membership is a per-document function** | "Take documents until the budget is full" makes membership depend on read order — Finding E's defect exactly. It also lets Finding G's softened form apply: a sampled phase 1 estimates the band quantiles honestly |
| **Both arms share one held-out set** | §4.3's primary endpoint is validation BPB on the A and B curves. Per-arm held-out sets would compare numbers computed on different data |
| **Held-out budget changes cannot move a document between arms** | Bands grow down from the top, arms grow up from zero — while the train pool still covers the arm cuts. Past that the arm is truncated and reported `unmet` |
| **Every boundary is an integer** | Session 10 lost a stage-8 removal to `array("f")` holding 0.80 as 0.80000001. `bucket < cut` between two ints has no boundary behaviour to get wrong |

**Both columns of a parallel row hash to the same bucket.** Stage 8's driver reads a
Roman-Urdu-Parl row as `id#roman` and `id#urdu`; hashing those independently would put a sentence's
Roman side in train and its Urdu side in test roughly half the time — **the splitter manufacturing
the contamination stage 8 exists to remove**, and scoring §4.5's transliteration endpoint against
training data. `pair_key()` strips the suffix before hashing.

---

## 3. Tokens do not exist yet, and the stage is built so it does not matter

The tokenizer is Week 5 (§7); the freeze is Weeks 3–4. Stage 9's budgets are denominated in tokens
and **no measured fertility exists**. Three things follow from how that is handled.

* **Characters are measured; tokens are derived at solve time.** `chars_per_token` is per
  population, declared in `configs/data/splits.json`, and is the only estimated number in the stage.
* **The plan carries its histogram**, so a corrected fertility re-solves every boundary without a
  corpus pass. Measured on the real Wikipedia plan: **0.32 s**, against the ~20 minutes the pass
  that produced it took.

  ```
  ravaan-splits reports/stage9/plan_wikipedia.json --chars-per-token urdu=4.5
  ```

  At 3.5 chars/token arm A's native cut sits at bucket 34,161; at 4.5 it moves to 43,648 and still
  holds 17.65M tokens. **The estimate being wrong moves where the cuts land; it cannot break the
  nesting, the band ordering, or the reproducibility of any assignment.**
* **The assumption is reported in units a reader has intuition for.** Every pass prints the
  characters-per-word it measured beside the ratio it solved with, so the implied tokens-per-word is
  visible rather than buried:

  | Population | chars/word measured | solved at | implied tokens/word |
  |---|---|---|---|
  | urdu | 4.89 | 3.5 chars/token | 1.40 |
  | roman_urdu | 5.50 | 4.2 | 1.31 |
  | code_switched | 5.71 | 3.8 | 1.50 |

  These are plausible for a 16k unigram model and they are **not measurements of it**. Week 5 must
  re-solve, and the report must not quote a token count from this stage as though it were counted.

---

## 4. A complete pass over Urdu Wikipedia

93,606 documents reach stage 9 (200,148 read; stage 5 keeps 46.8%, matching session 6's 46.72%).
416 fall outside the budgeted populations — 222 `other`, 184 `english`, 10 `arabic` — and are
counted rather than silently dropped.

| | documents | characters | ~tokens |
|---|---|---|---|
| **urdu** train | 83,488 | 167,932,053 | 47.98M |
| urdu validation | 3,080 | 6,321,365 | 1.81M |
| urdu test | 2,754 | 6,322,883 | 1.81M |
| **code_switched** train | 2,954 | 3,252,802 | 0.86M |
| code_switched validation | 492 | 571,938 | 0.15M |
| code_switched test | 420 | 566,391 | 0.15M |
| **roman_urdu** (all) | 2 | 70,969 | 0.02M |

**The band solve is accurate to five decimal places on real text.**

| Band | target chars | realized | error |
|---|---|---|---|
| urdu arm A | 61,764,706 | 61,764,222 | **−0.00078%** |
| urdu validation | 6,324,706 | 6,321,365 | −0.053% |
| urdu test | 6,324,706 | 6,322,883 | −0.029% |
| code_switched validation | 572,235 | 571,938 | −0.052% |

The error is bounded by one bucket of ~1,800 characters against a ~62M-character budget, and it is
**always an undershoot by construction**: an arm's budget *is* §4.3's U, and U is what the epoch
count divides 9.9B by, so a boundary that rounded upward would quietly buy fewer epochs than the
design specifies.

**The two structural guarantees were checked against the 93,606 real assignments, not only in
tests:** arm A ⊂ arm B strictly (33,557 of 86,442 documents), and **0** held-out documents carry an
arm.

**Wikipedia alone cannot fill arm B, and that is the expected shape.** It supplies 47.98M native
tokens against arm B's 70.59M. `roman_urdu` is 2 documents — Wikipedia is not a Roman Urdu source,
and the `unmet_heldout` flag fires correctly rather than the pool being quietly consumed.

**A defect this pass found in stage 9 itself.** On the first smoke run (2,482 documents) *every*
document landed in `test` and only the arms reported `unmet`. The bands are solved from the top, so
a pool smaller than §6.1's ~5K sequences does not merely produce a short validation set — it eats
the train pool, and every arm then reports unmet for a reason that is not its own. `unmet_heldout`
now names the upstream cause, and the driver prints it first.

---

## 5. FineWeb2 at 5%, and a reporting defect it caught

76,940 documents, **0** outside the budgeted populations — stage 3 is an assertion on this source,
the same shape sessions 4 and 5 found for stages 2 and 3.

| | documents | characters | ×20 → full shard |
|---|---|---|---|
| urdu train | 76,300 | 182,966,015 | 3.66G chars |
| code_switched train | 332 | 813,980 | 16.3M chars |
| roman_urdu | 0 | 0 | 0 |

**The defect: a sampled pass reported Gate G1 twenty times too low.** `gate_g1()` read the measured
character total without scaling by the sample rate, so this pass printed `ARM_A_ONLY — 52.7M clean
tokens` for a shard that actually holds **~1.05B**. That is the same figure as the complete
Wikipedia pass's 52.8M, by coincidence — which is exactly the kind of agreement that reads as
corroboration.

This is Findings O and P a third time — **one number meaning two things depending on how it was
produced** — arriving at the one number in this stage that is a *project decision* rather than a
statistic. G1's ladder cuts arm B at 25–100M and stops the project below 25M. Fixed: the gate
scales by the sample rate, reports the measured figure beside the scaled one, and the arm targets
print at the rate they were solved against.

| | before | after |
|---|---|---|
| FineWeb2 5% G1 | `ARM_A_ONLY — 52.7M` | `PASS — 1,053.7M (from 52.7M measured at r=0.05)` |

**A second, smaller correction — to how the band error should be described.** §4 quotes arm A's
Wikipedia error as −0.00078% and calls the bound "one bucket". The FineWeb2 pass shows the real
bound: arm A undershot by 211,883 characters, and the bucket at the cut held a **single
238,787-character document**. With 76,940 documents in 100,000 buckets most buckets hold at most one
document, so **the undershoot is bounded by the largest single document at the cut, not by an
average bucket**, and raising `buckets` cannot reduce it below one document. At full-scale budgets
(247M characters for arm B's native share) a 500K-character document is a 0.2% undershoot, which is
acceptable — but the report must not quote Wikipedia's five-decimal accuracy as the general case.

**The precision therefore tracks document size, and the three passes bracket it:**

| source | unit | arm A error | arm B error |
|---|---|---|---|
| Roman-Urdu-Parl | sentences (~74 chars) | −0.0041% | −0.0029% |
| Urdu Wikipedia | articles (~2,000 chars) | −0.0008% | unmet |
| FineWeb2 | web pages, long tail to 240K chars | **−6.86%** | **−0.0110%** |

The two FineWeb2 figures are the whole point: the *same* mechanism, on the same corpus, one pass
apart. The error is one document's worth of characters, so it is large against arm A's budget and
negligible against arm B's four-times-larger one. Both are measured against budgets scaled to 5%,
so at freeze scale both shrink by a further 20×. The bound to quote is therefore **"the largest
document at the cut, divided by the budget"** — not a bucket, and not a fixed percentage.

---

## 6. What the corpus comes to, and the code-switched question

Projecting the complete Wikipedia pass and the FineWeb2 sample (×20). The freeze must re-measure
this in one unsampled pass, but only one line is close enough to the boundary to be in doubt:

| Population | Wikipedia | FineWeb2 (×20) | Roman-Urdu-Parl (×20) | total chars | ~tokens | **arm B needs** | margin |
|---|---|---|---|---|---|---|---|
| urdu | 180.6M | 3,671.8M | 0 | 3,852.4M | **1,100.7M** | 70.59M | **15.6×** |
| roman_urdu | 0.07M | 0 | 453.5M *(pre-dedup)* | 453.6M | **61.5M** *(post-dedup)* | 23.53M | **2.6×** |
| code_switched | 4.4M | 17.4M | 0 | 21.8M | **5.7M** | 5.88M | **0.97×** |

**Gate G1 passes on native Urdu by a factor of 15.6**, and §6.1's ~120M native collection target
has far more headroom than "20% for filtering losses" suggests — because arm B's native share is
70.59M under the corrected reading of U, not 100M.

**Roman-Urdu-Parl supplies the whole roman_urdu population, and the two independent estimates
agree.** A 5% pass over its train split assigns 281,215 of 301,389 rows (the 20,174 remainder is
14,210 `empty`, 5,669 `other`, 295 `english` — the unit mismatch session 5 measured, single
sentences below the letter floor). Its Roman column projects to 453.5M characters **before** stage
6, and session 8's Finding K′ measured 3,478,770 *distinct* sentences × 74.2 characters ≈ 258M
characters **after** — a 43% collapse, matching PRD §6.2's warning that the source is
machine-produced. Post-dedup that is **61.5M tokens against arm B's 23.53M, a 2.6× margin**, wider
than the ~1.4× the pre-Finding-R reading of §6.1's 40M target implied.

**The code-switched population is the one tight line, and Finding R more than halves the problem.**

| | requirement | available | verdict |
|---|---|---|---|
| Carried-forward note (§6.1's 10M target) | 10M tokens | ~7M | **43% short** |
| Corrected (arm B's 5.88M share) | 5.88M tokens | **5.7M** | **3% short** |

A 3% shortfall is not a design problem, and the carried-forward note already names the fix in
preference order: **(a) fetch FineWeb2 train shard 000 as well**, which roughly doubles the FineWeb2
contribution at ~$0 and ~25 minutes, taking the population to ~10.3M tokens. That is now the
recommended action rather than one of three options — (b) "accept a smaller share and say so" costs
a stated corpus-composition change and (c) "add a social-media source" costs a new licence-gate
decision, and neither is warranted for a 3% gap.

---

## 7. The second stage-8 run — the one stage 9 unblocked

Session 10 left this as "the most important decontamination run in the project and it has not
happened", blocked because the held-out split did not exist. It exists now.

**Setup.** Eval set: the 6,748 held-out Urdu Wikipedia documents (validation + test) from §4, word
5-grams, 2,553,769 distinct shingles, 43,214 indexed lines, **0 items below `min_shingles`** — every
held-out document is measurable by containment, unlike the sentence-unit sets where 24.8% are not.
Corpus: FineWeb2 at 5%, 76,940 documents.

| | |
|---|---|
| training documents removed | **15 of 76,940 = 0.0195%** |
| **held-out items compromised** | **15 of 6,748 = 0.222%** |
| removed by `exact_line` | 13 |
| removed by containment | 2 |
| removed by `exact_document` | **0** |

**Scaled to the full shard this is ~300 of 6,748 ≈ 4.4% of the held-out split**, since an eval item
with a single crawled copy is found with probability *r*. That number belongs in §8.2's description
of the held-out set, and the freeze must run this pass complete rather than sampled.

**Finding L is refined rather than confirmed, and the refinement matters.** Finding L measured the
*document*-level hash returning a confident zero on the wiki path, and it still does — **0** of 15.
But **line**-level exact matching, added in session 10 on a structural argument rather than a
measurement, carries **13 of 15**. Measured directly, by re-running the fuzzy half alone over the
same 15 documents:

| | |
|---|---|
| caught by containment alone | 6 of 15 |
| **survive without the exact half** | **9 of 15** |
| **survive without the fuzzy half** | **2 of 15** |

**Both halves are load-bearing on this path and neither subsumes the other.** The two
containment-only catches are the cleanest possible demonstration of Finding M: both are
`ur.wikipedia.org` crawls sharing **zero** whole lines with the held-out article — HTML rendering
re-flows the line breaks — while 92% and 90% of the word 5-grams are present. Document hashing
cannot see them, line hashing cannot see them, and Jaccard would not have proposed them.

**The mechanism, read rather than assumed.**

| host | shared lines | reading |
|---|---|---|
| `ur.wikipedia.org` / `ur.m.wikipedia.org` (9 documents) | 2–9 of 3–20 | crawled copies of the held-out article — Finding L's mechanism, at corpus scale |
| `top.hatnote.com/ur/` | 1 of 7 (286 chars) | Wikipedia's own top-articles aggregator, reproducing an extract |
| `baadban.tv`, `urdupoint.com` | 1 each (97, 66 chars) | specific news sentences shared verbatim — genuine reuse |
| `darululoom-deoband.com` | 3 of 15 | genuine |
| `aalmiakhbar.com` | 1 (91 chars) | **likely false positive** — "he was a prolific poet and author; among his collections the following are important" is a *genre formula*, not content |
| `dailypakistan.com.pk` | 1 (40 chars, exactly at the floor) | **likely false positive** — a line of a well-known ghazal, quoted independently by both documents |

**Precision ≈ 13/15 ≈ 0.87**, against 0.73 measured on the Roman-Urdu-Parl path in session 10. The
two errors are one nameable family and it is a *new* one: **the 40-character line floor admits
shared quotations — poetry and genre formulae — which are common third-source text rather than
evidence that one document contains the other.** Left in, on the standing argument that a false
positive costs one training row out of millions and a false negative costs the validity of an
evaluation number.

**This adjudication was made by Claude, not by a native speaker**, in the same way session 6's
200-sample validation was, and it belongs on the same list. The 15 hits are few enough that the
native-speaker sitting which owes stage 5 its 29 disagreements could settle these in minutes.

---

## 8. What this stage does not do

* **It has no threshold validated against read documents.** Stages 5, 7 and 8 each moved numbers by
  reading what they deleted. Stage 9 has no such number: its only estimated input is
  `chars_per_token`, and the honest treatment of that is not to validate it now but to make it
  re-solvable in Week 5, which §3 does.
* **It has not been run over all sources in one pass.** The runs here are per source, so each set of
  bands is calibrated to that source's totals rather than to the corpus. **The freeze must run one
  unsampled phase 1 over every source together** and apply that single plan with `--plan-in`;
  per-source plans give each source its own held-out share instead of the corpus's.
* **It ran before stages 6 and 7 in these passes.** Exact and near-duplicate removal were not
  applied, so the held-out split can still contain near-duplicates of training documents from
  *within* Wikipedia — the geo-stub farms session 9 measured at 10.7% of the dump. Stage 8 catches
  the cross-source case and does not catch that one. **The freeze order must be 6 → 7 → 9 → 8**, and
  the held-out split's integrity depends on stage 7 having run first.
* **The PII regex pass (§6.3) is still not built**, and it belongs before the corpus is written.
