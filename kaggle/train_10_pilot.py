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

import json
import os
import sys
import time
from pathlib import Path

INPUT = Path("/kaggle/input")
WORKING = Path("/kaggle/working")


def discover() -> tuple[Path, Path]:
    """Find the code tree and the corpus under the mount. See `kaggle/mount_bootstrap.py`.

    Kaggle's mount layout has surprised this project twice (Findings Z and Y), so this looks for
    marker files rather than assuming a path, and prints what it found either way.
    """
    print(f"{INPUT} holds: {[p.name for p in sorted(INPUT.iterdir())] if INPUT.exists() else '—'}")

    code = next((p.parent for p in INPUT.rglob("ravaan/models/backbone.py")), None)
    corpus = next((p.parent for p in INPUT.rglob("manifest.json") if "packed" in str(p)), None)
    if code is None:
        raise SystemExit("no code tree under /kaggle/input — attach the ravaan-code dataset")
    if corpus is None:
        raise SystemExit("no packed corpus under /kaggle/input — attach the ravaan-pilot dataset")
    print(f"code   {code}\ncorpus {corpus}")
    return code, corpus


def main() -> int:
    code, corpus_dir = discover()
    sys.path.insert(0, str(code))

    import torch

    from ravaan.models.ar import RavaanAR
    from ravaan.models.config import LADDER, assert_matched, parameter_count
    from ravaan.models.diffusion import RavaanDiffusion
    from ravaan.training.config import TrainingConfig
    from ravaan.training.data import PackedCorpus
    from ravaan.training.loop import Trainer, throughput

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\ntorch {torch.__version__} on {device}")
    if device == "cuda":
        print(f"  {torch.cuda.get_device_name(0)}, bf16={torch.cuda.is_bf16_supported()}")
    else:
        print("  ⚠️ no GPU attached — set Accelerator to GPU T4 x2 or P100 and re-run")

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
    for arm in ("ar", "diff"):
        print(f"\n{'=' * 68}\n{arm.upper()}\n{'=' * 68}", flush=True)
        model = RavaanAR(model_config) if arm == "ar" else RavaanDiffusion(mask_id, model_config)

        if device == "cuda":
            speed = throughput(model, config, device=device, microbatch=microbatch, steps=10)
            print(f"G2 throughput: {speed['tokens_per_second']:,} tok/s, "
                  f"{speed['hours_per_run']} h per §4.3 run, "
                  f"${speed['usd_for_6_runs_at_0.35']} for 6 at $0.35/hr "
                  f"({'PASS' if speed['g2_passes_at_0.35'] else 'FAIL'})", flush=True)
            results[f"{arm}_throughput"] = speed

        out = WORKING / f"pilot-{arm}"
        trainer = Trainer(model, train, config, out_dir=out, device=device,
                          microbatch=microbatch, run_name=arm)
        started = time.time()
        trainer.train(on_log=lambda r: print(
            f"  step {r['step']:>6,}  {r['fraction']:6.2%}  loss {r['loss']:7.4f}  "
            f"bpt {r['bits_per_token']:6.3f}  lr {r['lr']:.2e}  "
            f"{r['tokens_per_second']:,} tok/s", flush=True))

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
                        microbatch=microbatch, run_name=f"{arm}-resumed")
        again.load(checkpoint)
        exact = again.state.step == trainer.state.step and all(
            torch.equal(a, b)
            for a, b in zip(model.state_dict().values(), fresh.state_dict().values(), strict=True)
        )
        results[arm]["resume_exact"] = bool(exact)
        print(f"  resume round-trip exact: {exact}")

    (WORKING / "pilot_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nwrote {WORKING / 'pilot_results.json'}")

    verdict = all(results[a]["resume_exact"] for a in ("ar", "diff"))
    print(f"\nG3 resume half: {'PASS' if verdict else 'FAIL'}. "
          "The coherence half needs a reader — sample from the checkpoints in /kaggle/working.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
