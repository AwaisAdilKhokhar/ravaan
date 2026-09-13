"""Reading stage 10's packed corpus — the input side of every training run.

Stage 10 writes a flat little-endian token array per stream plus a JSON manifest, and this is the
other end of that contract. Nothing here re-derives anything about the corpus: the sequence length,
the dtype, the byte order and the per-sequence byte counts all come off the manifest, so a corpus
packed with different settings is read correctly or refused, never guessed at.

**Sequences are the unit, and they are already fixed length.** §6.3.10 packs to exactly
``sequence_length`` tokens with no padding anywhere, so a shard of *n* bytes holds exactly
``n / itemsize / sequence_length`` sequences and indexing is arithmetic rather than a scan. That
is what makes an epoch a permutation of an integer range instead of a shuffle of a token stream.

**An epoch is a permutation, and §4.3 needs ~396 of them.** At arm A's 25M unique tokens against
9.9B processed, the same sequence is seen roughly four hundred times, so the order it is seen in
is not a detail — a stream that walked the corpus in shard order would give every epoch the same
curriculum. :class:`SequenceSampler` permutes globally per epoch from a seed derived from the run
seed and the epoch number, which makes the order reproducible without storing it.

**The byte sidecar is carried, not dropped.** §8.3 reports bits-per-byte and §4.5 bootstraps over
sequences, so each sequence's UTF-8 byte count has to survive the trip from stage 10 to the
evaluation table. :meth:`PackedCorpus.text_bytes` is that number, per sequence, in the same index
space as the tokens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_DTYPES = {"uint16": np.dtype("<u2"), "uint32": np.dtype("<u4")}


@dataclass(frozen=True, slots=True)
class ShardHandle:
    """One packed shard, opened lazily and memory-mapped rather than read.

    Memory-mapped because arm A is ~200 MB and arm-B-sized corpora were budgeted at 800 MB, and
    because a training job that also holds the model, the optimizer state and a batch has better
    uses for resident memory than a corpus it touches one sequence at a time.
    """

    path: Path
    bytes_path: Path
    stream: str
    population: str
    split: str
    arm: str | None
    sequences: int
    tokens: int


class PackedCorpus:
    """A view over stage 10's output, filtered to one split and arm.

    The filter is not a convenience. §6.3.10 packs each arm independently and each population into
    its own stream, so "arm A's training data" is a set of streams rather than a directory, and a
    loader that took the directory would silently train on the held-out sets.
    """

    def __init__(
        self,
        root: str | Path,
        manifest: str | Path | None = None,
        *,
        split: str = "train",
        arm: str | None = "A",
        populations: tuple[str, ...] | None = None,
    ) -> None:
        self.root = Path(root)
        manifest_path = Path(manifest) if manifest else self.root / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"no packed-corpus manifest at {manifest_path} — stage 10 writes it alongside the "
                "shards, and a corpus read without one has no tokenizer identity"
            )
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        layout = payload["layout"]
        if layout["byte_order"] != "little":
            raise ValueError(f"unsupported byte order {layout['byte_order']!r}")
        self.dtype = _DTYPES[layout["dtype"]]
        self.sequence_length = int(layout["sequence_length"])
        self.tokenizer = payload["tokenizer"]
        if self.tokenizer.get("placeholder"):
            raise ValueError(
                f"this corpus was packed with {self.tokenizer['id']}, a placeholder tokenizer. "
                "Its fertility is a property of UTF-8 rather than of Urdu, and a model trained on "
                "it is a plumbing check — re-pack with §7's tokenizer"
            )

        self.shards: list[ShardHandle] = []
        for record in payload["shards"]:
            if record["split"] != split:
                continue
            if arm is not None and record["arm"] != arm:
                continue
            if populations and record["population"] not in populations:
                continue
            path = self.root / record["path"]
            self.shards.append(
                ShardHandle(
                    path=path,
                    bytes_path=path.with_suffix(".bytes"),
                    stream=record["stream"],
                    population=record["population"],
                    split=record["split"],
                    arm=record["arm"],
                    sequences=int(record["sequences"]),
                    tokens=int(record["tokens"]),
                )
            )
        if not self.shards:
            raise ValueError(
                f"manifest {manifest_path} holds no shards for split={split!r} arm={arm!r} "
                f"populations={populations!r}"
            )

        # A global index: sequence i lives in shard `searchsorted(offsets, i)`. Built once, so
        # every lookup afterwards is two integer operations rather than a walk.
        counts = np.array([s.sequences for s in self.shards], dtype=np.int64)
        self._offsets = np.concatenate([[0], np.cumsum(counts)])
        self._maps: dict[int, np.memmap] = {}
        self._byte_maps: dict[int, np.memmap] = {}

    def __len__(self) -> int:
        return int(self._offsets[-1])

    @property
    def tokens(self) -> int:
        return sum(s.tokens for s in self.shards)

    def _locate(self, index: int) -> tuple[int, int]:
        if not 0 <= index < len(self):
            raise IndexError(f"sequence {index} outside corpus of {len(self):,}")
        shard = int(np.searchsorted(self._offsets, index, side="right") - 1)
        return shard, index - int(self._offsets[shard])

    def _tokens_map(self, shard: int) -> np.memmap:
        cached = self._maps.get(shard)
        if cached is None:
            cached = np.memmap(self.shards[shard].path, dtype=self.dtype, mode="r")
            self._maps[shard] = cached
        return cached

    def __getitem__(self, index: int) -> np.ndarray:
        shard, offset = self._locate(index)
        start = offset * self.sequence_length
        # A copy, not a view into the mapping: the caller is about to hand this to `torch` and a
        # torch tensor sharing a memmap keeps the whole shard pinned for as long as the batch
        # lives, which at 396 epochs means for the whole run.
        return np.asarray(
            self._tokens_map(shard)[start : start + self.sequence_length], dtype=np.int64
        )

    def batch(self, indices: np.ndarray) -> np.ndarray:
        """``(len(indices), sequence_length)`` of token ids, gathered in one allocation."""
        out = np.empty((len(indices), self.sequence_length), dtype=np.int64)
        for row, index in enumerate(indices):
            out[row] = self[int(index)]
        return out

    def text_bytes(self, index: int) -> int:
        """§8.3's denominator for one sequence: the UTF-8 bytes its tokens stand for."""
        shard, offset = self._locate(index)
        cached = self._byte_maps.get(shard)
        if cached is None:
            cached = np.memmap(self.shards[shard].bytes_path, dtype=np.dtype("<u4"), mode="r")
            self._byte_maps[shard] = cached
        return int(cached[offset])

    def population_of(self, index: int) -> str:
        """Which of §6.1's three populations a sequence came from. §8.3 reports BPB by script."""
        shard, _ = self._locate(index)
        return self.shards[shard].population

    def describe(self) -> str:
        by_population: dict[str, int] = {}
        for shard in self.shards:
            by_population[shard.population] = by_population.get(shard.population, 0) + shard.tokens
        total = sum(by_population.values()) or 1
        lines = [
            f"{len(self):,} sequences of {self.sequence_length} — {self.tokens:,} tokens",
            f"tokenizer {self.tokenizer['id']} ({self.tokenizer['fingerprint']})",
        ]
        lines.extend(
            f"  {population:<14} {count:>12,}  {count / total:6.2%}"
            for population, count in sorted(by_population.items())
        )
        return "\n".join(lines)


class SequenceSampler:
    """An epoch-permuting index stream. §4.3's ~396 epochs, in order, reproducibly.

    Deliberately not a `torch.utils.data.Sampler`: the training loop needs to resume mid-epoch
    from a step count after a spot preemption (§9's cost controls require it), which means the
    order has to be a *function* of (seed, epoch) rather than the state of a shuffled iterator.
    Given those two numbers this reconstructs the permutation and seeks into it.
    """

    def __init__(
        self, size: int, batch_size: int, *, seed: int = 0, drop_last: bool = True
    ) -> None:
        if size < batch_size:
            raise ValueError(f"corpus of {size} sequences is smaller than a batch of {batch_size}")
        self.size = size
        self.batch_size = batch_size
        self.seed = seed
        self.drop_last = drop_last

    @property
    def batches_per_epoch(self) -> int:
        if self.drop_last:
            return self.size // self.batch_size
        return -(-self.size // self.batch_size)

    def permutation(self, epoch: int) -> np.ndarray:
        # `default_rng` seeded per epoch rather than one generator advanced across epochs: the
        # second is only reproducible if every epoch before it was drawn, which a resume is not.
        return np.random.default_rng([self.seed, epoch]).permutation(self.size)

    def batches(self, start_step: int = 0):
        """Yield ``(step, indices)`` from ``start_step``, indefinitely.

        Indefinite because §4.3 budgets in *tokens processed*, not epochs — the epoch count is a
        consequence of the arm's unique-token budget, and the loop stops on the token target.
        """
        per_epoch = self.batches_per_epoch
        step = start_step
        while True:
            epoch, within = divmod(step, per_epoch)
            order = self.permutation(epoch)
            for index in range(within, per_epoch):
                start = index * self.batch_size
                yield step, order[start : start + self.batch_size]
                step += 1


__all__ = ["PackedCorpus", "SequenceSampler", "ShardHandle"]
