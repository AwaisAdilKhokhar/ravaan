"""Turn a trained checkpoint into a Hugging Face model repository (PRD §2, session 34).

Three things the PRD requires of a release, and this driver is where two of them land:

**(a) Inference code ships with the weights.** ``RavaanDiffusion`` is not a ``transformers``
architecture and cannot be loaded by ``AutoModel``. From outside this repository the denoising
schedule, the step count and forbidding ``</s>`` *are* the model (Findings AO, AR, BG) — a
checkpoint alone is not a runnable artifact. So the repo carries a vendored, torch-only copy of
the inference path: ``ravaan_infer/``.

**(b) Everything the sampler needs comes off the checkpoint, never off a default.** The mask id
and §7's twelve framing pieces are read from the checkpoint's own ``tokenizer`` record, which is
the corpus manifest's record, which is what the corpus was packed with. A sampler pointed at a
different ``<mask>`` than the model trained under produces confident, fluent, wrong output with
no symptom anywhere. ``config.json`` in the release therefore carries that record verbatim.

**(c) The model card carries the caveats** — that is ``cards.py``, not here.

**Why safetensors.** The training checkpoints are pickles, and a pickle downloaded from the
internet is arbitrary code execution. The released weights are safetensors: no pickle, and the
Hugging Face viewer can read the tensor list without trusting it.

**Why the AR checkpoint gets smaller.** ``ar-s0_fp25.pt`` is 839 MB and two thirds of that is
Adam's two moments, which a released model has no use for (Finding BM). Stripping is not an
optimization here, it is what makes the upload finish.

    python scripts/release.py --out D:/ravaan-release
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import torch
from safetensors.torch import save_file

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

#: The two halves of the matched release pair. Same corpus (arm B, 85,362,688 unique tokens),
#: same task mixture, same model. Each is its arm's *best held-out checkpoint*, which on this
#: corpus is not the last one for either arm (Finding BF).
RELEASES = (
    {
        "name": "ravaan-diff-70m",
        "arm": "diff",
        "checkpoint": "D:/ravaan-runs/ship-diff-b64/diff-s0_f1_weights.pt",
        "run": "ship-diff-b64",
        "epochs": 64,
        "urdu_bpb": 0.7646,
    },
    {
        "name": "ravaan-ar-70m",
        "arm": "ar",
        "checkpoint": "D:/ravaan-runs/ship-ar-b/ar-s0_fp25.pt",
        "run": "ship-ar-b",
        "epochs": 4,
        "urdu_bpb": 0.7774,
    },
)

#: Vendored into every release repo, so `pip install torch sentencepiece` is the whole setup.
#: `training/tasks.py` is deliberately NOT vendored whole — it imports `ravaan.data.corruption`
#: and drags the corpus builder in behind it. `FramingTokens` is lifted out instead.
VENDOR = (
    "ravaan/__init__.py",
    "ravaan/models/__init__.py",
    "ravaan/models/config.py",
    "ravaan/models/backbone.py",
    "ravaan/models/ar/__init__.py",
    "ravaan/models/diffusion/__init__.py",
    "ravaan/sampling/__init__.py",
    "ravaan/sampling/checkpoint.py",
    "ravaan/sampling/decoding.py",
    "ravaan/sampling/diffusion.py",
    "ravaan/sampling/ar.py",
    "ravaan/sampling/prompts.py",
)


def strip_to_weights(payload: dict) -> dict:
    """Everything a cold-start load reads, and nothing a resume would need.

    ``Trainer.load`` reads ``optimizer`` and the RNG state because resuming needs them.
    :func:`ravaan.sampling.checkpoint.load_arm` reads ``model``, ``model_config`` and
    ``tokenizer``. The difference is two thirds of the file.
    """
    keep = ("model_config", "tokenizer", "config", "state", "fraction")
    return {k: payload[k] for k in keep if k in payload}


def build(spec: dict, out_root: Path, *, tokenizer_src: Path) -> Path:
    src = Path(spec["checkpoint"])
    if not src.exists():
        raise SystemExit(f"checkpoint missing: {src}")

    dest = out_root / spec["name"]
    dest.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {spec['name']} ===")
    print(f"  source   {src}  ({src.stat().st_size / 1e6:,.0f} MB)")

    payload = torch.load(src, map_location="cpu", weights_only=False)
    meta = strip_to_weights(payload)

    # --- weights -> safetensors -------------------------------------------------------------
    tensors = {k: v.contiguous() for k, v in payload["model"].items()}
    n_params = sum(t.numel() for t in tensors.values())
    if n_params != 69_975_680:
        raise SystemExit(f"expected 69,975,680 parameters, got {n_params:,} — wrong checkpoint?")
    weights_path = dest / "model.safetensors"
    save_file(
        tensors,
        weights_path,
        metadata={"format": "pt", "arm": spec["arm"], "run": spec["run"]},
    )
    print(f"  weights  {weights_path.name}  ({weights_path.stat().st_size / 1e6:,.0f} MB, "
          f"{n_params:,} params)")

    # --- config -----------------------------------------------------------------------------
    cfg = dict(meta.get("config") or {})
    cfg["model"] = _as_dict(meta["model_config"])
    cfg["tokenizer"] = meta["tokenizer"]
    cfg["release"] = {
        "name": spec["name"],
        "arm": spec["arm"],
        "run": spec["run"],
        "epochs": spec["epochs"],
        "corpus_arm": "B",
        "unique_tokens": 85_362_688,
        "fraction": meta.get("fraction"),
        "step": (meta.get("state") or {}).get("step"),
        "tokens_processed": (meta.get("state") or {}).get("tokens"),
        "validation_urdu_bpb": spec["urdu_bpb"],
        "weights_format": "safetensors",
        "optimizer_state": "stripped — this checkpoint cannot resume training",
    }
    (dest / "config.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("  config   config.json")

    # --- tokenizer --------------------------------------------------------------------------
    tok_dir = dest / "tokenizer"
    tok_dir.mkdir(exist_ok=True)
    for name in ("ravaan-16k.model", "ravaan-16k.vocab", "ravaan-16k.json"):
        shutil.copy2(tokenizer_src / name, tok_dir / name)
    fingerprint = meta["tokenizer"].get("fingerprint")
    print(f"  tokenizer ravaan-16k.model (fingerprint {fingerprint})")

    # --- inference code ---------------------------------------------------------------------
    vendored = vendor_inference(dest)
    print(f"  code     ravaan_infer/ ({vendored} modules, torch + sentencepiece only)")

    return dest


def _as_dict(obj) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dataclass_fields__"):
        return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
    raise TypeError(f"cannot serialize model_config of type {type(obj)!r}")


def vendor_inference(dest: Path) -> int:
    """Copy the torch-only inference path, rewriting `ravaan.` imports to `ravaan_infer.`.

    The rewrite is textual and it is checked: the built package is imported and used by
    ``verify.py`` before anything is pushed, so a missed import fails here rather than in a
    stranger's terminal.
    """
    pkg = dest / "ravaan_infer"
    if pkg.exists():
        shutil.rmtree(pkg)
    count = 0
    for rel in VENDOR:
        src = REPO / rel
        target = pkg / Path(rel).relative_to("ravaan")
        target.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        text = text.replace("from ravaan.", "from ravaan_infer.")
        text = text.replace("import ravaan.", "import ravaan_infer.")
        # FramingTokens lives in training/tasks.py, which imports the corpus builder. The
        # dataclass itself has no dependencies, so it is vendored standalone instead.
        text = text.replace(
            "from ravaan_infer.training.tasks import FramingTokens",
            "from ravaan_infer.framing import FramingTokens",
        )
        target.write_bytes(text.encode("utf-8"))
        count += 1
    _write_framing(pkg)

    # The two files that exist only for the release: a safetensors cold-start loader, and the
    # example that makes `python generate.py` the first thing that works after a clone.
    assets = REPO / "release_assets"
    shutil.copy2(assets / "loader.py", pkg / "loader.py")
    shutil.copy2(assets / "generate.py", dest / "generate.py")
    (dest / "requirements.txt").write_bytes(
        b"torch>=2.0\nsentencepiece>=0.2\nsafetensors>=0.4\n"
    )
    return count + 3


def _write_framing(pkg: Path) -> None:
    """Lift `FramingTokens` out of training/tasks.py, verbatim, with its imports trimmed."""
    source = (REPO / "ravaan/training/tasks.py").read_text(encoding="utf-8")
    start = source.index("@dataclass(frozen=True, slots=True)\nclass FramingTokens:")
    end = source.index("\n@dataclass", start + 10)
    body = source[start:end].rstrip()
    (pkg / "framing.py").write_bytes(
        (
            '"""§7\'s twelve framing pieces, lifted from `ravaan/training/tasks.py`.\n\n'
            "Verbatim, because a framing id that disagrees with the corpus the model was packed\n"
            "under produces fluent, confident, wrong output with no symptom anywhere. The only\n"
            "change is the import list: the original module pulls in the corpus builder.\n"
            '"""\n\n'
            "from __future__ import annotations\n\n"
            "from collections.abc import Mapping\n"
            "from dataclasses import dataclass\n\n"
            f"{body}\n"
        ).encode()
    )


def main() -> int:
    pin_utf8_streams()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="D:/ravaan-release", help="staging root for the repos")
    ap.add_argument("--tokenizer", default=str(REPO / "data/tokenizer"))
    ap.add_argument("--only", help="build just this release by name")
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    specs = [s for s in RELEASES if not args.only or s["name"] == args.only]
    if not specs:
        raise SystemExit(f"no release named {args.only!r}")

    built = [build(s, out_root, tokenizer_src=Path(args.tokenizer)) for s in specs]
    print(f"\nstaged {len(built)} repo(s) under {out_root}")
    print("next: python scripts/verify_release.py --root", out_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
