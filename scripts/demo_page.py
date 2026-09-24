#!/usr/bin/env python
"""The demo: each arm's best checkpoint on one corpus, and both ways of decoding the diffusion one.

`sample.py` writes every generation it makes; this writes the five that are worth showing
someone, and says out loud which five and why. Two artefacts, from one pass over
`reports/demo_b64.jsonl`:

* **`reports/demo.md`** — the reading view, Urdu first, with §8.3's metrics beside each sample.
* **`<out>.html`** — the same thing laid out in Nastaliq for a browser, which is the only way
  Urdu prose is actually legible to a reader who is being asked to judge it.

**The pairing is matched now, and that is what changed.** `ship-ar-b/ar-s0_fp25.pt` is arm B at
4 epochs and `ship-diff-b64/diff-s0_f1_weights.pt` is arm B at 64 — the same corpus and the same
mixture, where every earlier version of this page paired arm B against arm A and had to disclose
it. Each is still its own arm's best by held-out Urdu bpb among checkpoints that are not reciting
the corpus. What remains unmatched is *training length*, and that is the result rather than a
confound: AR turns at 4 epochs and is ruined by more, while the diffusion arm had not turned at
64. §4.5's crossover is the evidence and lives in `progress.md`.

**Three panels, two of them the same checkpoint.** The diffusion arm appears twice, differing
only in §4.4's A4 schedule, because on this checkpoint §8.3's metrics stopped separating them:
`random` leads distinct-1 0.68 to 0.41 on `lm/continue` and now ties `gumbel 2` on script
consistency, where on the 16-epoch checkpoint it lost that axis outright. The trade is
well-formed words that circle against varied content with malformed joins, no metric in this
repository ranks those, and a fluent reader settles it. Showing one and calling it the default
would be asserting an answer the project does not have.

**Five of twelve, and the rule is stated rather than implied.** The pool is twelve prompts drawn
evenly from the `urdu` validation split. ⚠️ **On this checkpoint eleven of the twelve qualify**,
where the previous version of this page could keep only five: prompt 9's prefix is not Arabic
script at all (every panel scores 0.00 script consistency on it) and it is the *only* exclusion,
against six dropped before for one arm or the other degenerating. The same five are kept so the
page stays comparable to the version it replaces, not because the rest failed — a selection that
narrow is now a choice about continuity rather than a filter, and saying so is the point.
Cherry-picking a demo is normal; doing it silently is not, so the pool ships beside the selection
and `--all` renders every prompt.

    python scripts/demo_page.py --samples reports/demo_b64.jsonl --out reports/demo
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

#: The five prompts every panel carried in the version this replaces, kept so the pages compare.
#: Read, not scored — §8.3's numbers rank a slot-looping sample above a wandering one, and the
#: whole point of a demo is that a person reads it. Eleven of the twelve now qualify; see above.
CHOSEN = (3, 4, 7, 10, 11)

#: What each prompt is about, for a reader who does not read Urdu. Descriptive, not a verdict.
TOPICS = {
    0: "the battle of Haldighati, 1576",
    1: "a naat — devotional verse",
    2: "a defence-analyst quote on an operation",
    3: "the economy, debt and the opposition",
    4: "the foreign-exchange market",
    5: "Karachi, and who owns it",
    6: "street robbery and mob beatings",
    7: "recognising the Taliban government",
    8: "political verse",
    9: "(not Arabic script — excluded)",
    10: "Pakistan–UK relations, a foreign-ministry readout",
    11: "a personal essay on moral values",
}

#: Which record in the samples file each panel is. A diffusion entry names its A4 schedule, so
#: two of them can sit beside one AR panel; `None` matches the AR arm, which has no schedule.
SELECTORS = {
    "ar": ("ar", None, None),
    "diff_random": ("diff", "random", None),
    "diff_gumbel": ("diff", "gumbel", 2.0),
}

ARMS = {
    "ar": {
        "name": "Ravaan-AR",
        "kind": "autoregressive",
        "checkpoint": "ship-ar-b/ar-s0_fp25.pt",
        "corpus": "arm B — 85,362,688 unique tokens",
        "epochs": "4 epochs (341M tokens seen)",
        "bpb": "0.7774",
        "bpb_note": "held-out Urdu bits-per-byte — an exact NLL",
        "decode": "temperature 0.9, top-p 0.95",
        "blurb": (
            "One token at a time, left to right; it chooses its own length and its likelihood "
            "is exact. 160 tokens cost it 160 sequential forward passes."
        ),
    },
    "diff_random": {
        "name": "Ravaan-DIFF · random",
        "kind": "masked diffusion",
        "checkpoint": "ship-diff-b64/diff-s0_f1_weights.pt",
        "corpus": "arm B — 85,362,688 unique tokens",
        "epochs": "64 epochs (5.46B tokens seen)",
        "bpb": "0.7646",
        "bpb_note": "held-out Urdu bits-per-byte — an ELBO, so read it as ≤",
        "decode": "8 denoising steps, random schedule, </s> forbidden",
        "blurb": (
            "The same checkpoint and the same eight steps as the panel beside it. It commits "
            "positions in a uniformly random order instead of by confidence — which is what "
            "changes, and the only thing that changes."
        ),
    },
    "diff_gumbel": {
        "name": "Ravaan-DIFF · gumbel 2",
        "kind": "masked diffusion",
        "checkpoint": "ship-diff-b64/diff-s0_f1_weights.pt",
        "corpus": "arm B — 85,362,688 unique tokens",
        "epochs": "64 epochs (5.46B tokens seen)",
        "bpb": "0.7646",
        "bpb_note": "held-out Urdu bits-per-byte — an ELBO, so read it as ≤",
        "decode": "8 denoising steps, gumbel schedule s=2, </s> forbidden",
        "blurb": (
            "Ranks positions by log p plus Gumbel noise annealed to zero — the one-parameter "
            "family whose endpoints are `confidence` and `random`. The project's shipped default."
        ),
    },
}


def load(path: Path, indices: tuple[int, ...]) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    rows = [r for r in rows if r["task"] == "lm/continue"]
    by_prompt: dict[int, dict] = {}
    for r in rows:
        selector = (r["arm"], r.get("schedule"), r.get("gumbel"))
        for key, want in SELECTORS.items():
            if selector == want:
                by_prompt.setdefault(r["prompt_index"], {})[key] = r
    out = []
    for i in indices:
        panels = by_prompt.get(i)
        missing = [k for k in SELECTORS if not panels or k not in panels]
        if missing:
            raise SystemExit(f"prompt {i} is missing {', '.join(missing)} in {path}")
        # Finding BT: a byte-fallback draw renders U+FFFD, because the decoder can commit the
        # middle byte of a character before its first. Those are rejected outright rather than
        # special-cased — on this checkpoint they are also the draws that stopped writing Urdu.
        broken = [k for k in SELECTORS if "�" in panels[k]["text"]]
        if broken:
            raise SystemExit(
                f"prompt {i}: {', '.join(broken)} decoded a byte-fallback draw (U+FFFD). "
                "Pick another prompt rather than shipping it"
            )
        out.append({"index": i, "prefix": panels["ar"]["prompt_text"], **panels})
    return out


def metrics(record: dict) -> str:
    s = record["stats"]
    return (
        f"script {s['script_consistency']:.2f} · distinct-1 {s['distinct']['1']:.2f} · "
        f"rep {s['repetition']:.3f} · longest repeat {s['longest_repeat']}"
    )


def markdown(pairs: list[dict], source: Path) -> str:
    lines = [
        "# The demo — each arm's best checkpoint, and both ways of decoding the diffusion one",
        "",
        "Generated by `scripts/sample.py`, selected and laid out by `scripts/demo_page.py`.",
        f"Every generation made is in [`{source.name}`]({source.name}); this is the five that",
        "were chosen, and the selection rule is in that driver's docstring.",
        "",
        "**Both checkpoints are arm B**, so unlike every earlier version of this page the "
        "pairing",
        "is matched on corpus and mixture. What is *not* matched is training length — AR's best "
        "rung",
        "is 4 epochs because it turns there and is ruined by more, while the diffusion arm had "
        "not",
        "turned at 64. That asymmetry is the result, not a confound; §4.5's crossover is the "
        "evidence",
        "and it lives in `progress.md`.",
        "",
        "**Two diffusion panels, one checkpoint.** They differ only in A4's unmasking schedule. "
        "On",
        "this checkpoint the metrics stopped separating them — `random` leads distinct-1 "
        "0.68/0.41 and",
        "ties on script consistency — so the choice is a fluent reader's: `gumbel 2` writes "
        "well-formed",
        "words that circle, `random` writes varied content with malformed joins.",
        "",
    ]
    for arm in ARMS.values():
        lines += [
            f"- **{arm['name']}** — `{arm['checkpoint']}`, {arm['corpus']}, {arm['epochs']}. "
            f"Urdu bpb **{arm['bpb']}** ({arm['bpb_note']}). Decode: {arm['decode']}.",
        ]
    lines += ["", "---", ""]
    for pair in pairs:
        lines += [
            f"## Prompt #{pair['index']} — {TOPICS.get(pair['index'], '')}",
            "",
            "**The prefix** — 48 tokens from the held-out validation split, never trained on:",
            "",
            "```",
            pair["prefix"].strip(),
            "```",
            "",
        ]
        for key in ARMS:
            lines += [
                f"**{ARMS[key]['name']}** — {metrics(pair[key])}",
                "",
                "```",
                pair[key]["text"].strip(),
                "```",
                "",
            ]
    return "\n".join(lines) + "\n"


def page(pairs: list[dict], overlap: dict[str, str]) -> str:
    """The browser view. Nastaliq, both themes, no library."""
    blocks = []
    for pair in pairs:
        panels = []
        for key in ARMS:
            record = pair[key]
            s = record["stats"]
            panels.append(
                f"""      <article class="panel {key}">
        <header class="panel-head">
          <span class="arm-name">{html.escape(ARMS[key]['name'])}</span>
          <span class="arm-kind">{html.escape(ARMS[key]['kind'])}</span>
        </header>
        <p class="urdu" dir="rtl" lang="ur">{html.escape(record['text'].strip())}</p>
        <dl class="stats">
          <div><dt>script</dt><dd>{s['script_consistency']:.2f}</dd></div>
          <div><dt>distinct-1</dt><dd>{s['distinct']['1']:.2f}</dd></div>
          <div><dt>rep</dt><dd>{s['repetition']:.3f}</dd></div>
          <div><dt>longest repeat</dt><dd>{s['longest_repeat']}</dd></div>
        </dl>
      </article>"""
            )
        blocks.append(
            f"""    <section class="sample">
      <header class="sample-head">
        <span class="idx">prompt #{pair['index']}</span>
        <h3>{html.escape(TOPICS.get(pair['index'], ''))}</h3>
      </header>
      <div class="prefix">
        <span class="prefix-label">the prefix — 48 held-out tokens</span>
        <p class="urdu" dir="rtl" lang="ur">{html.escape(pair['prefix'].strip())}</p>
      </div>
      <div class="panels">
{chr(10).join(panels)}
      </div>
    </section>"""
        )

    cards = []
    for key, arm in ARMS.items():
        cards.append(
            f"""      <article class="card {key}">
        <h2>{html.escape(arm['name'])}</h2>
        <p class="blurb">{html.escape(arm['blurb'])}</p>
        <dl class="spec">
          <div><dt>held-out Urdu bpb</dt><dd class="big">{arm['bpb']}</dd></div>
          <div><dt>checkpoint</dt><dd class="mono">{html.escape(arm['checkpoint'])}</dd></div>
          <div><dt>training corpus</dt><dd>{html.escape(arm['corpus'])}</dd></div>
          <div><dt>training length</dt><dd>{html.escape(arm['epochs'])}</dd></div>
          <div><dt>decoder</dt><dd class="mono">{html.escape(arm['decode'])}</dd></div>
          <div><dt>verbatim overlap, 16-gram+</dt><dd>{html.escape(overlap[key])}</dd></div>
        </dl>
        <p class="caveat">{html.escape(arm['bpb_note'])}</p>
      </article>"""
        )

    return TEMPLATE.format(cards=chr(10).join(cards), samples=chr(10).join(blocks))


TEMPLATE = """<title>Ravaan Writes Urdu</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;600&family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {{
    --paper: #ECEDE8;
    --surface: #F5F6F2;
    --ink: #191E1B;
    --muted: #5D6862;
    --rule: #D3D8D1;
    --ar: #2B3E77;
    --diff: #1D6B62;
    --gold: #90701F;
    --shadow: 0 1px 2px rgba(25, 30, 27, .06);
    --urdu: "Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", "Noto Naskh Arabic", serif;
    --display: "Spectral", Georgia, serif;
    --sans: "IBM Plex Sans", system-ui, sans-serif;
    --mono: "IBM Plex Mono", ui-monospace, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --paper: #131817;
      --surface: #1B2120;
      --ink: #E7EBE6;
      --muted: #99A39D;
      --rule: #2C3532;
      --ar: #93A7EA;
      --diff: #5CC6B7;
      --gold: #D2AC53;
      --shadow: 0 1px 2px rgba(0, 0, 0, .4);
    }}
  }}
  :root[data-theme="dark"] {{
    --paper: #131817;
    --surface: #1B2120;
    --ink: #E7EBE6;
    --muted: #99A39D;
    --rule: #2C3532;
    --ar: #93A7EA;
    --diff: #5CC6B7;
    --gold: #D2AC53;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4);
  }}

  body {{
    background: var(--paper);
    color: var(--ink);
    font-family: var(--sans);
    font-size: 15px;
    line-height: 1.6;
    margin: 0;
  }}
  .wrap {{
    max-width: 1300px;
    margin: 0 auto;
    padding: 0 20px;
    padding-block: 56px 72px;
    display: flex;
    flex-direction: column;
    gap: 56px;
  }}

  .masthead {{ display: flex; flex-direction: column; gap: 18px; }}
  .eyebrow {{
    font-family: var(--mono);
    font-size: 11.5px;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: var(--gold);
  }}
  h1 {{
    font-family: var(--display);
    font-size: clamp(30px, 5vw, 44px);
    font-weight: 600;
    line-height: 1.12;
    letter-spacing: -.01em;
    margin: 0;
    text-wrap: balance;
  }}
  .standfirst {{
    font-family: var(--display);
    font-size: 18px;
    line-height: 1.55;
    color: var(--muted);
    max-width: 62ch;
    margin: 0;
  }}

  .cards {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--rule);
    border-top: 3px solid var(--accent);
    padding: 22px 22px 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .card.ar {{ --accent: var(--ar); }}
  .card.diff_random, .card.diff_gumbel {{ --accent: var(--diff); }}
  .card h2 {{
    font-family: var(--display);
    font-size: 22px;
    font-weight: 600;
    margin: 0;
    color: var(--accent);
  }}
  .blurb {{ margin: 0; color: var(--muted); font-size: 14px; max-width: 46ch; }}
  .spec {{ margin: 0; display: flex; flex-direction: column; gap: 7px; }}
  .spec > div {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 14px;
    border-bottom: 1px dotted var(--rule);
    padding-bottom: 6px;
  }}
  .spec dt {{ color: var(--muted); font-size: 12.5px; white-space: nowrap; }}
  .spec dd {{ margin: 0; text-align: right; font-size: 13.5px;
             font-variant-numeric: tabular-nums; }}
  .spec dd.big {{
    font-family: var(--mono);
    font-size: 20px;
    font-weight: 500;
    color: var(--accent);
  }}
  .spec dd.mono {{ font-family: var(--mono); font-size: 12px; }}
  .caveat {{ margin: 0; font-size: 12.5px; color: var(--muted); font-style: italic; }}

  .note {{
    border-left: 3px solid var(--gold);
    padding: 2px 0 2px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .note p {{ margin: 0; max-width: 68ch; }}
  .note strong {{ color: var(--ink); }}
  .note .label {{
    font-family: var(--mono);
    font-size: 11.5px;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--gold);
  }}

  .samples {{ display: flex; flex-direction: column; gap: 44px; }}
  .sample-head {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 8px;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }}
  .idx {{
    font-family: var(--mono);
    font-size: 12px;
    color: var(--gold);
    letter-spacing: .04em;
  }}
  .sample-head h3 {{
    font-family: var(--display);
    font-style: italic;
    font-weight: 400;
    font-size: 17px;
    margin: 0;
    color: var(--muted);
  }}

  .prefix {{ margin-bottom: 18px; }}
  .prefix-label {{
    display: block;
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
  }}
  .prefix .urdu {{
    border-right: 3px solid var(--gold);
    padding-right: 14px;
    color: var(--muted);
  }}

  .panels {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }}
  .panel {{
    background: var(--surface);
    border: 1px solid var(--rule);
    border-top: 2px solid var(--accent);
    padding: 16px 18px 12px;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
  }}
  .panel.ar {{ --accent: var(--ar); }}
  .panel.diff_random, .panel.diff_gumbel {{ --accent: var(--diff); }}
  .panel-head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 4px;
  }}
  .arm-name {{ font-family: var(--display); font-weight: 600; color: var(--accent); }}
  .arm-kind {{ font-family: var(--mono); font-size: 11px; color: var(--muted); }}

  .urdu {{
    font-family: var(--urdu);
    font-size: 17px;
    line-height: 2.5;
    text-align: right;
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }}
  .panel .urdu {{ flex: 1; padding: 6px 0 10px; }}

  .stats {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin: 0;
    padding-top: 10px;
    border-top: 1px dotted var(--rule);
  }}
  .stats > div {{ display: flex; gap: 6px; align-items: baseline; }}
  .stats dt {{ font-size: 11px; color: var(--muted); font-family: var(--mono); }}
  .stats dd {{
    margin: 0;
    font-size: 12px;
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
  }}

  .reading {{ display: flex; flex-direction: column; gap: 16px; }}
  .reading h2, .closing h2 {{
    font-family: var(--display);
    font-size: 24px;
    font-weight: 600;
    margin: 0;
  }}
  .reading ul {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 10px; }}
  .reading li {{ max-width: 70ch; }}
  .reading code, .closing code {{
    font-family: var(--mono);
    font-size: 12.5px;
    background: var(--surface);
    border: 1px solid var(--rule);
    padding: 1px 5px;
  }}
  .closing {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    border-top: 1px solid var(--rule);
    padding-top: 28px;
  }}
  .closing p {{ margin: 0; max-width: 70ch; color: var(--muted); }}

  /* Three Nastaliq columns need real width; below that the comparison stacks rather than
     wrapping 2+1, which would break the side-by-side read the page exists for. */
  @media (max-width: 1080px) {{
    .cards, .panels {{ grid-template-columns: minmax(0, 1fr); }}
  }}
</style>

<div class="wrap">
  <header class="masthead">
    <span class="eyebrow">Ravaan · 70M parameters · Urdu</span>
    <h1>Two ways to write a sentence in Urdu</h1>
    <p class="standfirst">Five prefixes from the held-out validation split, continued by the
      project's best autoregressive checkpoint and its best masked-diffusion checkpoint —
      trained this time on the same corpus. Same prompts, same tokenizer, same 160 new tokens.
      The diffusion model appears twice because the order it commits words in changes what it
      writes, and the two orders fail in opposite directions.</p>
  </header>

  <div class="cards">
{cards}
  </div>

  <div class="note">
    <span class="label">read this first</span>
    <p><strong>Both checkpoints are trained on the same corpus now.</strong> Earlier versions of
      this page paired the two arms across different corpora and had to say so; this one does not.
      What still differs is how long each trained — the autoregressive arm's best checkpoint is
      its 4-epoch one, because it turns there and more compute actively makes it worse, while the
      diffusion arm was still improving at 64. That gap is the finding, not a flaw in the setup,
      and the measured crossover behind it lives in the project's log rather than here.</p>
    <p><strong>The diffusion model is shown twice, and it is one model.</strong> Same weights,
      same eight denoising steps; only the order it commits positions in differs. That order used
      to be settled by the metrics and on this checkpoint it no longer is — one setting writes
      well-formed words that circle back on themselves, the other writes more varied content and
      occasionally fuses two words into something that is not one. Picking between them is a
      fluent reader's call, so the page shows both instead of quietly choosing.</p>
    <p><strong>Five prompts of twelve, chosen by reading them.</strong> One of the twelve is not
      Arabic script at all and is the only one excluded for failing — eleven now survive, against
      five on the checkpoint this page used to show. These five are kept so the two versions can
      be compared. Every generation made is in <code>reports/demo_b64.jsonl</code>.</p>
    <p><strong>Neither model is reciting its corpus.</strong> Both were checked for verbatim
      n-gram overlap against the stream they trained on, with genuine held-out Urdu as the
      control — the check that caught an earlier checkpoint copying a quarter of its output back
      out of the training data.</p>
  </div>

  <main class="samples">
{samples}
  </main>

  <section class="reading">
    <h2>What the numbers under each sample mean</h2>
    <ul>
      <li><code>script</code> — the share of letters in Arabic script. A sample that quietly
        stopped writing Urdu shows up here and nowhere else.</li>
      <li><code>distinct-1</code> — unique words over total words. Low means a small vocabulary
        recycled.</li>
      <li><code>rep</code> — one minus distinct-4. A degenerate loop shows up in 4-grams long
        before it shows up in single words.</li>
      <li><code>longest repeat</code> — the longest word run that occurs at least twice. The one
        that catches the failure the others blur: forty good words, then one clause to the end of
        the canvas.</li>
    </ul>
    <p><strong>None of these says the text is good.</strong> They are a floor — a sample that
      fails them has failed before a fluent reader is asked to spend time on it. A sample can
      score well on all four and be grammatical nonsense.</p>
  </section>

  <section class="closing">
    <h2>The honest caption</h2>
    <p>The autoregressive arm writes fluent, grammatical, locally coherent Urdu and loses the
      thread over a paragraph, which is what 70M parameters buys. The diffusion arm, at 64 epochs
      on the same corpus, now holds a paragraph together well enough that eleven of the twelve
      prompts in the pool survive selection where five did before. The decoder is doing more work
      than it looks: at 160 denoising steps this same checkpoint collapses into a loop, at 8 it
      does not, and the two schedules shown here fail in opposite directions rather than in
      degree.</p>
    <p><strong>One native speaker has now read this page, and that is new.</strong> The project's
      maintainer — a fluent Urdu speaker — first reported the diffusion samples reading worse than
      the AR arm's, which is what sent the older checkpoint back for re-measurement; on this one
      the same reader calls the output substantially more coherent. That is one reader and an
      informed one, so it is a lead rather than a result: it does not replace the three
      independent annotators §8.3's generation claim still needs, and every other Urdu judgement
      in this project remains an LLM's.</p>
  </section>
</div>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--samples", default="reports/demo_b64.jsonl")
    parser.add_argument("--out", default="reports/demo")
    parser.add_argument("--html", default=None, help="defaults to <out>.html")
    parser.add_argument("--all", action="store_true", help="render every prompt, not the five")
    args = parser.parse_args(argv)

    source = Path(args.samples)
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line]
    indices = (
        tuple(sorted({r["prompt_index"] for r in rows if r["task"] == "lm/continue"}))
        if args.all
        else CHOSEN
    )
    pairs = load(source, indices)

    # Both checkpoints are arm B now, so one measurement covers the page. The two diffusion
    # panels share a row because verbatim overlap is a property of the checkpoint, not of the
    # schedule that decoded it — and `overlap.py` groups by arm, so they were scored together.
    overlap = {}
    measured = Path("reports/eval/overlap_demo_b64.json")
    for key in ARMS:
        arm = SELECTORS[key][0]
        if measured.exists():
            data = json.loads(measured.read_text(encoding="utf-8"))
            row = next(r for name, r in data["verbatim_rate"].items() if name.startswith(arm))
            control = data["verbatim_rate"]["held-out (control)"]
            overlap[key] = f"{row['16']:.3f} (held-out control {control['16']:.3f})"
        else:
            overlap[key] = "not measured"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".md").write_text(markdown(pairs, source), encoding="utf-8", newline="\n")
    html_path = Path(args.html) if args.html else out.with_suffix(".html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(page(pairs, overlap), encoding="utf-8", newline="\n")
    print(f"{len(pairs)} pairs -> {out.with_suffix('.md')} and {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
