# Stage 10 — tokenization, packing, and the estimate this stage retires

**Stage:** Tokenization and sequence packing (PRD §6.3.10) — the last pipeline stage
**Written:** 2026-08-05, session 12, before the corpus freeze
**Decision:** sequences are **concatenate-and-chunk within a population, never across one**, joined
by EOS, with **no padding anywhere** — the residual tail of each stream is dropped and counted.
**Decision:** each arm packs its own sequences. Arm A ⊆ arm B in *documents*; its sequences are not
a prefix of arm B's, and must not be.
**Blocked on:** §7's tokenizer, which is Week 5. The stage is built and tested against a
placeholder that is refused by default, so the measurement it owes stage 9 is one command away
rather than a rewrite.
**Evidence:** 46 tests in `tests/test_packing.py`; a real pass over Urdu Wikipedia writing 7 shards
verified by digest, sequence count, byte sidecar and round-trip decode.

---

## 1. Four decisions, and what each one is protecting

| Decision | The alternative, and what it costs |
|---|---|
| **Sequences never cross a population boundary** | §8.3 reports validation BPB **by script**. A sequence built from Urdu Wikipedia and Roman-Urdu-Parl rows has no script to report it under, and the aggregate would move with the mixture rather than with the model — the same failure stage 9 avoids by carving held-out at the arm mixture. Costs one partial sequence per population instead of one per corpus |
| **Documents *are* concatenated within a population** | Roman-Urdu-Parl rows are single sentences averaging ~18 tokens. One document per sequence would be **97% padding** on the population §6.1 budgets 23.53M tokens for |
| **No pad token exists** | §4.3's arithmetic is 396 × 25M = 9.9B tokens processed and C = 6ND over exactly that D. A pad token costs compute and carries no data, so a padded corpus makes the epoch count and the unique-token budget mean two different things — Finding A's error in miniature. The tail is dropped instead: at most 511 tokens per stream against a 100M budget, and an *undershoot*, which is the direction stage 9's band solve already errs in for the same reason |
| **Each arm packs independently** | Taking arm A as a prefix of arm B's packed stream would make it a **contiguous block** of the corpus — Finding E's defect, arriving one stage after stage 9 spent its entire design avoiding it. §6.1 requires the arms to share *documents*; each arm is its own training set |

**A separator is a token and is counted as one.** Documents are joined with EOS, which is ~0.2% of
a native-Urdu stream and ~5% of Roman-Urdu-Parl's, where a document is one sentence. Large enough
that a fertility measured on content alone would put stage 9's Roman band 5% over budget, so the
ratio this stage hands back is **effective** — characters per token including separators.

---

## 2. The tokenizer does not exist yet, and the stage says so out loud

§7's tokenizer is Week 5; the freeze is Weeks 3–4. Stage 10 is therefore built against a
`Tokenizer` protocol with two implementations: `SentencePieceTokenizer`, which loads §7's model
when it exists, and `ByteTokenizer`, which encodes UTF-8 and exists only so the plumbing can be
tested and run.

**The placeholder is refused by default, and its id says what it is.** `PackedWriter` raises on any
tokenizer whose id starts with `placeholder:` unless `--allow-placeholder` is passed:

```
placeholder:utf8-bytes is a placeholder and cannot produce a freezable corpus — its
fertility is a property of the placeholder, not of Urdu.
```

This is stage 1's licence gate again, and for the same reason. A placeholder whose output is
indistinguishable from the real thing is worse than no placeholder: it is Finding D's shape, a
component that passes every test it has and is wrong about the corpus. Measured on real Wikipedia,
the placeholder reads **0.573 chars/token** against stage 9's 3.5 estimate — an 84% "error" that is
entirely a property of UTF-8 and says nothing whatever about Urdu. A run that reported that number
without the word *placeholder* attached to it would be actively misleading, so every shard manifest
carries the tokenizer's id, fingerprint, vocabulary size and a `placeholder: true` flag.

---

## 3. How much the unknown fertility actually costs — measured, not assumed

Stage 9's boundaries are solved from a declared `chars_per_token`, and the standing worry has been
that the arm cuts move when the real ratio arrives. Swept over the complete Urdu Wikipedia plan
(`plan_wikipedia.json`, 0.3 s per re-solve, no corpus pass):

| chars/token | arm A cut | arm B cut | validation from | arm A realized | A ⊆ B |
|---|---|---|---|---|---|
| 2.50 | 24,389 | 95,448 | 95,448 | **17.65M** | ✅ |
| 3.00 | 29,289 | 94,505 | 94,505 | **17.65M** | ✅ |
| **3.50** *(shipped)* | **34,161** | **93,470** | **93,470** | **17.65M** | ✅ |
| 3.87 | 37,709 | 92,722 | 92,722 | **17.65M** | ✅ |
| 4.20 | 40,830 | 91,954 | 91,954 | **17.65M** | ✅ |
| 4.50 | 43,648 | 91,252 | 91,252 | **17.65M** | ✅ |
| 5.00 | 48,631 | 90,302 | 90,302 | **17.65M** | ✅ |

**Two things follow, and they point in opposite directions.**

- **The budget is held exactly, at every ratio.** Arm A realizes 17.65M tokens whether the estimate
  is 2.5 or 5.0. That is by construction rather than by luck — the band solve converts the budget
  and then cuts the histogram to it — so it is a check that the construction works, not evidence
  about Urdu.
- **The *reach* moves by a factor of two.** Arm A's cut runs 24,389 → 48,631 buckets across the
  plausible range, so **which documents are in arm A roughly doubles.** This is exactly why the
  re-solve has to happen before the corpus is written rather than after: a corpus packed to the old
  cuts is a corpus of the wrong documents, even though its token count would be right.

Nothing breaks in either direction. Arm A stays nested inside arm B at every ratio, the band
ordering holds, and every assignment stays reproducible — which is what stage 9 promised when it
chose to carry the histogram rather than the answer.

*(Arm B reports `unmet` at every ratio here because this is Wikipedia alone: 47.98M native tokens
at 3.5 against arm B's 70.59M share. FineWeb2 is the bulk source, and this pass is a sensitivity
measurement, not a corpus.)*

---

## 4. What §8.3 needs that is easy to forget: bytes

**BPB is negative log-likelihood divided by bytes**, and §4.5's paired bootstrap resamples
*sequences* — so the byte count has to be recorded per sequence, at pack time, or it cannot be
reconstructed afterwards. Every shard therefore ships a `.bytes` sidecar: one `uint32` per
sequence, the UTF-8 byte length of the text that sequence's tokens stand for. Four bytes against a
1,024-byte sequence, so 0.4% overhead.

Separators stand for no text and contribute no bytes. A document straddling a sequence boundary has
its bytes attributed proportionally by token count, in integer arithmetic that sums to the
document's own byte count exactly — so **corpus totals are exact and only the split at a boundary
is an approximation.** §7 requires stable offset mappings; when they exist this becomes a lookup
and the per-sequence figures get exact too.

**Bytes per token is not derivable from characters per token.** Urdu is 2 UTF-8 bytes per character
and Roman Urdu is 1, so the two ratios differ by ~2× between populations sitting in the same
corpus. Both are measured and reported per population.

---

## 5. Two numbers that mean different things, kept apart

The recurring defect in this project has been one number standing for two quantities — Findings O,
P and S were each an instance, and Finding U (session 12) was the fourth. Stage 10 has the same
trap in two places and names both:

| | |
|---|---|
| `tokens_written` | what reached a shard — the corpus size |
| `tokens_encoded` | everything the tokenizer produced, dropped tail included — **the fertility denominator** |

They differ by at most 511 tokens per stream, which is negligible; the point is that `chars` is
counted over every document and `tokens_written` is not, so a ratio built from the pair would be
counted over two different sets of documents. Fertility uses `tokens_encoded`, which covers exactly
the documents `chars` does.

The same care applies to a document that tokenizes to **nothing** — whitespace a SentencePiece model
drops. Its characters against zero tokens would inflate chars/token, so bands would come out larger
and an arm would end up over budget. Such documents are counted as `empty_documents` and excluded
from both sides of the ratio. The bias would have been in the *safe-looking* direction, which is
the kind that survives review.

---

## 6. On disk

A stream is `{population}/{split}` for held-out and `{population}/train/{arm}` for training data —
held-out is not arm-scoped, because §4.3's endpoint compares the arm A and arm B curves and two
held-out sets would make that a comparison of numbers computed on different data.

| Property | Choice |
|---|---|
| Token array | flat `uint16`, **little-endian, pinned** |
| Byte sidecar | `.bytes`, one `uint32` per sequence |
| Shard size | 20,000 sequences ≈ 20 MB |
| Integrity | SHA-256 per shard in the manifest |
| Writes | via `.part` and rename, as stage 1 does for downloads |

**Byte order is pinned rather than inherited.** `array` is native-endian, so a corpus written on a
big-endian machine and read on a little-endian one decodes to entirely different, entirely *valid*
token ids — a silent corruption with no symptom until the loss curve. Every shard is byte-swapped
on write if it has to be, and the manifest states `"byte_order": "little"`.

**The width is checked against the vocabulary, not assumed.** A token id past `uint16` wraps to a
different, perfectly plausible token, and no later stage could tell. `PackingConfig` refuses a
vocabulary the dtype cannot hold, and the packer refuses an id outside the configured vocabulary
rather than writing it.

**A resumed pass produces the same corpus or it fails.** The packer's partial buffer is part of its
checkpoint; without it a resumed run restarts each buffer empty and every subsequent sequence
boundary shifts, producing a corpus that is valid and is not the one the checkpoint claims to
continue. A checkpoint from a different config or a different tokenizer is refused outright — stage
9's `resume()` and stage 1's digest check take the same position.

---

## 7. Verified against real text

Fixture tests prove a rule does what it says; only real text shows whether it fires on the right
things (Finding D, and the standing practice since). A pass over Urdu Wikipedia through stages
2→5→9→10 wrote 7 shards across 7 streams, and every one was checked back off disk:

- **7 of 7 digests match**, sequence counts match the manifest, and each `.bytes` sidecar has one
  entry per sequence summing exactly to the shard's recorded `text_bytes`.
- **The corpus decodes back to Urdu.** Read cold from `urdu/train/A`, sequence 3 is a Wikipedia
  geo-stub about a French commune — which is also, unprompted, session 9's Finding I looking back
  at us from inside the packed corpus.
- Mean bytes per sequence **511.7 against a 512-token cap**, the gap being the separators, which
  carry no bytes.
- Separator share **0.064%** on this pass. Lower than the ~0.2% expected of the real tokenizer, and
  for a legible reason: the placeholder makes documents ~3× longer in tokens, so it *understates*
  the separator share. Another number to re-measure in Week 5 rather than carry forward.

---

## 8. What this stage does not do

- **It has not measured Urdu's fertility.** That needs §7's tokenizer and it is Week 5's first
  deliverable. `--measure-only --resolve-plan` is the command, the stage is wired for it, and the
  re-solve costs 0.3 s.
- **It does not write the frozen corpus.** That needs the freeze order 6 → 7 → 9 → 8 ahead of it,
  the PII pass, and a real tokenizer.
- **It does not mask document boundaries in attention.** Sequences concatenate across documents, so
  a model attends across a boundary. EOS positions are recoverable from the token stream, so
  block-diagonal masking stays available as a *training-time* choice in Week 6 at no corpus cost —
  which is the reason to note it here rather than decide it here.
- **It does not shuffle.** Sequence order within a shard is the reader's order, which is already a
  seeded shuffle of row groups and of rows within them (stage 0's design, Finding E). Determinism
  is inherited from the reader rather than re-invented, and the manifest records the digests.
