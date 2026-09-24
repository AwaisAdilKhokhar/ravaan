#!/usr/bin/env python
"""Does a commit *rule* fix the diffusion arm's Urdu? Four decoders, one checkpoint (§4.4, §8.3).

A fluent reader read the published demo and reported the diffusion samples as worse Urdu than the
AR arm's, on a checkpoint that **wins on bits-per-byte** — 0.7646 against 0.7774. Session 36 took
that as a schedule question. It is not: measuring the traces the demo already ships shows the
diffusion arm assembled **47%** (`gumbel 2`) and **66%** (`random`) of its multi-piece words out
of order against the AR arm's **0%**, and echoed a bigram of its own prompt on 5/10 and 4/10
continuations against AR's 1/10. Both are the same mechanism. `sample_diffusion` commits three or
four positions per step **from independent marginals**, and a word in §7's 16k vocabulary is
often two or three pieces, so a word's middle gets written by a pass that never saw its start.
The AR factorization cannot make that error, which is why nothing in §8.3 was built to detect it.

So the question this file asks is whether the defect is in the **weights** or in the **commit
rule**, and it asks it by changing only the rule:

* ``parallel`` — what ships. The baseline, and it is *asserted token-for-token* against the real
  `sample_diffusion` for the same seed, because a re-implementation that drifted would make every
  comparison below a comparison with something that is not the release. Finding BQ's lesson.
* ``wordwise`` — commit a position only if the piece sampled there **opens a word**, or its left
  neighbour is already written. Words then grow left to right while *different* words still
  decode in parallel, so the canvas stays a canvas. Drives the out-of-order rate to 0 by
  construction, and the question is what it costs in passes and whether the text improves.
* ``blockN`` — semi-autoregressive. Decode the canvas in contiguous left-to-right blocks of N,
  full diffusion within a block, so block *k* is written against finished text rather than
  against masks. Targets the prompt echo as well as the joins, and gives up more parallelism.

⚠️ **Every variant costs forward passes, and forward passes are the project's headline.** Finding
BP's 17.9× is measured against the AR arm's one-pass-per-token; a rule that needs more passes
spends it. `forwards` is recorded per draw for exactly that reason and the summary leads on it —
a fix that reads better and decodes at AR speed has not fixed anything, it has become AR.

⚠️ **Temperature has never been swept.** Every A3/A4 sweep in this project ran at 0.9 and the
hosted demo runs at 1.0, so the one dial that most directly governs malformed pieces is the one
corner of §4.4's grid nobody has looked in. It is swept here as a factor. That is a **deviation
from the preregistered grid** — §4.4 preregisters steps × schedule — and is logged as one, in the
same way session 23 logged adding `gumbel` as a third schedule (Finding AR).

**This script decides nothing.** It writes `reports/decode_variants.jsonl` and a summary table;
`release_assets/generate.py`, both model cards and the demos are untouched. Finding BU's rule
stands — a decode default moves on a reader's verdict, and what this produces is the evidence a
reader should be shown, not a replacement for one.

    python -u scripts/decode_variants.py                 # the full grid, ~1 h on a 4060
    python -u scripts/decode_variants.py --probe         # one cell, to time it first
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

from scripts.demo_trace import PROMPTS  # noqa: E402

#: The wordhood lexicon. Not optional: the table's leading columns are computed from it, and every
#: conclusion this file reached on 2026-09-25 turned on them rather than on §8.3's three.
LEXICON = REPO / "reports/eval/urdu_lexicon.tsv.gz"

#: A3's optimum, held three times now (Findings AP, BG, BU). Overridable with `--steps` since
#: session 38, which needed the axis and reached it by reassigning this from a scratch script.
STEPS = 8
TOP_P = 0.95

#: The grid. `blockN` is spelled by its block width; two are run because the width trades the fix
#: against the passes it costs, and one width cannot show that trade.
VARIANTS = ("parallel", "wordwise", "block8", "block4")
SCHEDULES = (("gumbel", 2.0), ("random", 0.0))
TEMPERATURES = (0.7, 0.8, 0.9, 1.0)
#: Eight, not the demo's sixteen. This measures *rates* over 10 prompts — 80 draws a cell — rather
#: than selecting one draw to show, and a rate does not need the tail the selection rule needs.
DRAWS = 8

#: Passes per block for the semi-autoregressive variants, chosen so a 28–32 token canvas costs
#: about what `parallel` costs at `STEPS`: four blocks of 8 at 2 passes each is 8 passes. Without
#: that the comparison would be reading a pass budget as if it were a commit rule.
BLOCK_STEPS = 2
#: `wordwise` cannot always fill its quota — a step where few sampled pieces open a word commits
#: what it can and carries the rest — so it needs a ceiling rather than a fixed count. One pass
#: per masked position is the worst case and is exactly AR's cost, which is the right place to
#: give up: past it the variant has no speed claim left to defend.
MAX_PASSES_PER_MASK = 1.0


def word_start_table(sp, vocab_size: int, device: str) -> torch.Tensor:
    """``[vocab]`` bool — does this piece open a new word?

    SentencePiece marks a word opening with `▁`. Everything else continues the piece to its left,
    **including §7's byte-fallback `<0xNN>` pieces**, which is the behaviour `wordwise` wants: a
    character spread over three positions is the most extreme case of a unit that must be written
    in order, and Finding BT is the record of it rendering as `�` when it was not.

    Control and framing ids sit below the text range and are never sampled into the canvas here,
    but they are marked as openings rather than continuations so that a stray one can never make
    the position to its right ineligible forever.
    """
    flags = torch.ones(vocab_size, dtype=torch.bool)
    for token in range(vocab_size):
        piece = sp.id_to_piece(token)
        if piece and not piece.startswith("\u2581") and not piece.startswith("<"):
            flags[token] = False
        if piece.startswith("<0x"):
            flags[token] = False
    return flags.to(device)


def _score(schedule, gumbel, confidence, shape, device, generator, index, total):
    """A4's ranking, lifted verbatim from `sample_diffusion` so the variants share it.

    Including *which* branch draws from the generator and in what order — `random` consumes one
    `torch.rand`, `gumbel` with a positive scale consumes one, `confidence` consumes none. Get
    that wrong and `parallel` diverges from the shipped sampler on seed alone, which is what the
    assertion in :func:`decode` would then report as drift in the commit rule.
    """
    if schedule == "random":
        return torch.rand(shape, device=device, generator=generator)
    if schedule == "confidence":
        return confidence
    score = confidence.clamp_min(1e-20).log()
    scale = gumbel * (1.0 - (index + 1) / total)
    if scale > 0:
        draw = torch.rand(shape, device=device, generator=generator).clamp(1e-20, 1.0 - 1e-20)
        score = score + scale * -(-draw.log()).log()
    return score


@torch.no_grad()
def decode(arm, prompt, *, variant, schedule, gumbel, temperature, seed, forbid, device,
           word_start, verify=False) -> dict:
    """One draw under one commit rule. Returns the tokens, the passes it took, and the trace."""
    from ravaan_infer.sampling.decoding import SamplingConfig, build_generator, sample_ids
    from ravaan_infer.sampling.diffusion import sample_diffusion, unmask_counts

    model, mask_id = arm.model, arm.mask_id
    config = SamplingConfig(temperature=temperature, top_p=TOP_P)
    forbid_ids = tuple(dict.fromkeys((*(int(i) for i in forbid), int(mask_id))))
    generator = build_generator(device, seed)

    given = torch.tensor([prompt.tokens], dtype=torch.long, device=device)
    locked = torch.tensor([prompt.locked], dtype=torch.bool, device=device)
    tokens = torch.where(locked, given, torch.full_like(given, mask_id))
    masked = ~locked
    width = tokens.shape[1]
    positions = torch.arange(width, device=device).unsqueeze(0).expand_as(tokens).contiguous()

    commit_step = [-1] * width
    forwards = 0
    started = time.perf_counter()

    # Which positions this pass is allowed to look at. `parallel` and `wordwise` see the whole
    # canvas; the block variants see one window at a time, which is the whole of what makes them
    # semi-autoregressive.
    if variant.startswith("block"):
        span = int(variant[len("block"):])
        free = masked[0].nonzero().flatten().tolist()
        windows = [free[i:i + span] for i in range(0, len(free), span)]
    else:
        windows = [masked[0].nonzero().flatten().tolist()]

    for window in windows:
        if not window:
            continue
        scope = torch.zeros_like(masked)
        scope[0, window] = True
        steps = BLOCK_STEPS if variant.startswith("block") else STEPS
        counts = unmask_counts(len(window), steps)
        # `wordwise` can under-fill a pass, so the loop runs to completion rather than to a fixed
        # count, and the ceiling is the point at which it has become AR and has nothing left to
        # claim: one pass per outstanding position. `parallel` and the block variants never reach
        # either the extra passes or the ceiling — their quota sums to the window exactly.
        ceiling = int(len(window) * MAX_PASSES_PER_MASK) + steps
        index = passes = 0
        while bool((masked & scope).any()) and passes < ceiling:
            take = counts[index] if index < len(counts) else int((masked & scope).sum().item())
            index += 1
            if take <= 0:
                continue
            logits = model(tokens)
            forwards += 1
            passes += 1
            ids, confidence = sample_ids(logits, config, generator=generator, forbid=forbid_ids)
            score = _score(schedule, gumbel, confidence, tokens.shape, device, generator,
                           min(index - 1, len(counts) - 1), len(counts))

            allowed = masked & scope
            if variant == "wordwise":
                # A position may be written when the piece sampled there opens a word, or when
                # the position to its left is already written (or was given). Position 0 has no
                # left neighbour and is always anchored. This is the entire fix.
                opens = word_start[ids]
                left_written = torch.ones_like(masked)
                left_written[:, 1:] = ~masked[:, :-1]
                allowed = allowed & (opens | left_written)
                if not bool(allowed.any()):
                    # Nothing is anchored this pass. Fall back to the leftmost outstanding
                    # position, which is anchored by definition, rather than spin.
                    first = (masked & scope)[0].nonzero().flatten()[0]
                    allowed = torch.zeros_like(masked)
                    allowed[0, first] = True

            score = score.masked_fill(~allowed, float("-inf"))
            order = score.argsort(dim=-1, descending=True)
            rank = torch.empty_like(order)
            rank.scatter_(1, order, positions)
            commit = (rank < min(take, int(allowed.sum().item()))) & allowed
            tokens = torch.where(commit, ids, tokens)
            masked = masked & ~commit
            for position in commit[0].nonzero().flatten().tolist():
                commit_step[position] = forwards - 1

    elapsed = time.perf_counter() - started
    out = tokens[0].tolist()

    if int((tokens == mask_id).sum().item()):
        raise AssertionError(f"{variant} left the canvas masked after {forwards} passes")

    # The baseline must *be* the release, not resemble it. Checked on demand rather than every
    # draw because it costs a second decode, and drift is a property of the code, not the seed.
    if verify and variant == "parallel":
        reference = sample_diffusion(
            model, given, steps=STEPS, schedule=schedule, gumbel=gumbel, locked=locked,
            config=config, forbid=forbid, generator=build_generator(device, seed),
        )
        if reference.tokens[0].tolist() != out:
            raise AssertionError(
                "the `parallel` baseline no longer reproduces sample_diffusion — every variant "
                "below would be compared against a decoder the release does not ship. Re-sync "
                "decode() against ravaan_infer/sampling/diffusion.py."
            )

    return {"tokens": out, "commit_step": commit_step, "forwards": forwards,
            "seconds": round(elapsed, 4)}


@torch.no_grad()
def decode_ar(arm, prompt, *, temperature, seed, budget, forbid, device) -> dict:
    """The AR arm at the same temperature, as the reference row. Shipped sampler, unchanged."""
    from ravaan_infer.sampling.ar import sample_ar
    from ravaan_infer.sampling.decoding import SamplingConfig, build_generator

    config = SamplingConfig(temperature=temperature, top_p=TOP_P)
    width = len(prompt.tokens)
    started = time.perf_counter()
    out = sample_ar(arm.model, torch.tensor([prompt.tokens], dtype=torch.long, device=device),
                    max_new_tokens=budget, config=config, forbid=forbid, eos_id=arm.eos_id,
                    generator=build_generator(device, seed))
    elapsed = time.perf_counter() - started
    length = int(out.lengths[0])
    return {"tokens": out.tokens[0, :length].tolist(),
            "commit_step": [-1] * width + list(range(length - width)),
            "forwards": out.forwards, "seconds": round(elapsed, 4)}



def reading_view(path: Path, temperature: float, seed: int) -> str:
    """Every decoder on one prompt at one seed, laid out to be *read* rather than scored.

    This is the artefact that can actually settle the question, and the table above is not. Every
    number in this file is a proxy standing in for a fluent reader, the proxies have already been
    caught ranking the two schedules in the reader's opposite order once, and adding two more
    proxies does not retire the risk — it only makes it visible. So the grid ends in prose, one
    prompt per block, same seed down the column so a difference between two rows is the commit
    rule and nothing else.

    **Not filtered and not ranked.** `scripts/demo_trace.py` selects the best of sixteen seeds
    under a stated rule because a demo page is a demo page; this is evidence, so it shows a fixed
    seed and whatever that seed produced, including the bad ones.
    """
    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    order = ["ar"] + [f"{v}/{s}" for v in VARIANTS for s, _ in SCHEDULES]
    out = [
        f"# Decode variants — read, not scored (temperature {temperature}, seed {seed})",
        "",
        "One prompt per block, every decoder at the same seed. The prefix is the first words of "
        "each line; everything after it is what that decoder wrote. `fwd` is forward passes — "
        "the AR row is the cost the diffusion rows are claiming to beat.",
        "",
    ]
    for spec in PROMPTS:
        picked = {
            (row["variant"] if row["variant"] == "ar" else f"{row['variant']}/{row['schedule']}"):
            row
            for row in rows
            if row["prompt"] == spec["id"]
            and row["temperature"] == temperature
            and row["seed"] == seed
        }
        out += [f"## {spec['id']} — {spec['gloss']}", "",
                f"> {spec['prefix']}", ""]
        for label in order:
            row = picked.get(label)
            if row is None:
                continue
            marks = row["commit_order"]
            out += [
                f"**{label}** — {row['forwards']} fwd · "
                f"out-of-order {marks['out_of_order']}/{marks['multi_piece']} · "
                f"echo {'yes' if row['echo']['echoed'] else 'no'} · "
                f"distinct-1 {row['stats']['distinct']['1']:.2f}",
                "",
                "> " + row["written"].replace("\n", " ").strip(),
                "",
            ]
    return "\n".join(out)


def summarize(path: Path) -> str:
    """The grid as a table, led by the column that turned out to decide it.

    Ordered so the trade is readable in one pass: `forwards` is what a fix costs, `bad` and `echo`
    are what it buys, and distinct-1 and `longest_repeat` are §8.3's numbers carried alongside so a
    variant that fixes the joins by degenerating into a loop is visible rather than flattering.
    **`ooo` on a cell with few multi-piece words says little** — `n=` is printed next to it because
    a rate over three words is not a rate, and a rule that avoids multi-piece words rather than
    ordering them would otherwise read as a perfect score.

    ⚠️ **`ooo` led this table when it was written and no longer does.** It is a share of
    multi-piece words written out of left-to-right order, and it counts a tie — two pieces of one
    word committed on the *same* pass — as in order, which is defensible and is a door. `block8`
    went through it: windows of eight at two passes each commit four adjacent positions at once,
    which halved `ooo` and tripled `tied`, and the Urdu got worse. So `tied` is printed beside
    `ooo` always, and the leading column is now `bad` — the share of draws carrying a word that is
    not a word, invented or fragmented, measured against the corpus rather than against the string.
    Real held-out Urdu scores 0.4% on `inv` and that, not zero, is the floor.
    """
    import statistics as st
    from collections import defaultdict

    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    cells = defaultdict(list)
    for row in rows:
        label = row["variant"] if row["variant"] == "ar" else (
            # The scale is part of the identity: Finding CE sweeps six of them and without this
            # they would pool into one row and average the dial away.
            f"{row['variant']}/{row['schedule']}"
            + (f" {row['gumbel']:g}" if row.get("gumbel") is not None else "")
        )
        cells[(label, row["temperature"])].append(row)

    out = [
        f"{'decoder':<18}{'temp':>5}{'fwd':>6}{'bad':>6}{'inv':>6}{'chars':>6}"
        f"{'ooo':>6}{'tied':>6}{'n':>5}{'echo':>6}{'d1':>7}{'lrep':>6}{'words':>7}"
    ]
    out.append("-" * len(out[0]))
    for (label, temperature) in sorted(cells, key=lambda k: (k[0] != "ar", k[0], k[1])):
        draws = cells[(label, temperature)]
        multi = sum(d["commit_order"]["multi_piece"] for d in draws)
        disordered = sum(d["commit_order"]["out_of_order"] for d in draws)
        pairs = sum(d["commit_order"].get("pairs", 0) for d in draws)
        tied = sum(d["commit_order"].get("tied", 0) for d in draws)
        # `fabrication` is absent from rows written before 2026-09-25. Those cells print `-`
        # rather than a clean sweep on a file that was never scored.
        scored = [d for d in draws if "fabrication" in d]
        words = sum(d["fabrication"]["words"] for d in scored)
        invented = sum(d["fabrication"]["fabricated"] for d in scored)
        affected = sum(
            1 for d in scored
            if d["fabrication"]["fabricated"] or d["fabrication"]["fragments"]
        )
        letters = (
            sum(d["fabrication"]["characters"] * d["fabrication"]["words"] for d in scored) / words
            if words
            else 0.0
        )
        out.append(
            f"{label:<18}{temperature:>5}"
            f"{st.mean(d['forwards'] for d in draws):>6.1f}"
            + (f"{affected / len(scored):>6.0%}" if scored else f"{'-':>6}")
            + (f"{invented / words:>6.1%}" if words else f"{'-':>6}")
            + (f"{letters:>6.2f}" if words else f"{'-':>6}")
            + f"{(disordered / multi if multi else 0.0):>6.0%}"
            + (f"{tied / pairs:>6.0%}" if pairs else f"{'-':>6}")
            + f"{multi:>5}"
            f"{st.mean(d['echo']['echoed'] for d in draws):>6.0%}"
            f"{st.mean(d['stats']['distinct']['1'] for d in draws):>7.3f}"
            f"{st.mean(d['stats']['longest_repeat'] for d in draws):>6.1f}"
            f"{st.mean(d['stats']['words'] for d in draws):>7.1f}"
        )
    return "\n".join(out)


def main() -> int:
    global STEPS, BLOCK_STEPS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--release", type=Path, default=Path("D:/ravaan-release"))
    ap.add_argument("--out", type=Path, default=REPO / "reports" / "decode_variants.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    # Repeatable, not `nargs="+"` — the same shape `scripts/sample.py` uses for §4.4's axes, and
    # the one session 20 got wrong once in a way that cost a 4.6 h pass.
    ap.add_argument("--temperature", type=float, action="append",
                    help=f"repeatable; defaults to {TEMPERATURES}")
    ap.add_argument("--variant", action="append", choices=list(VARIANTS),
                    help=f"repeatable; defaults to {VARIANTS}")
    # Session 38 reached both of these by reassigning module globals from a scratch script, which
    # is not a thing anyone else can re-run. They are flags now. `--gumbel` in particular is the
    # axis nobody had swept: every sweep before it ran s = 1 and s = 2, and the interior of the
    # family — whose endpoints are `confidence` and `random` — is free, eight passes at any scale.
    ap.add_argument("--steps", type=int, default=STEPS,
                    help=f"A3's denoising steps for the un-windowed variants (default {STEPS})")
    ap.add_argument("--block-steps", type=int, default=BLOCK_STEPS,
                    help=f"passes spent inside one block (default {BLOCK_STEPS})")
    ap.add_argument("--gumbel", type=float, action="append",
                    help="repeatable gumbel scale; defaults to the two in SCHEDULES")
    ap.add_argument("--probe", action="store_true",
                    help="one prompt, one seed, every cell — to time the grid before running it")
    ap.add_argument("--summarize", action="store_true",
                    help="read --out and print the table, decoding nothing")
    ap.add_argument("--read", nargs=2, metavar=("TEMPERATURE", "SEED"),
                    help="write the side-by-side reading view at one temperature and seed")
    args = ap.parse_args()
    STEPS, BLOCK_STEPS = args.steps, args.block_steps

    if args.read:
        temperature, seed = float(args.read[0]), int(args.read[1])
        page = reading_view(args.out, temperature, seed)
        report = args.out.with_name(args.out.stem + "_read.md")
        report.write_text(page, encoding="utf-8")
        print(f"wrote {report}", file=sys.stderr)
        return 0

    if args.summarize:
        table = summarize(args.out)
        print(table)
        report = args.out.with_suffix(".md")
        report.write_text(
            "# Decode variants — does a commit rule fix the diffusion arm's Urdu?\n\n"
            "See `scripts/decode_variants.py` for what each row is and what it cost.\n\n"
            "```\n" + table + "\n```\n", encoding="utf-8")
        print(f"\nwrote {report}", file=sys.stderr)
        return 0

    sys.path.insert(0, str(args.release / "ravaan-diff-70m"))
    import sentencepiece as spm
    from ravaan_infer.loader import load
    from ravaan_infer.sampling import prompts as prompt_builders

    from ravaan.evaluation.generation import (
        GenerationStats,
        commit_order,
        prefix_echo,
        same_pass,
    )
    from ravaan.evaluation.lexicon import Lexicon

    if not LEXICON.exists():
        raise SystemExit(
            f"{LEXICON.relative_to(REPO)} is missing — run `python scripts/lexicon.py --control`. "
            "Every conclusion in this file's table turned on the wordhood column, so it does not "
            "run without one."
        )
    lexicon = Lexicon.load(LEXICON)
    print(f"lexicon: {len(lexicon):,} word skeletons", file=sys.stderr)

    device = args.device
    arms = {"diff": load(args.release / "ravaan-diff-70m", device=device),
            "ar": load(args.release / "ravaan-ar-70m", device=device)}
    sp = spm.SentencePieceProcessor(model_file=str(arms["diff"].tokenizer_path))
    first_text_id = len(arms["diff"].framing.PIECES) + 4
    word_start = word_start_table(sp, sp.get_piece_size(), device)

    specs = PROMPTS[:1] if args.probe else PROMPTS
    draws = 1 if args.probe else args.draws
    temperatures = tuple(args.temperature) if args.temperature else TEMPERATURES
    variants = tuple(args.variant) if args.variant else VARIANTS
    # `--gumbel` replaces the gumbel half of SCHEDULES and leaves `random` in place, because
    # `random` is the scale's limit rather than a point on it — Finding CE is the sweep of the
    # interior, and it needs the endpoint in the same table to be read as one dial.
    schedules = (
        tuple(("gumbel", scale) for scale in args.gumbel) + (("random", 0.0),)
        if args.gumbel else SCHEDULES
    )
    print(f"{len(specs)} prompts x {draws} seeds x {len(variants)} variants x "
          f"{len(schedules)} schedules x {len(temperatures)} temperatures", file=sys.stderr)

    rows, verified = [], set()
    started = time.perf_counter()
    for spec in specs:
        prefix_ids = sp.encode(spec["prefix"])
        diff_prompt = prompt_builders.lm(
            arms["diff"].framing, "diff", prefix=prefix_ids,
            length=len(prefix_ids) + 1 + spec["tokens"], mask_id=arms["diff"].mask_id)
        ar_prompt = prompt_builders.lm(arms["ar"].framing, "ar", prefix=prefix_ids)

        for temperature in temperatures:
            cells = [("ar", "ar", 0.0)] + [
                (variant, schedule, gumbel)
                for variant in variants for schedule, gumbel in schedules
            ]
            for variant, schedule, gumbel in cells:
                for offset in range(draws):
                    seed = args.seed + offset
                    if variant == "ar":
                        draw = decode_ar(arms["ar"], ar_prompt, temperature=temperature,
                                         seed=seed, budget=spec["tokens"],
                                         forbid=arms["ar"].forbidden, device=device)
                    else:
                        key = (variant, schedule)
                        draw = decode(
                            arms["diff"], diff_prompt, variant=variant, schedule=schedule,
                            gumbel=gumbel, temperature=temperature, seed=seed,
                            # `</s>` is forbidden on a fixed-width canvas — Finding AO.
                            forbid=arms["diff"].forbidden + (arms["diff"].eos_id,),
                            device=device, word_start=word_start,
                            verify=key not in verified)
                        verified.add(key)

                    pieces = [None if t < first_text_id
                              else sp.id_to_piece(t).replace("\u2581", " ")
                              for t in draw["tokens"]]
                    text = sp.decode([t for t in draw["tokens"] if t >= first_text_id])
                    written = text[len(spec["prefix"]):]
                    rows.append({
                        "prompt": spec["id"], "variant": variant, "schedule": schedule,
                        "gumbel": gumbel if schedule == "gumbel" else None,
                        "temperature": temperature, "seed": seed,
                        "forwards": draw["forwards"], "seconds": draw["seconds"],
                        "text": text, "written": written,
                        "stats": GenerationStats.of(written).to_dict(),
                        "commit_order": commit_order(pieces, draw["commit_step"]),
                        "same_pass": same_pass(pieces, draw["commit_step"]),
                        "echo": prefix_echo(spec["prefix"], written),
                        "fabrication": lexicon.measure(written).to_dict(),
                    })
            print(f"  {spec['id']:<11} t={temperature}  {len(rows)} draws  "
                  f"{time.perf_counter() - started:.0f}s", file=sys.stderr, flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nwrote {args.out} — {len(rows)} draws in "
          f"{time.perf_counter() - started:.0f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
