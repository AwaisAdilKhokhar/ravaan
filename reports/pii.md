# PII redaction — the two patterns, and what reading their matches changed

**Stage:** Minimal PII handling (PRD §6.3), between stage 5 and stage 6
**Written:** 2026-08-05, session 13, before the corpus freeze
**Decision:** two regexes, both **anchored on structure rather than on runs of digits**; matches
replaced by `[@]` and `[#]`, placeholders chosen so that every earlier stage returns the same
verdict when re-run over the frozen corpus.
**Evidence:** `reports/probe_pii_wikipedia.json`, `probe_pii_fineweb.json`, `probe_pii_roman.json`
— 56,214 documents across all three sources, with the context of every match kept in a form that
can be adjudicated without being a contact list (§5).

PRD §6.3 gives this stage its scope and its ceiling in one sentence: *"Minimal PII handling: one
regex pass for phone numbers and emails. Do not build a PII system."* So there is no model, no
gazetteer and no name detection here. What there is instead is two design decisions that a
one-line regex would have got wrong, and one measured correction that a one-line regex would have
shipped.

---

## 1. The correction, first, because it is the point

The first version of the phone pattern required a national trunk zero, ten to twelve digits, and
a separator set that excluded `:` and `.`. That is already far more careful than "seven or more
digits", and every one of its 61 unit tests passed, including the ones asserting that dates, year
ranges, prices, Quranic citations (`2:255`) and hyphenated ISBNs survive untouched.

Pointed at Urdu Wikipedia it matched 13 phone numbers in 19,999 documents. **Eleven of them were
ISBNs.**

```
آئی ایس بی این [#] ایورز، ڈیفو سے آسٹن تک انگریزی ناول میں …
بین الاقوامی معیاری کتابی عدد-13: 978-[#]. مزید دیکھیے …
```

An unhyphenated ISBN-10 in the English registration group is ten digits beginning with a zero,
which is character-for-character a ten-digit landline written without separators. The unit test
that was supposed to cover this used the *hyphenated* form `0-306-40615-2`, which the pattern
rejects for an unrelated reason — the first group has to be a contiguous trunk-zero-plus-prefix,
and `0-` is not. The test passed and proved nothing.

This is Finding D's lesson for the seventh time in this repo, and it arrived in Finding D's exact
shape: a rule that is right about what it matches and wrong about what that means, invisible to
fixtures and obvious within one run against real text. It is also the first time the lesson has
landed on a stage whose *failure mode is silent by construction* — a redaction leaves a
placeholder, so an over-eager pattern quietly deletes bibliography entries and there is nothing
left in the corpus to notice it by.

**Two changes, both from reading the matches rather than from adjusting a number.**

| | Before | After | What it removes |
|---|---|---|---|
| `min_national_digits_unseparated` | — (no such rule) | **11** | Unhyphenated ISBN-10, ten digits, leading zero |
| `min_international_digits` | 8 | **10** | ISBN-10 beginning `00`, read as `+0X` with 8 subscriber digits |

The second only became visible after the first: with the ISBN-10s gone, two matches remained and
both were ISBNs that had entered through the *international* branch, because `00` plus eight
digits cleared an E.164-theoretical floor that no country actually uses.

**The separator rule is the one worth defending, because the obvious fix was worse.** A flat floor
of eleven national digits also removes every ISBN — and it removes one of the two genuine numbers
Wikipedia contains, a ten-digit Multan landline. The discriminator in the data is not length:

> `ملتان … | 061- 4567890`  ·  `راولپنڈی | 051- 1234567-8`  ·  `آئی ایس بی این 0306406152`

**People separate phone numbers; databases do not.** Requiring a separator below eleven digits
removed all eleven false positives and kept both true positives. Eleven digits unseparated is
still accepted because that is the Pakistani mobile format (`03001234567`), which is 49 of
FineWeb2's 142 phone matches and cannot be given up.

**What the correction cost on the source that actually has phone numbers: three matches out of
286.** That asymmetry — 10 of 14 removed on Wikipedia, 3 of 286 on FineWeb2 — is the evidence
that the rule discriminates rather than just being stricter.

---

## 2. Where this runs, and why it is a position rather than a preference

After stage 5, before stage 6. Both edges are load-bearing.

* **Not before stage 5.** Stage 5's thresholds were moved by 200 manually adjudicated documents
  (`reports/quality_validation.md`), and those documents were unredacted. Redacting first would
  apply a validated filter to text the validation never saw.
* **Not after stage 6 or 7.** Those hash the text. Hashing first fingerprints a corpus that the
  release does not contain, and the manifest would describe documents by a digest of their
  pre-redaction form.

Between them, every hash, shingle, split assignment and packed token id is computed over the
redacted text and nothing is computed over anything else. All five drivers (`dedup.py`,
`neardedup.py`, `split.py`, `decontaminate.py`, `pack.py`) call it at that point; `probe.py`
measures it there without dropping documents, so a stage-5 reject still contributes to what the
patterns are known to fire on.

**One usage note for the freeze.** Stage 8 compares training text against the eval sets. Those
sets must go through the same redaction, or a training document whose only overlap with an eval
item is a phone number stops matching and is silently left in. It is the same function; it just
has to be called on both sides.

---

## 3. The placeholders are `[@]` and `[#]`, and that is a compatibility decision

The obvious choice is `<EMAIL>`. Stage 5 counts it as an HTML tag:

```python
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]{0,200})?/?>")
```

so anyone re-running the quality filter over the frozen corpus — an audit, a threshold revisit, a
reviewer — would score our own redactions as HTML residue and reject documents the run that
produced the corpus kept.

The obvious second choice is `[EMAIL]`. That puts five Latin letters into stage 3's letter count
and into the denominator of stage 5's `script_ratio`, which is the one rule whose measured
precision is already 0.50 and which the carried-forward notes have flagged for possible removal.

So the placeholders contain **no letters, no digits and no angle brackets**, and `PIIConfig`
raises on any placeholder that violates one of the three, naming the stage that would otherwise
disagree with itself. The no-digits rule is what makes redaction idempotent: the phone pattern
cannot match a placeholder, so a corpus can be re-read without redacting its own redactions.

Two tests assert the consequence directly rather than the property: `html_ratio` is 0.0 and
`script_ratio` is unchanged to 1e-9 after redacting a document containing both an email and a
phone number.

---

## 4. Measured — 56,214 documents, all three sources

Shipped configuration, fingerprint `ac44c4eb5021`.

| | Urdu Wikipedia | FineWeb2 `urd_Arab` | Roman-Urdu-Parl |
|---|---|---|---|
| documents | 19,999 | 19,997 | 16,218 |
| documents redacted | 3 (**0.02%**) | 201 (**1.01%**) | **0** |
| phone / email matches | 3 / 1 | 142 / 141 | 0 / 0 |
| characters removed | 52 | 4,267 | 0 |
| per million characters | **2.3** | **84.1** | **0.0** |
| distinct shapes | 4 | 36 | 0 |

**The three sources say three different things, and all three are the right answer.**

* **FineWeb2 is where the PII is**, at 40× Wikipedia's rate per character. It is a web crawl, and
  the contexts are exactly what that implies: `برائے رابطہ` (for contact), `موبائل:`,
  `ٹیلی فون:`, `واٹس ایپ:`, `ہمارے آفیشل ای میل`. Contact pages, news-desk submission notices,
  classified listings.
* **Urdu Wikipedia is nearly clean**, and after §1's correction its four remaining matches are one
  office listing carrying two numbers, one eleven-digit run next to an author's name, and one
  email. An encyclopedia is not where people publish their phone numbers.
* **Roman-Urdu-Parl matched nothing at all**, which is the fourth time a stage has turned out to
  be an *assertion* on a source rather than a filter (stage 2 and stage 3 on FineWeb2, stage 6 on
  both native sources). Its rows are single transliterated sentences from a curated parallel
  corpus. The report should say "this stage did not fire on this source", not "this source was
  cleaned".

---

## 5. The reports are adjudicable and are not a contact list

This stage's own output is the risk. A log that recorded what it matched would be a file of
harvested phone numbers and email addresses committed to the repository, which is the artifact the
stage exists to prevent — and §1 could not have been written without reading the matches.

Three things make both true at once:

1. **`PIIResult` has no `original` field.** `NormalizationResult` keeps one because PRD §6.3.4
   requires the transformation to be auditable. Here the original *is* the personal data, so it is
   never stored on the result and cannot leak into whatever serialises one.
2. **Matches carry a shape, not text.** `0300-1234567` → `dddd-ddddddd`; `ali.raza@example.com` →
   `xxx.xxxx@xxxxxxx.xxx`. This is sufficient to adjudicate precision, because a false positive is
   a date, a year range or an ISBN and those have different shapes — the entire §1 correction was
   diagnosed from the shape table alone. A test asserts that no serialised field of a result or a
   log contains the matched text.
3. **Context windows are cut from the *redacted* text.** Windowing the input would be one line
   shorter and would print the match itself.
4. **Residual digit runs in those windows are masked to their length** — `{10d}`. Point 3 is not
   sufficient on its own, and this is the second thing in this session that reasoning got wrong
   and grepping got right. A number the pass *missed* is still sitting in the redacted text, so
   the first committed version of these reports contained **29** of them: live Indian mobile
   numbers, a pair of Karachi landlines, the dot-separated number from §6. The window exists to
   show the *linguistic* context that decides whether a match is a phone number —
   `برائے رابطہ`, `موبائل:` — and a length is all a reader needs of the rest. Years, prices and
   page numbers stay legible because the floor is six digits.

The order those four were written in is worth recording: the first three came from thinking about
the failure mode, and the fourth came from running `re.findall` over the file that was about to be
committed. The stage that exists to remove phone numbers from a corpus had put twenty-nine of them
into its own report, and no amount of care about the *design* had caught it.

---

## 6. Known limitations, stated because they are recall and recall is the side that leaks

Every one of these is measured or reasoned, none is speculative, and none is fixed — PRD §6.3 caps
this stage's scope and these are what the cap costs.

* **Indian mobile numbers are missed.** They are ten digits beginning 6–9 with no trunk prefix,
  and several appear in the FineWeb2 sample next to Hyderabad and Patna datelines — they are the
  `{10d}` runs in `pii_examples`. Catching them means matching a bare ten-digit run, which is
  exactly the ISBN shape §1 removed. The `+91` form is caught. **Urdu is written in India, so this
  is a country-shaped hole rather than an edge case**, and it is the largest single item on this
  list.
* **Dot-separated numbers are missed.** One appears in the FineWeb2 sample in the same sentence as
  a number that *was* redacted, as an `{11d}` run. `.` is not in the separator set because it
  makes every version string, IP address and dotted date a candidate.
* **Nine-digit helplines are missed** — the `{9d}` run in the Wikipedia sample is below the
  national floor. These are published service numbers rather than personal ones.
* **`[at]`-style obfuscation is not decoded**, and neither is the `[email protected]` marker that
  some source pages already carry from Cloudflare — the address was removed upstream, so there is
  nothing left to redact.
* **CNIC numbers are not redacted.** Pakistani national ID numbers (`35202-1234567-1`) are PII and
  are out of §6.3's stated scope, which names phone numbers and emails. They are not caught by
  accident either: the first digit is a province code in 1–7, so no CNIC has a trunk zero.
* **Zero-padded structured identifiers of the `0001-0002-0003-0004` shape still match**, truncated
  to twelve digits. Zero instances in 56,214 documents, so this is a constructed worry rather than
  a measured one, and it is recorded rather than patched with an unswept rule.
* **Precision is not adjudicated by a native speaker.** The contexts are legible enough that the
  ISBN family was unmistakable, but the same sitting that owes stage 5 its 29 disagreements and
  stage 7 its sampled pairs could confirm the residual — particularly Wikipedia's one ambiguous
  eleven-digit run, which sits next to an author's name where an ISBN would also sit.

---

## 7. What the technical report should say

> Personal data was handled by a single regex pass over phone numbers and email addresses, applied
> after quality filtering and before deduplication so that every hash in the released manifest
> describes the redacted text. Matches were replaced by placeholders containing no letters and no
> digits, so that re-running the earlier filters over the released corpus reproduces their original
> verdicts. Measured over 56,214 documents, the pass redacted 1.01% of FineWeb2 documents, 0.02% of
> Urdu Wikipedia documents and none of Roman-Urdu-Parl's, removing 84.1 and 2.3 characters per
> million respectively. An initial version of the phone pattern matched unhyphenated ISBN-10s,
> which are ten digits beginning with a zero; eleven of its first thirteen Wikipedia matches were
> bibliographic identifiers rather than phone numbers. Requiring a separator below eleven digits
> removed all eleven while costing three of 286 matches on the crawl source. Known recall
> limitations — Indian mobile formats, dot-separated numbers, and `[at]`-style obfuscation — are
> listed in `reports/pii.md` §6. This is deliberately not a PII system.
