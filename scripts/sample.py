#!/usr/bin/env python
"""Read text out of a trained checkpoint — G3's coherence half, and §4.4's A3/A4 (PRD §8, §11).

G3 asks two things and session 21 answered one of them: "both models resume from checkpoint
correctly" passed on both arms, and "20M pilot DIFF produces coherent Urdu after 50 epochs" could
not even be attempted, because nothing in the repository could turn a checkpoint into a sentence.
This driver is that. It writes two artefacts from one pass:

* **`<out>.jsonl`** — one record per generation: the prompt, the tokens, the text, §8.3's three
  generation metrics, and the decoder settings that produced it. Machine-readable, and the thing
  an ablation table is built from.
* **`<out>.md`** — the same generations laid out to be *read*, Urdu first, with the metrics
  beside each one. G3's verdict comes from a person reading this file; the metrics are there so
  the person is not the one who has to notice that a sample stopped being Urdu.

Three prompt sets, and each is here for a reason rather than for variety:

* **`lm/free`** — `<lm>` and nothing else. The unconditional sample, which is what "produces
  coherent Urdu" means without a prompt to lean on, and the hardest thing a 25M model trained for
  50 epochs on 7.4M tokens is asked to do.
* **`lm/continue`** — `<lm>` plus a real prefix from the *validation* split. Distinguishes "the
  model has learned Urdu" from "the model has learned how Urdu documents start".
* **`infill`** — a hole in a real sequence, framed per §4.1: FIM for the AR arm, a masked span
  in place for the diffusion one. The only set where the two arms are doing visibly different
  work, and the one §4.4's ablations sweep.

**The prefixes come from validation, never from training.** A continuation of text the model was
trained on is a memorization check wearing a coherence check's clothes, and at 50 epochs over 7.4M
tokens memorization is the outcome to rule out rather than the one to assume away.

**`--forbid-eos` is a third axis, and on this corpus it matters more than either of §4.4's.** A
diffusion canvas has a width the caller chose, so "the document ends here" is not a decision the
model is being asked for — and the first run of this driver measured the confidence schedule
spending **47% of its first 128 commits on `</s>`**, then filling the remainder with Roman-Urdu
function words, for an Arabic-script share of **0.00**. Forbidding `</s>` takes that to **1.00**.
That is a large effect from a decoder default, so it is swept and reported rather than chosen
here: `always` is almost certainly the right setting for a fixed-width canvas, and the number that
says so should be in the report rather than in this file's history.

    python scripts/sample.py --checkpoint runs/pilot/pilot-ar/ar_f1.pt \\
        --checkpoint runs/pilot/pilot-diff/diff_f1.pt \\
        --corpus data/packed-pilot --tokenizer data/tokenizer/ravaan-16k.model \\
        --out reports/pilot_samples --samples 6 --new-tokens 160

Requires the `[train]` and `[tokenizer]` extras.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

import numpy as np  # noqa: E402
import torch  # noqa: E402

from ravaan.evaluation.generation import GenerationStats  # noqa: E402
from ravaan.sampling import SamplingConfig, generate, load_arm, prompts  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402
from ravaan.training.tasks import SentencePieceCodec  # noqa: E402

#: §4.4's A3 rung, extended past its top. Swept for the diffusion arm only; the AR arm has no
#: step count to vary. §4.4 stops at 64, which on a 160-position canvas still commits 2-3
#: positions per step from independent marginals; the grid's ceiling was doing as much work as
#: its contents, so 160 — one position per step, the exact any-order ancestral sampler — is here
#: as the reference point the four rungs are read against. Nothing above the number of masked
#: positions does anything, since those steps commit nothing.
A3_STEPS = (8, 16, 32, 64, 160)
#: §4.4's A4 rung, plus the schedule session 23 added between them — see
#: `ravaan.sampling.diffusion`. Swept together because A4's two turned out to be the endpoints of
#: the family the third one parameterizes, and reporting only the endpoints is what hid the fact
#: that a readable setting sits between them.
A4_SCHEDULES = ("confidence", "random", "gumbel")
#: Not in §4.4, and swept anyway — see `--forbid-eos`.
EOS_CHOICES = ("never", "always", "both")

#: The `gumbel` schedule's one knob. Swept rather than picked, for the reason A3 and A4 are.
GUMBEL_SCALES = (1.0, 2.0)


def build_arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--checkpoint", action="append", required=True, help="repeatable; one per arm"
    )
    parser.add_argument("--corpus", default="data/packed-pilot")
    parser.add_argument("--tokenizer", default=None, help="defaults to data/tokenizer/<manifest>")
    parser.add_argument("--out", default="reports/pilot_samples")
    parser.add_argument("--population", default="urdu")
    parser.add_argument("--samples", type=int, default=6, help="prompts per set")
    parser.add_argument("--new-tokens", type=int, default=160)
    parser.add_argument("--prefix-tokens", type=int, default=48)
    parser.add_argument("--infill-span", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--top-k", type=int, default=0)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--steps",
        type=int,
        action="append",
        help=f"§4.4's A3; repeatable. Defaults to {A3_STEPS}",
    )
    parser.add_argument(
        "--schedule",
        action="append",
        choices=list(A4_SCHEDULES),
        help=f"§4.4's A4; repeatable. Defaults to {A4_SCHEDULES}",
    )
    parser.add_argument(
        "--forbid-eos",
        choices=list(EOS_CHOICES),
        default="both",
        help=(
            "whether the diffusion decoder may commit `</s>` on a fixed-width canvas. Swept by "
            "default because it is worth more than either §4.4 axis here — see the module "
            "docstring"
        ),
    )
    parser.add_argument(
        "--gumbel",
        type=float,
        action="append",
        help=(
            "noise scale for the `gumbel` schedule, annealed to zero over the decode; repeatable. "
            f"Defaults to {GUMBEL_SCALES}. 0 reproduces `confidence` exactly, so the sweep does "
            "not need to include it"
        ),
    )
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser


def pick_prefixes(corpus: PackedCorpus, count: int, seed: int) -> list[np.ndarray]:
    """Evenly spaced sequences from the validation split, not the first ``count``.

    The same argument stage 9 and the tokenizer sampler both make about prefixes: a packed stream
    is written in corpus order, so its head is one source's opening documents. Spacing costs
    nothing and removes a bias nobody would see in the output.
    """
    total = len(corpus)
    if total == 0:
        raise ValueError("the validation split is empty")
    stride = max(1, total // max(count, 1))
    return [corpus[min(i * stride, total - 1)] for i in range(count)]


def decode(codec: SentencePieceCodec, ids: list[int], framing_ids: set[int]) -> str:
    """Text for a reader: framing pieces dropped, everything else as the tokenizer renders it.

    The framing tokens are §7's own pieces and SentencePiece renders them as literal `<lm>`
    strings, which puts furniture in the middle of a paragraph a native speaker is being asked to
    judge. The JSONL keeps the raw ids, so nothing is lost — this is the reading view.
    """
    return codec.decode([i for i in ids if i not in framing_ids])


def main(argv: list[str] | None = None) -> int:
    args = build_arguments().parse_args(argv)
    steps = tuple(args.steps or A3_STEPS)
    schedules = tuple(args.schedule or A4_SCHEDULES)
    gumbels = tuple(args.gumbel or GUMBEL_SCALES)

    corpus = PackedCorpus(
        args.corpus, split="validation", arm=None, populations=(args.population,)
    )
    name = Path(str(corpus.tokenizer["id"])).name.split(":")[-1]
    tokenizer_path = Path(args.tokenizer) if args.tokenizer else Path("data/tokenizer") / name
    if not tokenizer_path.exists():
        print(f"§7's tokenizer is not at {tokenizer_path}", file=sys.stderr)
        return 2
    codec = SentencePieceCodec(str(tokenizer_path))
    if codec.tokenizer.fingerprint() != corpus.tokenizer.get("fingerprint"):
        print(
            f"{tokenizer_path} fingerprints {codec.tokenizer.fingerprint()} against the corpus's "
            f"{corpus.tokenizer.get('fingerprint')} — the text would be decoded in the wrong "
            "vocabulary",
            file=sys.stderr,
        )
        return 2

    config = SamplingConfig(
        temperature=args.temperature, top_k=args.top_k, top_p=args.top_p, seed=args.seed
    )
    prefixes = pick_prefixes(corpus, args.samples, args.seed)
    records: list[dict] = []

    for checkpoint in args.checkpoint:
        arm = load_arm(checkpoint, device=args.device)
        framing_ids = {getattr(arm.framing, field) for _, field in arm.framing.PIECES}
        framing_ids.add(arm.mask_id)
        framing_ids.add(arm.framing.pad)
        print(arm.describe())

        eos_axis = {"never": (False,), "always": (True,), "both": (False, True)}[args.forbid_eos]
        # `gumbel` is the only schedule with a scale, so the other two take it once rather than
        # once per value — otherwise the sweep silently doubles them and the summary averages a
        # setting twice.
        settings = (
            [(None, None, None, False)]
            if arm.arm == "ar"
            else [
                (s, sched, g if sched == "gumbel" else None, e)
                for s in steps
                for sched in schedules
                for g in (gumbels if sched == "gumbel" else (None,))
                for e in eos_axis
            ]
        )

        for index, sequence in enumerate(prefixes):
            clean = [int(t) for t in sequence.tolist()]
            prefix = clean[: args.prefix_tokens]
            span = args.infill_span
            hole_at = max(1, len(clean) // 3)
            infill_prefix = clean[:hole_at]
            infill_suffix = clean[hole_at + span : hole_at + span + args.prefix_tokens]

            mask_id = arm.mask_id if arm.arm == "diff" else None
            plans = [
                (
                    "lm/free",
                    prompts.lm(
                        arm.framing, arm.arm, length=args.new_tokens + 1, mask_id=mask_id
                    ),
                ),
                (
                    "lm/continue",
                    prompts.lm(
                        arm.framing,
                        arm.arm,
                        prefix=prefix,
                        length=len(prefix) + args.new_tokens + 1,
                        mask_id=mask_id,
                    ),
                ),
                (
                    "infill",
                    prompts.infill(
                        arm.framing,
                        arm.arm,
                        prefix=infill_prefix,
                        suffix=infill_suffix,
                        span=span,
                        mask_id=mask_id,
                    ),
                ),
            ]

            for task, prompt in plans:
                for step_count, schedule, gumbel, forbid_eos in settings:
                    started = time.time()
                    out = generate(
                        arm.model,
                        prompt,
                        config=replace(config, seed=config.seed + index),
                        max_new_tokens=args.new_tokens,
                        steps=step_count or 32,
                        schedule=schedule or "confidence",
                        gumbel=1.0 if gumbel is None else gumbel,
                        forbid=(*arm.forbidden, arm.eos_id) if forbid_eos else arm.forbidden,
                        eos_id=arm.eos_id if task != "infill" else None,
                    )
                    elapsed = time.time() - started
                    written = out.written()[0]
                    text = decode(codec, written, framing_ids)
                    stats = GenerationStats.of(text)
                    records.append(
                        {
                            "checkpoint": str(Path(checkpoint)),
                            "arm": arm.arm,
                            "fraction": arm.fraction,
                            "task": task,
                            "prompt_index": index,
                            "prompt_tokens": list(prompt.tokens),
                            "prompt_text": decode(codec, list(prompt.tokens), framing_ids),
                            "hinted_length": prompt.hinted_length,
                            "steps": step_count,
                            "schedule": schedule,
                            "gumbel": gumbel,
                            "forbid_eos": forbid_eos,
                            "seed": config.seed + index,
                            "forwards": out.forwards,
                            "seconds": round(elapsed, 3),
                            "tokens": written,
                            "text": text,
                            "stats": stats.to_dict(),
                            "detail": out.detail,
                        }
                    )
                    axis = (
                        ""
                        if step_count is None
                        else (
                            f"{step_count:4d} {schedule:10s}"
                            f"{'' if gumbel is None else f' g{gumbel:g}':>4s}"
                            f" eos{'-' if forbid_eos else '+'}"
                        )
                    )
                    print(
                        f"  {arm.arm:4s} {task:12s} #{index} {axis} "
                        f"{len(written):4d} tok  {elapsed:5.2f}s  "
                        f"script {stats.script_consistency:.2f}  rep {stats.repetition:.2f}"
                    )

    out_base = Path(args.out)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    jsonl = out_base.with_suffix(".jsonl")
    with jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    markdown = out_base.with_suffix(".md")
    markdown.write_text(render(records, config, args), encoding="utf-8", newline="\n")
    print(f"\n{len(records)} generations -> {jsonl} and {markdown}")
    return 0


def render(records: list[dict], config: SamplingConfig, args) -> str:  # noqa: ANN001
    """The reading view. Urdu is right-to-left, so every sample gets its own fenced block."""
    lines = [
        "# Pilot samples — G3's coherence half",
        "",
        "Generated by `scripts/sample.py`. **This file is for reading**, and the verdict G3 asks",
        "for is a fluent speaker's, not a metric's. §8.3's three generation numbers sit beside",
        "each sample so that a sample which stopped being Urdu, or which is four phrases on a",
        "loop, is visible without reading all of them.",
        "",
        f"- decoder: temperature {config.temperature}, top-k {config.top_k}, top-p {config.top_p},"
        f" seed {config.seed}",
        f"- prompts: {args.samples} per set, from the **validation** split of `{args.population}`",
        f"- new tokens: {args.new_tokens}; infill span: {args.infill_span}",
        "",
        "`script` is the Arabic-script share of letters, `rep` is 1 − distinct-4, and `run` is the",
        "longest repeated word run. A diffusion row carries the A3 step count and A4 schedule it",
        "was decoded under — with the noise scale, where the schedule is `gumbel` — and an AR row",
        "has neither, because that arm has no such dial.",
        "",
        "## Summary",
        "",
        "| arm | task | steps | schedule | n | script | distinct-1 | rep | run |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    groups: dict[tuple, list[dict]] = {}
    for record in records:
        key = (
            record["arm"],
            record["task"],
            record["steps"],
            record["schedule"],
            record["gumbel"],
            record["forbid_eos"],
        )
        groups.setdefault(key, []).append(record)

    def mean(rows: list[dict], *path: str) -> float:
        values = []
        for row in rows:
            value = row["stats"]
            for key in path:
                value = value[key]
            values.append(float(value))
        return sum(values) / len(values) if values else 0.0

    def describe(schedule: str | None, gumbel: float | None, forbid_eos: bool) -> str:
        """The decoder axes as one cell. `gumbel` has a scale and the other two do not."""
        if schedule is None:
            return ""
        scale = "" if gumbel is None else f" {gumbel:g}"
        return f"{schedule}{scale}, `</s>` " + ("forbidden" if forbid_eos else "allowed")

    for (arm, task, steps, schedule, gumbel, forbid_eos), rows in groups.items():
        lines.append(
            f"| {arm} | {task} | {steps or ''} | {describe(schedule, gumbel, forbid_eos)} "
            f"| {len(rows)} "
            f"| {mean(rows, 'script_consistency'):.3f} | {mean(rows, 'distinct', '1'):.3f} "
            f"| {mean(rows, 'repetition'):.3f} | {mean(rows, 'longest_repeat'):.1f} |"
        )

    lines += ["", "## Samples", ""]
    for (arm, task, steps, schedule, gumbel, forbid_eos), rows in groups.items():
        head = f"### {arm.upper()} — {task}"
        if steps:
            head += f" — {steps} steps, {describe(schedule, gumbel, forbid_eos)}"
        lines += [head, ""]
        for row in rows:
            stats = row["stats"]
            lines.append(
                f"**#{row['prompt_index']}** — {len(row['tokens'])} tokens, "
                f"script {stats['script_consistency']:.2f}, rep {stats['repetition']:.2f}, "
                f"run {stats['longest_repeat']}"
            )
            if row["prompt_text"].strip():
                lines += ["", "prompt:", "", "```", row["prompt_text"].strip(), "```"]
            lines += ["", "```", row["text"].strip() or "(empty)", "```", ""]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
