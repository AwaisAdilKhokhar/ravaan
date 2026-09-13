"""§4.2's framings, built for inference instead of for a loss (PRD §4.2, §8.2).

A model trained on `<lm>`-prefixed sequences and prompted with bare text is being asked a question
it was never taught, and the answer tells you about the prompt rather than about the model. So the
layouts here are the same layouts :mod:`ravaan.training.tasks` builds — token for token, including
the parts that look like mistakes — and the two are pinned against each other in
``tests/test_sampling.py`` so a change to one that is not made to the other fails a test rather
than quietly degrading every number in §8.3.

Each builder returns a :class:`Prompt` for one arm, because the arms genuinely disagree about what
a conditional prompt *is*:

* The **AR** arm gets the framing up to the point where the answer starts, and appends. Its
  ``locked`` is all-True: the decoder writes past the end, never into it.
* The **DIFF** arm gets a full canvas — framing, `<mask>` where the answer goes, and whatever
  follows it — because a diffusion decode has a fixed width from its first forward pass.

**That difference is a result, not an inconvenience.** §4.1 matches the arms on parameters, data,
tokenizer and objective budget; it cannot match them on this, because "how long is the answer" is
a question the AR factorization answers for itself and the absorbing-state one cannot. Any metric
scored against a gold string therefore hands the diffusion arm a hint the AR arm has to infer, and
§8.3's infill exact-match is where it will show up largest. The honest handling is to say so and
to report the length the diffusion arm was given; the dishonest one is to let the difference sit
inside a helper. Hence ``Prompt.hinted_length``, which is not None exactly when a length was given
away.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ravaan.training.tasks import FramingTokens

ARMS = ("ar", "diff")


@dataclass(frozen=True, slots=True)
class Prompt:
    """One framed question. ``tokens`` is what the decoder is handed; ``locked`` is what it may
    not touch — all-True for AR, since that decoder only ever appends."""

    tokens: tuple[int, ...]
    locked: tuple[bool, ...]
    task: str
    arm: str
    #: Set when the framing had to state the answer's length. See the module docstring.
    hinted_length: int | None = None

    def __post_init__(self) -> None:
        if len(self.tokens) != len(self.locked):
            raise ValueError(
                f"{len(self.tokens)} tokens against {len(self.locked)} locked flags"
            )

    @property
    def open_positions(self) -> int:
        return sum(1 for flag in self.locked if not flag)


def _check(arm: str, mask_id: int | None) -> None:
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")
    if arm == "diff" and mask_id is None:
        raise ValueError(
            "the diffusion arm needs `mask_id` — its canvas is `<mask>` everywhere the answer "
            "goes, and there is no arm-agnostic default for the absorbing state"
        )


def _canvas(prefix: Sequence[int], span: int, suffix: Sequence[int], mask_id: int) -> Prompt:
    tokens = (*prefix, *([mask_id] * span), *suffix)
    locked = (*([True] * len(prefix)), *([False] * span), *([True] * len(suffix)))
    return Prompt(tokens, locked, task="", arm="diff", hinted_length=span)


def lm(
    framing: FramingTokens,
    arm: str,
    *,
    prefix: Sequence[int] = (),
    length: int | None = None,
    mask_id: int | None = None,
) -> Prompt:
    """§4.2's plain-LM row: ``<lm>`` then the text. ``prefix`` may be empty — that is the
    unconditional sample, and the one G3's coherence half is about.

    ``length`` is the full canvas width and is required for the diffusion arm only.
    """
    _check(arm, mask_id)
    head = (framing.lm, *prefix)
    if arm == "ar":
        return Prompt(head, tuple([True] * len(head)), task="lm", arm="ar")
    if length is None or length <= len(head):
        raise ValueError(
            f"the diffusion arm needs a canvas longer than its {len(head)}-token prompt; "
            f"got length={length}"
        )
    built = _canvas(head, length - len(head), (), int(mask_id))
    return Prompt(
        built.tokens, built.locked, task="lm", arm="diff", hinted_length=built.hinted_length
    )


def infill(
    framing: FramingTokens,
    arm: str,
    *,
    prefix: Sequence[int],
    suffix: Sequence[int],
    span: int,
    mask_id: int | None = None,
) -> Prompt:
    """§4.1's infilling row. AR gets the FIM rearrangement; DIFF gets the hole left in place.

    The AR layout is ``<infill> <fim_prefix> prefix <fim_suffix> suffix <fim_middle>`` and the
    answer follows it — which is why this arm is not told ``span`` and has to decide for itself
    where the middle ends. The diffusion layout is ``<infill> prefix <mask>*span suffix``, which
    is the training layout with the maskable window made fully masked.
    """
    _check(arm, mask_id)
    if span < 1:
        raise ValueError(f"span must be at least one token, got {span}")
    if arm == "ar":
        tokens = (
            framing.infill,
            framing.fim_prefix,
            *prefix,
            framing.fim_suffix,
            *suffix,
            framing.fim_middle,
        )
        return Prompt(tokens, tuple([True] * len(tokens)), task="infill", arm="ar")
    built = _canvas((framing.infill, *prefix), span, suffix, int(mask_id))
    return Prompt(
        built.tokens, built.locked, task="infill", arm="diff", hinted_length=span
    )


def pair(
    framing: FramingTokens,
    arm: str,
    *,
    marker: int,
    source_marker: int,
    target_marker: int,
    source: Sequence[int],
    target_length: int | None = None,
    task: str = "pair",
    mask_id: int | None = None,
) -> Prompt:
    """§4.2's conditional framing: ``<task> <src-mark> source <sep> <tgt-mark>`` then the answer.

    Identical across the arms up to the target marker, which is exactly how
    :meth:`~ravaan.training.tasks.TaskGenerator._frame_pair` builds it — the two arms differ in
    how they *score* the target, not in where it sits. Everything after the target marker is the
    answer: appended by the AR decoder, masked for the diffusion one.
    """
    _check(arm, mask_id)
    head = (marker, source_marker, *source, framing.sep, target_marker)
    if arm == "ar":
        return Prompt(head, tuple([True] * len(head)), task=task, arm="ar")
    if not target_length or target_length < 1:
        raise ValueError(
            f"the diffusion arm needs a target length for task {task!r} and got "
            f"{target_length!r} — see the module docstring on what this costs"
        )
    built = _canvas(head, target_length, (), int(mask_id))
    return Prompt(
        built.tokens, built.locked, task=task, arm="diff", hinted_length=target_length
    )


def transliterate(
    framing: FramingTokens,
    arm: str,
    *,
    source: Sequence[int],
    direction: str = "ur2rom",
    target_length: int | None = None,
    mask_id: int | None = None,
) -> Prompt:
    """§4.2's "Roman ↔ native" row, either way round.

    ``direction`` is ``"ur2rom"`` or ``"rom2ur"``; the markers follow the source and target
    scripts, as in training.
    """
    if direction not in ("ur2rom", "rom2ur"):
        raise ValueError(f"direction must be 'ur2rom' or 'rom2ur', got {direction!r}")
    source_marker = framing.ur if direction == "ur2rom" else framing.rom
    target_marker = framing.rom if direction == "ur2rom" else framing.ur
    return pair(
        framing,
        arm,
        marker=framing.translit,
        source_marker=source_marker,
        target_marker=target_marker,
        source=source,
        target_length=target_length,
        task=f"translit/{direction}",
        mask_id=mask_id,
    )


def restore(
    framing: FramingTokens,
    arm: str,
    *,
    source: Sequence[int],
    target_length: int | None = None,
    mask_id: int | None = None,
) -> Prompt:
    """§4.2's OCR/spacing restoration row.

    The source marker is `<restore>` again rather than a script marker — the layout
    :meth:`~ravaan.training.tasks.TaskGenerator._frame` builds for this task repeats the task
    token in the source slot. It reads like a slip and it is what the model was trained on, so it
    is what inference has to send. `tests/test_sampling.py` pins it against the trainer.
    """
    return pair(
        framing,
        arm,
        marker=framing.restore,
        source_marker=framing.restore,
        target_marker=framing.ur,
        source=source,
        target_length=target_length,
        task="restore",
        mask_id=mask_id,
    )


def codeswitch(
    framing: FramingTokens,
    arm: str,
    *,
    source: Sequence[int],
    target_length: int | None = None,
    mask_id: int | None = None,
) -> Prompt:
    """§4.2's code-switch row: a Roman-injected source back to native Urdu."""
    return pair(
        framing,
        arm,
        marker=framing.codeswitch,
        source_marker=framing.rom,
        target_marker=framing.ur,
        source=source,
        target_length=target_length,
        task="codeswitch",
        mask_id=mask_id,
    )


__all__ = [
    "ARMS",
    "Prompt",
    "codeswitch",
    "infill",
    "lm",
    "pair",
    "restore",
    "transliterate",
]
