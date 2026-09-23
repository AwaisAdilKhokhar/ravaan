#!/usr/bin/env python
"""Build the interactive decoder demo — the page that replays how each arm writes (PRD §4.1).

`release_assets/decoder_demo.template.html` has one `__DATA__` marker; this fills it from
`reports/demo_trace.json` and writes `reports/decoder_demo.html`. Built rather than hand-written
for `scripts/landing.py`'s reason, which has not stopped being true: **the Urdu must come out of
the sample file and never out of a transcription.** Copying Arabic-script text by hand between
documents is how a demo ends up showing something the model did not write, and nothing downstream
would catch it.

**Two views of the same trace, because one of them cannot be both correct and legible.**

* The **canvas** is per *token*. One cell per position, coloured by the step that committed it.
  This is the trace exactly as `demo_trace.py` recorded it, and it is what shows that diffusion
  commits position 19 before position 4.
* The **prose** is per *word*. A word is revealed on the step its **last** token commits.

That second grouping is not a simplification for its own sake — it is a typographic requirement.
Urdu is written in Nastaliq, where letters within a word join and the shape of a letter depends on
its neighbours. Splitting a word across several `<span>` elements so each token could be revealed
separately would break that joining and render text no Urdu reader would accept. So the canvas
carries the exact order and the prose carries the correct shaping, and the page says which is
which rather than letting a reader assume the prose is token-by-token.

    python scripts/decoder_demo.py            # -> reports/decoder_demo.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

#: Order the prompts appear in the picker. Not the order `demo_trace.py` generates them in: this
#: is a reading order, strongest register first, so the sample showing when the page loads is one
#: that rewards the ten seconds a visitor gives it. Every prompt that survives the filter is
#: listed — this reorders, it does not select. Selection is `demo_trace.py`'s, and it is stated.
ORDER = (
    "health",
    "technology",
    "book",
    "economy",
    "address",
    "city",
    "cricket",
    "weather",
    "school",
    "tea",
)

#: The arm-B curves both released checkpoints come from — the same corpus, the same 85,362,688
#: unique tokens, each arm's own budget. Read from `reports/eval/` rather than typed, because
#: these are the numbers the whole page is an argument about.
CURVES = {"ar": "curve_ar_b.json", "diff": "curve_diff_b64.json"}
UNIQUE_TOKENS = 85_362_688


def words(pieces: list[str | None], steps: list[int]) -> list[dict]:
    """Group token positions into whitespace words. See the module note on Nastaliq joining.

    A word's step is the **max** over its tokens: it is complete, and can be drawn, only once its
    last token has committed. `given` marks a word the decoder was handed rather than wrote, and
    is decided by the word's *first* token — a word whose opening token is part of the prompt is
    part of the prompt, even in the rare case where the model continues it.
    """
    out: list[dict] = []
    for piece, step in zip(pieces, steps):
        if piece is None:  # framing and control positions — never shown, see `_pieces`
            continue
        if piece.startswith(" ") or not out:
            out.append({"t": piece.strip(), "s": step, "g": step < 0, "n": 1})
            continue
        word = out[-1]
        word["t"] += piece
        word["n"] += 1
        # `given` is the first token's property; the step is the last token's.
        word["s"] = max(word["s"], step)
    return [w for w in out if w["t"]]


def arm_payload(rec: dict) -> dict:
    cells = [s for piece, s in zip(rec["pieces"], rec["commit_step"]) if piece is not None]
    return {
        "words": words(rec["pieces"], rec["commit_step"]),
        "cells": cells,
        "forwards": rec["forwards"],
        "seconds": rec["seconds"],
        "seed": rec["seed"],
        "text": rec["text"],
        "d1": round(rec["stats"]["distinct"]["1"], 3),
        "run": rec["stats"]["longest_repeat"],
    }


def curve(path: Path, total_epochs: float) -> list[dict]:
    """Held-out Urdu bpb against epochs. `fraction` is of the run, so epochs is fraction × total."""
    data = json.loads(path.read_text(encoding="utf-8"))
    points = []
    for key, point in data["points"].items():
        points.append(
            {
                "epochs": round(point["tokens"] / UNIQUE_TOKENS, 2),
                "bpb": round(point["evaluation"]["urdu"]["bits_per_byte"], 4),
                "tokens": point["tokens"],
            }
        )
    return sorted(points, key=lambda p: p["epochs"])


def build(trace: Path, evaldir: Path) -> dict:
    payload = json.loads(trace.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in payload["samples"]}
    missing = [i for i in ORDER if i not in by_id]
    extra = [i for i in by_id if i not in ORDER]
    if missing or extra:
        # A prompt that stopped surviving the filter must change this list deliberately, not be
        # silently dropped from a page that still claims to show what the filter kept.
        raise SystemExit(
            f"ORDER disagrees with the trace — missing {missing}, unlisted {extra}. "
            "Re-read reports/demo_trace.json and update ORDER."
        )

    samples = []
    for name in ORDER:
        rec = by_id[name]
        samples.append(
            {
                "id": rec["id"],
                "gloss": rec["gloss"],
                "topic": rec["topic"],
                "prefix": rec["prefix"],
                "diff": arm_payload(rec["diff"]),
                "ar": arm_payload(rec["ar"]),
            }
        )

    diff_release = payload["meta"]["diff_release"]
    ar_release = payload["meta"]["ar_release"]
    return {
        "samples": samples,
        "steps": payload["meta"]["steps"],
        "draws": payload["meta"]["draws"],
        "decoder": {
            "schedule": payload["meta"]["schedule"],
            "gumbel": payload["meta"]["gumbel"],
            "temperature": payload["meta"]["temperature"],
            "top_p": payload["meta"]["top_p"],
        },
        "release": {
            "diff": {
                "name": diff_release["name"],
                "epochs": diff_release["epochs"],
                "bpb": diff_release["validation_urdu_bpb"],
            },
            "ar": {
                "name": ar_release["name"],
                "epochs": ar_release["epochs"],
                "bpb": ar_release["validation_urdu_bpb"],
            },
            "unique_tokens": UNIQUE_TOKENS,
        },
        "curves": {
            "diff": curve(evaldir / CURVES["diff"], 64),
            "ar": curve(evaldir / CURVES["ar"], 16),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--trace", type=Path, default=REPO / "reports" / "demo_trace.json")
    ap.add_argument("--eval", type=Path, default=REPO / "reports" / "eval")
    ap.add_argument(
        "--template", type=Path, default=REPO / "release_assets" / "decoder_demo.template.html"
    )
    ap.add_argument("--out", type=Path, default=REPO / "reports" / "decoder_demo.html")
    args = ap.parse_args()

    data = build(args.trace, args.eval)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    template = args.template.read_text(encoding="utf-8")
    if "__DATA__" not in template:
        raise SystemExit(f"{args.template} has no __DATA__ marker")
    args.out.write_text(template.replace("__DATA__", blob), encoding="utf-8")

    size = args.out.stat().st_size
    print(f"wrote {args.out} — {len(data['samples'])} samples, {size / 1024:.0f} KB",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
