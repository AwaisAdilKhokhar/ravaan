# Ravaan

**Does masked diffusion pay off for a genuinely low-resource language?**

Ravaan trains two ~70M-parameter Urdu language models that differ in exactly one thing — the
factorization — and measures where, if anywhere, their curves cross.

| | Ravaan-AR | Ravaan-DIFF |
|---|---|---|
| Attention | Causal | Bidirectional |
| Objective | Next-token prediction | Masked diffusion (MDLM-style, time-agnostic) |
| Infilling | FIM (prefix/suffix/middle) | Mask the middle span |

Same corpus, same tokenizer, same parameter count (within 2%), same context length, same optimizer
and schedule, same tokens processed, same seeds, **same training tasks**.

The motivating claim from the literature is that masked diffusion overtakes autoregression when
compute is abundant but unique data is scarce. Prabhudesai et al. ([arXiv:2507.15857]) measured
that on clean English C4 and fitted a critical-compute threshold. Urdu web text is noisier, more
duplicated and more domain-skewed, and the script, morphology and tokenizer fertility all differ.
**Does the law transfer?**

Two arms, both processing ~9.9B tokens, differing only in how much unique data those tokens are
drawn from — because compute is parameters × tokens *processed*, so unique data is free:

| Arm | Unique U | Epochs | Seeds | Predicted |
|---|---|---|---|---|
| **A** (primary) | 25M | ~396 | 3 | **1.79× past** the fitted crossover |
| **B** (bracket) | 100M | ~99 | 1 | **0.09× of** it |

Arm A is predicted to cross and arm B is not, so the paired outcome tests the crossover's
*location*, not merely its sign. Both arms sit **inside** the reference paper's fitted range of U,
so no claim here depends on extrapolating their law. The predictions are committed in
[`reports/preregistration.md`](reports/preregistration.md), written before any training.

**This is not an Urdu chat model, and it will not become one.**

[arXiv:2507.15857]: https://arxiv.org/abs/2507.15857

The full specification lives in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md). Session-by-session status
lives in [`progress.md`](progress.md).

---

## Status

Pre-alpha. Weeks 3–4 of 16. Nothing has been trained. Gate G0 (novelty) passed; the corpus
pipeline has stages 1–6 built and validated against real text, and the raw corpus is on disk.
See `progress.md`.

## Layout

```
configs/            data, tokenizer, model, training, sampling, eval configs
ravaan/
  data/             acquisition, normalization, langid, dedup, quality, corruption, packing
  tokenization/     SentencePiece Unigram 16k + fertility benchmark
  models/           shared backbone, ar/, diffusion/
  training/
  sampling/
  evaluation/
tests/              engineering invariants (PRD §8.1) — these are CI, never results
scripts/
demo/               HF Space
reports/            preregistration, literature review, technical report
```

## Install

```bash
python -m pip install -e ".[dev]"
# add extras as the pipeline needs them: .[data] .[tokenizer] .[train]
```

The core package has no runtime dependencies. Every stage that *decides* something — acquisition,
encoding validation, language ID, normalization, quality filtering, exact dedup — is
standard-library-only on purpose: they choose which bytes the project is built on and what every
later stage reads, so they stay auditable. Heavy dependencies are opt-in extras, and `[data]` is
needed only to *read* the corpus, where parquet must be parsed.

## Test

```bash
python -m pytest
```

## Corpus pipeline

```bash
python scripts/acquire.py plan                        # sources, licences, sizes, fingerprint
python scripts/acquire.py fetch --max-bytes 3e9       # download, verify, record the manifest
python scripts/acquire.py verify                      # re-check what is on disk
python scripts/validate_encoding.py shard.jsonl --jsonl -o clean.jsonl
python scripts/normalize.py raw.txt -o clean.txt --log stats.json

# what the stages actually do on real text — every threshold gets one of these before the freeze
python scripts/probe.py --source fineweb2-urd_Arab --limit 20000 --sample-rate 0.02   # stages 2-5
python scripts/dedup.py --source urdu-wikipedia --limit 250000                        # stage 6

# the 200-sample manual validation PRD §6.3.5 requires
python scripts/quality_sample.py draw --out reports/quality_sample.md
```

Fixture tests prove a rule does what it says; only real text shows whether it fires on the right
things. Session 4 found a mojibake detector that passed 57 unit tests and would have deleted 3% of
a clean corpus, so every threshold in stages 2, 3, 5 and 6 is pointed at the actual sources before
the corpus is frozen, and the output is committed under `reports/probe_*.json`.

Sources are declared in [`configs/data/sources.json`](configs/data/sources.json): every source
pinned to a commit SHA, every file carrying its SHA-256 before download, and every licence checked
against what PRD §6.3 promises to ship. Sources that were considered and declined stay in the file
with their reasons — the corpus cap is a design decision, and that is only checkable if what was
declined sits next to what was taken.

## Data and release policy

No raw text is redistributed. This repository ships code, a corpus manifest, checksums, and
statistics only (PRD §6.3). One permissive checkpoint will be released.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
