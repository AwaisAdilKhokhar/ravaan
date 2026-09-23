"""Build the public landing page — the thing a link in a post actually opens.

The page is `release_assets/landing.template.html` with one `__SAMPLES__` marker, filled from
`reports/release_samples.jsonl`. It is built rather than hand-written for the same reason
`scripts/cards.py` is: **the Urdu must come out of the sample file, not out of a transcription.**
Copying Arabic-script text by hand between documents is how a demo ends up showing something the
model did not write, and nothing downstream would catch it.

The numbers in the template's prose are the ones `cards.py` prints and `elbo_diff_b64.json` holds.
If those move, the template moves with them — it is the one place on this page where a figure is
typed rather than read, and it is typed once.

    python scripts/landing.py                       # -> reports/landing.html

Publish the result as an artifact; the built file is committed so the page can be rebuilt or
re-hosted without this session.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

#: Three held-out prefixes that between them show the register the corpus actually contains:
#: encyclopaedic history, political commentary, and reported speech. Prompt 9 is deliberately
#: excluded — its prefix is Devanagari, a genuine corpus artifact, and it scores script 0.00 on
#: both arms. Showing it would be honest about the corpus and misleading about the models.
PROMPTS = (0, 3, 11)


def clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text[:limit].rstrip() + "…" if len(text) > limit else text


def pair_block(prefix: dict, ar: dict, diff: dict) -> str:
    def column(rec: dict, css: str, name: str) -> str:
        s = rec["stats"]
        return f"""        <div class="col {css}">
          <div class="col-head">
            <span class="col-name">{name}</span>
            <span class="col-meta">{rec['seconds']:.1f}s &middot; {rec['forwards']} passes &middot; rep {s['repetition']:.3f}</span>
          </div>
          <p class="ur">{html.escape(clip(rec['text'], 300))}</p>
        </div>"""

    return f"""    <div class="pair">
      <div class="pair-prefix">
        <span class="rubric">Prefix &middot; held-out text</span>
        <p class="ur">{html.escape(clip(prefix['prompt_text'], 120))}</p>
      </div>
      <div class="cols">
{column(ar, 'ar', 'Ravaan-AR')}
{column(diff, 'diff', 'Ravaan-DIFF')}
      </div>
    </div>"""


def main() -> int:
    pin_utf8_streams()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", default=str(REPO / "reports/release_samples.jsonl"))
    ap.add_argument("--template", default=str(REPO / "release_assets/landing.template.html"))
    ap.add_argument("--out", default=str(REPO / "reports/landing.html"))
    args = ap.parse_args()

    rows = [json.loads(line) for line in Path(args.samples).read_text(encoding="utf-8").splitlines()]
    by_prompt: dict[int, dict[str, dict]] = {}
    for record in rows:
        if record["task"] != "lm/continue":
            continue
        by_prompt.setdefault(record["prompt_index"], {})[record["arm"]] = record

    blocks = []
    for index in PROMPTS:
        pair = by_prompt.get(index)
        if not pair or "ar" not in pair or "diff" not in pair:
            raise SystemExit(f"prompt {index} has no matched ar/diff continuation")
        blocks.append(pair_block(pair["ar"], pair["ar"], pair["diff"]))

    template = Path(args.template).read_text(encoding="utf-8")
    if "__SAMPLES__" not in template:
        raise SystemExit(f"{args.template} has no __SAMPLES__ marker")
    page = template.replace("__SAMPLES__", "\n".join(blocks))

    Path(args.out).write_text(page, encoding="utf-8")
    print(f"wrote {args.out} — {len(page):,} chars, {len(blocks)} sample pairs")
    print("publish it as an artifact; the built file is committed so it can be rebuilt without a session")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
