"""Kaggle kernel 10 — Gate G3's pilot: both arms, one seed, on a GPU (PRD §10, §11).

G3 asks two questions and this kernel answers both: *"20M pilot DIFF produces coherent Urdu after
50 epochs; both models resume from checkpoint correctly."* The second is checked here directly —
the kernel trains, saves, reloads into a fresh model and asserts the next step's loss is identical.
The first is a judgement a reader makes about sampled text, so the kernel writes samples and does
not grade them.

**It runs both arms in one session on purpose.** §4.1's matched pair is only meaningful if the two
runs shared everything they were supposed to; running them in one process, from one config object,
over one corpus, on one device, removes every way they could quietly differ. The cost is that a
session cap has to hold two runs rather than one, which at 20M parameters it comfortably does.

Mounts:
  * `ravaan-code`   — the repo tree (`push.py code`)
  * `ravaan-pilot`  — `data/packed-pilot` and §7's tokenizer (`push.py data`)

Accelerator: **GPU T4 x2 or P100**. Internet: off — everything it needs is mounted.

⚠️ **The corpus is the pilot corpus, not the frozen one.** Stage 8 has not run, FineWeb2's stage
6+7 has not run, and the split is not stage 9's. `scripts/pack_pilot.py` says this at length and
the manifest carries it as `pilot.is_frozen_corpus = false`. **No number this kernel prints goes in
a results table.** It exists to make G3 answerable before the freeze finishes, which is what the
schedule asks for.
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
from pathlib import Path

INPUT = Path("/kaggle/input")
WORKING = Path("/kaggle/working")
REPO = Path(__file__).resolve().parents[1]

# Windows picks cp1252 for a console *and* for a redirected pipe, and cp1252 raises rather than
# mangles — so this has to happen before the first non-ASCII print, which here is the pilot-corpus
# warning. `ravaan.console` is the class fix from session 14 and this is the sixth instance of the
# same Windows text default; the guard is called, never copied. It is reached through REPO because
# the code tree's real location is not known until `discover()` has run, and on Kaggle that import
# fails harmlessly: the tree is under the mount and Linux stdout is UTF-8 already.
sys.path.insert(0, str(REPO))
try:
    from ravaan.console import pin_utf8_streams

    pin_utf8_streams()
except ImportError:
    pass


def on_kaggle() -> bool:
    """Whether this is a Kaggle kernel, as opposed to any other host with a GPU."""
    return INPUT.exists()


def working_dir() -> Path:
    """Where checkpoints and results go: `/kaggle/working` there, `runs/pilot` here."""
    if on_kaggle():
        return WORKING
    out = Path(os.environ.get("RAVAAN_OUT", REPO / "runs" / "pilot"))
    out.mkdir(parents=True, exist_ok=True)
    return out


def discover() -> tuple[Path, Path]:
    """Find the code tree and the corpus — under Kaggle's mount, or in the repo.

    Kaggle's mount layout has surprised this project twice (Findings Z and Y), so the Kaggle path
    looks for marker files rather than assuming a path, and prints what it found either way.

    **The local path is not a convenience, it is the one that runs.** Kaggle gates *accelerators*
    behind phone verification, not only notebook internet — Finding Z' recorded the internet half
    and this kernel needs the other half, so on that host it has no GPU to run on at all.
    `colab/freeze_colab.py` is the precedent: a runner named for one host and deliberately
    dependent on nothing that host provides.
    """
    if not on_kaggle():
        corpus = Path(os.environ.get("RAVAAN_CORPUS", REPO / "data" / "packed-pilot"))
        if not (corpus / "manifest.json").exists():
            raise SystemExit(f"no packed corpus at {corpus} — run `scripts/pack_pilot.py` first")
        print(f"host   local\ncode   {REPO}\ncorpus {corpus}")
        return REPO, corpus

    print(f"{INPUT} holds: {[q.name for q in sorted(INPUT.iterdir())]}")
    code = next((q.parent for q in INPUT.rglob("ravaan/models/backbone.py")), None)
    corpus = next((q.parent for q in INPUT.rglob("manifest.json") if "packed" in str(q)), None)
    if code is None:
        raise SystemExit("no code tree under /kaggle/input — attach the ravaan-code dataset")
    if corpus is None:
        raise SystemExit("no packed corpus under /kaggle/input — attach the ravaan-pilot dataset")
    print(f"host   kaggle\ncode   {code}\ncorpus {corpus}")
    return code, corpus


def main() -> int:
    code, corpus_dir = discover()
    work = working_dir()
    sys.path.insert(0, str(code))

    import torch

    from ravaan.models.ar import RavaanAR
    from ravaan.models.config import LADDER, assert_matched, parameter_count
    from ravaan.models.diffusion import RavaanDiffusion
    from ravaan.training.config import TrainingConfig
    from ravaan.training.data import PackedCorpus
    from ravaan.training.loop import Trainer, throughput
    from ravaan.training.tasks import build_tasks

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\ntorch {torch.__version__} on {device}")
    if device == "cuda":
        print(f"  {torch.cuda.get_device_name(0)}, bf16={torch.cuda.is_bf16_supported()}")
    else:
        print("  ⚠️ no GPU — on Kaggle set Accelerator to GPU; locally install a CUDA torch build")

    train = PackedCorpus(corpus_dir, split="train", arm="A")
    val = PackedCorpus(corpus_dir, split="validation", arm=None)
    print(f"\n{train.describe()}")
    print(f"held-out: {len(val):,} sequences")

    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("pilot", {}).get("is_frozen_corpus", True):
        print("\n⚠️ PILOT CORPUS — not the freeze. Outstanding: " + ", ".join(
            manifest["pilot"]["not_run"]
        ))
    mask_id = int(manifest["tokenizer"]["special_tokens"]["<mask>"])

    # §4.2's generator decodes packed sequences back to text, so it needs the tokenizer the
    # corpus was packed with — mounted beside the shards on Kaggle, `data/tokenizer` here.
    name = Path(str(manifest["tokenizer"]["id"])).name.split(":")[-1]
    tokenizer_path = next(
        (q for q in (corpus_dir / name, code / "data" / "tokenizer" / name) if q.exists()),
        None,
    )
    if tokenizer_path is None:
        raise SystemExit(
            f"§7's tokenizer ({name}) is beside neither the corpus nor data/tokenizer. "
            "§4.2's five tasks cannot be built without it, and training the bare objective "
            "instead is not the experiment (§4.1)."
        )

    size = os.environ.get("RAVAAN_SIZE", "25M")
    model_config = LADDER[size]
    matched = assert_matched(model_config.as_ar(), model_config.as_diffusion())
    print(f"\n§5 at {size}: both arms at {matched:,} parameters "
          f"({parameter_count(model_config)['non_embedding']:,} non-embedding)")

    # G3 is an implementation check, so the budget is epochs over the pilot corpus rather than
    # §4.3's 9.9B — "coherent Urdu after 50 epochs" is the gate's own wording.
    epochs = int(os.environ.get("RAVAAN_EPOCHS", "50"))
    tokens_per_step = int(os.environ.get("RAVAAN_TOKENS_PER_STEP", "65536"))
    microbatch = int(os.environ.get("RAVAAN_MICROBATCH", "32"))
    config = TrainingConfig.from_dict({
        **TrainingConfig().to_dict(),
        "tokens_processed": float(train.tokens * epochs),
        "tokens_per_step": tokens_per_step,
        "warmup_steps": 100,
        "log_every": 25,
        "checkpoint_every": 500,
    })
    print(f"budget  {epochs} epochs = {config.tokens_processed:,.0f} tokens over "
          f"{config.total_steps:,} steps of {tokens_per_step:,}")

    results = {}
    previous: list = []
    for arm in ("ar", "diff"):
        print(f"\n{'=' * 68}\n{arm.upper()}\n{'=' * 68}", flush=True)
        # Whatever the last arm left on the card goes before this one is built. Without it the
        # second arm is measured against 8 GB minus the first arm's weights, optimizer state and
        # the resume check's second copy — which showed up as DIFF at 14,546 tok/s inside this
        # kernel against 40,575 standalone, a 2.8x penalty that falls on whichever arm runs
        # second and would have made the in-kernel arm comparison pure ordering artefact.
        previous.clear()
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        model = RavaanAR(model_config) if arm == "ar" else RavaanDiffusion(mask_id, model_config)

        if device == "cuda":
            # §4.3's budget, not the pilot's. `config` below has `tokens_processed` set to
            # epochs over the pilot corpus, and handing that to `throughput` makes
            # `hours_per_run` a figure for a run nobody is costing — it printed 0.05 h and a
            # G2 PASS at $0.11 for 6 runs. A gate that reports pass on the wrong quantity is
            # Finding U's shape, so the measurement takes the default config and only the
            # training below takes the pilot's.
            speed = throughput(model, TrainingConfig(), device=device,
                               microbatch=microbatch, steps=10)
            print(f"G2 throughput: {speed['tokens_per_second']:,} tok/s, "
                  f"{speed['hours_per_run']} h per §4.3 run of "
                  f"{TrainingConfig().tokens_processed:,.0f} tokens, "
                  f"${speed['usd_for_6_runs_at_0.35']} for 6 at $0.35/hr "
                  f"({'PASS' if speed['g2_passes_at_0.35'] else 'FAIL'})", flush=True)
            results[f"{arm}_throughput"] = speed

        # §4.2's five objectives. Without this the Trainer runs the bare objective quite
        # happily — which is what this kernel did until session 21, and the loss curve gave
        # no sign of it. `build_tasks` moved into the library so that "the driver built a
        # mixture and the kernel did not" stops being a thing that can happen.
        tasks = build_tasks(arm, train, config, tokenizer_path)
        out = work / f"pilot-{arm}"
        trainer = Trainer(model, train, config, out_dir=out, device=device,
                          microbatch=microbatch, run_name=arm,
                          tasks=tasks)
        started = time.time()
        trainer.train(on_log=lambda r: print(
            f"  step {r['step']:>6,}  {r['fraction']:6.2%}  loss {r['loss']:7.4f}  "
            f"bpt {r['bits_per_token']:6.3f}  lr {r['lr']:.2e}  "
            f"{r['tokens_per_second']:,} tok/s", flush=True))

        # ⚠️ Finding AJ: a starved mixture is invisible in the loss and visible only here —
        # three of the five objectives sat at 0.00% while the curve looked unremarkable.
        print("\n  §4.2's mixture as built (target in brackets):")
        for task, share in tasks.realized_shares().items():
            short = (tasks.counts.get(f"shortfall/{task}", 0)
                     + tasks.counts.get(f"fallback/{task}", 0))
            note = f"   {short:,} unplaceable" if short else ""
            print(f"    {task:<12} {share:6.2%}  [{tasks.shares[task]:.0%}]{note}")
        padded = tasks.counts.get("pad_tokens", 0)
        print(f"    padding      {padded:,} tokens "
              f"({padded / max(trainer.state.tokens, 1):.4%} of tokens processed)",
              flush=True)

        evaluation = trainer.evaluate(val, limit=512)
        results[arm] = {
            "steps": trainer.state.step,
            "tokens": trainer.state.tokens,
            "hours": round((time.time() - started) / 3600, 3),
            "evaluation": evaluation,
        }
        print(f"\n{arm} held-out (§8.3 bits-per-byte; ELBO for diff, exact NLL for ar):")
        for key, entry in sorted(evaluation.items()):
            print(f"  {key:<14} bpb {entry['bits_per_byte']:7.4f}  "
                  f"bpt {entry['bits_per_token']:7.4f}  {entry['sequences']:,} seqs")

        # G3's second half, checked rather than asserted in prose: §9 requires resume to work
        # before any paid run, because spot instances get preempted.
        checkpoint = trainer.save(out / f"{arm}-resume-check.pt")
        fresh = RavaanAR(model_config) if arm == "ar" else RavaanDiffusion(mask_id, model_config)
        again = Trainer(fresh, train, config, out_dir=out, device=device,
                        microbatch=microbatch, run_name=f"{arm}-resumed",
                        tasks=tasks)
        again.load(checkpoint)
        exact = again.state.step == trainer.state.step and all(
            torch.equal(a, b)
            for a, b in zip(model.state_dict().values(), fresh.state_dict().values(), strict=True)
        )
        results[arm]["resume_exact"] = bool(exact)
        previous.extend((model, trainer, fresh, again))
        print(f"  resume round-trip exact: {exact}")

    (work / "pilot_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nwrote {work / 'pilot_results.json'}")

    verdict = all(results[a]["resume_exact"] for a in ("ar", "diff"))
    print(f"\nG3 resume half: {'PASS' if verdict else 'FAIL'}. "
          f"The coherence half needs a reader — sample from the checkpoints in {work}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
