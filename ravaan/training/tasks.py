"""§4.2's task mixture, framed for both arms — the other half of §4.1's "same training tasks".

`ravaan.data.corruption` damages text. This turns clean packed sequences into the exact tensors
each arm trains on, and it is the single place where §4.1's table becomes code:

======================  ==================================  ==================================
§4.2 objective          Ravaan-AR                           Ravaan-DIFF
======================  ==================================  ==================================
Plain-text LM (65%)     next token over the sequence        random-ratio masking, loss on masked
Span infilling (10%)    FIM: prefix / suffix / middle       middle span masked, prefix+suffix kept
Transliteration (10%)   ``<src> <sep> <tgt>``, loss on tgt  source kept unmasked, target diffused
Restoration (8%)        same framing                        same framing
Code-switch (7%)        same framing                        same framing
======================  ==================================  ==================================

**The three conditional tasks produce byte-identical token layouts for both arms.** Same framing
tokens, same order, same lengths — the arms differ only in *what is done with the target half*:
AR predicts it left to right with the source masked out of the loss, DIFF diffuses it with the
source pinned via ``keep``. That is §4.1's "differ in exactly one thing" holding at the level of
the batch, not just at the level of the model, and it is why the framing lives here rather than
twice in two arms' dataloaders.

**Infilling is the one task where the layouts differ, and it has to be.** FIM *is* a reordering —
it is how an autoregressive model is given a suffix to condition on — while the diffusion arm
conditions on a suffix by simply not masking it. §4.1 states both in the same row. The consequence
worth naming: AR's FIM example is scored over the whole rearranged sequence, as published FIM is,
while DIFF's is scored over the middle span alone. That asymmetry is intrinsic to the objectives
and already present in plain LM (AR scores every position, the ELBO scores the masked ones), which
is why §4.3 insists the report state that the diffusion number is a bound and lead with downstream
metrics.

**The realized mixture is measured, not assumed.** Two of the five tasks can only be built from
native-script text, so a batch of Roman-Urdu sequences cannot supply them. Rather than drawing a
task per sequence and silently falling back — which would bend §4.2's frozen shares by the
population mixture, about 6 points at arm A's 23.53% Roman share — :class:`TaskGenerator`
apportions each batch to §4.2's shares first and then assigns the constrained tasks to eligible
sequences. Whatever it still cannot place is counted in ``shortfall/<task>`` and shows up in the
run log, so a deviation from a frozen share is visible rather than inferred.

**Sequence budget.** Every framed sequence is exactly ``sequence_length`` tokens, because the
corpus is and because §4.3's token accounting is over tokens *processed*. The conditional tasks
cannot hit that exactly by construction — the corrupted source re-tokenizes to a length nothing
knows in advance — so :meth:`TaskGenerator.build` fits the clean window to the budget in at most
``max_fit_rounds`` re-encodes and pads the remainder. Padding is masked out of attention and out
of the loss, and counted in ``pad_tokens`` so the waste is a number in the log rather than a
rounding error nobody looked at.

The default of four rounds is where that curve bends, measured on the pilot corpus at batch 64:

====== ===================== ============ ==================
rounds ms per 64 sequences   padding      pairs truncated
====== ===================== ============ ==================
2      36                    0.75%        25 / 144
**4**  **45**                **0.59%**    **7 / 144**
6      60                    0.38%        7 / 144
8      66                    0.30%        7 / 144
====== ===================== ============ ==================

**That cost is not free and G2 has to see it.** 45 ms per 64 sequences is ~180 ms of single-core
work per 256-sequence optimizer step, against a step time on a 4090 that is of the same order. So
`ravaan.training.loop.throughput` builds tasks by default rather than measuring the bare objective
— G2 is "measured throughput implies 6 core runs <= $90" and a number that left this out would be
measuring a run nobody is going to make.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
import torch
from torch import Tensor

from ravaan.data.corruption import (
    CORRUPTION_VERSION,
    CorruptionConfig,
    code_switch,
    corrupt_restore,
    romanize,
)
from ravaan.models.ar import IGNORE_INDEX

# §4.2's table, frozen. "These shares are a hypothesis, frozen before Stage C and not tuned
# afterwards" — so they are a module constant and a change to them is a change to the experiment.
TASK_SHARES: dict[str, float] = {
    "lm": 0.65,
    "infill": 0.10,
    "translit": 0.10,
    "restore": 0.08,
    "codeswitch": 0.07,
}

# Which of §6.1's populations each task can be built from. `None` means any.
#
# Transliteration and code-switch normalization both need native-script text: the first because a
# rule-based romanizer runs one way only, the second because the *target* of code-switch
# normalization is single-script native text and a `code_switched` document is not that. Neither
# restriction is a limitation of this module — a Roman-Urdu sentence has no native original on
# disk to be the answer.
TASK_POPULATIONS: dict[str, tuple[str, ...] | None] = {
    "lm": None,
    "infill": None,
    "restore": None,
    "translit": ("urdu",),
    "codeswitch": ("urdu",),
}

TASKS_VERSION = "1.0.0"

__all__ = [
    "TASKS_VERSION",
    "TASK_POPULATIONS",
    "TASK_SHARES",
    "FramingTokens",
    "SentencePieceCodec",
    "TaskBatch",
    "TaskGenerator",
    "TextCodec",
]


# ---------------------------------------------------------------------------
# The seams: the tokenizer, and §7's framing pieces
# ---------------------------------------------------------------------------


@runtime_checkable
class TextCodec(Protocol):
    """What the task generator needs from §7's tokenizer: both directions.

    Stage 10 only ever needed ``encode``; the corruptions are text transforms, so a clean sequence
    has to come back to text before it can be damaged and go forward again after. A round trip is
    not required to be the identity and nothing here assumes it is — the *target* side is always
    the re-encoding of the decoded text, never the original ids, so source and target are always
    two encodings of the same tokenizer's output rather than one of each.
    """

    def encode(self, text: str) -> list[int]: ...

    def decode(self, ids: Sequence[int]) -> str: ...


class SentencePieceCodec:
    """:class:`~ravaan.data.packing.SentencePieceTokenizer` with the decode half bound in."""

    def __init__(self, model_path: str) -> None:
        from ravaan.data.packing import SentencePieceTokenizer  # noqa: PLC0415

        self._tokenizer = SentencePieceTokenizer(model_path)

    @property
    def tokenizer(self):  # noqa: ANN201 - passthrough for callers that want the manifest fields
        return self._tokenizer

    def encode(self, text: str) -> list[int]:
        return self._tokenizer.encode(text)

    def decode(self, ids: Sequence[int]) -> str:
        return self._tokenizer.decode(ids)


@dataclass(frozen=True, slots=True)
class FramingTokens:
    """§7's twelve framing pieces, by id.

    Read off the corpus manifest rather than off a constant, for the reason `scripts/train.py`
    gives about ``<mask>``: a model pointed at the wrong framing id trains perfectly happily and
    produces a corpus-shaped disaster with no downstream symptom.
    """

    pad: int
    sep: int
    fim_prefix: int
    fim_suffix: int
    fim_middle: int
    lm: int
    infill: int
    translit: int
    restore: int
    codeswitch: int
    ur: int
    rom: int

    #: manifest piece -> field, in §7's own declaration order.
    PIECES = (
        ("<sep>", "sep"),
        ("<fim_prefix>", "fim_prefix"),
        ("<fim_suffix>", "fim_suffix"),
        ("<fim_middle>", "fim_middle"),
        ("<lm>", "lm"),
        ("<infill>", "infill"),
        ("<translit>", "translit"),
        ("<restore>", "restore"),
        ("<codeswitch>", "codeswitch"),
        ("<ur>", "ur"),
        ("<rom>", "rom"),
    )

    @classmethod
    def from_manifest(cls, tokenizer: dict) -> FramingTokens:
        """Build from a packed corpus's ``tokenizer`` record. Refuses a partial one.

        A missing piece is not defaulted. §7 put all twelve *inside* the 16,384 precisely so both
        arms would embed the same vocabulary, and inventing an id here would undo that quietly.
        """
        special = tokenizer.get("special_tokens") or {}
        missing = [piece for piece, _ in cls.PIECES if piece not in special]
        if missing:
            raise ValueError(
                f"the corpus manifest names {len(special)} framing pieces and §4.2 needs all "
                f"twelve — {', '.join(missing)} are absent. Re-write the manifest from §7's "
                "tokenizer (scripts/pack_pilot.py and scripts/pack.py both carry the full set)"
            )
        control = tokenizer.get("control_ids") or {}
        return cls(
            pad=int(control.get("pad", 0)),
            **{field: int(special[piece]) for piece, field in cls.PIECES},
        )


# ---------------------------------------------------------------------------
# The batch
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TaskBatch:
    """One framed microbatch, plus what it was made of.

    ``keep`` is present only for the diffusion arm. The AR arm expresses the same conditioning
    through ``labels`` — a source position carries :data:`IGNORE_INDEX` and contributes no
    gradient and no count — so handing it a ``keep`` it would ignore would be a second, silently
    diverging statement of the same fact.
    """

    tokens: Tensor
    labels: Tensor
    keep: Tensor | None
    padding_mask: Tensor | None
    tasks: tuple[str, ...]
    counts: Counter

    def loss_kwargs(self) -> dict:
        """Exactly what ``model.loss`` takes, so the training loop does not branch on the arm."""
        kwargs: dict = {
            "tokens": self.tokens,
            "labels": self.labels,
            "padding_mask": self.padding_mask,
        }
        if self.keep is not None:
            kwargs["keep"] = self.keep
        return kwargs


# ---------------------------------------------------------------------------
# The generator
# ---------------------------------------------------------------------------


def _apportion(
    shares: dict[str, float], size: int, order: tuple[str, ...], rng: random.Random
) -> dict[str, int]:
    """Apportion ``size`` sequences over ``shares``, unbiased at any batch size.

    A microbatch cannot represent a 7% share exactly, so something has to decide where the
    leftover sequences go — and **the obvious answer is wrong in a way that does not average
    out.** Largest-remainder with a fixed tie-break gives the *same* answer for every batch of the
    same size, so the bias is constant rather than converging: at a microbatch of 4 it assigns
    three plain-LM sequences and one infilling sequence, forever, and §4.2's other three
    objectives never appear at all. Measured on the pilot corpus, which is how it was found.

    So the whole parts are floored and the leftovers are drawn by **systematic sampling over the
    fractional parts** — one uniform draw, then every fractional-part boundary it crosses at
    ``u``, ``u+1``, ``u+2``. That selects exactly the right number of leftovers and gives each
    task an inclusion probability equal to its fractional part, so the expected count is
    ``share × size`` exactly, at every batch size, and the realized mixture converges on §4.2's
    table rather than on whatever the batch size rounds to.

    Stateless, and a pure function of ``rng``: the run's mixture has to be reconstructible from
    (seed, step) after a preemption, so a running ledger of who is owed what is not available.
    """
    exact = {task: shares[task] * size for task in order}
    counts = {task: int(math.floor(value)) for task, value in exact.items()}
    leftovers = size - sum(counts.values())
    if leftovers <= 0:
        return counts

    start = rng.random()
    cumulative = 0.0
    crossed = 0
    for task in order:
        cumulative += exact[task] - counts[task]
        while crossed < leftovers and start + crossed < cumulative:
            counts[task] += 1
            crossed += 1
    # Floating-point drift can leave the last boundary a hair short of the last threshold.
    for task in order[::-1]:
        if crossed >= leftovers:
            break
        counts[task] += 1
        crossed += 1
    return counts


class TaskGenerator:
    """§4.2's mixture, framed for one arm.

    Constructed per arm rather than per call: the arm decides the token layout of an infilling
    example and whether ``keep`` exists at all, so a generator that took the arm as an argument
    would be two generators sharing a name.
    """

    def __init__(
        self,
        codec: TextCodec,
        framing: FramingTokens,
        *,
        arm: str,
        sequence_length: int,
        seed: int = 0,
        shares: dict[str, float] | None = None,
        populations: dict[str, tuple[str, ...] | None] | None = None,
        corruption: CorruptionConfig | None = None,
        max_fit_rounds: int = 4,
    ) -> None:
        if arm not in ("ar", "diff"):
            raise ValueError(f"arm must be 'ar' or 'diff', got {arm!r}")
        self.codec = codec
        self.framing = framing
        self.arm = arm
        self.sequence_length = sequence_length
        self.seed = seed
        self.shares = dict(shares or TASK_SHARES)
        total = sum(self.shares.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"§4.2's shares must sum to 1, got {total:.6f}")
        self.populations = dict(populations or TASK_POPULATIONS)
        self.corruption = corruption or CorruptionConfig()
        self.max_fit_rounds = max_fit_rounds
        self.counts: Counter = Counter()

        # §4.2's order, and also the order constrained tasks get first pick of a batch in: fewest
        # eligible populations first, then largest share. The tightest task chooses first, so a
        # batch that can satisfy the mixture does.
        self._order = tuple(self.shares)
        self._constrained = tuple(
            sorted(
                (t for t in self._order if self.populations.get(t) is not None),
                key=lambda t: (len(self.populations[t] or ()), -self.shares[t], t),
            )
        )

    # --- provenance --------------------------------------------------------

    def to_dict(self) -> dict:
        """What the run's ``config.json`` records. §4.2: "the generator version and seed"."""
        return {
            "tasks_version": TASKS_VERSION,
            "corruption_version": CORRUPTION_VERSION,
            "corruption_fingerprint": self.corruption.fingerprint(),
            "corruption": self.corruption.to_dict(),
            "shares": self.shares,
            "populations": {k: list(v) if v else None for k, v in self.populations.items()},
            "seed": self.seed,
            "arm": self.arm,
            "max_fit_rounds": self.max_fit_rounds,
        }

    # --- assignment --------------------------------------------------------

    def assign(self, populations: Sequence[str], rng: random.Random) -> list[str]:
        """Which task each sequence becomes: §4.2's shares first, then eligibility."""
        size = len(populations)
        targets = _apportion(self.shares, size, self._order, rng)
        order = list(range(size))
        rng.shuffle(order)

        assigned: list[str | None] = [None] * size
        free = set(order)
        for task in self._constrained:
            eligible = self.populations[task] or ()
            need = targets[task]
            for index in order:
                if need == 0:
                    break
                if index in free and populations[index] in eligible:
                    assigned[index] = task
                    free.discard(index)
                    need -= 1
            if need:
                # The batch could not supply it. Counted rather than absorbed: a frozen share that
                # is not being met is a fact about the run, and §4.2 froze these before Stage C.
                self.counts[f"shortfall/{task}"] += need
                targets["lm"] += need

        remaining = [index for index in order if index in free]
        for task in self._order:
            if task in self._constrained:
                continue
            for _ in range(targets[task]):
                if not remaining:
                    break
                assigned[remaining.pop()] = task
        for index in remaining:  # apportionment rounding, never more than a sequence or two
            assigned[index] = "lm"
        return [task or "lm" for task in assigned]

    # --- building ----------------------------------------------------------

    def build(
        self,
        sequences: np.ndarray,
        populations: Sequence[str],
        *,
        step: int = 0,
        device: str | torch.device = "cpu",
    ) -> TaskBatch:
        """Frame ``(batch, sequence_length)`` of clean ids into this arm's training tensors."""
        if sequences.ndim != 2 or sequences.shape[1] != self.sequence_length:
            raise ValueError(
                f"expected (batch, {self.sequence_length}) of packed ids, got {sequences.shape}"
            )
        batch = sequences.shape[0]
        # Seeded from (seed, step) rather than advanced: a resume reconstructs the stream from a
        # step count, exactly as `SequenceSampler` does, so the tasks have to be a function of it.
        # A string key rather than a tuple: `random.Random` stopped accepting tuples in 3.14,
        # and a str seed goes through SHA-512, so it is stable across hosts and releases.
        rng = random.Random(f"{self.seed}:{step}:assign")
        tasks = self.assign(populations, rng)

        length = self.sequence_length
        tokens = np.zeros((batch, length), dtype=np.int64)
        labels = np.full((batch, length), IGNORE_INDEX, dtype=np.int64)
        keep = np.zeros((batch, length), dtype=bool)
        padded = np.ones((batch, length), dtype=bool)
        any_padding = False

        for row in range(batch):
            task = tasks[row]
            row_rng = random.Random(f"{self.seed}:{step}:{row}")
            clean = sequences[row].tolist()
            built = self._frame(task, clean, row_rng)
            if built is None:  # the text was unusable — an empty decode, a degenerate window
                self.counts[f"fallback/{task}"] += 1
                task = tasks[row] = "lm"
                built = self._frame("lm", clean, row_rng)
            row_tokens, row_labels, row_keep, pad = built
            tokens[row] = row_tokens
            labels[row] = row_labels
            keep[row] = row_keep
            if pad:
                any_padding = True
                padded[row, length - pad :] = False
                self.counts["pad_tokens"] += pad
            self.counts[task] += 1
        self.counts["sequences"] += batch

        to = torch.as_tensor
        return TaskBatch(
            tokens=to(tokens).to(device),
            labels=to(labels).to(device),
            keep=to(keep).to(device) if self.arm == "diff" else None,
            padding_mask=to(padded).to(device) if any_padding else None,
            tasks=tuple(tasks),
            counts=self.counts,
        )

    def realized_shares(self) -> dict[str, float]:
        """The mixture that was actually built, against §4.2's table. Goes in the run log."""
        total = self.counts.get("sequences", 0)
        if not total:
            return {}
        return {task: self.counts.get(task, 0) / total for task in self._order}

    # --- the five framings -------------------------------------------------

    def _frame(
        self, task: str, clean: list[int], rng: random.Random
    ) -> tuple[list[int], list[int], list[bool], int] | None:
        if task == "lm":
            return self._frame_lm(clean)
        if task == "infill":
            return self._frame_infill(clean, rng)
        if task == "translit":
            return self._frame_translit(clean, rng)
        if task == "restore":
            return self._frame_pair(
                clean,
                rng,
                marker=self.framing.restore,
                source_marker=self.framing.restore,
                target_marker=self.framing.ur,
                make=lambda text: (corrupt_restore(text, rng, self.corruption), text),
            )
        if task == "codeswitch":
            return self._frame_pair(
                clean,
                rng,
                marker=self.framing.codeswitch,
                source_marker=self.framing.rom,
                target_marker=self.framing.ur,
                make=lambda text: (code_switch(text, rng, self.corruption), text),
            )
        raise ValueError(f"unknown task {task!r}")

    def _frame_lm(self, clean: list[int]) -> tuple[list[int], list[int], list[bool], int]:
        """``<lm>`` then the sequence. One framing token so a sequence carries which objective
        made it — §7 put the marker in the vocabulary for exactly this."""
        length = self.sequence_length
        tokens = [self.framing.lm, *clean[: length - 1]]
        keep = [True] + [False] * (length - 1)
        return tokens, list(tokens), keep, 0

    def _frame_infill(
        self, clean: list[int], rng: random.Random
    ) -> tuple[list[int], list[int], list[bool], int] | None:
        """AR gets §4.1's FIM reordering; DIFF gets the middle span left maskable in place."""
        length = self.sequence_length
        reserved = 4 if self.arm == "ar" else 1
        content = clean[: length - reserved]
        n = len(content)
        if n < 8:
            return None
        # A middle span of 5–50% of the content, with a non-empty prefix and suffix on both sides.
        span = max(1, int(n * rng.uniform(0.05, 0.5)))
        start = rng.randrange(1, max(2, n - span))
        stop = min(n - 1, start + span)
        if stop <= start:
            return None
        prefix, middle, suffix = content[:start], content[start:stop], content[stop:]

        if self.arm == "ar":
            tokens = [
                self.framing.infill,
                self.framing.fim_prefix,
                *prefix,
                self.framing.fim_suffix,
                *suffix,
                self.framing.fim_middle,
                *middle,
            ]
            # Published FIM trains on the whole rearranged sequence, and §4.1 describes this row
            # as a reordering rather than as "loss on target". See the module docstring.
            return tokens, list(tokens), [False] * length, 0

        tokens = [self.framing.infill, *content]
        labels = [IGNORE_INDEX] * length
        keep = [True] * length
        for position in range(1 + start, 1 + stop):
            labels[position] = tokens[position]
            keep[position] = False
        return tokens, labels, keep, 0

    def _frame_translit(
        self, clean: list[int], rng: random.Random
    ) -> tuple[list[int], list[int], list[bool], int] | None:
        """§4.2's "Roman ↔ native" — both directions, drawn evenly.

        The Roman side is synthesized by `ravaan.data.corruption.romanize` in both directions, so
        ``ur → rom`` trains the model to reproduce *that map*. The module docstring there records
        why a rule-based map beats Roman-Urdu-Parl's pairs as training supervision, and §8.2's
        human-written set is what measures what the choice cost.
        """
        if rng.random() < 0.5:
            return self._frame_pair(
                clean,
                rng,
                marker=self.framing.translit,
                source_marker=self.framing.rom,
                target_marker=self.framing.ur,
                make=lambda text: (romanize(text), text),
            )
        return self._frame_pair(
            clean,
            rng,
            marker=self.framing.translit,
            source_marker=self.framing.ur,
            target_marker=self.framing.rom,
            make=lambda text: (text, romanize(text)),
        )

    def _frame_pair(
        self,
        clean: list[int],
        rng: random.Random,
        *,
        marker: int,
        source_marker: int,
        target_marker: int,
        make,
    ) -> tuple[list[int], list[int], list[bool], int] | None:
        """``<task> <src-mark> source <sep> <tgt-mark> target`` — identical for both arms.

        The arms then differ in one thing: AR masks the source out of the *loss* and predicts the
        target left to right; DIFF pins the source with ``keep`` and diffuses the target. Same
        tokens, same positions, same target — §4.1's conditional row, twice.
        """
        length = self.sequence_length
        budget = length - 4
        window = budget // 2
        best: tuple[list[int], list[int]] | None = None
        last: tuple[list[int], list[int]] | None = None

        for attempt in range(self.max_fit_rounds + 1):
            text = self.codec.decode(clean[:window])
            if not text.strip():
                return None
            source_text, target_text = make(text)
            source = self.codec.encode(source_text)
            target = self.codec.encode(target_text)
            total = len(source) + len(target)
            if total == 0:
                return None
            last = (source, target)
            # **Keep the best undershoot, not the last attempt.** The window is an integer number
            # of clean tokens and one of them is worth two or three framed ones, so the fit
            # oscillates around the budget by a few tokens and cannot land on it. Overshooting
            # costs a truncation, which misaligns source and target; undershooting costs a pad
            # token, which does not. So the loop keeps the closest fit that still fits.
            if total <= budget and (best is None or total > len(best[0]) + len(best[1])):
                best = (source, target)
            if total == budget or attempt == self.max_fit_rounds:
                break
            # Total length is close to linear in the window, so one proportional step lands within
            # a few tokens of the budget and the rest is the oscillation above.
            nxt = max(8, min(len(clean), round(window * budget / total)))
            if nxt == window:
                break
            window = nxt

        source, target = best or last or ([], [])
        overflow = len(source) + len(target) - budget
        if overflow > 0:
            # Every attempt overran. Trim both sides by the same fraction so they keep covering
            # the same content, rather than cutting the answer off the target or the question off
            # the source — and count the tokens, not just the events, so the log says how far.
            self.counts["truncated_pairs"] += 1
            self.counts["truncated_tokens"] += overflow
            scale = budget / (len(source) + len(target))
            source = source[: max(1, min(int(len(source) * scale), budget - 1))]
            target = target[: budget - len(source)]
        if not source or not target:
            return None

        tokens = [marker, source_marker, *source, self.framing.sep, target_marker, *target]
        start = len(source) + 4
        pad = length - len(tokens)
        tokens = tokens + [self.framing.pad] * pad

        labels = [IGNORE_INDEX] * length
        keep = [True] * length
        for position in range(start, length - pad):
            labels[position] = tokens[position]
            keep[position] = False
        return tokens, labels, keep, pad
