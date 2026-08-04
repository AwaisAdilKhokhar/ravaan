# Stage 7 — choosing the near-duplicate threshold

**Stage:** MinHash near-deduplication (PRD §6.3.7)
**Written:** 2026-08-04, session 9, before the corpus freeze
**Decision:** ship **Jaccard ≥ 0.80** over word 5-grams, clustering by connected components.
**Evidence:** `reports/probe_minhash_wikipedia.json`, `probe_minhash_joint.json`,
`probe_minhash_findingI.json`, `probe_minhash_wikipedia_bands16x8.json`, and the measured pairs in
`minhash_pairs_*.jsonl`.

Session 8 recorded that a similarity threshold must be "made on measured pairs, not inherited",
because every stage-5 threshold that survived the metric distribution still had to be moved by
documents. This is that record for stage 7.

---

## 1. What the threshold was chosen from

One pass over a source retains every candidate pair at or above `retain_pairs_above` with its
measured similarity, so `MinHashDeduplicator.sweep()` re-clusters at any threshold **exactly**,
without re-reading the corpus. Every table below comes from two passes, not from twenty.

That is only honest if the banding generates candidates across the whole swept range — see §4.

---

## 2. Urdu Wikipedia, complete dump, after stages 2–6

93,606 documents reach stage 6; 93,597 survive it; all 93,597 are eligible for stage 7
(none below `min_shingles`), averaging 396 word-5-grams each.

| threshold | clusters | documents removed | largest cluster |
|---|---|---|---|
| 0.30 | 1,236 | 15,853 | **9,979** |
| 0.40 | 1,407 | 11,305 | 1,455 |
| 0.50 | 1,502 | 6,734 | 518 |
| 0.60 | 1,157 | 2,795 | 88 |
| 0.70 | 357 | 657 | 25 |
| 0.75 | 201 | 349 | 25 |
| **0.80** | **118** | **179** | **23** |
| 0.85 | 72 | 103 | 20 |
| 0.90 | 38 | 45 | 6 |
| 0.95 | 18 | 19 | 3 |

**The largest-cluster column is the argument, and it is not a gentle curve.** Clustering is
connected components over verified pairs, so transitivity is deliberate — if A ≈ B and B ≈ C they
are one document even when the A–C estimate lands under the cut. The cost of that choice is
chaining, and the table shows exactly where it becomes ruinous: at 0.60 the largest cluster is 88
documents, at 0.50 it is 518, and at 0.30 a single component swallows **9,979 documents — 10.7% of
the entire dump** — every one of which except the lowest-keyed survivor would be deleted. Nothing
in Urdu Wikipedia is 9,979 copies of one article. That is a chain of weakly-similar stubs closing
transitively, and it is a corpus-destroying outcome reached by moving one number.

Above 0.70 the largest cluster is stable at 23–25 and removals fall smoothly. **0.80 sits inside
that stable region with margin on both sides**, which is what a threshold should look like.

At 0.80 stage 7 removes **179 of 93,597 documents (0.19%)** and 0.20% of characters.

---

## 3. Finding L — the acceptance test, and it passes

Session 8 set this before the code existed: Urdu Wikipedia articles also sit inside FineWeb2 as
crawled HTML, 2,388 documents in shard 001 come from wiki hosts, and **not one is byte-identical**
to its counterpart in the `wikimedia` dump. "If stage 7 does not cluster those, it is not doing the
job stage 8 needs it to have done."

Measured by pulling that population out of the shard by URL (`--host-filter`) and running it
against the complete Wikipedia dump — 2,159 of the wiki-host documents survive stages 2–6 and join
93,597 Wikipedia documents:

| | stage 6 (exact) | stage 7 at 0.80 |
|---|---|---|
| cross-source groups / clusters | **1** | **633** |
| FineWeb2 wiki-host documents removed | — | 302 of 2,159 (14.0%) |
| Urdu Wikipedia documents removed as cross-source | — | 331 |

**Stage 7 finds 633 cross-source clusters where exact hashing finds one.** Every cross-source
cluster is size 2 — one Wikipedia article and one crawled copy of it — which is the right shape
and a good sign the clusters are not chaining.

The accounting balances against the standalone run exactly: 179 Wikipedia-internal removals here,
the same 179 the Wikipedia-only pass produced, plus 331 + 302 cross-source and 1 FineWeb2-internal
= 813.

**Why the shipped threshold suffices, contrary to the expectation this stage was designed around.**
The joint pairs are mostly *high* Jaccard with near-identical shingle counts — 0.992 at 884/882,
0.984 at 174/173, 0.977 at 330/331. FineWeb2's HTML-to-text extraction strips most navigation
chrome, so the crawled copy is close to the article rather than the article buried in furniture.
The module was built expecting the opposite and reports containment for that reason; the
expectation was wrong about the *majority* of the population.

**It was not wrong about all of it, and the residue is stage 8's problem.** Of 49 sampled
cross-source pairs, **11 fall below the 0.80 Jaccard cut**, and several of those are the asymmetric
case exactly as predicted:

| Jaccard | containment | shingles |
|---|---|---|
| 0.656 | **1.000** | 150 / 96 |
| 0.695 | 0.949 | 117 / 89 |
| 0.664 | 0.947 | 166 / 121 |
| 0.727 | 0.931 | 262 / 216 |
| 0.711 | 0.913 | 496 / 414 |

The first row is a Wikipedia article whose every shingle is present in the FineWeb2 copy, scoring
0.656 on Jaccard because the crawled page carries 54 shingles the article does not. **A
Jaccard-thresholded near-dedup cannot see that pair and a containment-thresholded one cannot miss
it.** This is the measured form of Finding L's requirement on §6.3.8: stage 8's fuzzy matching must
score containment against the eval sets, not Jaccard, or it will report a confident under-count on
the most likely contamination path in the project.

---

## 4. The banding, and a claim that did not survive its own control

Banding generates candidates; verification is exact against the full 128-value signature. The
shipped configuration is **32 bands × 4 rows**, S-curve inflection 0.420 — far wider than the
textbook (16, 8) at 0.707 for a 0.8 threshold.

**It was very nearly shipped for the wrong reason.** An early comparison showed (16, 8) removing
178 documents and (32, 4) removing 813 at the same threshold, which looks like a 4.6× recall gap
and was briefly written down as one. It is not: the 813 came from the *joint* run, whose population
includes the 2,159 FineWeb2 documents that duplicate Wikipedia. Run on the identical population:

| Urdu Wikipedia, threshold 0.80 | clusters | removed | largest |
|---|---|---|---|
| bands 16 × 8 | 118 | 178 | 23 |
| bands 32 × 4 | 118 | 179 | 23 |

**The same corpus to within one document.** The banding does not change what stage 7 removes.

What it changes is what the *sweep* can measure. (16, 8) has 6% recall at J = 0.5, so every row of
§2's table below ~0.70 would be reporting the banding rather than the corpus — and a threshold
chosen from that is a threshold chosen from an artefact. (32, 4) has 87% recall at J = 0.5, which
makes the swept range honest over the whole span a threshold could plausibly come from. The cost is
candidates: 60,355 proposed on Wikipedia against 240 that verify at 0.80, a banding precision of
**0.004**. Verification is 128 byte-slice comparisons, so 60,355 of them is about a second.

---

## 5. Finding I — the negative prediction, confirmed

Session 8 measured, before this code existed, that stage 5's four surviving false accepts
(`urdu-wikipedia:122264`, `:122214`, `:363641`, `:122110` — company and geography stubs at 411–602
characters) top out at word-shingle Jaccard 0.677 at n=2 and 0.423 at n=5, and predicted stage 7
would not touch them.

Measured with the shipped implementation, at threshold **0.50** with high-recall banding — a far
more aggressive setting than ships — all four come back `kept=True, cluster=-1, cluster_size=1`:

| pair | Jaccard | containment |
|---|---|---|
| `:122214` – `:122264` | 0.258 | 0.504 |
| `:122110` – `:363641` | 0.023 | 0.048 |
| all four other pairs | 0.000 | 0.000 |

The prediction holds and is sharper than it was: these four are not near the cut, they are nowhere
near it. **The four survive the whole pipeline**, so `quality_validation.md`'s error budget needs
its correction made permanent — stage 5's false-accept rate is stage 5's, not a debt owed to a
later stage. Session 8 booked this correction; stage 7 has now confirmed it against the real code.

---

## 6. What is not settled

- **FineWeb2 has no full-shard stage 7 pass yet.** Finding H predicts near-inertness: FineWeb2
  removed 31.02% of `urd_Arab` by its own MinHash before we saw it. That prediction is untested
  here. Measured cost of the pass: stages 2–5 run at ~380 documents/second, so 1,547,542 documents
  is ~68 minutes per pass and ~2.3 hours for the two-pass run. Finding G forbids sampling it — a
  pair statistic sampled at rate *r* is measured at *r²*. Take it at freeze time.
- **Roman-Urdu-Parl has none either**, and it needs `shingle_unit="char"`: its rows are ~10-word
  sentences with six word-5-grams, below anything the estimator can work with. Stage 6 already
  removed 84.8% of the Urdu column exactly, so the incremental near-dedup yield is the open number.
- **The threshold is validated against clusters and pairs, not against read documents.** §2 and §3
  rest on cluster structure and on 168 sampled pairs with their measured similarity, which is a
  stronger footing than stage 5 had before its 200-sample validation — but it is not a human
  reading Urdu and saying "yes, these two are the same document". The sampled pairs in
  `minhash_pairs_*.jsonl` are built to be read that way, and the same native-speaker pass that
  owes stage 5 its 29 disagreements could settle this in the same sitting.
- **Chaining is bounded by measurement, not by design.** Nothing in the module stops a component
  from growing; §2's table is the reason to believe it does not at 0.80. A source with heavier
  templating than Wikipedia could behave differently, and the largest-cluster figure is the number
  to watch when the remaining sources are run.
