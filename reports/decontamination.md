# Stage 8 — choosing the decontamination instrument and its thresholds

**Stage:** Evaluation decontamination (PRD §6.3.8)
**Written:** 2026-08-04, session 10, before the corpus freeze
**Decision:** score **containment of the eval item**, measured **exactly** from an inverted index
over the test sets — not a MinHash sketch, and not Jaccard. Thresholds are **per test set**:
documents at containment ≥ 0.80, sentence-unit sets at ≥ 0.90 over character 5-grams with a
25-shingle floor.
**Evidence:** `reports/probe_decontamination_rup.json` (the acceptance test, §4–§6),
`probe_decontamination_wikipedia.json` and `probe_decontamination_fineweb2.json` (the cross-source
result, §7), the adjudicated survivors in `probe_decon_rup_survivors.json`, and the measured hits in
`decon_hits_*.jsonl`. The two native-source hit files carry the hits **at or above the shipped
threshold**; their unfiltered form is 890 MB of sub-threshold noise (see §8.6) and is not committed.
`eval_coverage` in the two native JSONs under-reports — those passes predate the fix that records
every compromised eval item rather than the strongest per document — so §7's item counts are
computed from the hit files, which were always complete.

Session 9 handed stage 8 two instructions. One survived contact with the problem and one did not,
and the one that did not is the main content of this record.

* **"Score containment, not Jaccard"** — Finding M. This survived, and the measurements below
  strengthen it: on the cross-source path *every* genuine hit has a Jaccard low enough that a
  Jaccard-thresholded decontamination would report a clean corpus.
* **"Reuse the sketch — stage 8 is the same instrument pointed at the test sets"** — this did not,
  and §2 is why. The sketch estimates Jaccard and LSH proposes candidates by Jaccard, so the pair
  has to become a candidate *before* any containment could be computed from it. At the sizes stage
  8 actually deals with, it does not.

---

## 1. What stage 8 is, in one line of arithmetic

Stages 6 and 7 compare a corpus against **itself** — 1.5M × 1.5M pairs — which is why they need a
sketch and a banding at all. Stage 8 compares a corpus against a **bounded** artifact: §8.2's test
sets are ~6K items. That asymmetry is the whole design. The eval side fits in memory exactly, so
one dict lookup per corpus shingle yields the **true** intersection, and containment and Jaccard
both follow from it with no estimation error, no S-curve, and no second threshold nobody swept.

---

## 2. Why the sketch is not reused, measured

An eval item sitting **verbatim** inside a training document — containment 1.000, the exact shape
Finding M says stage 8 must catch — has a Jaccard of |E| / |T|, which *falls as the document grows*.
The shipped (32, 4) banding proposes such a pair with this probability:

| eval item | training document | Jaccard | P(banding proposes it) |
|---|---|---|---|
| 96 shingles | 150 | 0.640 | 0.997 |
| 100 | 200 | 0.500 | 0.873 |
| 100 | 400 | 0.250 | 0.118 |
| 100 | 800 | 0.125 | 0.0078 |
| **100** | **1,500** | **0.067** | **0.0006** |

**Retuning does not rescue it**, and this is the part that makes it structural rather than a bad
setting. The precision column is measured on this corpus rather than assumed: over 2,775 pairs of
unrelated long Urdu Wikipedia articles, sampled across the whole dump, Jaccard has **median 0.0000,
mean 0.00034, p99 0.0044** — and Urdu Wikipedia's templated stub farm, which session 9 measured at
10.7% of the dump, sits far higher at **J ≈ 0.23**.

| bands × rows | inflection | recall at J = 0.067 | P(candidate) at mean | at p99 | at the stub farm |
|---|---|---|---|---|---|
| 32 × 4 (shipped) | 0.420 | **0.0006** | ~0 | ~0 | 0.090 |
| 64 × 2 | 0.125 | 0.248 | 0.000007 | 0.0012 | 0.972 |
| 128 × 1 | 0.008 | **0.9999** | **0.043** | **0.429** | **1.000** |

At (128, 1) the recall arrives and the precision collapses: at the *measured mean* alone, 4.3% of
pairs become candidates, which over a 1.5M-document corpus × a 5K-item test set is **3.2 × 10⁸**
verifications — and every stub-farm pair is proposed with certainty on top of that. Either end
fails, because **Jaccard between a small item and a large document is low however complete the
containment is**, and MinHash estimates Jaccard.

> A measurement that had to be redone, recorded because it nearly shipped. The first baseline was
> taken from the first 400 documents of the dump filtered to >400 characters, and returned a median
> Jaccard of **0.38** — which is not a baseline at all. That selection is almost pure French-commune
> geo-stub, Finding I's population, where near-identity is the *content*. Spreading the sample
> across the dump and asking for real articles moved the median to 0.0000. Finding E's lesson yet
> again: a prefix is not a sample, and the number that came back was wrong in the direction that
> would have flattered the argument being made.

So the shingling is shared with stage 7 — `shingle_hashes` is imported, so both stages agree what a
document is made of — and the sketch is not. Stage 7 *derives* its intersection from an estimate
because it never holds both shingle sets at once; stage 8 holds the eval side whole and counts.

**This is Finding E's lesson in a fourth costume: the instrument has to be able to measure the
quantity being asked for.** A stage 8 built on the sketch would have run, raised nothing, removed
almost nothing, and reported a clean corpus.

---

## 3. Direction — the containment helper stage 7 already has is the wrong one

`containment_from_jaccard` divides by `min(|A|, |B|)`, which answers stage 7's symmetric question:
"is either of these inside the other". Stage 8's question has a subject and an object — *is this
test item inside this training document* — and when the eval item is the larger of the two, `min()`
silently measures the training document's containment and reports a number about the wrong object.
A 500-shingle eval item sharing 100 shingles with a 100-shingle training row is 20% contaminated;
`min()` calls it 100% and deletes a clean document. `containment_of()` divides by the eval item.

Removal is always of the **training** document. Stage 8 has no survivor rule and no lowest-key
tie-break, because it is not choosing between two copies: a test set is an instrument, and
shrinking it to fit the corpus is measuring the thermometer. That also makes the stage trivially
order-independent — a verdict is a function of the document and the sealed eval index and nothing
else — which is the property stages 6 and 7 each pay a second corpus pass to obtain.

---

## 4. The acceptance test: is the reference split already inside its own train split?

PRD §6.2 warns Roman-Urdu-Parl is substantially machine-produced and its 6.37M pairs collapse to
roughly 1.09M unique Urdu sentences. §4.5 makes transliteration chrF on this corpus a **secondary
endpoint**. If its test rows are also train rows, that number measures memorisation.

Run over a 20,000-row slice of the train split (35,858 documents after stages 2–5, **both
columns**), against the complete 16,241-row test split indexed on both sides.

### 4.1 The first run was wrong, and reading its output is what showed it

| | first run | after §5's two fixes |
|---|---|---|
| documents checked | 35,858 | 35,858 |
| documents removed | 648 (**1.81%**) | **11 (0.031%)** |
| test items implicated | 229 | 23 |

The 648 was a **59× over-count**. It is recorded here because the number looked plausible, matched
the prior ("this corpus is known to be duplicated"), and was wrong — and nothing but reading the
hits would have caught it. The threshold sweep from the corrected pass shows how steep the region
is, which is itself the reason the first number was so far out:

| containment | documents removed | test items implicated |
|---|---|---|
| 0.80 | 75 | 138 |
| **0.90** | **11** | **23** |
| 1.00 | 1 | 1 |

---

## 5. Two false-positive families, two different levers

Reading the strongest hits at containment ≥ 0.80 split the errors cleanly in two, and neither lever
fixes the other's family.

**Family 1 — degenerate fragments, fixed by `min_shingles`.** Two thirds of the hits (918 of 1,389)
came from eval items of 8–15 character 5-grams, i.e. 12–19 characters:

| eval item | training document | containment |
|---|---|---|
| `angrezi blog` | `az rashid Kamraan urdu blog angrezi blog az Shah` | 1.000 |
| `Pakistani bhai` | `woh bhi agar Pakistani bhai agar dawat den to` | 1.000 |
| `chahiye chahiye` | `chaar chahiye chaar !` | 1.000 |

Every one is *genuinely contained*. None is contamination. **The cause is that `min_shingles = 8`
means two different things in the two units** — ~12 words in the word unit, ~12 *characters* in the
character unit — and nothing in the config said so. One number, two meanings, and the character
unit exists precisely because Roman-Urdu-Parl needed it.

**Family 2 — templates, fixed by the threshold.** These are *long* and score just over 0.80, so
`min_shingles` never touches them:

| eval item | training document | containment | Jaccard |
|---|---|---|---|
| `qaisrani , September 4 , 2006` | `qaisrani , September 25 , 2006` | 0.800 | 0.645 |
| `tehreek azaadi jammu Kashmir - 5,329 baar` | `... - 5,261 baar` | 0.811 | 0.682 |
| `scan safha number 36 : ( kitaab safha 29 ) : typing mukammal az nayaab` | `... 21 : ( ... 14 ) ...` | 0.809 | 0.680 |

A byline with a different year is not contamination. The 0.90+ band, by contrast, is the mechanism
§6.2 names — the same sentence re-transliterated by a second crowdworker.

**Both fixes are per test set, not per stage**, which is the shape stage 5 already established when
its Urdu-script floor turned out to delete the whole Roman Urdu population. `EvalSetSpec.for_sentences()`
moves all three settings together because they were measured together: character 5-grams,
`min_shingles = 25`, `containment_threshold = 0.90`.

`min_shingles = 25` (~29 characters) excludes **24.8%** of the test rows from containment scoring.
That is deliberate and it is not a hole: those rows stay in the run and stay covered by the exact
half, which is the right instrument for a string that short.

---

## 6. What survives, adjudicated one by one

All 11 documents removed from the 20,000-row slice, read individually:

| # | eval item | training document | containment | Jaccard | verdict |
|---|---|---|---|---|---|
| 1 | `parcham sitara o Halal` | `parcham sitara o halal` | 1.000 (exact) | 1.000 | **genuine** |
| 2 | `layibriri ka naya project hona chahiye jis se aap...` | `... jis hum aap ...` | 0.935 | 0.870 | **genuine** |
| 3 | `bohat si daad qubool kijiyej !` | `is achay intikhab par bohat si daad qubool kijiyej` | 0.923 | **0.500** | **genuine** |
| 4 | `Sayeda shagufata , May 17 , 2007` | `... May 17 , 2009` | 0.964 | 0.931 | false positive |
| 5 | `zeeshan Haider , feb 22 , 2009` | `... feb 22 , 2010` | 0.923 | 0.857 | false positive |
| 6 | `qaisrani , decemeber 8 , 2006` | `... decemeber 8 , 2013` | 0.920 | 0.852 | false positive |

Rows 2 and 3 each cover several documents. **8 of 11 documents are genuine contamination and 3 are
false positives — precision 0.73 — and all three errors are one named family**: a byline whose year
differs. They are left in rather than tuned away, because the asymmetry runs one way: a false
positive costs one training row out of millions, a false negative costs the validity of an
evaluation number.

**Row 3 is the argument for containment in the primary corpus, not just on the wiki path.** The test
row appears verbatim as a *suffix* of a longer training row: containment 0.923, **Jaccard 0.500**. A
fuzzy match thresholded on Jaccard at anything sane misses it entirely.

### 6.1 A defect in the reference test set, found on the way

Nine test rows — `test_set.csv:1:606` through `1:614` — are spelling variants of one sentence
(`jis se` / `jis say` / `jiss se`, `haasil` / `hasil`), and all nine match the same training row.
Their Urdu column is *identical* across all nine.

This is not a contamination finding, it is a finding about the instrument: **the reference
transliteration split contains internal near-duplicates**, so any metric computed on it weights that
one sentence nine times. It belongs in the report next to the chrF number, and it is an independent
reason §8.2's human-written transliteration set exists.

---

## 7. Cross-source: the test set is in the *native* corpus too

Roman-Urdu-Parl's Urdu side was crawled from the web, and Urdu Wikipedia is in that crawl — so the
transliteration test set can be contaminated by a source it shares no lineage with. Measured on the
**complete Urdu Wikipedia dump** and a **5% sample of FineWeb2 shard 001**, both at the shipped
per-set settings:

| | Urdu Wikipedia (complete) | FineWeb2 `urd_Arab` (5%) |
|---|---|---|
| documents checked | 93,606 | 74,489 |
| training documents removed | **674 (0.72%)** | **214 (0.29%)** |
| **Urdu-side test items compromised** | **2,729 of 16,241 = 16.8%** | **1,977 = 12.2%** |
| Roman-side test items compromised | 0 | 0 |
| caught by | 673 containment, 1 exact line | 214 containment, 0 exact |
| **max Jaccard over every hit** | **0.2616** | **0.0749** |

**This is the largest contamination result in the project, and it is invisible to every instrument
except the one this stage was built around.** One sixth of the Urdu side of §8.2's reference
transliteration split is sitting in Urdu Wikipedia, which is a *training* source — and the single
highest Jaccard among all 2,729 compromised items is **0.26**, against a stage-7 removal threshold
of 0.80. A Jaccard-thresholded decontamination finds **none of it**, at any threshold anyone would
choose, and reports a clean corpus.

The Roman side is 0 in both, which is the correct result and a useful control: Wikipedia and
FineWeb2 `urd_Arab` are Arabic-script Urdu, so only the Urdu column of a parallel test set can
appear in them. A stage 8 reporting Roman-side contamination here would be reporting a bug.

> **These supersede an earlier 2,000-document smoke test that read 1 removal in 839 documents
> (0.12%).** The full dump is 6× that rate. The smoke pass was a `--limit 2000` truncation of a
> shuffled stream rather than a spread sample, which is Finding E's lesson for the third time in
> this report. The direction was right and the magnitude was not, and no conclusion here rests on
> the smaller number.

**This path is the cleanest demonstration in the project of why §6.3.8's fuzzy half cannot be
Jaccard.** The representative hit is a 26-shingle test sentence inside a **15,994**-shingle
Wikipedia article:

| | containment | Jaccard |
|---|---|---|
| test sentence in the article | **0.923** | **0.0015** |

At J = 0.0015 the shipped stage-7 banding would propose that pair with probability **1.6 × 10⁻¹⁰**.
And it is not one unlucky pair — over the complete dump, **99.9% of the 11,508 hits above the
threshold carry a Jaccard below 0.20**, and the maximum across all of them is 0.2616. On this
population the two scores do not merely disagree; their ranges do not intersect.

A Jaccard-thresholded decontamination run on this corpus would remove nothing and report a clean
result, and every part of it — the hash half, the sketch, the banding, the threshold — would have
been individually defensible.

---

## 8. Which half of §6.3.8 fired

§6.3.8 asks for "hash + fuzzy match" as though the two were co-equal. Measured, they are not, and
the imbalance is now confirmed on a third population:

| population | documents checked | exact (document) | exact (line) | containment |
|---|---|---|---|---|
| Roman-Urdu-Parl train (20K-row slice, both columns) | 35,858 | **1** | 0 | 10 |
| Urdu Wikipedia (complete dump) | 93,606 | **0** | **1** | **673** |
| FineWeb2 `urd_Arab` (5% of shard 001) | 74,489 | **0** | **0** | **214** |

Finding L predicted the hash half returns a confident zero on the wiki path. **It does: 0 document
matches over 168,095 native-corpus documents, against 887 caught by containment.** It very nearly
returns zero on Roman-Urdu-Parl too — a corpus that is *machine-produced and known to be
duplicated* — because crowdsourced re-transliteration changes a word, and a hash cannot see through
one word. Across every population measured, the hash half accounts for **1 of 899 removals**.

**The exact half is still not optional**, for one reason that has nothing to do with its yield:
it is the only cover for the 30% of eval items too short to shingle. Line-level hashing is included
for a shape document-level hashing structurally cannot see — an eval sentence quoted inside a longer
training document — with a 40-character floor, because `اہم خبریں` is a true exact match against
thousands of documents and evidence of nothing.

---

## 8.5 What stage 8 costs, and the optimisation deliberately not taken

The exact index is cheap to build — 32,482 eval items produce **76,609 distinct shingles** and
5,914 indexed lines, a few seconds and a few tens of MB. The corpus side is where the time goes, and
it is **not symmetric in the shingle unit**:

| corpus | unit | throughput |
|---|---|---|
| Roman-Urdu-Parl (sentence rows, ~40 chars) | char | ~400 documents/s |
| Urdu Wikipedia (articles, ~3,500 chars) | char | ~50–70 documents/s |

A 3,500-character article yields ~3,500 character 5-grams, each a blake2b hash and a dict lookup,
and common Urdu character 5-grams hit many eval items at once — so the per-document tally is large
even when nothing crosses the threshold. **Character shingling is what makes short test sets
measurable and it is also what makes long-document passes slow**; the two are the same property.

The obvious fix is an IDF-style cutoff — skip shingles owned by more than *N* eval items, since they
carry almost no evidence and cost the most. **It is deliberately not built.** It would introduce a
recall hole that nothing in the pass could detect, in the one stage whose failure mode is already
silence, to save minutes on a pass that runs twice. If it is ever needed, the honest version caps by
*measured* eval-item ownership and reports the number of shingles it skipped.

### 8.6 A ceiling that would have fired at the worst possible moment

Memory, not time, was the real hazard, and it was found by watching a running pass grow from 320 MB
to 565 MB rather than by reasoning about it.

A 30-shingle test sentence shares **half** its character 5-grams with a long article constantly. At
the original global `retain_hits_above = 0.50`, Urdu Wikipedia retained **11.9 hits per document, of
which 0.05% were above threshold** — 99.95% pure noise, held in memory so `sweep()` could explore a
range no one would ever sweep. Projected over a full FineWeb2 shard:

| | retained per document | projected over 1.49M documents | against the 20M ceiling |
|---|---|---|---|
| floor 0.50 (global default) | 11.91 | 17.7M | 88% consumed |
| floor 0.50, **measured on the complete dump** | **38.96** | **58.0M** | **290% — hard failure** |
| floor 0.80 (`for_sentences`) | 0.08 | 0.12M | 0.6% |

**A `MemoryError` partway through the multi-hour pass that writes the frozen corpus** — the single
worst time for this stage to fail, and it would have looked like a bug in stage 8 rather than a
retention floor set for a different unit.

The projection above was made from the 839-document smoke pass and **understated the problem by
3.3×**. The completed full-dump run settles it: 93,606 documents retained **3,646,596** hits at the
0.50 floor — 39 per document, not 12, because full articles are longer than the smoke sample's.
Extrapolated honestly that is 58M against a 20M ceiling, so the pass would not have come close to
finishing. It also made the evidence file unshippable at **890 MB**; what is committed is the
11,508 hits at or above the threshold, which is the subset any reader needs.

The fix belongs with the sentence variant rather than in the global default, because word shingles
have no such problem: unrelated documents measure mean Jaccard 0.00034, so containment ≥ 0.50
between two unrelated *documents* is genuinely rare. It is the same lesson as `min_shingles` in §5,
found a second time: **a number carried across a change of unit is not the same number.** Verified
on real text — the floor change cuts retention 151× and **leaves every verdict identical**.

---

## 9. What is decided

- **Containment, measured exactly, is the primary score.** Jaccard is carried beside it on every
  hit because the two disagree and the disagreement is the finding.
- **Thresholds are per test set.** Documents 0.80; sentence-unit sets `for_sentences()` — character
  5-grams, floor 25, threshold 0.90.
- **Removal is always of the training document.**
- **Sampling is honest at stage 8, uniquely among the cross-document stages.** Finding G forbids
  sampling stages 6 and 7 because a pair statistic sampled at rate *r* is measured at *r*². Stage 8
  indexes the eval side **whole** and samples only the corpus, so a contaminated document is found
  with probability *r*. The absolute count scales by 1/*r*; the rate does not need to.

## 10. Carried forward

- **The three surviving false positives are a named family**, not a threshold to tune. If a native
  speaker ever reads this sheet, the question worth asking is whether a byline-with-date rule
  belongs in stage 5 instead.
- **Two of §8.2's five test sets do not exist yet** — the human-written transliteration pairs and
  the real-OCR lines. Both are sentence/line unit, so `for_sentences()` is the variant they inherit,
  and neither has been measured. The held-out native split does not exist either: it is created at
  **stage 9**, so the most important decontamination run in the project has not happened yet and
  cannot until splits exist. Stage 8 must run **twice** — once now against the external sets, and
  once after stage 9 against the held-out split.
- **The stage-9 run is the one Finding L was really about.** §8.2 draws held-out evaluation text
  from Urdu Wikipedia while the same articles sit in the training data as crawled FineWeb2 HTML.
  Session 9 measured that population directly: 633 cross-source clusters where exact dedup found 1,
  and 11 of 49 sampled pairs below a 0.80 Jaccard cut. Stage 8 at containment ≥ 0.80 is built for
  exactly that, and the number is not yet on the record.
