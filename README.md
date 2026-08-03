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
and schedule, same tokens processed, same seeds, **same training tasks**. Both are trained to ~33
epochs over ~300M unique tokens and checkpointed at epochs 1, 2, 4, 8, 16, 33.

The motivating claim from the literature is that masked diffusion overtakes autoregression when
compute is abundant but unique data is scarce. That result was measured on *artificially subsampled*
English. Urdu is *naturally* data-constrained, and noisier. Whether the finding survives is open.

**This is not an Urdu chat model, and it will not become one.**

The full specification lives in [`Ravaan_PRD_v2.md`](Ravaan_PRD_v2.md). Session-by-session status
lives in [`progress.md`](progress.md).

---

## Status

Pre-alpha. Week 1 of 16. Nothing has been trained. See `progress.md`.

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

The core package has no runtime dependencies. Heavy dependencies are opt-in extras so that the
corpus-normalization stage stays auditable.

## Test

```bash
python -m pytest
```

## Data and release policy

No raw text is redistributed. This repository ships code, a corpus manifest, checksums, and
statistics only (PRD §6.3). One permissive checkpoint will be released.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
