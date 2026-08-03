"""Quality filtering — stage 5 of the corpus pipeline (PRD §6.3.5).

Stage 5 is the first stage that throws away text on grounds of *taste* rather than of fact.
Stages 2 and 3 answer questions with right answers — is this valid UTF-8, is this Arabic script.
"Is this document good enough to train on" has no such answer, which is exactly why PRD §6.3.5
requires the rules to be validated against 200 manually inspected samples rather than asserted.
That validation is the deliverable; this module is what it validates.

Five rule families, per §6.3.5: script ratio, repetition, URL density, HTML residue, and
replacement-character frequency. Four properties they are built around.

**1. Every rule is evaluated; none short-circuits.** A filter that stops at the first failure can
tell you how many documents it rejected and nothing else. :class:`QualityLog` therefore records
both ``rejections`` (documents each rule fired on, overlapping) and ``sole_rejections`` (documents
*only* that rule rejected). The second number is the one that matters: a rule with zero sole
rejections is not filtering the corpus, it is agreeing with another rule, and it should be
removed or its threshold moved rather than kept because the PRD names it. Stages 2 and 3 both
turned out to be assertions rather than filters on FineWeb2, and the only reason that is known is
that it was measured.

**2. Thresholds are per population, because there are three of them.** PRD §6.1 budgets native
Urdu (~120M tokens), Roman Urdu (~40M) and code-switched (~10M) separately. A single
"Urdu-script ratio ≥ x" floor — the obvious reading of §6.3.5 — silently deletes the entire Roman
Urdu population, which is Latin script by definition, and most of the code-switched one. So the
rule is "the share of letters in the scripts this label is *expected* to be written in", and the
label comes from stage 3.

**3. Stage 5 rejects; it does not repair.** Stage 2 repairs mojibake because a mis-decoded page is
recoverable and its correct form is not a matter of opinion. There is no such operation here:
stripping a document's boilerplate to save it means deciding what its content was, and a stage
that rewrites text on a guess is how a corpus acquires artefacts no later stage can trace.

**4. Script ratios are read from stage 3, not recomputed.** :func:`check` accepts the ``scripts``
mapping :class:`~ravaan.data.langid.LangIDResult` already carries. Stage 3 runs *before*
normalization and stage 5 runs after, so this is only sound because the ratios are near-invariant
under stage 4: it folds presentation forms to Arabic-block letters (still Arabic), maps digits and
strips zero-width and bidi marks (none of them letters, none of them counted). The one real
difference is tatweel (U+0640), which is category Lm — a letter — and which stage 4 removes;
measured at 0.03–0.07 occurrences per document it moves no ratio meaningfully.
``tests/test_quality.py`` locks the invariance with that tolerance rather than trusting the
argument.

Entry point: :func:`check`. :class:`QualityLog` aggregates for the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from ravaan.data.langid import script_ratios

__all__ = [
    "QUALITY_VERSION",
    "QualityConfig",
    "QualityMetrics",
    "QualityResult",
    "QualityLog",
    "RULE_FAMILIES",
    "check",
    "measure",
    "score",
    "EXPECTED_SCRIPTS",
]

# Bump on any change to which documents are accepted. The manifest records it, so a frozen corpus
# can be traced to the exact filter that produced it.
QUALITY_VERSION = "1.0.0"

REPLACEMENT_CHAR = "�"


# ---------------------------------------------------------------------------
# What each population is expected to be written in
#
# Keyed by stage 3's label. A label absent from this mapping has no script expectation and the
# script rule does not apply to it — `other`, `english` and friends are not kept anyway, but the
# filter has to be callable on them without inventing a requirement.
# ---------------------------------------------------------------------------

EXPECTED_SCRIPTS: dict[str, tuple[str, ...]] = {
    "urdu": ("arabic",),
    "roman_urdu": ("latin",),
    # Both, and the threshold is on their *sum*: a code-switched document is Urdu plus English by
    # construction, so what this rule catches is a third script taking the document over.
    "code_switched": ("arabic", "latin"),
}


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Word-ish tokens for the repetition rules. Whitespace-delimited, which Urdu supports: it writes
# real spaces, unlike the scripts that motivate character-level segmentation.
_TOKEN_RE = re.compile(r"\S+")

# URLs, including the bare-`www.` form that survives HTML-to-text extraction. The terminator set
# excludes the brackets and quotes that ordinarily follow a link so a trailing `)` is not counted
# as part of it.
_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'،؛)\]}]+", re.IGNORECASE)

# Residue of HTML that a text extractor missed. Tags must start with a letter, so an Urdu
# comparison written `<` is not a tag; the attribute run is bounded so a stray `<` followed by
# half a page of prose cannot match as one enormous tag.
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]{0,200})?/?>")
_HTML_ENTITY_RE = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]{1,31}|#\d{1,7}|#[Xx][0-9A-Fa-f]{1,6});")

_LINE_SPLIT_RE = re.compile(r"[\r\n]+")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _pairs(data: object, name: str) -> tuple[tuple[int, float], ...]:
    """Read ``{"3": 0.18}`` or ``[[3, 0.18]]`` into sorted ``((3, 0.18),)``.

    A mapping keyed by n is how the thresholds are legible in JSON; a tuple of pairs is how the
    config stays hashable, which it must be because it is frozen and cached.
    """
    if isinstance(data, dict):
        items = [(int(k), float(v)) for k, v in data.items()]
    elif isinstance(data, list | tuple):
        items = [(int(n), float(v)) for n, v in data]
    else:
        raise ValueError(f"{name} must be a mapping or a list of [n, threshold] pairs")
    for n, value in items:
        if n < 1:
            raise ValueError(f"{name} has a non-positive n: {n}")
        if not 0.0 < value <= 1.0:
            raise ValueError(f"{name}[{n}] must be in (0, 1], got {value!r}")
    return tuple(sorted(items))


@dataclass(frozen=True, slots=True)
class QualityConfig:
    """Thresholds for stage 5. Defaults are the Ravaan corpus v1 settings.

    Every number here was set in two passes, and the second one is the one PRD §6.3.5 asks for.
    First from a measured distribution over real FineWeb2 and Urdu Wikipedia text rather than
    from a paper (`reports/probe_*.json`); then against 200 manually adjudicated documents
    (`reports/quality_validation.md`), which moved four of the six families and improved agreement
    with human judgement from 0.76 to 0.92 on the unbiased stratum. Where a threshold was
    inherited from published practice — the n-gram repetition family follows Rae et al.'s Gopher
    rules — the distribution and then the sample both overruled it, because those values were
    fitted to English words.
    """

    # --- length ---------------------------------------------------------
    # Not one of §6.3.5's five rules. Added because the population it removes — navigation stubs,
    # single-line error pages, category shells — is the one every other rule measures badly: a
    # 40-character document has no repetition, no URL density worth the name, and a script ratio
    # computed over a dozen letters. Cheap, and it makes the other four rules meaningful.
    #
    # 400, not the 200 the distribution suggested, and this is the largest single result of the
    # manual validation. At 200 the rule had *perfect* precision (32/32 rejections agreed with)
    # and was still the biggest source of error in the filter, because it was letting through 24
    # of the 91 documents a human would drop — Urdu Wikipedia's template geo-stubs, which are one
    # factual sentence wrapped in section headers and category footers and run 200–420 characters.
    # A rule can be perfectly precise and still be set far too low; only the *accept* side shows
    # it, which is why the sample has an unbiased stratum at all.
    min_chars: int = 400
    min_words: int = 40

    # --- script ratio (§6.3.5) ------------------------------------------
    # Share of letters in the scripts EXPECTED_SCRIPTS names for the label. Deliberately not 0.85:
    # Urdu Wikipedia's geographic stubs quote foreign place names in Latin at ~25% of letters by
    # volume and are entirely legitimate Urdu, and the same misreading of the same documents
    # already cost stage 3 a rewrite (session 5). Measured, the 1st percentile is 0.80 on FineWeb2
    # and 0.65 on Wikipedia.
    #
    # **This is the rule the validation could not fix, and the report should say so.** At 0.70 it
    # rejected 60 of the sampled documents and a human agreed with 33 of them (precision 0.55);
    # at 0.60 it rejects 14 and a human agrees with 7 (0.50). The failure is structural, not a
    # threshold: the documents on both sides of every candidate cut are the same shape — an Urdu
    # news article quoting an English tweet scores 0.66, a porn-spam page with Urdu keyword salad
    # scores 0.58, and an Urdu ghazal printed beside its Roman transliteration scores 0.52. Latin
    # share does not separate them because it is not what distinguishes them. 0.60 is chosen as
    # the point where the rule still removes the wholly-English pages that stage 3 let through
    # while leaving Urdu journalism alone; it is a backstop, and the language decision belongs to
    # stage 3, which made it with far better evidence.
    min_urdu_script_ratio: float = 0.60
    min_roman_script_ratio: float = 0.60
    min_mixed_script_ratio: float = 0.90

    # --- repetition (§6.3.5) --------------------------------------------
    #
    # These are the thresholds that moved furthest from published practice, and the reason is
    # measured rather than argued. Rae et al.'s Gopher values — dup_line 0.30, top n-gram
    # 0.20/0.18/0.16, dup n-gram 0.15…0.10 — reject **13.7% of FineWeb2 `urd_Arab`**, and
    # inspecting that 13.7% shows it is almost entirely clean Urdu news prose. Two things about
    # Urdu web text make short-n-gram repetition a much weaker signal than it is on English C4:
    #
    #   1. **Urdu news wire copy restates the headline verbatim in the lead paragraph.** It is the
    #      house style. A 500-character article carrying its own 60-character headline twice is
    #      over 20% duplicate 5-grams by arithmetic with nothing wrong with it.
    #   2. **Function-word density.** Urdu's compound verbs and postpositional phrases (کے مطابق،
    #      کی جانب سے، ہو گیا ہے) make a repeated five-word run ordinary where the English
    #      equivalent is a template.
    #
    # The other half of the argument is that the repetition which *does* matter in this corpus is
    # cross-document, not within-document: Urdu Wikipedia's geographic stub farms and Finding F's
    # republished religious texts are near-duplicates of *each other*, which is stages 6 and 7's
    # job and which they do properly. So stage 5's repetition family is set as a backstop against
    # a single pathological document rather than as the corpus's repetition control. At these
    # values it rejects 0.0% of FineWeb2 and 2.5% of Urdu Wikipedia, and the Wikipedia rejects are
    # overwhelmingly template stubs. See `reports/quality_validation.md`.
    # The manual validation then split the family in two, which is the finding worth carrying into
    # the report: **the top-n-gram rules discriminate and the duplicate-n-gram rules did not.**
    # Every document the top-n-gram rules rejected was a Wikipedia disambiguation or list page —
    # "بفیلو ٹاؤن شپ" twenty times with a different county each time — and a human agreed with all
    # of them. The duplicate-n-gram rules were rejecting *biographies*: a politician's article
    # repeats his name and "پنجاب کی صوبائی اسمبلی کے رکن" because that is what an article about
    # one person says, and it scored 0.41–0.60 where a list page scores on the top-n-gram side
    # instead. So the duplicate thresholds are raised until they only catch a genuinely degenerate
    # document, and the top thresholds are left where the distribution put them.
    max_dup_line_ratio: float = 0.50
    # Share of characters in the single most frequent word n-gram.
    #
    # **n=2 is deliberately absent.** It was the one top-n-gram rule with a false positive: a
    # 4,700-character article on the UN Convention on the Rights of the Child scores 0.38 on the
    # bigram بچوں کے ("children's"), which is the article's topic, not its boilerplate. Urdu's
    # postpositional phrases and compound verbs make any two-word span common enough that a
    # bigram rate measures subject matter. n=3 and n=4 do not have this problem and catch the list
    # pages on their own — dropping n=2 took the family's precision on the sample from 0.90 to
    # 1.00 while still rejecting every list page.
    max_top_ngram_ratio: tuple[tuple[int, float], ...] = ((3, 0.26), (4, 0.22))
    # Share of characters covered by *any* word n-gram that occurs more than once.
    max_dup_ngram_ratio: tuple[tuple[int, float], ...] = (
        (5, 0.60),
        (6, 0.58),
        (7, 0.56),
        (8, 0.54),
        (9, 0.52),
        (10, 0.50),
    )
    # Repetition is O(words) per n and there are nine n. A handful of religious-library documents
    # run to hundreds of thousands of words (Finding F), so the analysis is capped and the cap is
    # *recorded* on the metrics rather than hidden — a truncated measurement that does not say so
    # is how a threshold ends up meaning something different for long documents.
    max_repetition_words: int = 100_000

    # --- URL density (§6.3.5) -------------------------------------------
    # Deliberately high, because on these sources URL density does not measure what it is meant
    # to. Every document between 0.10 and 0.30 in the probe was a legitimate Wikipedia article
    # whose *references and external-links section* is made of URLs — structurally identical to a
    # link farm by this metric, and the same artefact that made Wikipedia look 30% bilingual to
    # stage 3 (session 5). Worse, citation-heavy articles are systematically the longer,
    # better-sourced ones, so a threshold that catches them changes corpus composition in the
    # wrong direction. At 0.30 the rule keeps only documents that are *majority* link, which is
    # unambiguous. It is close to an assertion on FineWeb2 and Wikipedia; it is a real filter on
    # rawer material, which is why it stays.
    max_url_ratio: float = 0.30

    # --- HTML residue (§6.3.5) ------------------------------------------
    # Unlike the two above, this one is precise: across 7,999 probed documents every match was a
    # genuine tag — `</i>`, `<noinclude>`, `<ref name=census>`, an embedded Twitter card with its
    # `<script>` — and there were no false positives to trade against. Wiki markup is caught
    # incidentally by the same pattern, which is a bonus rather than an accident. The entity half
    # of the rule never fired at all: both sources decode entities upstream.
    #
    # Precise about what it *matches*, and — at the 0.02 the distribution suggested — wrong about
    # what that means. The validation put its precision at 0.38: it was deleting clean Wikipedia
    # biographies carrying a handful of `</i>` and `<ref>` tags in an otherwise perfect body. The
    # rule should fire when a document *is* markup, not when it *contains* some, and 0.10 is where
    # those separate — a `{{Infobox}}` dump or a bare `<noinclude>` stub clears it, a poet's
    # biography with five stray tags does not. Precision on the sample goes 0.38 → 1.00.
    max_html_ratio: float = 0.10

    # --- replacement characters (§6.3.5) --------------------------------
    # The same 0.001 stage 2 enforces. In the assembled pipeline this rule cannot fire — stage 2
    # already rejected anything above it — and that is the point: it is what makes stage 5 sound
    # when run on its own, and `sole_rejections` in the log will show it contributing nothing,
    # which is the honest way to report a rule that is an assertion rather than a filter.
    max_replacement_rate: float = 0.001

    def __post_init__(self) -> None:
        for name in (
            "min_urdu_script_ratio",
            "min_roman_script_ratio",
            "min_mixed_script_ratio",
            "max_dup_line_ratio",
            "max_url_ratio",
            "max_html_ratio",
            "max_replacement_rate",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value!r}")
        if self.min_chars < 0 or self.min_words < 0:
            raise ValueError("min_chars and min_words must be >= 0")
        if self.max_repetition_words < 1:
            raise ValueError("max_repetition_words must be >= 1")
        # Normalize whatever `from_dict` or a caller handed us into the canonical pair form, so a
        # config built in Python and one loaded from JSON fingerprint identically.
        object.__setattr__(
            self, "max_top_ngram_ratio", _pairs(self.max_top_ngram_ratio, "max_top_ngram_ratio")
        )
        object.__setattr__(
            self, "max_dup_ngram_ratio", _pairs(self.max_dup_ngram_ratio, "max_dup_ngram_ratio")
        )

    def min_script_ratio(self, label: str) -> float:
        """The script floor for one of PRD §6.1's populations."""
        if label == "roman_urdu":
            return self.min_roman_script_ratio
        if label == "code_switched":
            return self.min_mixed_script_ratio
        return self.min_urdu_script_ratio

    def for_sentences(self) -> QualityConfig:
        """A variant for sources whose unit is a sentence, not a document.

        Roman-Urdu-Parl's rows are single sentences of ~45 characters
        (:data:`ravaan.data.shards.LAYOUTS`), so the document-length floor would reject the entire
        source and the line- and n-gram-repetition rules have nothing to measure inside one
        sentence. Making that an explicit, named config rather than a quiet special case in the
        driver keeps it in the manifest fingerprint, where a reader can see which rules were
        applied to which source.
        """
        return replace(
            self,
            min_chars=20,
            min_words=3,
            max_dup_line_ratio=1.0,
            max_top_ngram_ratio=((2, 1.0),),
            max_dup_ngram_ratio=(),
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["max_top_ngram_ratio"] = {str(n): v for n, v in self.max_top_ngram_ratio}
        payload["max_dup_ngram_ratio"] = {str(n): v for n, v in self.max_dup_ngram_ratio}
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> QualityConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"quality_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown quality config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> QualityConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"quality_version": QUALITY_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": QUALITY_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QualityMetrics:
    """What was measured, independent of any threshold.

    Separated from the verdict on purpose: the 200-sample validation compares human judgement
    against *thresholds*, and re-running it after a threshold moves must not require re-reading
    the corpus. Metrics are computed once and scored as often as needed.
    """

    chars: int = 0
    words: int = 0
    lines: int = 0
    letters: int = 0
    script_ratio: float = 0.0  # letters in EXPECTED_SCRIPTS[label], as a share of all letters
    arabic_ratio: float = 0.0
    latin_ratio: float = 0.0
    replacement_rate: float = 0.0
    url_ratio: float = 0.0
    html_ratio: float = 0.0
    dup_line_ratio: float = 0.0
    top_ngram_ratio: tuple[tuple[int, float], ...] = ()
    dup_ngram_ratio: tuple[tuple[int, float], ...] = ()
    repetition_truncated: bool = False

    @property
    def max_top_ngram(self) -> float:
        return max((v for _, v in self.top_ngram_ratio), default=0.0)

    @property
    def max_dup_ngram(self) -> float:
        return max((v for _, v in self.dup_ngram_ratio), default=0.0)

    def to_dict(self) -> dict:
        return {
            "chars": self.chars,
            "words": self.words,
            "lines": self.lines,
            "letters": self.letters,
            "script_ratio": round(self.script_ratio, 5),
            "arabic_ratio": round(self.arabic_ratio, 5),
            "latin_ratio": round(self.latin_ratio, 5),
            "replacement_rate": round(self.replacement_rate, 6),
            "url_ratio": round(self.url_ratio, 5),
            "html_ratio": round(self.html_ratio, 5),
            "dup_line_ratio": round(self.dup_line_ratio, 5),
            "top_ngram_ratio": {str(n): round(v, 5) for n, v in self.top_ngram_ratio},
            "dup_ngram_ratio": {str(n): round(v, 5) for n, v in self.dup_ngram_ratio},
            "repetition_truncated": self.repetition_truncated,
        }


def _matched_chars(pattern: re.Pattern[str], text: str) -> int:
    return sum(len(m) for m in pattern.findall(text))


def _dup_line_ratio(text: str) -> tuple[float, int]:
    """``(share of characters in repeated lines, non-empty line count)``.

    Lines are compared stripped, so indentation does not make two copies of a menu distinct, and
    the share is over characters rather than lines, so one repeated word does not weigh the same
    as one repeated paragraph.
    """
    lines = [line.strip() for line in _LINE_SPLIT_RE.split(text)]
    lines = [line for line in lines if line]
    if not lines:
        return 0.0, 0
    counts = Counter(lines)
    total = sum(len(line) for line in lines)
    repeated = sum(len(line) for line in lines if counts[line] > 1)
    return (repeated / total if total else 0.0), len(lines)


def _merged_length(spans: list[tuple[int, int]]) -> int:
    """Total length covered by spans that arrive sorted by start and may overlap."""
    covered = 0
    current_start = -1
    current_end = -1
    for start, end in spans:
        if start > current_end:
            covered += current_end - current_start if current_end > current_start else 0
            current_start, current_end = start, end
        elif end > current_end:
            current_end = end
    if current_end > current_start:
        covered += current_end - current_start
    return covered


def _ngram_ratios(
    tokens: list[str],
    spans: list[tuple[int, int]],
    chars: int,
    top_ns: tuple[int, ...],
    dup_ns: tuple[int, ...],
) -> tuple[tuple[tuple[int, float], ...], tuple[tuple[int, float], ...]]:
    """Top-n-gram and duplicate-n-gram character shares.

    Definitions, stated because the thresholds are meaningless without them and published
    implementations differ:

    * **top n-gram** — ``occurrences × len(" ".join(gram)) / chars`` for the single most frequent
      n-gram. Overlapping occurrences ("aa aa aa" for n=2) can push this above 1, so it is capped.
    * **duplicate n-gram** — characters covered by *every* occurrence of *any* n-gram seen more
      than once, counting each character once however many n-grams cover it. Spans are merged
      rather than summed; summing double-counts the overlap between consecutive n-grams and
      inflates a mildly repetitive document into a rejected one.

    Tokens are lowercased before comparison. Urdu has no case, so this costs nothing there and
    stops ``Aik``/``aik`` from reading as distinct in the Roman Urdu population.
    """
    lowered = [token.lower() for token in tokens]
    count = len(lowered)
    top: list[tuple[int, float]] = []
    dup: list[tuple[int, float]] = []

    for n in top_ns:
        if count < n:
            top.append((n, 0.0))
            continue
        grams = Counter(tuple(lowered[i : i + n]) for i in range(count - n + 1))
        gram, occurrences = grams.most_common(1)[0]
        if occurrences < 2:
            top.append((n, 0.0))
            continue
        size = len(" ".join(gram))
        top.append((n, min(occurrences * size / chars, 1.0) if chars else 0.0))

    for n in dup_ns:
        if count < n:
            dup.append((n, 0.0))
            continue
        grams = [tuple(lowered[i : i + n]) for i in range(count - n + 1)]
        seen = Counter(grams)
        repeated = [
            (spans[i][0], spans[i + n - 1][1]) for i, gram in enumerate(grams) if seen[gram] > 1
        ]
        dup.append((n, _merged_length(repeated) / chars if chars and repeated else 0.0))

    return tuple(top), tuple(dup)


def measure(
    text: str,
    config: QualityConfig | None = None,
    *,
    label: str = "urdu",
    scripts: dict[str, float] | None = None,
    letters: int | None = None,
) -> QualityMetrics:
    """Measure a document. No thresholds are applied — see :func:`check` for that.

    ``scripts`` and ``letters`` are :class:`~ravaan.data.langid.LangIDResult`'s fields of the same
    names. Pass them together or not at all: passing the ratios alone would still cost the full
    letter pass to recover the count, which is the work the reuse exists to avoid.
    """
    config = config or _DEFAULT_CONFIG
    chars = len(text)
    if not chars:
        return QualityMetrics()

    if scripts is None or letters is None:
        scripts, letters = script_ratios(text)

    expected = EXPECTED_SCRIPTS.get(label)
    if expected:
        script_ratio = sum(scripts.get(name, 0.0) for name in expected)
    else:
        # No script expectation for this label — every such label (`english`, `persian`, `other`)
        # was already dropped by stage 3, so the rule does not apply and the value is reported
        # rather than used. The dominant script's share is the informative thing to report.
        script_ratio = max(scripts.values(), default=0.0)

    tokens_with_spans = [(m.group(), m.span()) for m in _TOKEN_RE.finditer(text)]
    words = len(tokens_with_spans)
    truncated = words > config.max_repetition_words
    if truncated:
        tokens_with_spans = tokens_with_spans[: config.max_repetition_words]
    tokens = [token for token, _ in tokens_with_spans]
    spans = [span for _, span in tokens_with_spans]
    # When the token list is capped the ratios must be taken over the characters actually
    # examined, or a long document is scored as unrepetitive by arithmetic alone.
    rep_chars = spans[-1][1] if truncated and spans else chars

    dup_line, lines = _dup_line_ratio(text)
    top_ratio, dup_ratio = _ngram_ratios(
        tokens,
        spans,
        rep_chars,
        tuple(n for n, _ in config.max_top_ngram_ratio),
        tuple(n for n, _ in config.max_dup_ngram_ratio),
    )

    return QualityMetrics(
        chars=chars,
        words=words,
        lines=lines,
        letters=letters,
        script_ratio=script_ratio,
        arabic_ratio=scripts.get("arabic", 0.0) if scripts else 0.0,
        latin_ratio=scripts.get("latin", 0.0) if scripts else 0.0,
        replacement_rate=text.count(REPLACEMENT_CHAR) / chars,
        url_ratio=_matched_chars(_URL_RE, text) / chars,
        html_ratio=(_matched_chars(_HTML_TAG_RE, text) + _matched_chars(_HTML_ENTITY_RE, text))
        / chars,
        dup_line_ratio=dup_line,
        top_ngram_ratio=top_ratio,
        dup_ngram_ratio=dup_ratio,
        repetition_truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

# Rule names are `family` or `family:detail`. The family is what PRD §6.3.5 lists and what the
# report will talk about; the detail is which member of the repetition family actually fired,
# which is what threshold tuning needs.
RULE_FAMILIES: tuple[str, ...] = (
    "too_short",
    "script_ratio",
    "repetition",
    "url_density",
    "html_residue",
    "replacement_chars",
)


@dataclass(frozen=True, slots=True)
class QualityResult:
    """One document's verdict, with every rule that fired and the metrics behind them."""

    accepted: bool
    reasons: tuple[str, ...] = ()
    label: str = "urdu"
    metrics: QualityMetrics = field(default_factory=QualityMetrics)
    quality_version: str = QUALITY_VERSION
    config_fingerprint: str = ""

    @property
    def families(self) -> tuple[str, ...]:
        """The §6.3.5 rule families that fired, de-duplicated and in a stable order."""
        seen = dict.fromkeys(reason.split(":", 1)[0] for reason in self.reasons)
        return tuple(seen)

    def to_dict(self, include_metrics: bool = True) -> dict:
        payload: dict = {
            "accepted": self.accepted,
            "label": self.label,
            "reasons": list(self.reasons),
            "families": list(self.families),
            "quality_version": self.quality_version,
            "config_fingerprint": self.config_fingerprint,
        }
        if include_metrics:
            payload["metrics"] = self.metrics.to_dict()
        return payload


@dataclass
class QualityLog:
    """Corpus-level aggregate — the stage-5 line of the manifest and the statistics table."""

    config: QualityConfig = field(default_factory=QualityConfig)
    documents: int = 0
    documents_kept: int = 0
    chars_in: int = 0
    chars_kept: int = 0
    # Documents each rule fired on. These overlap: one document can fail four rules.
    rejections: Counter[str] = field(default_factory=Counter)
    families: Counter[str] = field(default_factory=Counter)
    # Documents rejected by exactly one *family*. The number that says whether a rule is doing
    # work no other rule is doing — see the module docstring.
    sole_rejections: Counter[str] = field(default_factory=Counter)
    by_label: Counter[str] = field(default_factory=Counter)
    kept_by_label: Counter[str] = field(default_factory=Counter)
    chars_kept_by_label: Counter[str] = field(default_factory=Counter)
    truncated_documents: int = 0

    def add(self, result: QualityResult) -> None:
        self.documents += 1
        self.chars_in += result.metrics.chars
        self.by_label[result.label] += 1
        if result.metrics.repetition_truncated:
            self.truncated_documents += 1
        if result.accepted:
            self.documents_kept += 1
            self.chars_kept += result.metrics.chars
            self.kept_by_label[result.label] += 1
            self.chars_kept_by_label[result.label] += result.metrics.chars
            return
        for reason in result.reasons:
            self.rejections[reason] += 1
        families = result.families
        for family in families:
            self.families[family] += 1
        if len(families) == 1:
            self.sole_rejections[families[0]] += 1

    @property
    def keep_rate(self) -> float:
        return self.documents_kept / self.documents if self.documents else 0.0

    @property
    def char_keep_rate(self) -> float:
        return self.chars_kept / self.chars_in if self.chars_in else 0.0

    def to_dict(self) -> dict:
        return {
            "quality_version": QUALITY_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "config": self.config.to_dict(),
            "documents": self.documents,
            "documents_kept": self.documents_kept,
            "documents_rejected": self.documents - self.documents_kept,
            "keep_rate": round(self.keep_rate, 6),
            "chars_in": self.chars_in,
            "chars_kept": self.chars_kept,
            "char_keep_rate": round(self.char_keep_rate, 6),
            "rejections": dict(sorted(self.rejections.items())),
            "families": dict(sorted(self.families.items())),
            "sole_rejections": dict(sorted(self.sole_rejections.items())),
            "by_label": dict(sorted(self.by_label.items())),
            "kept_by_label": dict(sorted(self.kept_by_label.items())),
            "chars_kept_by_label": dict(sorted(self.chars_kept_by_label.items())),
            "truncated_documents": self.truncated_documents,
        }


# ---------------------------------------------------------------------------
# The filter
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = QualityConfig()


@lru_cache(maxsize=16)
def _fingerprint(config: QualityConfig) -> str:
    return config.fingerprint()


def score(metrics: QualityMetrics, config: QualityConfig, label: str = "urdu") -> tuple[str, ...]:
    """Apply thresholds to an already-measured document; return every rule that fired.

    Split from :func:`measure` so the 200-sample validation can re-score a stored sample under a
    changed threshold without re-reading the corpus — which is what makes tuning a threshold
    against human judgement a minute's work rather than an hour's.
    """
    reasons: list[str] = []

    if metrics.chars < config.min_chars or metrics.words < config.min_words:
        reasons.append("too_short")

    if label in EXPECTED_SCRIPTS and metrics.letters and (
        metrics.script_ratio < config.min_script_ratio(label)
    ):
        reasons.append("script_ratio")

    if metrics.dup_line_ratio > config.max_dup_line_ratio:
        reasons.append("repetition:dup_lines")
    thresholds = dict(config.max_top_ngram_ratio)
    for n, value in metrics.top_ngram_ratio:
        if n in thresholds and value > thresholds[n]:
            reasons.append(f"repetition:top_{n}gram")
    thresholds = dict(config.max_dup_ngram_ratio)
    for n, value in metrics.dup_ngram_ratio:
        if n in thresholds and value > thresholds[n]:
            reasons.append(f"repetition:dup_{n}gram")

    if metrics.url_ratio > config.max_url_ratio:
        reasons.append("url_density")
    if metrics.html_ratio > config.max_html_ratio:
        reasons.append("html_residue")
    if metrics.replacement_rate > config.max_replacement_rate:
        reasons.append("replacement_chars")

    return tuple(reasons)


def check(
    text: str,
    config: QualityConfig | None = None,
    *,
    label: str = "urdu",
    scripts: dict[str, float] | None = None,
    letters: int | None = None,
) -> QualityResult:
    """Filter one document.

    ``label`` is stage 3's verdict and decides which script the document is *expected* to be in;
    passing the default for a Roman Urdu document would reject it for not being Arabic script,
    which is why :func:`ravaan.data.langid.classify` runs first and its label is threaded through
    rather than re-derived here. ``scripts`` and ``letters`` are that same result's measurements,
    reused rather than recomputed — see the module docstring for why that is sound across
    normalization.
    """
    config = config or _DEFAULT_CONFIG
    metrics = measure(text, config, label=label, scripts=scripts, letters=letters)
    reasons = score(metrics, config, label)
    return QualityResult(
        accepted=not reasons,
        reasons=reasons,
        label=label,
        metrics=metrics,
        config_fingerprint=_fingerprint(config),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="input file (default: stdin)")
    parser.add_argument("-c", "--config", help="quality config JSON")
    parser.add_argument("--jsonl", action="store_true", help="one JSON document per line")
    parser.add_argument("--field", default="text", help="JSONL text field (default: text)")
    parser.add_argument("--label", default="urdu", help="stage-3 label for every document")
    parser.add_argument("--label-field", help="JSONL field holding each document's stage-3 label")
    parser.add_argument("--log", help="write the stage-5 log here as JSON")
    args = parser.parse_args(argv)

    config = QualityConfig.from_json_file(args.config) if args.config else QualityConfig()
    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()

    if args.jsonl:
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        documents = [
            (r[args.field], r.get(args.label_field, args.label) if args.label_field else args.label)
            for r in records
        ]
    else:
        documents = [(raw, args.label)]

    log = QualityLog(config=config)
    for text, label in documents:
        result = check(text, config, label=label or args.label)
        log.add(result)
        print(json.dumps(result.to_dict(), ensure_ascii=False))

    report = json.dumps(log.to_dict(), indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
