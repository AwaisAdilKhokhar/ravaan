#!/usr/bin/env python
"""Pack the tokenizer sample into a pilot corpus — G3's input, and nothing more.

**This is not the frozen corpus and must never be reported as one.** It exists because §10's
schedule puts a pilot at Week 8 ("20M params, all 4 configs, 1 seed" → Gate G3) and G3 asks a
question that does not need the frozen corpus: *does the implementation work, and do both models
resume from checkpoint correctly?* Answering that with a corpus already on disk costs nothing and
unblocks the modelling work while stages 8, 9 and 10 are still owed their full passes.

What makes it legitimate input for that question: the text is **real pipeline output**. The
sampler that wrote `data/tokenizer/sample_*.txt` ran the same stages 2→5 `scripts/pack.py` runs,
applied the same stage 6+7 removal lists, and redacted PII at the same point in the order. It is
tokenized here with §7's frozen tokenizer, packed by stage 10's own `SequencePacker` and written
by stage 10's own `PackedWriter`, so the shards are the real format read by the real loader.

What makes it **not** the frozen corpus, stated here so the distinction survives this file:

* **Stage 8 has not run.** Decontamination against the held-out and evaluation sets is outstanding,
  so a pilot's held-out numbers are contaminated by an unmeasured amount — Finding T projects
  ~4.4%. No BPB from this corpus goes in a results table.
* **FineWeb2's stage 6+7 has not run.** The rented-box pass is still the one thing left in the
  freeze. Expected to remove almost nothing (9 clusters in 193,666 documents), but not measured.
* **The split is not stage 9's.** Stage 9 assigns split and arm by a keyed hash of the document id
  so arm A is structurally a prefix of the bucket range; this file holds out a fraction of packed
  *sequences* instead, which is the cheap approximation and not the guarantee.
* **`code_switched` is at 43% of its mixture share**, because the sampler's FineWeb2 cap bound
  before that population filled. §6.1's mixture is therefore approximated, not held.

    python scripts/pack_pilot.py --out data/packed-pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

from ravaan.data.packing import (  # noqa: E402
    PackedWriter,
    PackingConfig,
    SentencePieceTokenizer,
    SequencePacker,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--sample", default="data/tokenizer")
    parser.add_argument("--tokenizer", default="data/tokenizer/ravaan-16k.model")
    parser.add_argument("--out", default="data/packed-pilot")
    parser.add_argument(
        "--heldout-fraction",
        type=float,
        default=0.02,
        help="sequences per population held out. Stage 9's job, approximated (see the docstring)",
    )
    parser.add_argument("--arm", default="A")
    parser.add_argument(
        "--purpose",
        default="PRD §11 Gate G3 — implementation and resume check at 20M params",
        help="what this corpus is for; travels in the manifest beside is_frozen_corpus=false",
    )
    args = parser.parse_args(argv)

    tokenizer = SentencePieceTokenizer(args.tokenizer)
    config = PackingConfig()
    writer = PackedWriter(args.out, config, tokenizer)

    print(
        f"tokenizer {tokenizer.tokenizer_id} ({tokenizer.fingerprint()}), "
        f"vocab {tokenizer.vocab_size:,}, eos {tokenizer.eos_id}",
        file=sys.stderr,
    )

    totals: dict[str, dict[str, int]] = {}
    for path in sorted(Path(args.sample).glob("sample_*.txt")):
        population = path.stem.removeprefix("sample_")
        # One packer per stream, as stage 10 requires — sequences never span populations, because
        # §8.3 reports BPB by script and a mixed sequence has none.
        train = SequencePacker(config, tokenizer)
        heldout = SequencePacker(config, tokenizer)
        entry = totals.setdefault(
            population, {"train": 0, "validation": 0, "documents": 0, "chars": 0}
        )

        index = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry["documents"] += 1
                entry["chars"] += len(line)
                # Every 1/f-th document to held-out. Deterministic and contiguous-free; stage 9
                # does this properly by hashing the document id, which this pilot does not have.
                to_heldout = args.heldout_fraction > 0 and (
                    index % max(int(1 / args.heldout_fraction), 1) == 0
                )
                index += 1
                packer = heldout if to_heldout else train
                stream = (
                    f"{population}/validation"
                    if to_heldout
                    else f"{population}/train/{args.arm}"
                )
                for sequence in packer.add(line):
                    writer.add(stream, sequence)
                    entry["validation" if to_heldout else "train"] += 1

        for packer, stream, key in (
            (train, f"{population}/train/{args.arm}", "train"),
            (heldout, f"{population}/validation", "validation"),
        ):
            # The final partial sequence is dropped, never padded — §6.3.10's rule, and the
            # reason the arm budgets and the epoch count mean the same number of tokens.
            writer.flush(stream)
            entry[f"{key}_dropped_tokens"] = packer.dropped_tokens
            entry[f"{key}_chars_per_token"] = (
                round(entry["chars"] / packer.encoded_tokens, 4) if packer.encoded_tokens else None
            )

    shards = writer.close()
    manifest = writer.manifest()
    # The warning travels with the corpus. A manifest that looked like stage 10's and was not
    # would be exactly the confusion this whole file exists to prevent.
    # `source` and `purpose` are read off the invocation rather than written in, because this
    # driver has now packed two different corpora and a manifest that names the wrong one is the
    # exact confusion the rest of this file exists to prevent.
    manifest["pilot"] = {
        "is_frozen_corpus": False,
        "purpose": args.purpose,
        "not_run": ["stage 8 decontamination", "FineWeb2 stage 6+7", "stage 9 split assignment"],
        "source": f"{args.sample}/sample_*.txt, written by scripts/tokenizer.py sample",
        "populations": totals,
    }
    # Stage 10's own manifest names the tokenizer; this adds the piece ids the objectives and
    # §4.2's task generator need. **All twelve**, not the subset the diffusion arm alone uses:
    # `FramingTokens.from_manifest` refuses a partial set rather than inventing an id, because §7
    # put all twelve inside the 16,384 precisely so both arms would embed one vocabulary.
    import sentencepiece as spm  # noqa: PLC0415

    from scripts.tokenizer import SPECIAL_TOKENS  # noqa: PLC0415

    sp = spm.SentencePieceProcessor(model_file=args.tokenizer)
    manifest["tokenizer"]["special_tokens"] = {
        piece: sp.piece_to_id(piece) for piece in SPECIAL_TOKENS
    }
    manifest["tokenizer"]["control_ids"] = {
        "pad": sp.pad_id(),
        "unk": sp.unk_id(),
        "bos": sp.bos_id(),
        "eos": sp.eos_id(),
    }
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"\n{len(shards)} shards", file=sys.stderr)
    grand = 0
    for population, entry in sorted(totals.items()):
        tokens = (entry["train"] + entry["validation"]) * config.sequence_length
        grand += tokens
        print(
            f"  {population:<14} {entry['train']:>7,} train + {entry['validation']:>5,} val "
            f"sequences  {tokens:>11,} tokens  {entry['train_chars_per_token']} chars/token",
            file=sys.stderr,
        )
    print(f"  {'TOTAL':<14} {grand:>48,} tokens", file=sys.stderr)
    print(f"\nwrote {args.out}/manifest.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
