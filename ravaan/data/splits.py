"""Split creation — stage 9 of the corpus pipeline (PRD §6.3.9).

Stage 9 decides three things at once, and they are the same decision: which documents are held
out for evaluation, which make up the frozen training corpus, and which of those belong to arm A
(U = 25M) as against arm B (U = 100M). PRD §6.1 requires arm A to be "a deterministic, seeded
subsample of the frozen 100M corpus — not a separate collection", and §4.1 requires the two arms
to differ **in size and nothing else**. Both are structural properties of how the assignment is
computed, so they are built in rather than checked afterwards.

**A document's entire fate at this stage is one integer.** ``bucket_of(doc_id)`` hashes the id to
a bucket in ``[0, buckets)``, uniformly and independently of everything about the document, and
every split and arm is a *range of buckets*:

    0                                        arm A   arm B      train_to  val_from      buckets
    |------------------------------------------|-------|-----------|---------|-------------|
    |<------------- arm A -------------->|
    |<------------------- arm B ---------------------->|
    |<------------------------ train ------------------------>|   validation |    test

Five properties follow from that picture, and each is a requirement somewhere in the PRD:

**1. The arms are nested by construction.** Arm A is a prefix of arm B in bucket order, so
``A ⊆ B`` holds for *any* pair of budgets, with no second pass and no stored membership list to
drift. §6.1's "subsample of, not a separate collection" is not a property this stage maintains; it
is a property it cannot violate.

**2. Membership is a per-document function, never "take documents until the budget is full".**
The fill rule is the tempting implementation and it is wrong here: it makes membership depend on
the order the corpus was read, which is the exact defect Finding E caught in session 4 and
`shards.py` was rebuilt around. A bucket range is order-independent, resumable, computable for one
document in isolation, and identical on every machine. It is also what lets Finding G's softened
form apply — a split assignment is a property of one document, so a sampled phase-1 pass estimates
the thresholds honestly, unlike the pair statistics of stages 6 and 7.

**3. Both arms share one held-out set.** The bands are carved from the top of the same number line
for every arm, so arm A, arm B, both models and all seeds are evaluated on identical validation and
test sets. Carving held-out per arm would have made §4.3's primary endpoint — validation BPB on the
A and B curves — a comparison of two numbers computed on different data, which is not a comparison.

**4. Enlarging or shrinking the held-out budget does not move documents between the arms.** The
bands grow downward from the top and the arms grow upward from zero, and the cumulative below an
arm cut does not depend on anything above it. Changing §6.1's ~5K sequences to 8K re-solves the
bands and leaves every arm assignment identical — *while the train pool still covers the arm cuts*.
Once it does not, the arm is truncated and reported in ``unmet_arms``, which is the loud failure
rather than the silent one.

**5. The boundaries are integers.** Buckets, not float thresholds. Stage 8 lost a boundary-only
removal to ``array("f")`` holding 0.80 as 0.80000001 (session 10), and stage 7's threshold is a
float comparison guarded by a sweep. Here the comparison that decides whether a document trains
arm A is ``bucket < cut`` between two ints, which has no boundary behaviour to get wrong.

**What U counts, and why this module does not take §6.1 at face value.**

PRD §6.1 lists per-component targets — ~120M native Urdu ("100M for arm B + ~20% headroom"), ~40M
Roman Urdu, ~10M code-switched — and §4.3 fixes U ∈ {25M, 100M} at ~396 and ~99 epochs. **These do
not describe the same corpus.** Assembling an arm by taking each population's target whole gives
arm A 25M native + 40M Roman + 10M code-switched = **75M unique tokens**, not 25M. Both readings
cannot be right, and §4.3's own arithmetic settles it: 396 × 25M = 9.9B and 99 × 100M = 9.9B, so
epochs are counted over the *whole training set*, and so is the U that the reference paper's law
takes as its independent variable.

The cost of the other reading is not cosmetic. At 70M parameters and the same 9.9B tokens
processed, arm A at a true U = 75M sits **6× short** of C_crit instead of 1.79× past it — the same
class of error as Finding A, in the same direction, on the arm carrying the primary endpoint.
Reproduce with ``python scripts/crossover.py --params 70e6 --unique 75e6 --epochs 132``.

So **U is the total unique-token budget of an arm**, and §6.1's component figures are *pool*
targets: how much to collect, not how much to train on. The arms are assembled from the pools at a
fixed mixture — §6.1's targets in proportion, 120 : 40 : 10 — which is the only corpus mixture the
PRD states. Holding the mixture fixed across arms is what "differ in size and nothing else" means
once there is more than one population; scaling only the native component would confound U with
source mix, which is precisely what §6.1 forbids for the crawl-date case.

**Tokens do not exist yet, and this stage is built so that does not matter.** The tokenizer is
Week 5 (§7, §10) and the freeze is Weeks 3–4, so stage 9 cannot count the tokens its budgets are
denominated in. It therefore measures **characters**, which are exact and available, and converts
with a declared ``chars_per_token`` per population. The conversion happens at *solve* time, not
during the pass, and :meth:`SplitAssigner.plan` serializes the histogram — so when the real
fertility is known in Week 5, the thresholds re-solve from the saved plan in milliseconds without
re-reading a byte of corpus. The estimate being wrong moves where the cuts land; it cannot break
the nesting, the band ordering, or the reproducibility of any assignment.

    plan = SplitAssigner(config)
    for doc in corpus:                       # phase 1: measure
        plan.measure(doc.doc_id, text, label)
    plan.seal()                              # solve the bands and arm cuts
    for doc in corpus:                       # phase 2: assign
        write(plan.assign(doc.doc_id, text, label))
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from array import array
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

__all__ = [
    "SPLITS_VERSION",
    "SPLIT_NAMES",
    "PopulationBands",
    "SplitAssigner",
    "SplitAssignment",
    "SplitConfig",
    "SplitLog",
    "SplitPlan",
    "assign_splits",
    "bucket_of",
    "pair_key",
]

# Bump on any change to which documents land in which split or arm: the salt, the bucket count,
# the band order, the solve. The manifest records it, so a frozen corpus and the checkpoints
# trained on it can be traced to the exact partition that produced them.
SPLITS_VERSION = "1.0.0"

SPLIT_NAMES = ("train", "validation", "test")

# Keyed apart from stage 6's content hashes, stage 7's shingles and stage 8's line hashes, for the
# same reason those are keyed apart from each other: two hash spaces that can collide are one hash
# space with a bug in it.
_SPLIT_PERSON = b"ravaan/split"


def pair_key(doc_id: str, separator: str = "#") -> str:
    """The id a split is decided on, with any per-column suffix removed.

    Stage 8's driver reads a parallel row as two documents, ``id#roman`` and ``id#urdu``, because
    contamination can arrive on either side. Hashing those two strings independently would put a
    sentence's Roman side in train and its Urdu side in test roughly half the time — **the splitter
    would be manufacturing the contamination stage 8 exists to remove**, and the transliteration
    endpoint of §4.5 would be scored against training data. Splitting on the row id keeps a pair
    whole, which is also what §6.1's "~500K deduplicated pairs" presupposes.
    """
    return doc_id.split(separator, 1)[0] if separator else doc_id


def bucket_of(doc_id: str, *, salt: str, buckets: int, separator: str = "#") -> int:
    """Map a document id to a bucket in ``[0, buckets)``, deterministically and order-independently.

    The same primitive as :func:`~ravaan.data.shards.stable_unit`, quantized to an integer at the
    point of use rather than compared as a float. Everything downstream — which split, which arm —
    is an integer comparison against an integer boundary, so no assignment can turn on the binary
    representation of a decimal threshold. Session 10 lost a stage-8 removal to exactly that.

    blake2b keyed to this stage: a document's split must not be correlated with its dedup hash or
    its shingles, or a rule at one stage would silently bias the partition at another.
    """
    digest = hashlib.blake2b(
        f"{salt}\x00{pair_key(doc_id, separator)}".encode(), digest_size=8, person=_SPLIT_PERSON
    ).digest()
    return int.from_bytes(digest, "big") * buckets >> 64


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _default_arm_tokens() -> dict[str, int]:
    return {"A": 25_000_000, "B": 100_000_000}


def _default_population_targets() -> dict[str, int]:
    # PRD §6.1's collection targets, verbatim. They set the *mixture* (their proportions) and the
    # *pool sufficiency check* (their absolute values); they are not arm budgets — see the module
    # docstring on what U counts.
    return {"urdu": 120_000_000, "roman_urdu": 40_000_000, "code_switched": 10_000_000}


def _default_chars_per_token() -> dict[str, float]:
    # ESTIMATES, and the only estimated numbers in this stage. The tokenizer is Week 5 and the
    # freeze is Weeks 3-4, so no measured fertility exists yet; §7 will produce one per script,
    # which is why this is per population rather than a single ratio. The values assume a 16k
    # unigram model splitting an Urdu word of ~5-6 characters into ~1.6 pieces, and Roman Urdu
    # slightly coarser because its subwords are shared with the Latin-script material around them.
    #
    # SplitAssigner reports the characters-per-word it actually measured beside the ratio each
    # population was solved with, so the assumption is auditable in units a reader has intuition
    # for. When §7 lands, re-solve from the saved plan rather than re-reading the corpus.
    return {"urdu": 3.5, "roman_urdu": 4.2, "code_switched": 3.8}


@dataclass(frozen=True, slots=True)
class SplitConfig:
    """Stage 9 settings. Defaults are the Ravaan corpus v1 partition."""

    # PRD §4.3's two arms. Total unique tokens per arm, not per population — see the module
    # docstring. Nesting is automatic: the smaller budget is a prefix of the larger.
    arm_tokens: dict[str, int] = field(default_factory=_default_arm_tokens)

    # §6.1's per-component collection targets. Used for their *ratio* (the corpus mixture, held
    # identical across arms so the arms differ in size and nothing else) and for their absolute
    # values (whether the pool is big enough to have been worth collecting).
    population_targets: dict[str, int] = field(default_factory=_default_population_targets)

    chars_per_token: dict[str, float] = field(default_factory=_default_chars_per_token)

    # §6.1's "~5K sequences, decontaminated", at §5's context length. Two sets rather than one,
    # and the reason is Gate G4 rather than convention: at mid-W10 the gate *reads the arm A
    # curves* and may cut arm B on what it sees. That is a decision taken on validation data, so
    # the number §8.2 finally reports cannot come from the same set. Held out from the pool, not
    # from an arm, so neither arm's U changes when these move.
    heldout_sequences: int = 5_000
    sequence_length: int = 512

    # Resolution of the cumulative histogram the bands are solved from. A boundary lands inside
    # one bucket, so this bounds the budget error at total/buckets — ~0.001% of a native-Urdu
    # pool of a few hundred million characters. Higher costs memory linearly and buys nothing.
    buckets: int = 100_000

    # Versioned into the salt deliberately. A partition is only reproducible if the thing that
    # produced it is named, and re-salting is how you would deliberately re-draw the corpus.
    salt: str = "ravaan/split/v1"

    # Separator marking a per-column suffix on a parallel row's id. See :func:`pair_key`.
    pair_separator: str = "#"

    def __post_init__(self) -> None:
        if not self.arm_tokens:
            raise ValueError("at least one arm is required — the arms are the experiment")
        for name, budget in self.arm_tokens.items():
            if not name:
                raise ValueError("an arm needs a name; it is what the report attributes runs to")
            if budget <= 0:
                raise ValueError(f"arm {name!r} budget must be > 0, got {budget}")
        if not self.population_targets:
            raise ValueError("population_targets is the corpus mixture; it cannot be empty")
        for population, target in self.population_targets.items():
            if target <= 0:
                raise ValueError(f"population {population!r} target must be > 0, got {target}")
            ratio = self.chars_per_token.get(population)
            if ratio is None:
                raise ValueError(
                    f"population {population!r} has a token target and no chars_per_token — "
                    "stage 9 measures characters and cannot budget it without the conversion"
                )
            if ratio <= 0:
                raise ValueError(f"chars_per_token[{population!r}] must be > 0, got {ratio}")
        if self.heldout_sequences < 0:
            raise ValueError(f"heldout_sequences must be >= 0, got {self.heldout_sequences}")
        if self.sequence_length < 1:
            raise ValueError(f"sequence_length must be >= 1, got {self.sequence_length}")
        if self.buckets < 1_000:
            raise ValueError(
                f"buckets must be >= 1000, got {self.buckets} — a coarse histogram puts the "
                "budget error above the precision the arm sizes are quoted to"
            )
        if not self.salt:
            raise ValueError("salt must be set — an unnamed partition is not reproducible")

    # --- derived quantities ------------------------------------------------

    @property
    def populations(self) -> tuple[str, ...]:
        """Budgeted populations, largest target first — the order reports read in."""
        return tuple(
            sorted(self.population_targets, key=lambda p: (-self.population_targets[p], p))
        )

    @property
    def mixture(self) -> dict[str, float]:
        """§6.1's targets as shares. The corpus mixture, identical in every arm."""
        total = sum(self.population_targets.values())
        return {p: t / total for p, t in self.population_targets.items()}

    @property
    def arm_names(self) -> tuple[str, ...]:
        """Arms smallest budget first, which is also nesting order."""
        return tuple(sorted(self.arm_tokens, key=lambda a: (self.arm_tokens[a], a)))

    @property
    def heldout_tokens(self) -> int:
        """Tokens in one held-out set — §6.1's sequence count at §5's context length."""
        return self.heldout_sequences * self.sequence_length

    def population_chars(self, population: str, tokens: float) -> float:
        """Convert a token budget to the characters stage 9 can actually measure."""
        return tokens * self.chars_per_token[population]

    def arm_chars(self, arm: str, population: str) -> float:
        """One arm's character budget for one population, at the fixed mixture."""
        return self.population_chars(population, self.arm_tokens[arm] * self.mixture[population])

    def heldout_chars(self, population: str) -> float:
        """One held-out set's character budget for one population.

        Carved at the same mixture as the arms, so validation composition equals training
        composition. §8.3 reports validation BPB *by script*; if the held-out mixture differed
        from the training mixture, the aggregate BPB would move with the mixture rather than with
        the model, and the A/B curves would not be comparable.
        """
        return self.population_chars(population, self.heldout_tokens * self.mixture[population])

    # --- serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SplitConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"splits_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown splits config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> SplitConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"splits_version": SPLITS_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": SPLITS_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Solved boundaries
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PopulationBands:
    """One population's solved bucket boundaries, and what they actually came out to.

    Every boundary is an integer bucket index. ``target_*`` is what the config asked for and
    ``chars_*`` is what the corpus supplied — reported separately because the difference is the
    finding whenever a budget goes unmet, and averaging them away is how a corpus ends up smaller
    than the report claims.
    """

    population: str
    buckets: int
    test_from: int
    validation_from: int
    train_to: int  # == validation_from; named separately because it is the pool boundary
    arm_cuts: dict[str, int] = field(default_factory=dict)

    total_chars: int = 0
    chars_train: int = 0
    chars_validation: int = 0
    chars_test: int = 0
    chars_by_arm: dict[str, int] = field(default_factory=dict)

    target_chars_validation: float = 0.0
    target_chars_test: float = 0.0
    target_chars_by_arm: dict[str, float] = field(default_factory=dict)

    # Arms whose budget the pool could not fill. Not an exception: PRD §11's Gate G1 has a
    # documented fallback ("25-100M -> run arm A only") that needs this number to fire.
    unmet_arms: tuple[str, ...] = ()

    # Held-out sets §6.1's ~5K sequences could not fill. Reported separately from the arms because
    # it is the *upstream* failure: the bands are solved from the top, so a starved held-out
    # budget eats the train pool and every arm then reports unmet for a reason that is not its own.
    unmet_heldout: tuple[str, ...] = ()

    def split_of(self, bucket: int) -> str:
        if bucket >= self.test_from:
            return "test"
        if bucket >= self.validation_from:
            return "validation"
        return "train"

    def arms_of(self, bucket: int) -> tuple[str, ...]:
        if bucket >= self.train_to:
            return ()
        return tuple(
            sorted(
                (arm for arm, cut in self.arm_cuts.items() if bucket < cut),
                key=lambda a: self.arm_cuts[a],
            )
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SplitAssignment:
    """One document's partition membership.

    ``arms`` is a tuple rather than a single label because membership is nested: a document in
    arm A is necessarily in arm B, and a representation that could express otherwise would let
    §6.1's subsample guarantee be violated by a typo.
    """

    doc_id: str
    population: str
    split: str  # "train" | "validation" | "test" | "unassigned"
    bucket: int
    arms: tuple[str, ...] = ()
    chars: int = 0

    @property
    def assigned(self) -> bool:
        return self.split != "unassigned"

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "population": self.population,
            "split": self.split,
            "bucket": self.bucket,
            "arms": list(self.arms),
            "chars": self.chars,
        }


# ---------------------------------------------------------------------------
# The log
# ---------------------------------------------------------------------------


@dataclass
class SplitLog:
    """Corpus-level totals for the manifest, in characters (exact) and tokens (estimated)."""

    config: SplitConfig = field(default_factory=SplitConfig)
    measured: int = 0
    assigned: int = 0
    unassigned: int = 0
    sample_rate: float | None = None

    documents: Counter[str] = field(default_factory=Counter)  # "population/split"
    chars: Counter[str] = field(default_factory=Counter)
    words: Counter[str] = field(default_factory=Counter)
    arm_documents: Counter[str] = field(default_factory=Counter)  # "population/arm"
    arm_chars: Counter[str] = field(default_factory=Counter)
    by_source: Counter[str] = field(default_factory=Counter)  # "source/split"
    # Counted in the two phases separately rather than in one shared counter. Phase 1 sees every
    # document and phase 2 may see a subset, so a single counter would double-count a full run and
    # under-count a plan applied by a later stage — a number that means two things depending on how
    # it was produced, which is the defect Findings O and P were both instances of.
    unbudgeted_measured: Counter[str] = field(default_factory=Counter)
    unassigned_labels: Counter[str] = field(default_factory=Counter)

    def key(self, population: str, split: str) -> str:
        return f"{population}/{split}"

    def tokens(self, population: str, chars: float) -> float:
        ratio = self.config.chars_per_token.get(population)
        return chars / ratio if ratio else 0.0

    def chars_per_word(self, population: str) -> float:
        """Measured, and the only check available on the fertility assumption before Week 5."""
        words = sum(v for k, v in self.words.items() if k.startswith(f"{population}/"))
        chars = sum(v for k, v in self.chars.items() if k.startswith(f"{population}/"))
        return chars / words if words else 0.0

    def arm_tokens(self, arm: str) -> float:
        """An arm's realized U — the quantity §4.3's epoch count divides into 9.9B."""
        return sum(
            self.tokens(population, self.arm_chars.get(f"{population}/{arm}", 0))
            for population in self.config.population_targets
        )

    def clean_tokens(self) -> float:
        """Every budgeted token stage 9 saw. Gate G1 (PRD §11) is a threshold on this."""
        return sum(
            self.tokens(population, chars)
            for key, chars in self.chars.items()
            for population in [key.split("/", 1)[0]]
            if population in self.config.population_targets
        )

    @property
    def scale(self) -> float:
        """Multiplier from what this pass measured to the full corpus it sampled."""
        return 1.0 / self.sample_rate if self.sample_rate else 1.0

    def gate_g1(self) -> dict:
        """G1: clean corpus >= 100M tokens, with the fallback ladder §11 actually specifies.

        **Scaled by the sample rate.** Measured on a 5% FineWeb2 pass, the unscaled figure reads
        52.7M and returns ``arm_a_only`` for a shard that actually holds ~1.05B — a gate verdict
        that means two different things depending on how the pass was invoked. That is the same
        defect as Findings O and P (one number, two units) arriving at the one place in this stage
        where a wrong number is a project decision rather than a statistic.
        """
        clean = self.clean_tokens() * self.scale
        if clean >= 100_000_000:
            verdict = "pass"
        elif clean >= 25_000_000:
            verdict = "arm_a_only"  # §11: "25-100M -> run arm A only, report single-arm"
        else:
            verdict = "stop"  # §11: "Below 25M -> stop"
        return {
            "clean_tokens_estimated": round(clean),
            "clean_tokens_measured": round(self.clean_tokens()),
            "sample_rate": self.sample_rate,
            "scaled_by": self.scale,
            "threshold": 100_000_000,
            "verdict": verdict,
            "note": "tokens are estimated from characters; re-solve when §7's tokenizer exists",
        }

    def to_dict(self) -> dict:
        populations = self.config.populations
        return {
            "splits_version": SPLITS_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "measured": self.measured,
            "assigned": self.assigned,
            "unassigned": self.unassigned,
            "sample_rate": self.sample_rate,
            "unbudgeted_measured": dict(self.unbudgeted_measured.most_common()),
            "unassigned_labels": dict(self.unassigned_labels.most_common()),
            "populations": {
                population: {
                    "target_tokens": self.config.population_targets[population],
                    "mixture_share": round(self.config.mixture[population], 6),
                    "chars_per_token": self.config.chars_per_token[population],
                    "chars_per_word_measured": round(self.chars_per_word(population), 3),
                    "splits": {
                        split: {
                            "documents": self.documents.get(self.key(population, split), 0),
                            "chars": self.chars.get(self.key(population, split), 0),
                            "tokens_estimated": round(
                                self.tokens(
                                    population, self.chars.get(self.key(population, split), 0)
                                )
                            ),
                        }
                        for split in SPLIT_NAMES
                    },
                    "arms": {
                        arm: {
                            "documents": self.arm_documents.get(f"{population}/{arm}", 0),
                            "chars": self.arm_chars.get(f"{population}/{arm}", 0),
                            "tokens_estimated": round(
                                self.tokens(
                                    population, self.arm_chars.get(f"{population}/{arm}", 0)
                                )
                            ),
                            "target_tokens": round(
                                self.config.arm_tokens[arm] * self.config.mixture[population]
                            ),
                            # What the budget was actually solved against on this pass. Equal to
                            # target_tokens unsampled; on a 5% pass the realized figure is 5% of
                            # the target by design, and printing only the full target makes a
                            # correct arm look 95% short.
                            "target_tokens_this_pass": round(
                                self.config.arm_tokens[arm]
                                * self.config.mixture[population]
                                / self.scale
                            ),
                        }
                        for arm in self.config.arm_names
                    },
                }
                for population in populations
            },
            "arms": {
                arm: {
                    "target_tokens": self.config.arm_tokens[arm],
                    "tokens_estimated": round(self.arm_tokens(arm)),
                    "documents": sum(self.arm_documents.get(f"{p}/{arm}", 0) for p in populations),
                }
                for arm in self.config.arm_names
            },
            "by_source": dict(sorted(self.by_source.items())),
            "gate_g1": self.gate_g1(),
        }


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


@dataclass
class SplitPlan:
    """Solved bands plus the histogram they were solved from.

    The histogram is carried deliberately. Stage 9 budgets in tokens and can only measure
    characters until §7's tokenizer exists in Week 5, one week *after* the freeze — so the plan is
    written such that a corrected ``chars_per_token`` re-solves every boundary from the stored
    counts in milliseconds, with no corpus pass. :meth:`resolve` is that operation, and it is the
    reason the ordering problem between §6.3.9 and §7 is a nuisance rather than a blocker.
    """

    config: SplitConfig
    bands: dict[str, PopulationBands] = field(default_factory=dict)
    histogram: dict[str, list[int]] = field(default_factory=dict)
    sample_rate: float | None = None

    def resolve(self, config: SplitConfig | None = None) -> SplitPlan:
        """Re-solve the bands under a different config, reusing the measured histogram.

        Refuses a plan written without its histogram. That is not a hypothetical: plans are
        committed with the histogram stripped when they are superseded, and without this guard
        :func:`_solve` falls back to an all-zero histogram and returns a **complete, plausible
        plan with every band at zero** — the silent-wrong-answer shape rather than the loud one.
        """
        if not any(self.histogram.values()):
            raise ValueError(
                "this plan carries no histogram, so its bands cannot be re-solved — re-run "
                "phase 1 rather than accepting the empty-corpus answer a missing histogram gives"
            )
        target = config or self.config
        if target.buckets != self.config.buckets:
            raise ValueError(
                f"cannot re-solve at {target.buckets} buckets from a histogram measured at "
                f"{self.config.buckets} — the counts describe the old bucketing"
            )
        return SplitPlan(
            config=target,
            bands=_solve(target, self.histogram, self.sample_rate),
            histogram=self.histogram,
            sample_rate=self.sample_rate,
        )

    def to_dict(self, *, include_histogram: bool = True) -> dict:
        payload: dict = {
            "splits_version": SPLITS_VERSION,
            "config": {"splits_version": SPLITS_VERSION, **self.config.to_dict()},
            "config_fingerprint": self.config.fingerprint(),
            "sample_rate": self.sample_rate,
            "bands": {p: b.to_dict() for p, b in sorted(self.bands.items())},
        }
        if include_histogram:
            payload["histogram"] = {p: list(h) for p, h in sorted(self.histogram.items())}
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> SplitPlan:
        config = SplitConfig.from_dict(data["config"])
        return cls(
            config=config,
            bands={
                population: PopulationBands(
                    # JSON has no tuple. Restoring it as a list would make a round-tripped plan
                    # compare unequal to the one that produced it, which is how a freeze ends up
                    # unable to prove the plan it applied is the plan it measured.
                    **{
                        **band,
                        "unmet_arms": tuple(band.get("unmet_arms", ())),
                        "unmet_heldout": tuple(band.get("unmet_heldout", ())),
                    }
                )
                for population, band in data["bands"].items()
            },
            histogram={p: list(h) for p, h in data.get("histogram", {}).items()},
            sample_rate=data.get("sample_rate"),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> SplitPlan:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path, *, include_histogram: bool = True) -> None:
        Path(path).write_text(
            json.dumps(
                self.to_dict(include_histogram=include_histogram), indent=2, ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )


def _cut_from_below(counts: list[int], budget: float) -> tuple[int, int, bool]:
    """Largest prefix ``[0, cut)`` whose characters do not exceed ``budget``.

    Never overshoots. An arm's budget *is* §4.3's U, and U is what the epoch count divides 9.9B
    by; a boundary that rounded upward would quietly buy fewer epochs than the design specifies
    and move the arm's position against C_crit. Undershoot is bounded by one bucket.

    The third return value is whether the *range* ran out rather than the budget — the exact
    signal for an unmet arm. Comparing the shortfall against an average bucket instead is the
    obvious alternative and it is wrong: buckets vary, so a stop caused by one heavy bucket looks
    identical to an exhausted pool, and a sufficient corpus gets reported as failing Gate G1.
    """
    accumulated = 0
    for index, count in enumerate(counts):
        if accumulated + count > budget:
            return index, accumulated, False
        accumulated += count
    return len(counts), accumulated, accumulated < budget


def _cut_from_above(counts: list[int], upper: int, budget: float) -> tuple[int, int, bool]:
    """Smallest band ``[cut, upper)`` whose characters do not exceed ``budget``.

    Reports exhaustion for the same reason :func:`_cut_from_below` does, and here the failure is
    louder than an unmet arm: the held-out bands are solved *first*, so a pool smaller than
    §6.1's ~5K sequences does not merely produce a short validation set — it consumes the corpus
    from the top and leaves train empty. Measured on a 2,482-document probe, that is exactly what
    happened, and nothing in the arm-level reporting said the cause was the held-out budget.
    """
    accumulated = 0
    for index in range(upper - 1, -1, -1):
        if accumulated + counts[index] > budget:
            return index + 1, accumulated, False
        accumulated += counts[index]
    return 0, accumulated, accumulated < budget


def _solve(
    config: SplitConfig, histogram: dict[str, list[int]], sample_rate: float | None
) -> dict[str, PopulationBands]:
    """Turn measured character counts per bucket into integer band boundaries.

    Solved top-down — test, then validation, then the arms from zero — because that ordering is
    what makes arm membership invariant to the held-out budget. The cumulative below an arm cut
    does not depend on any band above it, so re-sizing §6.1's ~5K sequences re-solves the bands
    and leaves every arm assignment untouched.

    ``sample_rate`` scales the budgets, not the counts. A phase-1 pass sampled at rate *r*
    measures ~*r* of each bucket, so the threshold that would yield budget *B* on the full corpus
    is the one yielding *rB* on the sample. This is legitimate here and is not at stages 6 and 7:
    Finding G's objection is to *pair* statistics, which a sample at rate *r* measures at *r*², and
    a bucket's character count is a sum over single documents.
    """
    scale = sample_rate if sample_rate else 1.0
    bands: dict[str, PopulationBands] = {}

    for population in config.population_targets:
        counts = histogram.get(population) or [0] * config.buckets
        total = sum(counts)

        heldout_budget = config.heldout_chars(population) * scale
        test_from, chars_test, test_short = _cut_from_above(counts, config.buckets, heldout_budget)
        validation_from, chars_validation, validation_short = _cut_from_above(
            counts, test_from, heldout_budget
        )
        unmet_heldout = tuple(
            name
            for name, short in (("validation", validation_short), ("test", test_short))
            if short
        )

        arm_cuts: dict[str, int] = {}
        chars_by_arm: dict[str, int] = {}
        target_by_arm: dict[str, float] = {}
        unmet: list[str] = []
        for arm in config.arm_names:
            budget = config.arm_chars(arm, population) * scale
            target_by_arm[arm] = budget
            cut, chars, exhausted = _cut_from_below(counts[:validation_from], budget)
            arm_cuts[arm] = cut
            chars_by_arm[arm] = chars
            # Unmet means the train pool ran out before the budget did — not that the realized
            # size undershot, which it always does by up to one bucket.
            if exhausted:
                unmet.append(arm)

        bands[population] = PopulationBands(
            population=population,
            buckets=config.buckets,
            test_from=test_from,
            validation_from=validation_from,
            train_to=validation_from,
            arm_cuts=arm_cuts,
            total_chars=total,
            chars_train=sum(counts[:validation_from]),
            chars_validation=chars_validation,
            chars_test=chars_test,
            chars_by_arm=chars_by_arm,
            target_chars_validation=heldout_budget,
            target_chars_test=heldout_budget,
            target_chars_by_arm=target_by_arm,
            unmet_arms=tuple(unmet),
            unmet_heldout=unmet_heldout,
        )
    return bands


# ---------------------------------------------------------------------------
# The assigner
# ---------------------------------------------------------------------------


class SplitAssigner:
    """Two-phase: :meth:`measure` over the corpus, :meth:`seal`, then :meth:`assign`.

    The same shape as :class:`~ravaan.data.dedup.ExactDeduplicator` and
    :class:`~ravaan.data.decontamination.Decontaminator`, and for a related reason — the boundaries
    are a property of the whole corpus, so nothing can be decided on first sight of a document.
    What is different, and what makes stage 9 cheap, is that **phase 2 needs nothing from phase 1
    except a handful of integers**: no index, no sketch, no retained hits. Memory is
    ``populations × buckets`` counters and does not grow with the corpus.
    """

    def __init__(
        self, config: SplitConfig | None = None, *, sample_rate: float | None = None
    ) -> None:
        if sample_rate is not None and not 0.0 < sample_rate <= 1.0:
            raise ValueError(f"sample_rate must be in (0, 1], got {sample_rate!r}")
        self.config = config or SplitConfig()
        self.sample_rate = sample_rate if sample_rate != 1.0 else None
        self.log = SplitLog(config=self.config, sample_rate=self.sample_rate)
        # "q" — signed 64-bit. A corpus of 3.5G characters overflows nothing here, and unlike the
        # float array stage 8 was bitten by, an integer count has no representation to round.
        self._histogram: dict[str, array] = {
            population: array("q", bytes(8 * self.config.buckets))
            for population in self.config.population_targets
        }
        self._sealed = False
        self.plan: SplitPlan | None = None

    # --- phase 1 -----------------------------------------------------------

    def bucket(self, doc_id: str) -> int:
        return bucket_of(
            doc_id,
            salt=self.config.salt,
            buckets=self.config.buckets,
            separator=self.config.pair_separator,
        )

    def measure(self, doc_id: str, text: str, population: str) -> None:
        """Record one document's characters against its bucket. Order-independent."""
        if self._sealed:
            raise RuntimeError("measure() after seal() — the bands are already solved")
        self.log.measured += 1
        histogram = self._histogram.get(population)
        if histogram is None:
            self.log.unbudgeted_measured[population] += 1
            return
        histogram[self.bucket(doc_id)] += len(text)

    # --- solve -------------------------------------------------------------

    def seal(self) -> SplitPlan:
        """Solve the bands. Idempotent, so a driver can call it without tracking whether it did."""
        if not self._sealed:
            self.plan = SplitPlan(
                config=self.config,
                bands=_solve(
                    self.config,
                    {p: list(h) for p, h in self._histogram.items()},
                    self.sample_rate,
                ),
                histogram={p: list(h) for p, h in self._histogram.items()},
                sample_rate=self.sample_rate,
            )
            self._sealed = True
        assert self.plan is not None
        return self.plan

    def load_plan(self, plan: SplitPlan) -> SplitAssigner:
        """Adopt a plan solved elsewhere — the freeze applying boundaries measured in one pass.

        Refuses a plan solved under a different config for the same reason
        :meth:`~ravaan.data.shards.ShardReader.resume` refuses a foreign checkpoint: the
        boundaries would be silently describing a different partition, and every downstream
        artifact would be mislabelled rather than wrong in a way anything could detect.
        """
        if plan.config.fingerprint() != self.config.fingerprint():
            raise ValueError(
                f"plan was solved for config {plan.config.fingerprint()}, this assigner is "
                f"{self.config.fingerprint()} — refusing to assign into a different partition"
            )
        self.plan = plan
        self._sealed = True
        return self

    # --- phase 2 -----------------------------------------------------------

    def assign(
        self, doc_id: str, text: str, population: str, *, source: str = ""
    ) -> SplitAssignment:
        """This document's split and arms. A pure function of the id, the label and the bands."""
        if not self._sealed or self.plan is None:
            raise RuntimeError("assign() before seal() — no bands have been solved yet")

        bucket = self.bucket(doc_id)
        bands = self.plan.bands.get(population)
        if bands is None:
            self.log.unassigned += 1
            self.log.unassigned_labels[population] += 1
            return SplitAssignment(
                doc_id=doc_id,
                population=population,
                split="unassigned",
                bucket=bucket,
                chars=len(text),
            )

        split = bands.split_of(bucket)
        arms = bands.arms_of(bucket)
        chars = len(text)

        self.log.assigned += 1
        key = self.log.key(population, split)
        self.log.documents[key] += 1
        self.log.chars[key] += chars
        self.log.words[key] += len(text.split())
        for arm in arms:
            self.log.arm_documents[f"{population}/{arm}"] += 1
            self.log.arm_chars[f"{population}/{arm}"] += chars
        if source:
            self.log.by_source[f"{source}/{split}"] += 1

        return SplitAssignment(
            doc_id=doc_id,
            population=population,
            split=split,
            bucket=bucket,
            arms=arms,
            chars=chars,
        )

    # --- reporting ---------------------------------------------------------

    def to_dict(self) -> dict:
        payload = self.log.to_dict()
        if self.plan is not None:
            payload["bands"] = {p: b.to_dict() for p, b in sorted(self.plan.bands.items())}
            payload["unmet_arms"] = {
                population: list(band.unmet_arms)
                for population, band in sorted(self.plan.bands.items())
                if band.unmet_arms
            }
            payload["unmet_heldout"] = {
                population: list(band.unmet_heldout)
                for population, band in sorted(self.plan.bands.items())
                if band.unmet_heldout
            }
        return payload


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def assign_splits(
    documents: Iterable[tuple[str, str, str]], config: SplitConfig | None = None
) -> tuple[list[SplitAssignment], SplitAssigner]:
    """Two passes over an in-memory ``(doc_id, text, population)`` sequence.

    For tests and small sets only. The corpus path is `scripts/split.py`, which streams and never
    holds the corpus.
    """
    materialized = list(documents)
    assigner = SplitAssigner(config)
    for doc_id, text, population in materialized:
        assigner.measure(doc_id, text, population)
    assigner.seal()
    return [
        assigner.assign(doc_id, text, population) for doc_id, text, population in materialized
    ], assigner


# ---------------------------------------------------------------------------
# CLI — re-solve a saved plan without touching the corpus
# ---------------------------------------------------------------------------


def _iter_report(plan: SplitPlan) -> Iterator[str]:
    config = plan.config
    for population in config.populations:
        band = plan.bands[population]
        yield f"{population}"
        yield (
            f"  total {band.total_chars:>14,} chars"
            f"   train {band.chars_train:>14,}"
            f"   validation {band.chars_validation:>10,}"
            f"   test {band.chars_test:>10,}"
        )
        for arm in config.arm_names:
            chars = band.chars_by_arm.get(arm, 0)
            target = band.target_chars_by_arm.get(arm, 0.0)
            tokens = chars / config.chars_per_token[population]
            flag = "  UNMET" if arm in band.unmet_arms else ""
            yield (
                f"  arm {arm}: buckets [0, {band.arm_cuts.get(arm, 0):,}) "
                f"{chars:>14,} chars = {tokens / 1e6:>7.2f}M tokens "
                f"(target {target / config.chars_per_token[population] / 1e6:.2f}M){flag}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-solve a saved stage-9 plan under different assumptions, no corpus pass."
    )
    parser.add_argument("plan", help="a plan JSON written by scripts/split.py")
    parser.add_argument("--config", help="splits config JSON to re-solve against")
    parser.add_argument(
        "--chars-per-token",
        action="append",
        metavar="POPULATION=RATIO",
        help="override one population's fertility, e.g. urdu=3.72 — the Week 5 correction",
    )
    parser.add_argument("-o", "--out", help="write the re-solved plan here")
    args = parser.parse_args(argv)

    plan = SplitPlan.from_json_file(args.plan)
    config = SplitConfig.from_json_file(args.config) if args.config else plan.config
    if args.chars_per_token:
        ratios = dict(config.chars_per_token)
        for override in args.chars_per_token:
            population, _, raw = override.partition("=")
            if population not in ratios:
                raise SystemExit(f"--chars-per-token: unknown population {population!r}")
            ratios[population] = float(raw)
        config = SplitConfig.from_dict({**config.to_dict(), "chars_per_token": ratios})

    resolved = plan.resolve(config)
    for line in _iter_report(resolved):
        print(line, file=sys.stderr)
    if args.out:
        resolved.to_json_file(args.out)
        print(f"\nwrote {args.out}", file=sys.stderr)
    else:
        print(json.dumps(resolved.to_dict(include_histogram=False), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
