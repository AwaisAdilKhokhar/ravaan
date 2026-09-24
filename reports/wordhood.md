# Is the word a word? — the instrument §8.3 never had, and what it says about the demo

2026-09-25, session 38. Context: a fluent reader has now said three times that the diffusion
arm's Urdu on the published demo is wrong, and three times the metrics in this project have
either missed it or ranked the decoders in the reader's opposite order (Findings BU, BV, BX, CA).
This session asked why, on the assumption that the reader is right and the instruments are wrong.

**The instruments were wrong in a specific, boring way: none of them asks whether a word is a
word.** Script consistency asks what alphabet the letters are in. Distinct-*n* and the repetition
rate ask how the words are distributed. `commit_order` asks what order they were written in. A
fabricated word — `بْباغ`, `ٹیُباغے`, `طبیعتکبھی`, `علاجٹیکل` — is script-consistent, unrepeated,
and can be written in perfect left-to-right order. **All four were on the hosted page.**

---

## 1. The instrument

`ravaan/evaluation/lexicon.py` holds every Arabic-script word skeleton occurring at least twice
in the project's own 712.6M-character native-Urdu sample, and reports the share of a generation's
words that are absent from it. Built by `scripts/lexicon.py`:

| | |
|---|---|
| source | `data/urdu-sample/sample_urdu.txt` — 712.6M characters, same sources as the freeze |
| word tokens | 146,425,722 |
| skeletons kept (count ≥ 2) | **464,762** of 778,301 seen |
| artifact | [`reports/eval/urdu_lexicon.tsv.gz`](eval/urdu_lexicon.tsv.gz), 2.0 MB |
| **control — real held-out Urdu** | **0.43%** (955 of 221,036 words, 400 documents) |

⚠️ **The control is the whole of what makes the number readable.** A real writer uses words a
712.6M-character corpus missed, so the floor is 0.43% and not zero. A decoder is fabricating when
it is above the floor, not when it is above nothing.

⚠️ **Two things about this metric bit during the session and are worth reading before trusting
any number below.**

1. **The first version's tokenizer split inside the defect it was built to find.** Python's `\w`
   excludes combining marks — they are category `Mn` and `str.isalnum()` is False for every one —
   so `[^\W\d_]+` cut `بْباغ` into `ب` and `باغ`, two real words, and scored it clean. Marks are
   part of a word now, and the lexicon is keyed on the mark-stripped skeleton so that a correct
   izafat (`دعوتِ`) is not called a fabrication merely because the corpus writes it bare.
2. **A lexicon cannot see a real word split into real words.** `خوب رو با ل یٰاب` survived the
   first regenerated page: `با`, `ل` and `یٰاب` are all in the corpus. `Fabrication.fragments`
   counts one-letter words Urdu does not write as words — one-letter words are 0.68% of real
   held-out Urdu and `و`, `ء`, `آ` are 73% of those — and the two counts are summed everywhere.

**It is still not a speaker.** A sentence of real words can be ungrammatical and this metric
calls it clean. It rules out one failure cheaply and leaves the rest to G5's annotators.

---

## 2. What it says about the page as it stood on 2026-09-24

The ten draws the hosted demo was serving, scored on the continuation only:

| panel | invented words | what it was |
|---|---|---|
| real held-out Urdu | **0.43%** | the floor |
| `ar` | 0.8% | the AR arm |
| `diff` — `gumbel 2` | 1.1% | the release default, and the page's default panel |
| `diff_random` — `random` | 2.3% | also the shipped decoder, one flag away |
| **`diff_block` — `block 8`** | **11.3%** | the amber "proposal", 24 hours old |

Replicated over 80 draws a cell, 1,120 draws, `reports/decode_variants_wordhood.jsonl` — `inv`
is invented words as a share of words written, **`bad` is the share of *draws* carrying at least
one word that is not a word** (invented or fragmented), and `chars` is the mean letters per word,
printed because a decoder that writes shorter commoner words scores better on `inv` without
having improved:

| decoder | passes | inv | **bad** | chars | ooo | **tied** | echo | distinct-1 |
|---|---|---|---|---|---|---|---|---|
| `ar` t = 0.8 | 29.7 | 0.1% | 10% | 3.35 | 0% | — | 24% | 0.868 |
| `ar` t = 1.0 | 29.4 | 0.6% | 15% | 3.50 | 0% | — | 14% | 0.907 |
| `parallel/gumbel 2` t = 0.8 | 8.0 | 0.2% | **6%** | 3.32 | 54% | 13% | 78% | 0.606 |
| **`parallel/gumbel 2` t = 1.0 ← ships, and is the demo** | 8.0 | 0.6% | **14%** | 3.33 | 47% | 14% | 60% | 0.694 |
| `parallel/random` t = 0.8 | 8.0 | 1.2% | 24% | 3.37 | 64% | 7% | 40% | 0.789 |
| `parallel/random` t = 1.0 | 8.0 | 2.5% | 46% | 3.50 | 65% | 7% | 28% | 0.877 |
| `block8/gumbel 2` t = 0.8 | 8.0 | 1.5% | 38% | 3.20 | 29% | **37%** | 46% | 0.639 |
| `block8/gumbel 2` t = 1.0 | 8.0 | 5.0% | **65%** | 3.42 | **30%** | **40%** | 25% | 0.789 |
| `block8/random` t = 0.8 | 8.0 | 4.1% | 64% | 3.35 | 34% | **36%** | 26% | 0.787 |
| **`block8/random` t = 1.0 ← was on the page** | 8.0 | 5.4% | **84%** | 3.55 | **36%** | **34%** | 14% | 0.887 |
| `wordwise/gumbel 2` t = 1.0 | 8.1 | 0.0% | 5% | 3.29 | **0%** | 0% | 74% | 0.663 |
| `wordwise/random` t = 1.0 | 8.1 | 0.2% | 15% | 3.41 | **0%** | 0% | 29% | 0.844 |

The gumbel-scale sweep of §2.2 is a separate 1,440-draw run at temperature 1.0 only:

| gumbel scale | 1 | 2 ← ships | 3 | 4 | 6 | 8 | `random` (∞) |
|---|---|---|---|---|---|---|---|
| invented-word draws | **8%** | **13%** | 16% | 15% | 24% | 28% | **39%** |
| prompt echo | 73% | 60% | 55% | 46% | 43% | 38% | 28% |
| distinct-1 | 0.618 | 0.694 | 0.737 | 0.766 | 0.791 | 0.819 | 0.877 |

*(that run scored `bad` on invented words alone, before `fragments` existed; the table above it
is the stricter number, which is why `parallel/gumbel 2` reads 13% there and 14% here.)*

### 2.1 `block 8` was a regression, and the metric that justified it was gamed

`commit_order` is the share of multi-piece words whose pieces were **not** written left to right,
and it counts a tie — two pieces of one word committed on the *same* pass — as in order. That is
defensible: same-pass pieces were still sampled independently, which is the schedule's property
rather than the ordering's. **It is also a door.** Cutting a 30-token canvas into left-to-right
windows of eight and spending two passes on each commits **four adjacent positions at once**, so
violations become ties: `tied` goes 14% → 34%, `ooo` halves, and the words break — `bad` goes
**14% → 84%** at the same eight forward passes.

This is Finding BZ arriving a second time through the other door. BZ caught `wordwise` scoring 0%
out-of-order by avoiding multi-piece words; nobody checked whether `block8` was scoring 30% by
converting them into ties. `same_pass` now prints beside `commit_order` wherever it is reported,
and `commit_order` itself carries `pairs`/`tied`/`tied_rate` so the two cannot be separated.

⚠️ **And the cost of the window is not what "semi-autoregressive" suggests.** A window of eight
at two passes has *denser* local independence than the un-windowed decoder, which ranks across the
whole canvas and commits wherever it is confident. `block4` at 15.2 passes and `block8` b4 at 16
passes are both worse than plain `gumbel 2` at 8. **Blocks are dominated at every width and every
budget measured.**

### 2.2 A4 is one dial, and §8.3 could only see one end of it

Finding BU concluded that §8.3 "can no longer choose" between `gumbel 2` and `random`. The
gumbel *scale* had only ever been swept at 1 and 2; swept at 1/2/3/4/6/8 it is monotone in both
directions at once, at **eight forward passes for every point**:

* **invented words rise** 0.3% → 2.5% as the scale goes 1 → ∞ (`random`)
* **prompt echo falls** 73% → 28% over the same range
* distinct-1 rises 0.618 → 0.877

So the family's parameter trades exactly the two failures a reader reports, and **the two
instruments each see one end of it**: distinct-1 prefers the high-scale end because scattering
commits raises variety, and the lexicon prefers the low-scale end because it keeps words intact.
Neither alone can choose. Together they bracket it, and the shipped `gumbel 2` sits where the
invented-word rate equals the AR arm's — **0.6% / 13% against 0.6% / 13%**.

✅ **Finding BU's open question is answered and it answers in favour of what ships.** `random`
fabricates at 4× the rate and on 3× the draws. `release_assets/generate.py` and both model cards
are unchanged, and now for a measured reason rather than for want of one.

### 2.3 Temperature is the stronger dial, and it confirms Finding CA from the other side

Session 37 swept temperature and found every §8.3 metric improving monotonically to 1.3 while the
share of draws leaking out of Arabic script went 0% → 26%; its conclusion was "do not raise the
temperature". Re-scoring those same draws (`reports/decode_variants.jsonl`, no new GPU time):

| decoder | 0.7 | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 | 1.3 |
|---|---|---|---|---|---|---|---|
| `ar` | 3% | 4% | 8% | 13% | 29% | 44% | 51% |
| `parallel/gumbel 2` | 3% | 5% | 13% | 14% | 23% | 18% | 34% |
| `parallel/random` | 16% | 20% | 36% | 39% | 51% | 66% | 71% |
| `block8/random` | 44% | 56% | 69% | 71% | 84% | 85% | 89% |

*(share of draws carrying a word that is not a word)*

✅ **A second, reader-aligned instrument reaches Finding CA's conclusion by an independent route.**
It also shows the demo's own temperature of 1.0 is not the clean end of the dial — 0.8 roughly
thirds the rate — but at 0.8 `gumbel 2` echoes its prompt in 78% of draws, which is the failure
the page's selection filter screens on. **There is no setting that is clean and varied at once;
this is a Pareto frontier, not an unfound optimum.**

### 2.4 One lead, filed as a lead

`wordwise` — commit a position only if the piece sampled there opens a word, or its left
neighbour is already written — was rejected in session 37 on Finding BZ's grounds. At temperatures
**above** 1.0, where session 37 did not look at it, `wordwise/random` reads well and scores
`bad` 13% / echo 15% / distinct-1 0.875 at **8.1 passes** — the same `bad` as the shipped decoder
with a quarter of its echo. Two reasons it is not being proposed:

* ⚠️ it leaks Roman Urdu at those temperatures (`theen` for `تھیں` appears in the draws), which is
  exactly Finding CA's failure and is not visible in `bad`;
* ⚠️ **it is not in `ravaan_infer`**, so no card could honestly name it, and Finding BU's standing
  rule is that a decode default moves on a reader's verdict. `block 8` is the record of what
  happens when a decoder goes on the page because a metric liked it.

---

## 3. The demo, and the rule that was choosing what it showed

⚠️ **The selection rule was selecting for the failure.** `_rank` in `scripts/demo_trace.py` led on
`longest_repeat` ascending and then distinct-1 descending — *fewest repeated words, then highest
type/token ratio* — and **a draw of fragmented non-words wins both by construction.** Of sixteen
seeds per prompt it was reliably promoting the one that had stopped writing words. `طبیعتکبھی`,
`علاجٹیکل` and `پابھیتا پرشیش` were each their prompt's top-ranked draw.

This is Finding BU's inversion operating one level down. BU found distinct-1 preferring `random`
*because* it scatters commits; the same preference, inside the choice of which draw to show, was
promoting the most shattered draw of every sixteen.

**What changed** — `_rank` now leads on `fabricated + fragments`, then prompt echo, then the three
old terms in their old order:

| | before | after |
|---|---|---|
| draws shown with a word that is not a word | 6 of 30 | **1 of 30** |
| `block 8` panel | on the page, amber, "proposal" | **withdrawn** |
| tracks | 3 | 2, both the shipped decoder |
| page readout | — | invented + fragmented count, over its denominator |

The one remaining is `address`/`gumbel 2`, where only 2 of 16 draws clear the existing filter and
neither is clean. **It shows a draw with one invented word and the readout says so**, which is the
point: ranking reports the rate, filtering would hide it.

⚠️ **This is a change to a selection rule, which is a change to what a demo cherry-picks.** Three
things keep it honest: the rule is quoted verbatim on the page, all 480 draws ship in
[`demo_trace_pool.json`](demo_trace_pool.json) with per-draw scores and rejection reasons, and it
is applied identically to the AR arm — which also improves under it, so it is not a rule built to
flatter one arm. Fabrication is **ranked on, never filtered on**, because a threshold set on the
day a metric is introduced is a threshold set to produce the answer that motivated it.

---

## 4. What is not fixed, and cannot be fixed here

⚠️ **Grammar and meaning are the 70M-parameter limit, not a decoder setting.** Every panel now
writes real Urdu words; several still write them in ungrammatical order. `چائے پینے کے بعد وہ
بازار میں چائے کا انتظار کرتا تھا، اور پھر۔۔ اور، کہ وہ کشمیر میں چائے پیتا ہے` is words a reader
knows in an order a reader would not choose, and no setting in §4.4's grid changes that. A 70M
model on 85M unique tokens is what it is; the page's `scale` caveat already says so and is the
honest place for it.

**What this session could fix, it fixed:** the words are words, the metric that hid it exists, the
metric that was gamed prints its own denominator, the panel that was worst is gone, and the rule
that was choosing the worst draw of sixteen now chooses against the failure instead of for it.

---

## Reproducing

```bash
python scripts/lexicon.py --control                      # -> reports/eval/urdu_lexicon.tsv.gz
python scripts/decode_variants.py --gumbel 1 --gumbel 2 --gumbel 4 --gumbel 8 \
       --variant parallel --variant block8 --variant wordwise --temperature 1.0
python scripts/decode_variants.py --summarize            # the table in §2
python scripts/demo_trace.py                             # both models, two commit orders
python scripts/decoder_demo.py --site                    # -> site/index.html
python scripts/decoder_gif.py --og                        # -> site/og.png
```
