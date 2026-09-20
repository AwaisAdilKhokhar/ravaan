"""The training loop — one loop, both arms (PRD §4.1, §4.3, §9).

Like `ravaan.models.backbone`, this exists once so that §4.1's "differ in exactly one thing" has
one fewer place to be false. The loop does not know which objective it is running: it calls
``model.loss(batch)`` and both arms return a :class:`~ravaan.models.ar.LossOutput`. Swapping AR for
DIFF changes the model handed in and nothing here.

**Resume is a first-class path, not a recovery hack.** §9's cost controls require it in as many
words — *"checkpoint every 500 steps with resume tested before any paid run (spot instances get
preempted)"* — so the step counter, the optimizer state, the RNG state and the sampler position all
round-trip through the checkpoint, and `tests/` asserts that a resumed run produces the same next
loss as an uninterrupted one. A resume that is merely *close* would show up as a seam in the curve
at exactly the compute fractions §4.3 evaluates at.

**Checkpoints happen at two cadences and they mean different things.** Every ``checkpoint_every``
steps a *rolling* checkpoint is overwritten, which exists so a preemption costs minutes. At each of
§4.3's seven fractions a *kept* checkpoint is written under its fraction, which exists because the
curve is the experiment. Deleting a rolling checkpoint is housekeeping; deleting a kept one throws
away a point on the primary endpoint.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from ravaan.training.config import TrainingConfig
from ravaan.training.data import PackedCorpus, SequenceSampler
from ravaan.training.tasks import TaskGenerator


@dataclass
class TrainState:
    """Everything a resume needs that is not in the model or the optimizer."""

    step: int = 0
    tokens: int = 0
    wall_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {"step": self.step, "tokens": self.tokens, "wall_seconds": self.wall_seconds}


def build_optimizer(model: nn.Module, config: TrainingConfig) -> torch.optim.Optimizer:
    """AdamW with §6's decoupled decay, off norms and embeddings.

    The split comes from the model (`parameter_groups`) rather than from a name match here: which
    tensors are matmul weights is the architecture's business, and a regex in the trainer would be
    a second, quietly diverging answer to the same question.
    """
    decay, no_decay = model.backbone.parameter_groups()
    return torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": config.weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ],
        lr=config.peak_lr,
        betas=config.betas,
        eps=config.eps,
    )


def _autocast(device: torch.device, precision: str):
    """§5's BF16, where BF16 is what §5 means: on the accelerator.

    **CPU runs stay in fp32, deliberately.** `torch.autocast("cpu", bfloat16)` is numerically
    fine and, without AMX, roughly an order of magnitude slower than fp32 — measured here, on the
    20M config, where it turned a smoke test into a stall. Nothing whose numbers reach the report
    runs on CPU; what does run there is plumbing (the resume round-trip, the tiny pilots), and
    plumbing is better served by the fast path. §5's precision row is about the paid instances.
    """
    if precision == "bf16" and device.type == "cuda" and torch.cuda.is_bf16_supported():
        return torch.autocast("cuda", dtype=torch.bfloat16)
    return torch.autocast(device.type, enabled=False)


class Trainer:
    """Runs one arm, one seed, to §4.3's token budget."""

    def __init__(
        self,
        model: nn.Module,
        corpus: PackedCorpus,
        config: TrainingConfig,
        *,
        out_dir: str | Path,
        device: str | torch.device = "cpu",
        microbatch: int | None = None,
        run_name: str = "run",
        tasks: TaskGenerator | None = None,
    ) -> None:
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.corpus = corpus
        self.config = config
        self.run_name = run_name
        # §4.2's five-task mixture. Optional so the plumbing tests and `throughput` can run the
        # bare objective, and the *only* thing the loop does with it is call it — which framings
        # exist and what each arm sees of them is `ravaan.training.tasks`'s business, not this
        # module's, for the same reason the loop does not know which objective it is running.
        self.tasks = tasks
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        if corpus.sequence_length != config.sequence_length:
            raise ValueError(
                f"corpus packs {corpus.sequence_length}-token sequences and the training config "
                f"expects {config.sequence_length} — §4.3's token budget would mean two things"
            )

        sequences_per_step = config.tokens_per_step // config.sequence_length
        self.microbatch, self.accumulation = config.resolve_batching(
            microbatch or sequences_per_step
        )
        self.sampler = SequenceSampler(
            len(corpus), self.microbatch, seed=config.seed
        )
        self.optimizer = build_optimizer(self.model, config)
        self.state = TrainState()
        self._kept = config.checkpoint_steps()
        torch.manual_seed(config.seed)
        self.generator = torch.Generator(device=self.device).manual_seed(config.seed)

    # --- checkpointing -----------------------------------------------------

    def save(self, path: str | Path, *, fraction: float | None = None) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "state": self.state.to_dict(),
            "config": self.config.to_dict(),
            "model_config": self.model.config.to_dict(),
            "fraction": fraction,
            "torch_rng": torch.get_rng_state(),
            "generator": self.generator.get_state(),
            "tokenizer": self.corpus.tokenizer,
        }
        # Via `.part` and rename, for the reason stage 1 and stage 10 both give: a truncated
        # checkpoint that looks complete to the next resume costs a whole run to notice.
        part = path.with_suffix(path.suffix + ".part")
        torch.save(payload, part)
        part.replace(path)
        return path

    def load(self, path: str | Path) -> None:
        payload = torch.load(Path(path), map_location=self.device, weights_only=False)
        self.model.load_state_dict(payload["model"])
        self.optimizer.load_state_dict(payload["optimizer"])
        self.state = TrainState(**payload["state"])
        torch.set_rng_state(payload["torch_rng"].cpu())
        self.generator.set_state(payload["generator"].cpu())

    # --- the loop ----------------------------------------------------------

    def train(
        self,
        *,
        max_steps: int | None = None,
        on_log: Callable[[dict], None] | None = None,
    ) -> TrainState:
        config = self.config
        stop = min(config.total_steps, max_steps or config.total_steps)
        log_path = self.out_dir / f"{self.run_name}.jsonl"
        self.model.train()
        # Resume continues the clock rather than restarting it. `state.tokens` survives a
        # preemption and `wall_seconds` is restored beside it, so zeroing the origin here would
        # divide every token the run has ever processed by the seconds since the last resume —
        # and `tokens_per_second` is the number that says whether a rented instance is on budget.
        started = time.time() - self.state.wall_seconds

        stream = self.sampler.batches(self.state.step * self.accumulation)
        while self.state.step < stop:
            learning_rate = config.lr_at(self.state.step)
            for group in self.optimizer.param_groups:
                group["lr"] = learning_rate

            self.optimizer.zero_grad(set_to_none=True)
            running, counted = 0.0, 0
            for _ in range(self.accumulation):
                micro_step, indices = next(stream)
                sequences = self.corpus.batch(indices)
                if self.tasks is None:
                    framed = None
                    batch = torch.from_numpy(sequences).to(self.device, non_blocking=True)
                    kwargs = {"tokens": batch}
                else:
                    # Keyed on the microbatch step, not on a counter this object advances: a
                    # resume reconstructs the sequence order from a step number and the tasks
                    # have to be the same function of it, or the curve gets a seam at the
                    # preemption exactly as a mis-restored optimizer would.
                    framed = self.tasks.build(
                        sequences,
                        [self.corpus.population_of(int(i)) for i in indices],
                        step=micro_step,
                        device=self.device,
                    )
                    kwargs = framed.loss_kwargs()
                    batch = framed.tokens
                with _autocast(self.device, config.precision):
                    out = self.model.loss(**kwargs)
                # Divided by the accumulation so the optimizer sees the mean over the whole step,
                # not the sum — otherwise the effective learning rate would scale with whatever
                # microbatch the host happened to fit, which §4.1 forbids.
                (out.loss / self.accumulation).backward()
                running += float(out.loss.detach()) / self.accumulation
                counted += batch.numel()

            norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), config.grad_clip)
            self.optimizer.step()

            self.state.step += 1
            self.state.tokens += counted
            self.state.wall_seconds = time.time() - started

            if self.state.step % config.log_every == 0 or self.state.step == stop:
                record = {
                    "step": self.state.step,
                    "tokens": self.state.tokens,
                    "fraction": self.state.tokens / config.tokens_processed,
                    "loss": round(running, 5),
                    "bits_per_token": round(running / math.log(2), 5),
                    "lr": learning_rate,
                    "grad_norm": round(float(norm), 4),
                    "seconds": round(self.state.wall_seconds, 1),
                    "tokens_per_second": round(
                        self.state.tokens / max(self.state.wall_seconds, 1e-9)
                    ),
                }
                if self.tasks is not None:
                    # §4.2's shares are frozen, so the realized mixture belongs in the log next
                    # to the loss rather than in a summary written afterwards: a shortfall is a
                    # fact about the run and this is where a reader would look for it.
                    record["tasks"] = {
                        task: round(share, 4)
                        for task, share in self.tasks.realized_shares().items()
                    }
                    shortfalls = {
                        key: value
                        for key, value in self.tasks.counts.items()
                        if key.startswith(("shortfall/", "fallback/"))
                    }
                    if shortfalls:
                        record["task_shortfalls"] = shortfalls
                    record["pad_tokens"] = self.tasks.counts.get("pad_tokens", 0)
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
                if on_log is not None:
                    on_log(record)

            if self.state.step % config.checkpoint_every == 0:
                self.save(self.out_dir / f"{self.run_name}_rolling.pt")
            fraction = self._kept.get(self.state.step)
            if fraction is not None:
                self.save(
                    self.out_dir / f"{self.run_name}_f{fraction:g}.pt".replace("0.", "p"),
                    fraction=fraction,
                )

        return self.state

    # --- evaluation --------------------------------------------------------

    @torch.no_grad()
    def evaluate(self, held_out: PackedCorpus, *, limit: int | None = None) -> dict:
        """Validation loss over a held-out corpus, in nats, bits-per-token and bits-per-byte.

        §8.3 reports **bits-per-byte** so the comparison is tokenizer-independent, and stage 10's
        `.bytes` sidecar is what makes that computable — the denominator is the UTF-8 bytes of the
        text a sequence's tokens stand for, per sequence, summed. Reported by population as well
        as in aggregate, because §8.3 asks for it by script and the aggregate otherwise moves with
        the mixture rather than with the model.

        **Held-out scoring is plain LM for both arms, deliberately.** §4.5's primary endpoint is
        validation BPB, and a BPB that moved with a sampled task mixture would not be a property
        of the model. The corruption tasks are measured by §8.3's downstream metrics instead.

        ``out.scored`` rather than ``tokens.numel()``: the two arms cover different numbers of
        positions with the same sequence, and multiplying a per-token average by the sequence
        length would silently rescale one of them. See :class:`~ravaan.models.ar.LossOutput`.
        """
        self.model.eval()
        count = min(len(held_out), limit or len(held_out))
        totals: dict[str, list[float]] = {}
        for index in range(count):
            tokens = torch.from_numpy(held_out[index]).unsqueeze(0).to(self.device)
            with _autocast(self.device, self.config.precision):
                out = self.model.loss(tokens)
            scored = float(out.scored)
            nats = float(out.nats) * scored
            population = held_out.population_of(index)
            for key in ("all", population):
                entry = totals.setdefault(key, [0.0, 0.0, 0.0, 0.0])
                entry[0] += nats
                entry[1] += scored
                entry[2] += held_out.text_bytes(index)
                entry[3] += 1
        self.model.train()

        report = {}
        for key, (nats, scored_tokens, text_bytes, sequences) in totals.items():
            report[key] = {
                "nats_per_token": nats / max(scored_tokens, 1),
                "bits_per_token": nats / max(scored_tokens, 1) / math.log(2),
                "bits_per_byte": nats / max(text_bytes, 1) / math.log(2),
                "scored_tokens": int(scored_tokens),
                "sequences": int(sequences),
            }
        return report


def throughput(
    model: nn.Module,
    config: TrainingConfig,
    *,
    device: str = "cuda",
    microbatch: int = 8,
    steps: int = 20,
    tasks: TaskGenerator | None = None,
    corpus: PackedCorpus | None = None,
) -> dict:
    """§G2's measurement: tokens a second, and what it implies for the six core runs.

    G2 is "measured throughput implies 6 core runs ≤ $90", and this is the number that gate reads.
    Run it on the instance type you intend to rent, not on a proxy.

    **Pass ``tasks`` and ``corpus`` if the run will have them, which every core run will.** §4.2's
    generator decodes and re-encodes a quarter of every batch through SentencePiece on the CPU,
    measured at ~180 ms of single-core work per 256-sequence step — the same order as the step
    itself on a 4090. A throughput figure taken on the bare objective would flatter the gate by
    measuring a run nobody intends to make. Without a corpus the generator is fed random ids,
    which costs the right amount of tokenizer work on text that is not Urdu; with one it is exact.
    """
    device_ = torch.device(device)
    model = model.to(device_).train()
    optimizer = build_optimizer(model, config)
    random_ids = np.random.default_rng(0).integers(
        0, model.config.vocab_size, size=(microbatch, config.sequence_length)
    )
    populations = ["urdu"] * microbatch

    def one_step(step: int) -> None:
        if tasks is None:
            batch = torch.randint(
                0, model.config.vocab_size, (microbatch, config.sequence_length), device=device_
            )
            kwargs = {"tokens": batch}
        else:
            if corpus is not None:
                indices = np.arange(microbatch) % len(corpus)
                sequences = corpus.batch(indices)
                pops = [corpus.population_of(int(i)) for i in indices]
            else:
                sequences, pops = random_ids, populations
            kwargs = tasks.build(sequences, pops, step=step, device=device_).loss_kwargs()
        with _autocast(device_, config.precision):
            model.loss(**kwargs).loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)

    for warm in range(3):  # warmup: the first steps pay for allocator and kernel selection
        one_step(warm)

    if device_.type == "cuda":
        torch.cuda.synchronize()
    started = time.time()
    for step in range(steps):
        one_step(3 + step)
    if device_.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.time() - started

    tokens = steps * microbatch * config.sequence_length
    per_second = tokens / elapsed
    run_hours = config.tokens_processed / per_second / 3600
    return {
        "device": str(device_),
        "microbatch": microbatch,
        "tasks": None if tasks is None else tasks.to_dict()["tasks_version"],
        "tokens_per_second": round(per_second),
        "seconds_per_step": round(elapsed / steps, 4),
        "hours_per_run": round(run_hours, 2),
        "hours_for_6_runs": round(run_hours * 6, 1),
        # §9 assumes RTX 4090-class spot at ~$0.35/hr, to be verified against live pricing in W6.
        "usd_for_6_runs_at_0.35": round(run_hours * 6 * 0.35, 2),
        "g2_passes_at_0.35": run_hours * 6 * 0.35 <= 90,
    }


__all__ = ["Trainer", "TrainState", "build_optimizer", "throughput"]
