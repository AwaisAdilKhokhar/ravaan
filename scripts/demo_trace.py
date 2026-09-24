#!/usr/bin/env python
"""Generate short Urdu samples and record *how* each arm wrote them (PRD §4.1, §8).

Every demo this project has shipped so far prints finished text. Finished text is the one thing
that cannot show the difference between the two arms, because the difference is not in the output
— it is in the order the output was written. The AR arm emits token 1, then token 2, one forward
pass each. The diffusion arm starts from a canvas that is `<mask>` everywhere and commits a
*subset* of positions per pass, chosen by confidence, in whatever order the model is surest about;
eight passes later there are no masks left. Same corpus, same 70M backbone, same tokenizer,
different factorization — and you can watch it happen.

So this writes a **trace**: for every position, which step committed it and how confident the
model was. `reports/demo_trace.json` is that, plus the per-position SentencePiece pieces, so a
page can replay the decode rather than describe it.

**The diffusion arm is traced twice, under both of §4.4's surviving unmasking schedules.** Same
checkpoint, same seed, same eight steps — only the order it commits positions in differs, which
is exactly the quantity this page draws. Finding BU is the reason: at 64 epochs `random` ties
`gumbel 2` on script consistency and leads distinct-1, so §8.3's metrics no longer choose between
them, and animating one alone would assert a default the measurements stopped supporting. See
:data:`TRACKS`.

**The traced loop is asserted equal to the shipped one.** The diffusion trace is produced by a
re-implementation of `ravaan_infer.sampling.diffusion.sample_diffusion`'s commit loop — the
library function returns only the finished tensor and has no hook to record intermediate state.
A re-implementation that drifted would make the animation a cartoon of the decoder rather than
the decoder, so every trace is checked token-for-token against what the real sampler returns for
the same seed, and a mismatch is a hard failure rather than a warning. See `_trace_diffusion`.

**The models are the published ones, loaded from the release directory.** Not the training
pickles they were stripped from: `ravaan_infer/` + `model.safetensors` is what someone who runs
`pip install` and downloads from the Hub gets, so it is what the demo should be showing.

**The prompts are hand-written, not held-out corpus, and the page has to say so.** The existing
demo (`scripts/demo_page.py`) continues validation-split prefixes, which is the right thing for
judging the model and the wrong thing for a page someone reads in ten seconds: those prefixes are
encyclopaedic paragraphs. These are short simple sentences of the kind a reader can take in whole.
Nothing about a hand-written prefix is contaminated — the model never trained on these strings as
such — but a hand-written prefix is chosen by someone who knows what the model does well, and that
is a selection effect the page must disclose rather than absorb.

**Selection is mechanical and the pool ships.** A 70M model on a 28-token canvas degenerates on
some seeds and not others — at this size that is the honest state of the art, not a bug to hide.
So each prompt is drawn at :data:`DRAWS` seeds per arm, a filter removes draws that are unshowable
for a stated reason, and :func:`_rank` picks one of what is left. The rule is the same for both
arms and applied independently to each; every draw is written to `reports/demo_trace_pool.json`
with the reason it was rejected, so anyone can check what the rule discarded. Cherry-picking a
demo is normal; doing it silently is not, which is the line `demo_page.py` already took.

**One filter clause is about rendering, not quality, and is worth naming.** §7's tokenizer has
byte fallback, so a character outside the 16k vocabulary arrives as two or three `<0xNN>` pieces
at two or three *positions*. A page that reveals one position at a time cannot draw a third of a
character, and a diffusion decode can commit those bytes out of order, which renders as `�`
until the run completes. Rather than special-case the animation, draws containing byte-fallback
pieces are rejected — which costs little, since on this checkpoint they are also the draws that
had stopped writing Urdu.

    python scripts/demo_trace.py --release D:/ravaan-release   # -> reports/demo_trace.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

#: Short Urdu prefixes, each a plain sentence opening rather than a paragraph, with a gloss for a
#: reader who does not read Urdu. `tokens` is the continuation budget — the diffusion canvas width
#: and the AR token cap — kept small so a sample is read rather than skimmed.
PROMPTS = (
    {
        "id": "weather",
        "prefix": "آج موسم بہت",
        "gloss": "Today the weather is very…",
        "topic": "everyday speech",
        "tokens": 28,
    },
    {
        "id": "economy",
        "prefix": "ملک کی معیشت میں بہتری کے لیے",
        "gloss": "In order to improve the country's economy…",
        "topic": "news register",
        "tokens": 32,
    },
    {
        "id": "address",
        "prefix": "وزیر اعظم نے اپنے خطاب میں کہا کہ",
        "gloss": "In his address the Prime Minister said that…",
        "topic": "reported speech",
        "tokens": 32,
    },
    {
        "id": "tea",
        "prefix": "چائے پینے کے بعد وہ",
        "gloss": "After drinking tea, he/she…",
        "topic": "narrative",
        "tokens": 28,
    },
    {
        "id": "school",
        "prefix": "بچے صبح سویرے اسکول",
        "gloss": "Early in the morning the children … school",
        "topic": "everyday description",
        "tokens": 28,
    },
    {
        "id": "health",
        "prefix": "ڈاکٹروں کا کہنا ہے کہ صحت مند رہنے کے لیے",
        "gloss": "Doctors say that in order to stay healthy…",
        "topic": "health reporting",
        "tokens": 32,
    },
    {
        "id": "book",
        "prefix": "یہ کتاب اردو ادب کی",
        "gloss": "This book, of Urdu literature,…",
        "topic": "literary register",
        "tokens": 32,
    },
    {
        "id": "city",
        "prefix": "لاہور شہر اپنی تاریخ اور",
        "gloss": "The city of Lahore, for its history and…",
        "topic": "descriptive prose",
        "tokens": 32,
    },
    {
        "id": "cricket",
        "prefix": "کرکٹ کے میدان میں کھلاڑیوں نے",
        "gloss": "On the cricket field, the players…",
        "topic": "sport",
        "tokens": 28,
    },
    {
        "id": "technology",
        "prefix": "نئی ٹیکنالوجی نے لوگوں کی زندگی",
        "gloss": "New technology has … people's lives",
        "topic": "feature writing",
        "tokens": 32,
    },
)

#: The published decoder settings, which are part of the model rather than preferences — each was
#: measured (Findings BG, AR, AO) and each is named on the model card. Changing one here would
#: make the page a demo of a decoder the release does not ship.
STEPS = 8
SCHEDULE = "gumbel"
GUMBEL = 2.0
TEMPERATURE = 1.0
TOP_P = 0.95

#: What the page animates: the AR arm, and the *same* diffusion checkpoint decoded under both
#: of §4.4's surviving A4 schedules. Finding BU is why there are two — at 64 epochs `random`
#: ties `gumbel 2` on script consistency and leads distinct-1, so §8.3 no longer picks between
#: them and showing one would assert a default the measurements do not support. The commit order
#: is the one thing this page exists to draw, and the schedule *is* the commit order.
TRACKS = (
    ("diff", "gumbel", GUMBEL),
    ("diff_random", "random", 0.0),
)

#: Seeds drawn per prompt per arm before the filter and the selection rule run. Sixteen is enough
#: that a prompt which degenerates on every draw is visibly a property of the prompt rather than
#: of the seed — and that case should stay in the pool and stay off the page.
DRAWS = 16


def _pieces(sp, ids: list[int], first_text_id: int) -> list[str | None]:
    """Per-position display text. None where the position is scaffolding, not output.

    Rendering piece by piece rather than decoding the whole row is what lets the page reveal one
    position at a time. SentencePiece's `▁` is a word boundary, so it becomes the leading space it
    stands for; positions below `first_text_id` are framing and control pieces, which the reader
    should never see and which `generate.py` drops for the same reason.
    """
    out: list[str | None] = []
    for token in ids:
        if token < first_text_id:
            out.append(None)
        else:
            out.append(sp.id_to_piece(token).replace("\u2581", " "))
    return out


@torch.no_grad()
def _trace_diffusion(
    arm, prompt, *, seed: int, forbid, device: str,
    schedule: str = SCHEDULE, gumbel: float = GUMBEL,
) -> dict:
    """Run the absorbing-state decode and record every commit. Asserted against the real sampler.

    This is `sample_diffusion`'s loop with two lines added to remember what each step did. It is
    deliberately a copy and not a refactor of the library: the released `ravaan_infer/` is a
    vendored artifact that people have already downloaded, and a demo is not a reason to change
    what a published package does. The cost of copying is drift, and the assertion at the bottom
    is what pays it.
    """
    from ravaan_infer.sampling.decoding import build_generator, sample_ids
    from ravaan_infer.sampling.diffusion import sample_diffusion, unmask_counts

    model = arm.model
    mask_id = arm.mask_id
    tokens = torch.tensor([prompt.tokens], dtype=torch.long, device=device)
    locked = torch.tensor([prompt.locked], dtype=torch.bool, device=device)
    tokens = torch.where(locked, tokens, torch.full_like(tokens, mask_id))

    from ravaan_infer.sampling.decoding import SamplingConfig

    config = SamplingConfig(temperature=TEMPERATURE, top_p=TOP_P)
    forbid_ids = tuple(dict.fromkeys((*(int(i) for i in forbid), int(mask_id))))
    generator = build_generator(device, seed)

    masked = ~locked
    counts = unmask_counts(int(masked.sum(dim=-1).max().item()), STEPS)
    positions = torch.arange(tokens.shape[1], device=device).unsqueeze(0).expand_as(tokens)
    positions = positions.contiguous()

    #: commit_step[i] is the step that wrote position i; -1 means it was given, not written.
    commit_step = [-1] * tokens.shape[1]
    commit_conf = [0.0] * tokens.shape[1]
    steps_log: list[dict] = []
    forwards = 0
    started = time.perf_counter()

    for index, take in enumerate(counts):
        if take <= 0 or not bool(masked.any()):
            continue
        logits = model(tokens)
        forwards += 1
        ids, confidence = sample_ids(logits, config, generator=generator, forbid=forbid_ids)

        # Mirrors `sample_diffusion`'s three branches, including which of them draw from the
        # generator and in what order — `random` consumes one `torch.rand` where `gumbel` with a
        # positive scale consumes one and `confidence` consumes none. Get that wrong and the two
        # decoders diverge on seed alone, which the assertion below would report as drift.
        if schedule == "random":
            score = torch.rand(tokens.shape, device=device, generator=generator)
        elif schedule == "confidence":
            score = confidence
        else:
            score = confidence.clamp_min(1e-20).log()
            scale = gumbel * (1.0 - (index + 1) / len(counts))
            if scale > 0:
                draw = torch.rand(tokens.shape, device=device, generator=generator).clamp(
                    1e-20, 1.0 - 1e-20
                )
                score = score + scale * -(-draw.log()).log()
        score = score.masked_fill(~masked, float("-inf"))

        order = score.argsort(dim=-1, descending=True)
        rank = torch.empty_like(order)
        rank.scatter_(1, order, positions)
        commit = (rank < take) & masked
        tokens = torch.where(commit, ids, tokens)
        masked = masked & ~commit

        wrote = commit[0].nonzero().flatten().tolist()
        for position in wrote:
            commit_step[position] = len(steps_log)
            commit_conf[position] = round(float(confidence[0, position]), 4)
        steps_log.append({"committed": wrote, "remaining": int(masked.sum().item())})

    elapsed = time.perf_counter() - started
    traced = tokens[0].tolist()

    # The whole claim of this file: what the animation replays is what the shipped sampler does.
    reference = sample_diffusion(
        model,
        torch.tensor([prompt.tokens], dtype=torch.long, device=device),
        steps=STEPS,
        schedule=schedule,
        gumbel=gumbel,
        locked=torch.tensor([prompt.locked], dtype=torch.bool, device=device),
        config=config,
        forbid=forbid,
        generator=build_generator(device, seed),
    )
    if reference.tokens[0].tolist() != traced:
        raise AssertionError(
            "the traced diffusion loop no longer reproduces sample_diffusion — the animation "
            "would be showing a decoder the release does not ship. Re-sync _trace_diffusion "
            "against ravaan_infer/sampling/diffusion.py before rebuilding the page."
        )

    return {
        "tokens": traced,
        "commit_step": commit_step,
        "commit_conf": commit_conf,
        "steps": steps_log,
        "forwards": forwards,
        "seconds": round(elapsed, 4),
        "schedule": schedule,
        "gumbel": gumbel if schedule == "gumbel" else None,
    }


def _trace_ar(arm, prompt, *, seed: int, budget: int, forbid, device: str) -> dict:
    """The AR decode. Tracing it needs no re-implementation — step *i* writes position *i*.

    Run through the shipped sampler unchanged, then read the order off the result, because for a
    left-to-right factorization the order is not a fact that has to be recorded: it is the
    definition. `lengths` is what says where an EOS stopped the row.
    """
    from ravaan_infer.sampling.ar import sample_ar
    from ravaan_infer.sampling.decoding import SamplingConfig, build_generator

    config = SamplingConfig(temperature=TEMPERATURE, top_p=TOP_P)
    width = len(prompt.tokens)
    started = time.perf_counter()
    out = sample_ar(
        arm.model,
        torch.tensor([prompt.tokens], dtype=torch.long, device=device),
        max_new_tokens=budget,
        config=config,
        forbid=forbid,
        eos_id=arm.eos_id,
        generator=build_generator(device, seed),
    )
    elapsed = time.perf_counter() - started

    length = int(out.lengths[0])
    tokens = out.tokens[0, :length].tolist()
    commit_step = [-1] * width + list(range(length - width))
    return {
        "tokens": tokens,
        "commit_step": commit_step,
        "commit_conf": [0.0] * length,
        "forwards": out.forwards,
        "seconds": round(elapsed, 4),
        "stop": out.detail.get("stop"),
    }


#: A draw must clear all of these to be showable. Each is a stated reason, not a judgement of the
#: text: a reader can disagree with the thresholds and re-rank the pool, which is why it ships.
MIN_WORDS = 12
MIN_SCRIPT = 0.95
MAX_LONGEST_REPEAT = 4
#: distinct-1 is the type/token ratio, and it is the clause that catches the failure the others
#: miss: a draw that sprays one word non-contiguously — `کہیں، کہیں، کہیں` — has a longest run of
#: 1 and a perfect distinct-2, and is still unreadable. On this pool the threshold is not a close
#: call: the draws that fail it sit at 0.61 and the ones that pass start at 0.74.
MIN_DISTINCT1 = 0.70
#: Three or more punctuation marks in a row. A canvas that has run out of things to say fills the
#: rest of itself with `،،،،` — which every word-based metric above scores as clean, because the
#: marks attach to whitespace tokens and make them *look* distinct.
PUNCT_RUN = re.compile(r"[،؛؟۔.,;:!?…–—\"'()‘’“”]{3,}")


def _reject(draw: dict) -> str | None:
    """Why this draw cannot be shown, or None. See the module note on byte fallback."""
    stats = draw["stats"]
    if any(p is not None and p.startswith("<0x") for p in draw["pieces"]):
        return "byte-fallback pieces — one character over several positions, unrenderable"
    if stats["words"] < MIN_WORDS:
        return f"{stats['words']} words — under the {MIN_WORDS} a reader can judge"
    if stats["script_consistency"] < MIN_SCRIPT:
        return f"script consistency {stats['script_consistency']:.2f} — stopped writing Urdu"
    if stats["longest_repeat"] > MAX_LONGEST_REPEAT:
        return f"longest repeated run {stats['longest_repeat']} words — a clause on a loop"
    if stats["distinct"]["1"] < MIN_DISTINCT1:
        return f"distinct-1 {stats['distinct']['1']:.2f} — one word sprayed across the canvas"
    if PUNCT_RUN.search(draw["text"]):
        return "a run of punctuation — the canvas ran out of words before it ran out of room"
    return None


def _rank(draw: dict) -> tuple:
    """The selection rule, in one place so it can be quoted on the page verbatim.

    **§8.3's repetition rate is the wrong lead term at this length.** It is `1 - distinct-4` over
    whitespace words, and a 20-word continuation has 17 four-grams, so it reads 0.000 for almost
    every draw — including ones that repeat a *phrase* twice. What separates draws here is
    `longest_repeat`, which leads, and then distinct-1, the type/token ratio, which is the order
    that moves at all on 20 words. Distinct-2 and the seed break the remaining ties, so the rule
    is a total order and the same pool always yields the same choice.
    """
    stats = draw["stats"]
    return (
        stats["longest_repeat"],
        -stats["distinct"]["1"],
        -stats["distinct"]["2"],
        draw["seed"],
    )


def _note(name: str, record: dict, draws: dict) -> str:
    """One arm's line in the progress log: what the rule chose, and out of how much."""
    draw = record[name]
    if draw is None:
        return f"{name} — all {DRAWS} rejected"
    kept = sum(1 for d in draws[name] if d["rejected"] is None)
    return (
        f"{name} seed {draw['seed']} run {draw['stats']['longest_repeat']} "
        f"({kept}/{DRAWS} kept, {draw['forwards']} passes, {draw['seconds']:.2f}s)"
    )


def build(release: Path, device: str, base_seed: int) -> tuple[dict, dict]:
    sys.path.insert(0, str(release / "ravaan-diff-70m"))
    import sentencepiece as spm
    from ravaan_infer.loader import load
    from ravaan_infer.sampling import prompts as prompt_builders

    from ravaan.evaluation.generation import GenerationStats

    arms = {
        "diff": load(release / "ravaan-diff-70m", device=device),
        "ar": load(release / "ravaan-ar-70m", device=device),
    }
    sp = spm.SentencePieceProcessor(model_file=str(arms["diff"].tokenizer_path))
    # Framing pieces and the four control ids are scaffolding; text starts above them.
    first_text_id = len(arms["diff"].framing.PIECES) + 4
    for arm in arms.values():
        print(arm.describe(), file=sys.stderr)
    print(f"{DRAWS} draws per prompt per arm, seeds {base_seed}..{base_seed + DRAWS - 1}\n",
          file=sys.stderr)

    samples, pool = [], []
    for spec in PROMPTS:
        prefix_ids = sp.encode(spec["prefix"])
        record = {
            "id": spec["id"],
            "prefix": spec["prefix"],
            "gloss": spec["gloss"],
            "topic": spec["topic"],
            "prefix_tokens": len(prefix_ids),
            "budget": spec["tokens"],
        }

        diff_arm, ar_arm = arms["diff"], arms["ar"]
        diff_prompt = prompt_builders.lm(
            diff_arm.framing,
            "diff",
            prefix=prefix_ids,
            length=len(prefix_ids) + 1 + spec["tokens"],
            mask_id=diff_arm.mask_id,
        )
        ar_prompt = prompt_builders.lm(ar_arm.framing, "ar", prefix=prefix_ids)

        names = [name for name, _, _ in TRACKS] + ["ar"]
        draws: dict[str, list[dict]] = {name: [] for name in names}
        for offset in range(DRAWS):
            seed = base_seed + offset
            # `</s>` is forbidden for the diffusion arm only: on a fixed-width canvas it is not a
            # stop signal, it is a token that wins 47% of first commits (Finding AO).
            # Both schedules run from the same seed, so a difference between the two panels is
            # the commit order and nothing else.
            traced = [
                (
                    name,
                    _trace_diffusion(
                        diff_arm,
                        diff_prompt,
                        seed=seed,
                        forbid=diff_arm.forbidden + (diff_arm.eos_id,),
                        device=device,
                        schedule=schedule,
                        gumbel=gumbel,
                    ),
                )
                for name, schedule, gumbel in TRACKS
            ]
            ar = _trace_ar(
                ar_arm,
                ar_prompt,
                seed=seed,
                budget=spec["tokens"],
                forbid=ar_arm.forbidden,
                device=device,
            )
            for name, draw in (*traced, ("ar", ar)):
                draw["seed"] = seed
                draw["pieces"] = _pieces(sp, draw["tokens"], first_text_id)
                draw["text"] = sp.decode([t for t in draw["tokens"] if t >= first_text_id])
                # Scored on the continuation alone. Scoring the whole row would credit both arms
                # for the prefix they were handed, and the prefix is a third of a 28-token canvas.
                written = draw["text"][len(spec["prefix"]):]
                draw["stats"] = GenerationStats.of(written).to_dict()
                draw["rejected"] = _reject(draw)
                draws[name].append(draw)

        shown = True
        for name in names:
            eligible = [d for d in draws[name] if d["rejected"] is None]
            # A prompt on which every draw of either arm is rejected stays in the pool and off
            # the page — that is the case the filter exists to make visible rather than to paper
            # over by lowering a threshold until something passes.
            record[name] = min(eligible, key=_rank) if eligible else None
            shown = shown and bool(eligible)
            record[f"{name}_pool"] = [
                {
                    "seed": d["seed"],
                    "text": d["text"],
                    "stats": d["stats"],
                    "rejected": d["rejected"],
                }
                for d in sorted(draws[name], key=lambda d: (d["rejected"] is not None, _rank(d)))
            ]

        print(
            f"  {spec['id']:<11} "
            + "  ".join(f"{_note(name, record, draws):<44}" for name in names),
            file=sys.stderr,
        )
        pool.append({"id": spec["id"], "prefix": spec["prefix"], "shown": shown,
                     **{name: record[f"{name}_pool"] for name in names}})
        if shown:
            samples.append(record)
        else:
            print(f"  {'':<11} ^ dropped from the page — see the pool", file=sys.stderr)

    meta = {
        "base_seed": base_seed,
        "draws": DRAWS,
        "device": device,
        "steps": STEPS,
        "schedule": SCHEDULE,
        "gumbel": GUMBEL,
        "tracks": [
            {"name": name, "schedule": schedule, "gumbel": gumbel if schedule == "gumbel" else None}
            for name, schedule, gumbel in TRACKS
        ],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "diff_release": arms["diff"].release,
        "ar_release": arms["ar"].release,
        "prompt_source": "hand-written, not held-out corpus",
        "selection": "lowest §8.3 repetition rate of DRAWS seeds; ties by longest_repeat, "
                     "then seed. Applied independently to each arm.",
    }
    return {"meta": meta, "samples": samples}, {"meta": meta, "pool": pool}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--release", type=Path, default=Path("D:/ravaan-release"))
    ap.add_argument("--out", type=Path, default=REPO / "reports" / "demo_trace.json")
    ap.add_argument("--seed", type=int, default=0, help="first of the DRAWS consecutive seeds")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    payload, pool = build(args.release, args.device, args.seed)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    pool_path = args.out.with_name(args.out.stem + "_pool.json")
    pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {args.out} — {len(payload['samples'])} samples", file=sys.stderr)
    names = [name for name, _, _ in TRACKS] + ["ar"]
    drawn = sum(len(entry[arm]) for entry in pool["pool"] for arm in names)
    print(f"wrote {pool_path} — {drawn} draws", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
