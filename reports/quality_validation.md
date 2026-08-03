# Stage 5 quality filter — the 200-sample manual validation

**Date:** 2026-08-04 · **Stage:** 5 (quality filtering), PRD §6.3.5 · **Filter:** `quality` v1.0.0
**Shipped config:** `configs/data/quality.json`, fingerprint `53d04d3fd079`
**Pre-validation config:** `reports/quality_config_before.json`, fingerprint `57790136526b`

PRD §6.3.5 requires the quality rules to be "validated against 200 manually inspected random
samples". This is the write-up of that validation: what was sampled, what a reader disagreed with,
which thresholds moved as a result, and — the part that matters most — which rule the exercise
failed to fix.

> ### ⚠️ The adjudication is machine-made, not native-speaker
>
> The 200 verdicts in `reports/quality_sample.md` were written by Claude, not by a fluent Urdu
> speaker. They are real judgements and they found four wrong thresholds, but "200 manually
> inspected samples" in a technical report should mean a person who speaks the language.
> **Until that pass happens, the technical report must describe this validation as
> machine-adjudicated, in those words.** §9 says what a native speaker should do with it and why it
> is about twenty minutes of work rather than a full re-read.

---

## 1. Why the sample is stratified

The obvious reading of §6.3.5 is 200 uniform random documents. That sample cannot answer the
question being asked.

Under the pre-validation config stage 5 rejected **51 of 19,997 FineWeb2 documents — 0.26%**
(re-measured for this report; the config is committed, so this reproduces). A uniform 200 would
therefore have contained zero or one rejected FineWeb2 document, and **no rule's rejections could
have been validated at all** — the sample would only have measured how good the corpus is, which is
not in doubt, rather than whether the rules are right, which is.

The reverse sample fails in the mirror image. Drawing 200 documents from the rejections measures
each rule's precision well and says nothing about what the filter *wrongly keeps* — and the largest
error in the pre-validation filter turned out to be exactly that (§4.1).

So there are two strata, they are scored separately, and **they are never pooled**:

| Stratum | n | Drawn how | Answers |
|---|---|---|---|
| **uniform** | 100 (50 per source) | An unbiased sample of each source | False accepts, and overall agreement. Corpus-level rates may be computed from this stratum. |
| **rejected** | 100 (46 FineWeb2, 54 Wikipedia) | Oversampled from rejections, spread across rule families **smallest family first** | Per-rule precision. Deliberately not representative — **no corpus rate may be computed from it.** |

Rule families were filled smallest-first rather than proportionally because rules that fire rarely
are exactly the ones whose thresholds rest on the least evidence. `html_residue` is the case in
point: it is a rare rule — 12 of 20,000 Wikipedia documents under the shipped config, none at all
on FineWeb2 — so a proportional draw would have left it uninspected, and its threshold turned out
to be wrong by a factor of five. Smallest-first gave it 13 documents. As drawn, the rejection
stratum covered `script_ratio` 58, `too_short` 24, `repetition` 15, `html_residue` 13 (overlapping
— a document can fire several rules).

Both strata are selected by `stable_unit(doc_id, salt)` — a blake2b hash of the document id — so
the same seed draws the same 200 documents on any machine, in any read order, and after any resume.
Selection does not depend on the shard reader's shuffle. The sheet is then ordered by a *different*
hash of the id, which interleaves kept and rejected documents so that a reader cannot infer the
filter's answer from position on the page.

---

## 2. Headline result

Adjudicating 200 documents moved four of the six rule families.

| | pre-validation `57790136526b` | shipped `53d04d3fd079` |
|---|---|---|
| Agreement, **uniform stratum** (the honest one) | 0.76 | **0.92** |
| Agreement, rejection stratum | 0.59 | **0.79** |
| Agreement, all 200 (reported for completeness only) | 0.675 | 0.855 |
| Documents accepted in the uniform stratum | 91 | 67 |
| **False accepts** (filter keeps, human drops) | **24** | **4** |
| False rejects (filter drops, human keeps) | 0 | 4 |
| `repetition` precision | 0.60 | **1.00** |
| `html_residue` precision | 0.38 | **1.00** |
| `too_short` precision | 1.00 (n=32) | 0.93 (n=75) |
| `script_ratio` precision | 0.55 (n=60) | **0.50 (n=14)** |

Read the last two rows together with the two above them. **Precision went down on the two rules
that matter most, and the filter got substantially better** — because the pre-validation filter was
not making errors of precision, it was making errors of coverage. It rejected too little, of the
wrong kind, very confidently.

Everything in the table is reproducible from the committed artefacts without re-reading the corpus:

```
python scripts/quality_sample.py score reports/quality_sample.md \
    --quality-config reports/quality_config_before.json      # → quality_validation_before.json
python scripts/quality_sample.py score reports/quality_sample.md \
    --quality-config configs/data/quality.json               # → quality_validation.json
```

Both commands were re-run while writing this report and reproduce the committed JSON byte for byte.
This works because `measure()` and `score()` are separate functions: the sample stores *metrics*,
not verdicts, so the expensive half (a human reading documents) survives every threshold change and
a five-point sweep costs a minute instead of five corpus passes.

---

## 3. What the validation is really a finding about

**Inherited English thresholds do not transfer to Urdu web text, and they fail in a specific,
diagnosable way rather than by being uniformly too tight.**

Rae et al.'s Gopher repetition values — the standard, and the ones §6.3.5 implies — reject
**13.77% of FineWeb2 `urd_Arab`** (2,753 of 19,997 documents; `reports/probe_fineweb2_gopher.json`).
Reading that 13.77% shows it is almost entirely clean Urdu news prose. Two mechanisms, both specific
to this material:

1. **Urdu news wire copy restates the headline verbatim in the lead paragraph.** It is the house
   style. A 500-character article carrying its own 60-character headline twice is over 20%
   duplicate 5-grams by arithmetic, with nothing whatever wrong with it.
2. **Function-word density.** Urdu's compound verbs and postpositional phrases (کے مطابق، کی جانب
   سے، ہو گیا ہے) make a repeated five-word run ordinary where the English equivalent would be a
   template.

The decomposition is what makes this actionable, and it is unambiguous:

| Gopher rule | documents it fires on, of 19,997 |
|---|---|
| `dup_5gram` ≥ 0.15 | 2,353 |
| `dup_6gram` ≥ 0.14 | 1,675 |
| `dup_7gram` … `dup_10gram` | 1,376 / 1,289 / 1,235 / 1,185 |
| `top_2gram` ≥ 0.20, `top_4gram` ≥ 0.16 | **0** |
| `top_3gram` ≥ 0.18 | **1** |

**The entire 13.77% is the duplicate-n-gram half of the family. The top-n-gram half fires on one
document in twenty thousand.** The human adjudication reached the same split independently — on the
200 documents, Gopher's duplicate rules score precision 0.39 and its top-n-gram rules score 0.93
(§4.2). Two different instruments, corpus distribution and human judgement, pointing the same way.

The other half of the argument is that the repetition which actually matters in this corpus is
**cross-document, not within-document**: Urdu Wikipedia's geographic stub farms and Finding F's
republished religious texts are near-duplicates *of each other*, which is stages 6 and 7's job. So
stage 5's repetition family is correctly scoped as a backstop against a single pathological
document, and it is not — and should not be described in the report as — the corpus's repetition
control.

---

## 4. The four threshold changes, and the documents that forced them

### 4.1 `min_chars` 200 → 400 — the largest single result

At 200 the length rule had **perfect precision**: 32 rejections, 32 agreed with. It was also the
filter's single biggest source of error, because it was letting through 24 of the 91 documents the
uniform stratum said should go. Those 24 are Urdu Wikipedia's template geo-stubs — one factual
sentence wrapped in a section header and a category footer, running 200–420 characters.

**A rule can be perfectly precise and still be set far too low, and only the accept side shows it.**
That is the entire justification for having an unbiased stratum.

Sweeping the length floor, holding every other threshold at its shipped value. `min_chars` and
`min_words` move together at 10:1, which is close to this corpus's measured 4.82 characters per
word — at the shipped settings `min_words` never rejects a document `min_chars` does not, so the
rule is effectively `min_chars` alone:

| length floor | uniform agreement | accepted | false accepts | false rejects | `too_short` precision |
|---|---|---|---|---|---|
| (200, 25) | 0.75 | 92 | 25 | 0 | 1.00 (n=32) |
| (300, 30) | 0.88 | 77 | 11 | 1 | 0.98 (n=51) |
| **(400, 40)** | **0.92** | **67** | **4** | **4** | **0.93 (n=75)** |
| (500, 50) | 0.93 | 62 | 1 | 6 | 0.91 (n=87) |
| (600, 60) | 0.90 | 59 | 1 | 9 | 0.88 (n=92) |

**400 rather than 500, and the choice is close enough to state honestly.** 500 scores one document
better on agreement — one document out of 67 decided, well inside noise at this n — and buys it by
trading three false accepts for three additional false rejects. The documents it starts rejecting
are real: a 388-character dengue-ward news report, a 382-character political story, a 321-character
Wikipedia article on Early Modern Japanese. 400 is the more conservative of two statistically
indistinguishable cuts.

**The length rule does not separate cleanly, and the report should say so.** Under the shipped
config all four remaining false accepts are Wikipedia template stubs at 411, 415, 418 and 602
characters, and all four false rejects are genuine articles at 276, 321, 382 and 388. Good short
news and bad short stubs occupy the same length band. Length is a proxy that works well in
aggregate and cannot be tuned to work at the boundary — the population it removes cleanly is the
one every other rule measures badly (a 200-character document has no meaningful repetition, no URL
density, and a script ratio computed over a dozen letters), and that is the justification for
keeping it, not an ability to make the last five percent of calls correctly.

### 4.2 The repetition family split: `max_dup_ngram_ratio` 0.40 → 0.60, and n=2 dropped

Sweeping the two halves of the family separately against the same adjudication:

| Configuration | repetition rejections | precision |
|---|---|---|
| Gopher throughout | 29 | 0.48 |
| Gopher **top**-n-gram, shipped dup | 14 | **0.93** |
| Gopher **dup**-n-gram, shipped top | 23 | **0.39** |
| Pre-validation (dup ladder 0.40…0.30) | 13 | 0.62 |
| **Shipped** | **8** | **1.00** |
| Shipped with the dup rules disabled entirely | 8 | 1.00 |

Every document the top-n-gram rules rejected was a Wikipedia disambiguation or list page —
`واشنگٹن کاؤنٹی` repeated with a different state each time, top-2gram 0.47 — and the reader agreed
with all of them. The duplicate-n-gram rules were rejecting **biographies**: document 1 of the sheet
is a Punjab MPA's article scoring dup-5gram 0.41, and it repeats his name and
`پنجاب کی صوبائی اسمبلی کے رکن` because that is what an article about one person says.

**n=2 was dropped from the top-n-gram rules** because it was the family's only false positive: a
4,704-character article on the UN Convention on the Rights of the Child (`urdu-wikipedia:780634`)
scores **0.377** on the bigram بچوں کے — "children's", which is the article's subject, not its
boilerplate. Urdu's postpositional phrases and compound verbs make any two-word span common enough
that a bigram rate measures topic. n=3 and n=4 do not have this problem and catch the list pages
on their own; dropping n=2 took the family from 0.90 to 1.00 while still rejecting every list page.

**The last row of the table is a finding and it is reported rather than buried.** At the shipped
thresholds the duplicate-n-gram rules reject nothing on the 200-sample that the top-n-gram rules do
not already reject. Corpus-wide they are nearly as inert: disabling them entirely changes Urdu
Wikipedia's kept count by **4 documents in 19,999** (9,343 → 9,347) and FineWeb2's by zero. They are
retained as a backstop against a genuinely degenerate document, and `sole_rejections` in the corpus
manifest will keep saying how little they do. If a native-speaker pass confirms the picture, the
defensible options are to keep them with that caveat stated or to drop them — not to describe them
as part of the corpus's repetition control.

### 4.3 `max_html_ratio` 0.02 → 0.10

The pattern is precise about what it *matches*. Of the 200 sampled documents, 13 contain at least
one match and **every match in all 13 is a genuine tag** — `<div>`, `<noinclude>`, `<span>`,
`<small>`, `<ref>`, `<a>`, `<onlyinclude>`, `<blockquote>`, `<p>` — with no false positives, and
wiki markup caught incidentally by the same pattern. The entity half of the rule never fired at
all; both sources decode entities upstream. At 0.02 the rule was nonetheless wrong, because it was
wrong about what a match *means*.

| `max_html_ratio` | rejections | precision |
|---|---|---|
| 0.02 | 13 | 0.38 |
| 0.05 | 7 | 0.43 |
| **0.10** | **3** | **1.00** |
| 0.20 | 0 | — (rule never fires) |

At 0.02 the rule was deleting clean Wikipedia biographies carrying a handful of stray tags: a poet's
biography at 0.057, a cricket article with an embedded Twitter card at 0.067, a river article at
0.070. At 0.10 what remains is `<noinclude>` year-stubs of ~96 characters that are more markup than
text. **The rule should fire when a document *is* markup, not when it *contains* some**, and 0.10 is
where those separate. 0.20 is where the rule stops existing.

**The cost is named, not hidden:** raising the threshold makes two `{{Infobox}}` template dumps
(`urdu-wikipedia:1085863` at html 0.038, `urdu-wikipedia:1090364` at 0.020) into false accepts. The
right fix is not a lower HTML threshold — it is that `{{Infobox}}` is *wiki* markup and this rule
counts HTML tags. A wiki-markup rule belongs in Wikipedia-specific preprocessing, and lowering an
HTML threshold to catch it costs eight good biographies per two stubs. Noted as an open item (§9).

### 4.4 `max_url_ratio` 0.10 → 0.30 — changed before the sample, by the distribution

Every document between 0.10 and 0.30 in the probe was a legitimate Wikipedia article whose
*references and external-links section* is made of URLs — structurally identical to a link farm by
this metric. This is the same artefact that made Wikipedia look 30% bilingual to stage 3 in session
5. Worse, citation-heavy articles are systematically the longer, better-sourced ones, so a threshold
that catches them changes corpus composition in the wrong direction. At 0.30 the rule keeps only
documents that are *majority* link. It fires on 7 of 20,000 Wikipedia documents and 0 of FineWeb2.

---

## 5. `min_urdu_script_ratio` — the rule the validation could not fix

This is the one the report must not round off. The threshold moved 0.70 → 0.60 and **the rule is
still wrong about half the documents it rejects.**

| `min_urdu_script_ratio` | rejections in sample | precision | uniform agreement |
|---|---|---|---|
| 0.50 | 4 | 0.25 | 0.92 |
| **0.60 (shipped)** | **14** | **0.50** | **0.92** |
| 0.70 | 60 | 0.55 | 0.92 |
| 0.80 | 66 | 0.56 | 0.90 |

**No threshold makes this rule better than a coin flip.** Precision creeps from 0.25 to 0.56 across
the whole usable range while the number of documents affected changes by a factor of sixteen. That
is the signature of a metric that is not measuring the thing it is being asked about.

The reason is visible in the documents. Sorted by Latin share, in the band where the threshold
must sit, the human verdicts simply interleave:

| script ratio | document | verdict |
|---|---|---|
| 0.479 | Wikipedia: Spanish church, name quoted in Spanish twice | **keep** |
| 0.481 | Wikipedia: Philippine anthem stub, headers and external links | drop |
| 0.517 | `rekhta.org` ghazal, printed beside its Roman transliteration | **keep** |
| 0.542 | Wikipedia: Polish village stub, `village of Poland` untranslated | drop |
| 0.543 | `digilog.pk` e-commerce product page, cart furniture | drop |
| 0.570 | `acenews.pk` news article quoting an English tweet | **keep** |
| 0.578 | `pk.xxxbestporn.net`, Urdu keyword salad around Latin spam | drop |
| 0.579 | Wikipedia: Kazan Arena stub, English external links | drop |
| 0.587 | `pk.pornx.red`, same shape | drop |
| 0.589 | `rekhta.org` ghazal | **keep** |
| 0.594 | `rekhta.org` ghazal | **keep** |

Keep and drop alternate all the way down. There is no cut anywhere in this range that separates
them, because **Latin share is not what distinguishes them.** What does distinguish them is whether
the Latin is quoted material inside Urdu content or the page's own substance — which is much closer
to stage 3's lowercase-running-text test than to any ratio.

0.60 is therefore chosen as a **backstop, not a language decision**: it is the point that still
removes the wholly-English pages stage 3 let through while leaving Urdu journalism and Rekhta's
poetry archive alone. The language decision belongs to stage 3, which made it on far better
evidence — 0% English→Roman-Urdu error, 0.2% the other way, and independent corroboration from
FineWeb2's own GlotLID labels.

> Session 6's log quoted this band from memory as "news 0.66, porn-spam 0.58, ghazal 0.52". The
> measured values are the table above (news 0.570, spam 0.578/0.587, ghazals 0.517/0.589/0.594).
> The conclusion is unchanged and slightly strengthened — the true values interleave more tightly
> than the remembered ones.

---

## 6. What the shipped filter still gets wrong

All eight disagreements in the uniform stratum, in full. This is the error budget the technical
report should quote.

**False accepts (4)** — all Urdu Wikipedia template stubs just over the length floor:

| Document | chars | Why it survives |
|---|---|---|
| `urdu-wikipedia:122264` | 602 | Fortune-1000 company stub; boilerplate sentence + infobox residue |
| `urdu-wikipedia:122214` | 418 | Same template, different company |
| `urdu-wikipedia:363641` | 415 | Kentucky city geo-stub |
| `urdu-wikipedia:122110` | 411 | Chinese prefecture geo-stub |

These are the stub farm, and **stage 7 (MinHash near-dedup) is the right stage to remove them** —
they are near-duplicates of each other by construction, which is precisely what a length rule cannot
see and a near-dedup pass cannot miss. Session 6's carried-forward prediction that Wikipedia's stub
farm dominates the near-duplicate clusters is now backed by named documents.

**False rejects (4)** — all `too_short`, all genuine text: a 388-character dengue-ward report
(`fineweb2`), a 382-character political story, a 276-character foreign-minister story, and
`urdu-wikipedia:919995`, a 321-character article on Early Modern Japanese.

At the corpus scale these trade against each other in the right direction. Urdu is not
data-constrained at 70M parameters (Finding B), so discarding a short good article costs nothing we
have a shortage of, while keeping a stub farm costs the tokenizer and the dedup stages real work.

---

## 7. Corpus-level effect of the shipped filter

20,000 documents per source, sampled across row groups (Finding E), stages 2→5 in sequence.
`reports/probe_fineweb2.json`, `reports/probe_wikipedia.json`.

| | FineWeb2 `urd_Arab` | Urdu Wikipedia |
|---|---|---|
| documents kept | **96.48%** | **46.72%** |
| **characters kept** | **99.48%** | **87.38%** |
| `too_short` fired / sole | 694 / 694 | 10,568 / 10,174 |
| `script_ratio` | 9 / 9 | 61 / 22 |
| `repetition` | 0 / 0 | 406 / 55 |
| `html_residue` | 0 / 0 | 12 / 4 |
| `url_density` | 0 / 0 | 7 / 4 |
| `replacement_chars` | 0 / 0 | 0 / 0 |

- **Stage 5 is very nearly an assertion on FineWeb2.** It removes 0.5% of the characters. FineWeb2
  already ran encoding, language and Gopher-style repetition filtering upstream. This is the third
  stage in a row where the honest description of this source is "already clean in this dimension"
  (stage 2 and stage 3 were the first two), and the three together are a real finding about what
  FineWeb2 is — not evidence that Ravaan's pipeline is doing work.
- **Wikipedia loses half its documents and an eighth of its characters**, which is the right shape:
  the rejected half is the template stub farm, and it is short by definition.
- **`replacement_chars` never fires on either source, by construction.** Stage 2 already enforces
  the same 0.001 rate, so in the assembled pipeline this rule *cannot* fire. It exists so stage 5 is
  sound when run standalone, and `sole_rejections` reporting zero is the honest way to say so.
- **G1 is not at risk.** FineWeb2 shard 001 is ~3.5G characters before filtering and keeps 99.48% —
  roughly an order of magnitude past the ~120M-token target.

---

## 8. Method notes worth carrying into the technical report

- **The distribution tells you where the documents are, not which of them are good.** Every
  threshold in the pre-validation config had already been set from measured percentiles rather than
  from a paper, and the sample still moved four of the six families: `min_chars` 200→400, the
  dup-n-gram ladder 0.40→0.60 with n=2 dropped from the top-n-gram rules, `max_html_ratio`
  0.02→0.10, and `min_urdu_script_ratio` 0.70→0.60. What survived the sample untouched was
  `max_url_ratio`, `max_dup_line_ratio`, `max_replacement_rate` and the top-3/4-gram values. Both
  passes were necessary and neither was sufficient.
- **Measure precision and coverage separately, or a rule will look good while being the main source
  of error.** `min_chars` at 200 scored 1.00 precision and was the worst rule in the filter.
- **A rule's rejections must be read, not counted.** `html_residue` fired 12 times in 20,000
  Wikipedia documents — 0.06% — and its threshold was wrong by 5×. Sampling rare families
  smallest-first is what surfaced it.
- **Store metrics, not verdicts.** Every sweep table in this document was computed from one
  adjudication replayed against candidate configs. Storing verdicts would have made each row a fresh
  corpus pass and a fresh human read, and the sweeps would not have been done.

---

## 9. Open items

1. **Native-speaker adjudication.** The highest-value pass is *not* a re-read of all 200. It is
   re-marking the **29 disagreements** listed in `reports/quality_validation.json` — roughly twenty
   minutes. `reports/quality_sample.md` has a `**verdict:**` line per document and
   `scripts/quality_sample.py score --quality-config …` replays any marking against any config
   without touching the corpus.
2. **`script_ratio` — decide before the freeze.** If a native-speaker pass confirms precision ≈0.50,
   the honest options are (a) drop the rule, since stage 3 already made the language decision on
   better evidence, or (b) replace Latin *share* with a quoted-vs-own-content test, which is stage
   3's lowercase-running-text discriminator applied one stage later. Tuning the number is not an
   option — §5's table shows there is no number.
3. **Wiki markup is not HTML.** `{{Infobox}}` dumps escape the HTML rule at any usable threshold.
   The fix belongs in Wikipedia preprocessing before stage 5, not in `max_html_ratio`.
4. **The duplicate-n-gram rules are near-inert** (4 documents in 19,999). Keep with the caveat
   stated, or drop. Do not describe them as the corpus's repetition control.

---

## 10. Artefacts

| File | What it is |
|---|---|
| `reports/quality_sample.md` | The 200 documents with the reader's `verdict` and `note` per document |
| `reports/quality_sample.jsonl` | The same 200 with stored metrics — what makes re-scoring possible |
| `reports/quality_validation.json` | Scored under the shipped config `53d04d3fd079` |
| `reports/quality_validation_before.json` | The same adjudication under `57790136526b` |
| `reports/quality_config_before.json` | The pre-validation config, so the before/after reproduces |
| `reports/probe_fineweb2.json`, `reports/probe_wikipedia.json` | Stages 2→5 over 20,000 documents per source, with per-metric percentiles |
| `reports/probe_fineweb2_gopher.json` | The same probe under Gopher repetition values — the 13.77% in §3 |
| `configs/data/quality.json` | The shipped thresholds |

Redraw the sample (does not preserve the adjudication):

```
python scripts/quality_sample.py draw --out reports/quality_sample --seed 20260804
```

Reproduce the Gopher comparison in §3 — write the Gopher values into a config and probe with it:

```json
{ "max_dup_line_ratio": 0.30,
  "max_top_ngram_ratio": {"2": 0.20, "3": 0.18, "4": 0.16},
  "max_dup_ngram_ratio": {"5": 0.15, "6": 0.14, "7": 0.13,
                          "8": 0.12, "9": 0.11, "10": 0.10} }
```

```
python scripts/probe.py --source fineweb2-urd_Arab --split train --limit 20000 \
    --sample-rate 0.02 --seed 0 --quality-config <that file> --json out.json
```
