#!/usr/bin/env python
"""Train one arm, one seed — PRD §4.1, §4.3.

The seventh driver, and the first that is not about the corpus. It takes stage 10's packed shards
and §5's model and runs §4.3's budget to completion, checkpointing at the seven fractions the
epoch sweep evaluates at.

    # what the gate needs before anything is rented (G2)
    python scripts/train.py throughput --arm ar --device cuda --microbatch 16

    # the pilot G3 asks for: 20M params, both configs, one seed
    python scripts/train.py run --arm ar   --size 25M --steps 200 --out runs/pilot-ar
    python scripts/train.py run --arm diff --size 25M --steps 200 --out runs/pilot-diff

    # a core run
    python scripts/train.py run --arm ar --seed 0 --out runs/arm-a-ar-s0

**`--arm` is the only flag that changes the model.** Everything else — the corpus, the tokenizer,
the parameter count, the optimizer, the schedule, the seed, the token budget — is shared by
construction, and `--arm` selects between `RavaanAR` and `RavaanDiffusion` over the same
`ModelConfig`. That is §4.1 expressed as a command line: if running the two arms took two commands
that differed in more than one word, the claim would be harder to check than to make.

Requires the `[train]` extra.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import torch  # noqa: E402

from ravaan.data.corruption import CorruptionConfig  # noqa: E402
from ravaan.models.ar import RavaanAR  # noqa: E402
from ravaan.models.config import LADDER, ModelConfig, assert_matched, parameter_count  # noqa: E402
from ravaan.models.diffusion import RavaanDiffusion  # noqa: E402
from ravaan.training.config import PROVENANCE, TrainingConfig  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402
from ravaan.training.loop import Trainer, throughput  # noqa: E402
from ravaan.training.tasks import (  # noqa: E402
    FramingTokens,
    SentencePieceCodec,
    TaskGenerator,
)


def _mask_id(corpus: PackedCorpus | None, override: int | None) -> int:
    """§7's ``<mask>`` piece id, from the tokenizer sidecar rather than from memory.

    A diffusion model pointed at the wrong absorbing token trains without complaint and produces
    nothing usable, so this refuses to guess. The id lives next to the tokenizer that defined it.
    """
    if override is not None:
        return override
    if corpus is not None:
        special = corpus.tokenizer.get("special_tokens") or {}
        if "<mask>" in special:
            return int(special["<mask>"])
    raise SystemExit(
        "the diffusion arm needs §7's <mask> id. The packed corpus's tokenizer record does not "
        "carry one — pass --mask-id, or re-pack with a manifest that names it"
    )


def build_tasks(
    arm: str, corpus: PackedCorpus, config: TrainingConfig, tokenizer_path: str | None
) -> TaskGenerator:
    """§4.2's mixture, over §7's tokenizer.

    The tokenizer file is needed and not optional: the corruptions are text transforms, so a
    packed sequence has to decode before it can be damaged. The manifest names which tokenizer
    the corpus was written with, and this refuses a mismatch rather than producing tasks whose
    source half is in one vocabulary and target half in another.
    """
    path = tokenizer_path or f"data/tokenizer/{Path(corpus.tokenizer['id']).name.split(':')[-1]}"
    if not Path(path).exists():
        raise SystemExit(
            f"§4.2's task generator needs §7's tokenizer to decode packed sequences back to "
            f"text, and {path} is not there. Pass --tokenizer, or --no-tasks to train the bare "
            "objective (which is not the experiment — §4.1 requires both arms see all five tasks)"
        )
    codec = SentencePieceCodec(path)
    if codec.tokenizer.fingerprint() != corpus.tokenizer.get("fingerprint"):
        raise SystemExit(
            f"{path} fingerprints {codec.tokenizer.fingerprint()} and the corpus was packed with "
            f"{corpus.tokenizer.get('fingerprint')} — the corruption tasks would mix two "
            "vocabularies inside one sequence"
        )
    return TaskGenerator(
        codec,
        FramingTokens.from_manifest(corpus.tokenizer),
        arm=arm,
        sequence_length=config.sequence_length,
        seed=config.seed,
        corruption=CorruptionConfig(),
    )


def build_model(arm: str, config: ModelConfig, corpus: PackedCorpus | None, mask_id: int | None):
    if arm == "ar":
        return RavaanAR(config)
    if arm == "diff":
        return RavaanDiffusion(_mask_id(corpus, mask_id), config)
    raise SystemExit(f"--arm must be 'ar' or 'diff', got {arm!r}")


def _device(requested: str) -> str:
    if requested != "auto":
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


def cmd_run(args: argparse.Namespace) -> int:
    model_config = LADDER[args.size]
    training = TrainingConfig(seed=args.seed)
    if args.tokens_per_step:
        training = TrainingConfig.from_dict(
            {**training.to_dict(), "tokens_per_step": args.tokens_per_step}
        )

    corpus = PackedCorpus(args.corpus, split="train", arm=args.corpus_arm)
    held_out = PackedCorpus(args.corpus, split=args.eval_split, arm=None) if args.evaluate else None

    model = build_model(args.arm, model_config, corpus, args.mask_id)
    tasks = None if args.no_tasks else build_tasks(args.arm, corpus, training, args.tokenizer)
    counts = parameter_count(model.config)
    device = _device(args.device)

    print(f"corpus  {corpus.describe()}", file=sys.stderr)
    print(
        f"\nmodel   Ravaan-{args.arm.upper()} at {args.size}: {counts['total']:,} parameters "
        f"({counts['non_embedding']:,} non-embedding)\n"
        f"device  {device}\n"
        f"budget  {training.tokens_processed:,.0f} tokens over {training.total_steps:,} steps "
        f"of {training.tokens_per_step:,}\n"
        f"epochs  {training.tokens_processed / max(corpus.tokens, 1):.1f} over "
        f"{corpus.tokens:,} unique tokens",
        file=sys.stderr,
    )
    if tasks is None:
        print(
            "tasks   OFF — plain LM only. §4.1 requires both arms see all five of §4.2's tasks, "
            "so a run made this way is a smoke test and not a result",
            file=sys.stderr,
        )
    else:
        shares = "  ".join(f"{t} {s:.0%}" for t, s in tasks.shares.items())
        print(
            f"tasks   §4.2 v{tasks.to_dict()['tasks_version']} / corruption "
            f"{tasks.corruption.fingerprint()}  {shares}",
            file=sys.stderr,
        )

    trainer = Trainer(
        model,
        corpus,
        training,
        out_dir=args.out,
        device=device,
        microbatch=args.microbatch,
        run_name=f"{args.arm}-s{args.seed}",
        tasks=tasks,
    )
    if args.resume:
        trainer.load(args.resume)
        print(f"resumed at step {trainer.state.step:,}", file=sys.stderr)

    # The config and its provenance land next to the checkpoints, not in a lab notebook.
    # Preregistration §6 requires the report to state whose defaults these are.
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "config.json").write_text(
        json.dumps(
            {
                "arm": args.arm,
                "size": args.size,
                "seed": args.seed,
                "model": model.config.to_dict(),
                "training": training.to_dict(),
                "parameters": counts,
                "hyperparameter_provenance": PROVENANCE,
                "tokenizer": corpus.tokenizer,
                # §4.2: "with the generator version and seed recorded". Here rather than in a
                # lab notebook, next to the checkpoints the tasks produced.
                "tasks": tasks.to_dict() if tasks is not None else None,
            },
            indent=1,
        ),
        encoding="utf-8",
    )

    def report(record: dict) -> None:
        print(
            f"  step {record['step']:>7,}  {record['fraction']:6.2%}  "
            f"loss {record['loss']:7.4f}  bpt {record['bits_per_token']:6.3f}  "
            f"lr {record['lr']:.2e}  {record['tokens_per_second']:,} tok/s",
            file=sys.stderr,
            flush=True,
        )

    state = trainer.train(max_steps=args.steps, on_log=report)
    print(
        f"\nstopped at step {state.step:,} — {state.tokens:,} tokens in "
        f"{state.wall_seconds / 3600:.2f} h",
        file=sys.stderr,
    )
    if tasks is not None:
        print("\n§4.2's mixture as built (target in brackets):", file=sys.stderr)
        for task, share in tasks.realized_shares().items():
            short = tasks.counts.get(f"shortfall/{task}", 0) + tasks.counts.get(
                f"fallback/{task}", 0
            )
            note = f"   {short:,} unplaceable" if short else ""
            print(
                f"  {task:<12} {share:6.2%}  [{tasks.shares[task]:.0%}]{note}", file=sys.stderr
            )
        padded = tasks.counts.get("pad_tokens", 0)
        print(
            f"  padding      {padded:,} tokens "
            f"({padded / max(state.tokens, 1):.4%} of tokens processed)",
            file=sys.stderr,
        )

    if held_out is not None:
        evaluation = trainer.evaluate(held_out, limit=args.eval_limit)
        (Path(args.out) / "evaluation.json").write_text(
            json.dumps(evaluation, indent=1), encoding="utf-8"
        )
        print("\nheld-out (§8.3 reports bits-per-byte):", file=sys.stderr)
        for key, entry in sorted(evaluation.items()):
            print(
                f"  {key:<14} bpb {entry['bits_per_byte']:6.4f}  "
                f"bpt {entry['bits_per_token']:6.4f}  {entry['sequences']:,} seqs",
                file=sys.stderr,
            )
    return 0


def cmd_throughput(args: argparse.Namespace) -> int:
    """G2's number. §11: 'Measured throughput implies 6 core runs ≤ $90'."""
    model_config = LADDER[args.size]
    training = TrainingConfig()
    # §4.2's generator is a quarter of every batch's CPU cost and G2 is a budget gate, so it is
    # measured unless explicitly excluded. With --corpus it runs on the real thing.
    corpus = PackedCorpus(args.corpus, split="train", arm="A") if args.corpus else None
    tasks = (
        None
        if args.no_tasks
        else build_tasks(args.arm, corpus, training, args.tokenizer)
        if corpus is not None
        else None
    )
    if tasks is None and not args.no_tasks:
        print(
            "warning: no --corpus, so this is the bare objective without §4.2's task generator. "
            "G2 reads a number that a real run will not reproduce — pass --corpus",
            file=sys.stderr,
        )
    model = build_model(args.arm, model_config, corpus, args.mask_id or 4)
    result = throughput(
        model,
        training,
        device=_device(args.device),
        microbatch=args.microbatch,
        steps=args.steps,
        tasks=tasks,
        corpus=corpus,
    )
    result["arm"] = args.arm
    result["size"] = args.size
    result["parameters"] = parameter_count(model.config)["total"]
    print(json.dumps(result, indent=1))
    verdict = "PASS" if result["g2_passes_at_0.35"] else "FAIL — shrink the model, never the epochs"
    print(
        f"\nG2 at $0.35/hr spot: {result['hours_for_6_runs']} h for 6 runs = "
        f"${result['usd_for_6_runs_at_0.35']} against $90 — {verdict}",
        file=sys.stderr,
    )
    return 0


def cmd_spec(args: argparse.Namespace) -> int:
    """§5's CI assertion, runnable by hand. Both arms, every rung of the fallback ladder."""
    for name, config in LADDER.items():
        counts = parameter_count(config)
        shared = assert_matched(config.as_ar(), config.as_diffusion())
        print(
            f"{name:>4}  total {counts['total']:>12,}  non-embedding "
            f"{counts['non_embedding']:>12,}  arms matched at {shared:,}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="train one arm, one seed")
    r.add_argument("--arm", required=True, choices=("ar", "diff"))
    r.add_argument("--size", default="70M", choices=tuple(LADDER))
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--corpus", default="data/packed")
    r.add_argument("--corpus-arm", default="A", help="which §6.1 arm's streams to train on")
    r.add_argument("--out", required=True)
    r.add_argument("--device", default="auto")
    r.add_argument("--microbatch", type=int, help="sequences per forward; the rest is accumulated")
    r.add_argument("--tokens-per-step", type=int, help="override §4.3's step size")
    r.add_argument("--steps", type=int, help="stop early — pilots and smoke tests")
    r.add_argument("--resume", help="a checkpoint to continue from")
    r.add_argument("--mask-id", type=int, help="§7's <mask> id, if the manifest lacks it")
    r.add_argument("--tokenizer", help="§7's .model file; §4.2's corruptions decode through it")
    r.add_argument(
        "--no-tasks",
        action="store_true",
        help="plain LM only — a smoke test, not a run: §4.1 requires all five of §4.2's tasks",
    )
    r.add_argument("--evaluate", action="store_true", help="score the held-out split at the end")
    r.add_argument("--eval-split", default="validation")
    r.add_argument("--eval-limit", type=int, default=2_000)
    r.set_defaults(func=cmd_run)

    t = sub.add_parser("throughput", help="G2's measurement")
    t.add_argument("--arm", default="ar", choices=("ar", "diff"))
    t.add_argument("--size", default="70M", choices=tuple(LADDER))
    t.add_argument("--device", default="auto")
    t.add_argument("--microbatch", type=int, default=8)
    t.add_argument("--steps", type=int, default=20)
    t.add_argument("--mask-id", type=int)
    t.add_argument("--corpus", help="packed corpus; without it §4.2's task cost is not measured")
    t.add_argument("--tokenizer", help="§7's .model file")
    t.add_argument("--no-tasks", action="store_true", help="bare objective — understates G2")
    t.set_defaults(func=cmd_throughput)

    s = sub.add_parser("spec", help="§5's parameter-count assertion")
    s.set_defaults(func=cmd_spec)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
