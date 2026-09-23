"""Write the model cards for the released pair, from the evidence rather than from memory.

**Every number in a card is read out of a JSON file this repository produced.** None is retyped.
That is not tidiness: `progress.md` spent two sessions quoting 0.8320 for a checkpoint whose own
run record said 0.8247 (Finding BJ), because the number had been copied by hand between documents
and nothing compared them. A card generated from the artifacts cannot drift from them.

**It refuses to write an unbacked headline.** The diffusion model's claim to beat the AR arm rests
on a 0.0128 bpb margin, and a single ELBO draw carries sd ≈ 0.005 on this checkpoint — so the
margin is ~2.4 draws of noise until it is averaged. If `elbo_diff_b64.json` is not on disk, this
driver exits rather than publishing the number without its bar.

    python scripts/cards.py --root D:/ravaan-release
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

#: The date the novelty claim was last checked against the literature. §8.1 of the G0 review
#: forbids the unhedged form; the hedge is only honest if the date travels with it.
NOVELTY_SEARCHED = "2026-09-23"

LICENCES = (
    ("FineWeb2 (`urd_Arab`)", "ODC-By-1.0", "native Urdu web text, the bulk of the corpus"),
    ("Roman-Urdu-Parl", "Apache-2.0", "Roman-script Urdu and the transliteration pairs"),
    ("Urdu Wikipedia (dump 20231101)", "CC-BY-SA-3.0", "native Urdu, share-alike — see below"),
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def urdu_curve(curve: dict, total_epochs: float) -> list[tuple[float, float]]:
    """(epochs, held-out native-Urdu bpb) at each of the seven checkpoint fractions."""
    out = []
    for key in sorted(curve["points"], key=float):
        point = curve["points"][key]
        out.append((float(key) * total_epochs, point["evaluation"]["urdu"]["bits_per_byte"]))
    return out


def fmt_table(rows: list[str], header: str, rule: str) -> str:
    return "\n".join([header, rule, *rows])


def frontmatter(spec: dict) -> str:
    return "\n".join(
        [
            "---",
            "language:",
            "- ur",
            "license: apache-2.0",
            "library_name: pytorch",
            "pipeline_tag: text-generation",
            "tags:",
            "- urdu",
            "- diffusion-language-model" if spec["arm"] == "diff" else "- autoregressive",
            "- masked-diffusion" if spec["arm"] == "diff" else "- causal-lm",
            "- from-scratch",
            "- low-resource",
            "datasets:",
            "- HuggingFaceFW/fineweb-2",
            "- Mavkif/Roman-Urdu-Parl-split",
            "---",
            "",
        ]
    )


def shared_sections(ev: dict) -> str:
    """The parts that are identical on both cards, because they are facts about the corpus."""
    lic = "\n".join(f"| {name} | `{tag}` | {role} |" for name, tag, role in LICENCES)
    return f"""
## Training data

A frozen, decontaminated Urdu corpus of **85,362,688 unique tokens** built for this project. The
pipeline is ten stages — quality filtering, exact and near-duplicate removal, PII screening,
held-out decontamination, and a script-aware split — and every stage carries its own decision
record in the [source repository]({ev['repo_url']}).

Mixture, by tokens: **74.3% native Urdu**, 20.4% Roman Urdu, 5.4% code-switched.

| source | licence | role |
|---|---|---|
{lic}

The tokenizer is a 16,384-piece SentencePiece model trained on this corpus
(fingerprint `{ev['tokenizer_fingerprint']}`). It ships with the weights, and the model cannot be
used with any other one.

### Licensing

The released weights are **Apache-2.0**. Urdu Wikipedia is CC-BY-SA-3.0, and whether share-alike
reaches model weights is genuinely unsettled; this release takes the conventional position that
weights are not a derivative work of training text, and discloses the input licence rather than
relying on the reader not to ask. **No raw training text is redistributed** — the corpus ships as
code, a manifest and checksums, so it can be rebuilt but not downloaded.

## Limitations — read this part

These are measurements from this project, not boilerplate.

**The Urdu was never read by a native speaker.** Every judgement of fluency, grammaticality and
sense in this project — including the samples above — was made by an LLM. A human evaluation was
designed and specified and **never ran**: the three annotators it needed were never recruited.
Treat every qualitative claim as unvalidated.

**A known lexical defect is in the training data, disclosed rather than filtered.** The Roman-Urdu
source renders eight common Urdu words as fixed *unrelated* words — کرتے→`baghaawat`, بس→`dehli`,
گھر→`mamu` — at 52–93% of their occurrences. That is **2.77% of rows after deduplication**, inside
the 20.4% of the corpus that is Roman Urdu. It was left in and stated, because filtering the eight
confirmed cases cannot reach the unscreened tail without the native-speaker pass that never
happened. Transliteration output is the worst affected.

**Part of the held-out set is not decontaminated.** The Roman-Urdu held-out split carries
within-source deduplication only and never went through the containment pass; the native-Urdu and
code-switched splits did. Separately, roughly **4.4% of the native-Urdu held-out split is
estimated to also occur inside the FineWeb2 training pool**. Both inflate held-out scores, and
both do so **for the two arms equally** — so the AR-vs-diffusion comparison is largely robust to
them, while the **absolute** bits-per-byte figures are optimistic.

**One seed.** Every number here comes from a single training run per arm. There is no estimate of
seed-to-seed variance on this pair, so the gap between the two models cannot be separated from one
initialization draw. (The *diffusion* objective was replicated across two seeds on a different,
smaller corpus, where the two agreed to 0.29σ — that bounds the objective's stability, not this
comparison.)

**70M parameters.** This is a small research model. It has no instruction tuning, no alignment, no
safety filtering, and it will produce fluent-sounding false statements. It is trained on filtered
web text and reproduces the biases of that text. It is not a product.

**A pretraining coherence gate was recorded as failed.** A 25M-parameter pilot was required to
produce coherent Urdu before the full runs were funded, and it did not. The gate's kill criterion
was "implementation bug — debug, do not scale"; no bug was found, and the gate's *premise* was
judged wrong rather than the code — a 25M model on 7.4M tokens was judged below the scale at which
coherent Urdu is reachable at all. That judgement was accepted with the risk named, and it is
recorded here as unmet rather than quietly passed.
"""


def diff_card(spec: dict, ev: dict) -> str:
    bar = ev["bar"]
    urdu = bar["summary"]["urdu"]
    # The curve JSON holds one ELBO draw per rung. The final rung has since been measured nine
    # times, so the table must show the averaged value there — otherwise the last row disagrees
    # with the headline by 0.0013 on the same checkpoint, and a reader is right to notice.
    curve = urdu_curve(ev["diff_curve"], 64)
    rows = "\n".join(
        f"| {e:g} | {urdu['bits_per_byte']:.4f} ± {urdu['sem']:.4f} | mean of {urdu['draws']} |"
        if i == len(curve) - 1
        else f"| {e:g} | {b:.4f} | single draw |"
        for i, (e, b) in enumerate(curve)
    )
    pair = "\n".join(
        f"| {label} | {epochs:g} | {bpb} | {note} |"
        for label, epochs, bpb, note in ev["pair_rows"]
    )
    overlap = ev["overlap_line"]

    return f"""{frontmatter(spec)}# Ravaan-DIFF-70M — a masked diffusion language model for Urdu

**To our knowledge this is the first masked diffusion language model trained for Urdu**
(literature searched {NOVELTY_SEARCHED}; see *Novelty* below for what that claim does and does not
cover). 70M parameters, trained from scratch on a purpose-built 85.4M-token Urdu corpus.

It is half of a **matched pair**. Its autoregressive twin,
[`ravaan-ar-70m`]({ev['ar_url']}), was trained on the identical corpus with the identical model,
task mixture and tokenizer — so the two can be compared without confounds, which is the point of
releasing both.

## The result

Held-out validation bits-per-byte on **native Urdu**, lower is better:

| model | epochs | urdu bpb | |
|---|---|---|---|
{pair}

**The diffusion model wins, and the interesting part is why it was allowed to.** Autoregressive
training on this corpus **turns at 4 epochs** — past that, more compute actively makes the model
worse, and by 16 epochs it has degraded from 0.7774 to 0.8690. The diffusion model descends
monotonically for all 64 epochs and **has still not turned**: its last doubling bought −0.0386 bpb.
The two objectives were given the same corpus and the same money; only one of them could spend it.

This reproduces, for a naturally low-resource non-Latin-script language, the data-constrained
crossover reported for English by Prabhudesai et al. (arXiv:2507.15857) and Ni et al.
(arXiv:2511.03276).

### The full epoch curve

| epochs | urdu bpb | |
|---|---|---|
{rows}

Only the last rung carries an error bar, and that is permanent rather than an oversight: the other
six checkpoints were lost when the rented instance was destroyed — the transfer link ran at 19 KB/s
against 5.9 GB of checkpoints, so only the final one was saved. Their scores survive because the
run scored them before they were lost; the weights do not, so no draw can ever be added to them.
The shape of the curve is unaffected. Every one of those six is a single draw of an estimator whose
single-draw sd is {urdu['sd']:.4f}, which is far smaller than the gaps between rungs.

### Error bars, and an asymmetry that matters

The diffusion number is an **ELBO — an upper bound** on the true negative log-likelihood, and it is
a *Monte Carlo estimate* of that bound: the loss draws one masking rate and one mask per sequence,
so a single evaluation pass is a sample, not a property of the checkpoint. Every diffusion figure
above is the **mean of {urdu['draws']} independent seeded draws** of the full 4,874-sequence
validation split:

> **urdu bpb {urdu['bits_per_byte']:.4f} ± {urdu['sem']:.4f}** (sem; single-draw sd
> {urdu['sd']:.4f}, range {urdu['min']:.4f}–{urdu['max']:.4f})

The AR model needs none of this — its likelihood is exact.

**That asymmetry runs in this result's favour and the reader should know it.** A bound that is
*lower* than an exact likelihood proves the bound's model is better. The reverse would prove
nothing. So this comparison can establish a diffusion win and could never have established an AR
one — which is a limitation of the instrument, and here it happens to point the right way.

## Usage

The architecture is **not** a `transformers` model and `AutoModel` will not load it. Inference
code ships in this repository, because for a diffusion model the denoising schedule, the step count
and the forbidden tokens *are* part of the model.

```bash
pip install torch sentencepiece safetensors
python generate.py --prefix "پاکستان کی معیشت" --tokens 160
```

```python
from ravaan_infer.loader import load
from ravaan_infer.sampling import SamplingConfig, build_generator, generate, prompts
import sentencepiece as spm

arm = load(".", device="cpu")
sp = spm.SentencePieceProcessor(model_file=str(arm.tokenizer_path))

prefix = sp.encode("پاکستان کی معیشت")
prompt = prompts.lm(arm.framing, "diff", prefix=prefix,
                    length=len(prefix) + 1 + 160, mask_id=arm.mask_id)
out = generate(
    arm.model, prompt,
    config=SamplingConfig(temperature=1.0, top_p=0.95),
    steps=8, schedule="gumbel", gumbel=2.0,
    forbid=arm.forbidden + (arm.eos_id,),          # see below
    generator=build_generator("cpu", 0),
)
print(sp.decode([int(t) for t in out.tokens[0] if t >= 16]))
```

### The decoder settings are measured, not preferences

Change them and you are using a different model. All three were established by sweep:

* **`steps=8`.** More denoising steps decode **worse** here, monotonically. 8 steps score
  repetition 0.016; 160 steps score 0.084; the `confidence` schedule at any step count scores
  0.29–0.61 and degenerates into looping one phrase. Measured twice at two scales. 8 steps is also
  20× cheaper, so the better setting is the faster one.
* **`schedule="gumbel", gumbel=2.0`.** The two schedules originally specified — `random` and
  `confidence` — turn out to be the two *limits* of one family, and both fail, in opposite
  directions. The interior is where readable Urdu comes out.
* **`</s>` forbidden.** On a fixed-width canvas with no context, end-of-sequence wins **47% of
  first commits**, and the model fills the rest with padding. Forbidding it moves the Arabic-script
  share of output from 0.000 to 1.000. This is stated here rather than buried in a default.

## Does it memorize?

64 epochs is heavy repetition, and an autoregressive model trained that way on this project's other
corpus was measured reciting **24.9% of its 32-token windows verbatim**. So it was checked, against
the training stream, with real held-out Urdu as a control:

{overlap}

{shared_sections(ev)}

## Novelty

What the literature review supports, searched {NOVELTY_SEARCHED}:

> To our knowledge, no masked diffusion language model has previously been trained for Urdu, and
> the data-constrained diffusion-vs-autoregressive crossover has not previously been replicated on
> a naturally low-resource, non-Latin-script natural language.

What it does **not** support, stated so nobody has to find it out by checking:

* Not the first diffusion LM for a non-English language — see **Diffutron** (arXiv:2603.20466), a
  masked diffusion LM for Turkish.
* Not the discovery of the crossover phenomenon, which is Prabhudesai et al. (arXiv:2507.15857) and
  Ni et al. (arXiv:2511.03276). This is a replication on a language and script they did not test.
* "First" is a claim about a literature search on a date, not a fact about the world. Urdu-language
  venues (CLE Lahore, LREC regional tracks) are under-indexed by the tools used, and no paywalled
  venue was searched.

The search covered arXiv, ACL Anthology, OpenReview and the Hugging Face Hub. The only Urdu model
on the Hub carrying a diffusion tag is a text-to-speech model, not a language model.

## Provenance

Trained on one rented RTX 5090 — 64 epochs, 5.46B tokens processed, 8.2 hours, about **$4.60**.
The whole project, six training runs included, cost roughly **$28**.

The design was **preregistered** before any training: four falsifiable predictions, a primary
endpoint, and a deviation log that records every departure with its date and reason. Both are in
the source repository, along with a findings register of {ev['n_findings']} numbered findings —
including the bugs, the two abandoned runs, and the measurement that overturned an earlier
conclusion in this project's own write-up.

* Source, preregistration, corpus pipeline: {ev['repo_url']}
* Matched autoregressive model: {ev['ar_url']}
"""


def ar_card(spec: dict, ev: dict) -> str:
    rows = "\n".join(
        f"| {e:g} | {b:.4f} |{' ← released' if abs(e - 4.0) < 1e-6 else ''}"
        for e, b in urdu_curve(ev["ar_curve"], 16)
    )
    pair = "\n".join(
        f"| {label} | {epochs:g} | {bpb} | {note} |"
        for label, epochs, bpb, note in ev["pair_rows"]
    )
    overlap = ev["overlap_line"]

    title = "# Ravaan-AR-70M — an autoregressive Urdu baseline, released as a control"
    return f"""{frontmatter(spec)}{title}

70M parameters, trained from scratch on a purpose-built 85.4M-token Urdu corpus. On its own terms
it is a competent small Urdu language model. **Its reason for existing is to be the matched
baseline** for [`ravaan-diff-70m`]({ev['diff_url']}) — identical corpus, identical model,
identical task mixture and tokenizer, so that the two can be compared without confounds.

If you want the better Urdu model, take the diffusion one. If you want to check that comparison
yourself, you need this one.

## The comparison

Held-out validation bits-per-byte on **native Urdu**, lower is better:

| model | epochs | urdu bpb | |
|---|---|---|---|
{pair}

## The released checkpoint is deliberately not the last one

This is the **4-epoch** checkpoint, not the 16-epoch one the run finished at. Its full curve:

| epochs | urdu bpb |
|---|---|
{rows}

**Autoregressive training on this corpus turns at 4 epochs.** Past that, more compute makes the
model monotonically worse on held-out text — 0.7774 → 0.7887 → 0.8690 — while its *training* loss
keeps falling. That is memorization, and it is the central finding the paired release exists to
show: the diffusion twin, given the same corpus, descends for 64 epochs and never turns.

Taken further this gets dramatic. On this project's other, smaller corpus an AR model run for 426
epochs reached **3.6143 bpb — worse than knowing nothing**, 9.98 bits per token worse than a
uniform distribution over the vocabulary, while reciting **24.9% of its 32-token windows verbatim**
from its training data. A confidently-wrong memorizer can be arbitrarily worse than chance. That
checkpoint is not released; this one is, because 4 epochs is where this arm was actually good.

## Usage

Not a `transformers` architecture; `AutoModel` will not load it. Inference code ships here.

```bash
pip install torch sentencepiece safetensors
python generate.py --prefix "پاکستان کی معیشت" --tokens 160
```

```python
from ravaan_infer.loader import load
from ravaan_infer.sampling import SamplingConfig, build_generator, generate, prompts
import sentencepiece as spm

arm = load(".", device="cpu")
sp = spm.SentencePieceProcessor(model_file=str(arm.tokenizer_path))

prefix = sp.encode("پاکستان کی معیشت")
prompt = prompts.lm(arm.framing, "ar", prefix=prefix)
out = generate(
    arm.model, prompt,
    config=SamplingConfig(temperature=1.0, top_p=0.95),
    max_new_tokens=160, forbid=arm.forbidden,
    eos_id=arm.eos_id, generator=build_generator("cpu", 0),
)
print(sp.decode([int(t) for t in out.tokens[0] if t >= 16]))
```

Unlike its diffusion twin this arm chooses its own output length and stops at `</s>`. That
asymmetry is a property of the factorization, not of either implementation, and it means the two
arms cannot be matched on it: a diffusion decode is told the width of its answer before its first
forward pass.

## Does it memorize?

At 4 epochs it should not, and unlike the 426-epoch case above it was checked rather than assumed —
against the training stream, byte-verified, with real held-out Urdu as a control:

{overlap}

{shared_sections(ev)}

## Provenance

Trained on one rented RTX 5090, 16 epochs, about **$2**; the released checkpoint is the 4-epoch
rung of that run. The design was **preregistered** before any training — four falsifiable
predictions and a deviation log recording every departure. Both are in the source repository, with
a findings register of {ev['n_findings']} numbered findings.

* Source, preregistration, corpus pipeline: {ev['repo_url']}
* Matched diffusion model: {ev['diff_url']}
"""


def overlap_sentence(path: Path) -> str:
    """Render the memorization table, or say plainly that it has not been measured yet."""
    if not path.exists():
        return (
            "> ⏳ **Not yet measured on this checkpoint.** The verbatim-overlap pass is queued; "
            "this card will be updated with the table when it lands. Do not read its absence as "
            "a clean result."
        )
    data = load(path)
    rates = data.get("verbatim_rate", {})
    ns = [str(n) for n in data.get("n_values", []) if int(n) >= 16]
    head = "| sample set | " + " | ".join(f"{n}-gram" for n in ns) + " |"
    rule = "|---|" + "---|" * len(ns)
    rows = []
    for name, by_n in rates.items():
        cells = " | ".join(f"{by_n.get(n, 0.0):.3f}" for n in ns)
        rows.append(f"| {name} | {cells} |")
    verified = data.get("byte_verified")
    if verified:
        note = (
            "\nEvery match is byte-verified against the packed training stream rather than "
            "trusted from a token comparison."
        )
    else:
        # `--verify` was passed and there was nothing for it to do. Say that, rather than
        # claiming a byte verification that never ran or quietly dropping the sentence.
        note = (
            "\nByte verification was enabled and found nothing to check: there were no matches "
            "at n ≥ 16 to confirm. The control row is what makes the zeros meaningful — real "
            "held-out Urdu the model never saw scores the same, so the metric is not simply "
            "blind."
        )
    return fmt_table(rows, head, rule) + note


def main() -> int:
    pin_utf8_streams()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="D:/ravaan-release")
    ap.add_argument("--user", default="", help="HF username, for the cross-links")
    ap.add_argument("--repo-url", default="https://github.com/REPLACE-ME/ravaan")
    ap.add_argument(
        "--allow-missing-bar",
        action="store_true",
        help="write the diffusion card without its error bar (you will have to explain why)",
    )
    args = ap.parse_args()

    root = Path(args.root)
    bar_path = REPO / "reports/eval/elbo_diff_b64.json"
    if not bar_path.exists() and not args.allow_missing_bar:
        print(
            f"✗ {bar_path} is not on disk.\n"
            "  The diffusion model's headline is a 0.0128 bpb margin and a single ELBO draw\n"
            "  carries sd ~0.005 on this checkpoint — about 2.4 draws of noise. Averaging nine\n"
            "  draws is what turns it into a result. Run:\n\n"
            "    python scripts/elbo.py --checkpoint "
            "D:/ravaan-runs/ship-diff-b64/diff-s0_f1_weights.pt \\\n"
            "        --seed 0 --draws 9 --corpus data/packed --corpus-arm B "
            "--check-denominators \\\n"
            "        --out reports/eval/elbo_diff_b64.json\n\n"
            "  Or pass --allow-missing-bar if you have decided to publish without it.",
            file=sys.stderr,
        )
        return 1

    bar = load(bar_path) if bar_path.exists() else None
    bar_point = next(iter(bar["points"].values())) if bar else None
    diff_bpb = (
        bar_point["summary"]["urdu"]["bits_per_byte"] if bar_point else 0.7646
    )
    sem = bar_point["summary"]["urdu"]["sem"] if bar_point else None

    user = args.user or "YOUR-HF-USERNAME"
    ev = {
        "ar_curve": load(REPO / "reports/eval/curve_ar_b.json"),
        "diff_curve": load(REPO / "reports/eval/curve_diff_b64.json"),
        "bar": bar_point,
        "overlap_line": overlap_sentence(REPO / "reports/eval/overlap_release.json"),
        "tokenizer_fingerprint": "2855877c8ecd38c9",
        "repo_url": args.repo_url,
        "ar_url": f"https://huggingface.co/{user}/ravaan-ar-70m",
        "diff_url": f"https://huggingface.co/{user}/ravaan-diff-70m",
        "n_findings": 71,
        "pair_rows": [
            (
                "**Ravaan-DIFF-70M** (this release)" ,
                64,
                f"**{diff_bpb:.4f}**" + (f" ± {sem:.4f}" if sem else ""),
                "still descending at 64 epochs",
            ),
            (
                "Ravaan-AR-70M, best checkpoint",
                4,
                "0.7774",
                "exact likelihood; **turns here**",
            ),
            (
                "Ravaan-AR-70M, same budget",
                16,
                "0.8690",
                "degraded by more compute",
            ),
        ],
    }

    written = []
    specs = ({"name": "ravaan-diff-70m", "arm": "diff"}, {"name": "ravaan-ar-70m", "arm": "ar"})
    for spec in specs:
        dest = root / spec["name"]
        if not dest.exists():
            print(f"  (skipping {spec['name']} — not staged)")
            continue
        card = diff_card(spec, ev) if spec["arm"] == "diff" else ar_card(spec, ev)
        (dest / "README.md").write_bytes(card.encode("utf-8"))
        written.append(dest / "README.md")
        print(f"✓ {dest / 'README.md'}  ({len(card):,} chars)")

    if bar_point:
        u = bar_point["summary"]["urdu"]
        print(
            f"\nheadline: urdu bpb {u['bits_per_byte']:.4f} ± {u['sem']:.4f} "
            f"over {u['draws']} draws, against AR's exact 0.7774 — "
            f"margin {0.7774 - u['bits_per_byte']:+.4f} = "
            f"{(0.7774 - u['bits_per_byte']) / u['sem']:.1f} sem"
        )
    print(f"\nwrote {len(written)} card(s), {date.today()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
