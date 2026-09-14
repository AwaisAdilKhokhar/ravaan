"""§8.3's infill metrics: exact-match, token-F1, and locked-span preservation.

§4.5 makes infill exact-match one of three Holm-corrected secondary endpoints, and until this
module there was nothing in the repository that could compute it. That matters more than a missing
metric usually would, because **preregistration §8 commits to a scoring rule for it** — dated
2026-09-13, before any result existed — and a preregistered rule with no implementation is a
promise nobody has checked is keepable.

The rule, in one line: **the AR arm's generation is cut to the gold span's token length.**

Why that is the symmetric repair and not a generous one is argued in the preregistration and in
`reports/pilot_coherence.md` §7; the short version is that §4.2's FIM framing puts the middle at
the end of the sequence with no terminator after it, so the AR arm was never taught where an
infill *ends*, while the diffusion arm is handed the width of its answer before its first forward
pass because an absorbing-state canvas has a fixed width. Scoring AR unbounded would compare a
bounded answer against an unbounded one and inflate toward diffusion. So both arms are told the
length, and the residue — which the report has to state — is that **infill exact-match measures
content and not length, for either arm**.

Three consequences are built into the numbers here rather than left to a caller:

* :attr:`InfillScore.truncated` counts the items where the rule actually bit, so the report can
  say how much work it is doing rather than only that it was applied.
* :attr:`InfillScore.exact_untruncated` is the same metric with the rule switched off. It is a
  diagnostic and **not** the endpoint — the endpoint is preregistered — but reporting only the
  favourable half of a rule you chose is how a preregistration stops meaning anything.
* :attr:`InfillScore.locked_preserved` is §8.3's "with locked-span preservation". §8.1 asserts it
  as an invariant inside the decoders; here it is a *reported* rate, because an invariant that
  holds is worth one number in a table and a caller that builds prompts by hand can still break it.

Everything is scored on **tokens**, not characters. §8.3 names token-F1, and the token is the unit
that makes the arms comparable at all: the diffusion arm's canvas is token-wide, so a
character-level length hint would not be the hint it was actually given. Character-level metrics
(CER, chrF) are the transliteration and restoration rows, and they are a different module.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

#: Preregistration §8, 2026-09-13. Carried as a constant so the run record can name the rule it
#: scored under, and so a later change to the rule is a change to a named thing.
TRUNCATION_RULE = "ar-generation-cut-to-gold-token-length"

INFILL_VERSION = "1.0.0"


def truncate_to_gold(generated: Sequence[int], gold: Sequence[int], *, arm: str) -> list[int]:
    """Preregistration §8's rule, applied to one item.

    Only the AR arm is cut. The diffusion arm's generation is already exactly ``len(gold)`` tokens
    long — it decoded a canvas of that width — so cutting it is either a no-op or a sign that the
    caller built the canvas wrong, and silently trimming would hide that. The rule is therefore
    written as "cut AR" rather than "cut both to the gold length", which is the same operation on
    well-formed input and a different one on malformed input.
    """
    if arm not in ("ar", "diff"):
        raise ValueError(f"arm must be 'ar' or 'diff', got {arm!r}")
    if arm == "diff":
        if len(generated) != len(gold):
            raise ValueError(
                f"a diffusion infill returned {len(generated)} tokens against a {len(gold)}-token "
                "gold span. That arm decodes a fixed-width canvas, so this is a prompt built at "
                "the wrong width rather than something to truncate away"
            )
        return list(generated)
    return list(generated[: len(gold)])


def token_f1(predicted: Sequence[int], gold: Sequence[int]) -> float:
    """Bag-of-tokens F1 — multiset overlap, the SQuAD form, on ids rather than words.

    Multiset rather than set: a gold span that says the same token twice is only half-answered by
    a prediction that says it once, and set overlap would score that 1.0. With the truncation rule
    in force both sides are the same length, so precision and recall coincide and F1 is the
    overlap rate; the general form is kept anyway, because ``exact_untruncated``'s diagnostic runs
    without the rule and A2's ablation may yet be scored a different way.
    """
    if not predicted and not gold:
        return 1.0
    if not predicted or not gold:
        return 0.0
    overlap = sum((Counter(predicted) & Counter(gold)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(predicted)
    recall = overlap / len(gold)
    return 2 * precision * recall / (precision + recall)


@dataclass(frozen=True, slots=True)
class InfillItem:
    """One scored infill. ``generated`` is the raw decode, before the truncation rule."""

    arm: str
    gold: tuple[int, ...]
    generated: tuple[int, ...]
    scored: tuple[int, ...]
    exact: bool
    exact_untruncated: bool
    f1: float
    truncated: bool
    locked_preserved: bool

    @classmethod
    def of(
        cls,
        *,
        arm: str,
        gold: Sequence[int],
        generated: Sequence[int],
        locked_preserved: bool = True,
    ) -> InfillItem:
        scored = truncate_to_gold(generated, gold, arm=arm)
        return cls(
            arm=arm,
            gold=tuple(gold),
            generated=tuple(generated),
            scored=tuple(scored),
            exact=list(scored) == list(gold),
            exact_untruncated=list(generated) == list(gold),
            f1=token_f1(scored, gold),
            truncated=len(scored) != len(generated),
            locked_preserved=bool(locked_preserved),
        )

    def to_dict(self) -> dict:
        return {
            "arm": self.arm,
            "gold_length": len(self.gold),
            "generated_length": len(self.generated),
            "exact": self.exact,
            "exact_untruncated": self.exact_untruncated,
            "f1": self.f1,
            "truncated": self.truncated,
            "locked_preserved": self.locked_preserved,
        }


@dataclass(frozen=True, slots=True)
class InfillScore:
    """§8.3's infill row for one arm over one set of items."""

    items: int
    exact_match: float
    token_f1: float
    exact_untruncated: float
    truncated: float
    locked_preserved: float
    mean_generated_length: float
    mean_gold_length: float
    truncation_rule: str = TRUNCATION_RULE
    version: str = INFILL_VERSION

    @classmethod
    def of(cls, items: Sequence[InfillItem]) -> InfillScore:
        if not items:
            raise ValueError("no items to score")
        return cls(
            items=len(items),
            exact_match=mean(1.0 if item.exact else 0.0 for item in items),
            token_f1=mean(item.f1 for item in items),
            exact_untruncated=mean(1.0 if item.exact_untruncated else 0.0 for item in items),
            truncated=mean(1.0 if item.truncated else 0.0 for item in items),
            locked_preserved=mean(1.0 if item.locked_preserved else 0.0 for item in items),
            mean_generated_length=mean(len(item.generated) for item in items),
            mean_gold_length=mean(len(item.gold) for item in items),
        )

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "exact_match": self.exact_match,
            "token_f1": self.token_f1,
            "exact_untruncated": self.exact_untruncated,
            "truncated": self.truncated,
            "locked_preserved": self.locked_preserved,
            "mean_generated_length": self.mean_generated_length,
            "mean_gold_length": self.mean_gold_length,
            "truncation_rule": self.truncation_rule,
            "version": self.version,
        }


__all__ = [
    "INFILL_VERSION",
    "TRUNCATION_RULE",
    "InfillItem",
    "InfillScore",
    "token_f1",
    "truncate_to_gold",
]
