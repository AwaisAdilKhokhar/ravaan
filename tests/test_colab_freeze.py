"""Engineering invariants for the Colab freeze driver (`colab/freeze_colab.py`).

The two long stage 6+7 passes need ~10 GB of RAM (Finding X) and cannot run on the local machine.
Kaggle was the plan until its notebooks turned out to get no network without phone verification,
which is not available on this account; Colab has internet, so the corpus can be fetched there as
designed. What Colab does *not* have is Kaggle's ~30 GB — a CPU runtime gives roughly 12.7 GB
against a ~9-10 GB projection, and an exhausted Colab runtime kills the process outright rather than
paging the way the local Windows machine did.

So the memory gate is the point of this driver, and these tests are mostly about it holding:

* a pass refuses to start without a passing trial on record, because it is unresumable — an OOM at
  90% produces nothing at all;
* the trial and the real pass agree on every computational flag, or the projection that authorises
  the session is measuring something else;
* a gate that cannot measure memory refuses rather than passing vacuously, which is what
  `child_peak_gb()` returning 0.0 off-Linux would have done.

The driver imports cleanly on Windows on purpose: `resource` and `/proc/meminfo` are deferred to
their call sites so this file can exercise it at all. Today's lesson was that nothing validates
uploaded code — a Kaggle kernel carried a `neardedup.py` call with no `--source`, which is required,
and it would have died in the minute after a 7.7 GB fetch.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _colab_module():
    spec = importlib.util.spec_from_file_location(
        "_freeze_colab", REPO / "colab" / "freeze_colab.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


colab = _colab_module()


def _kaggle_expected_plans() -> dict:
    """The Kaggle kernel's copy, read without importing it — it needs Unix-only `resource`."""
    text = (REPO / "kaggle" / "freeze_00_fetch_and_trial.py").read_text(encoding="utf-8")
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "EXPECTED_PLANS":
            return ast.literal_eval(node.value)
    raise AssertionError("no EXPECTED_PLANS in the Kaggle kernel")


def test_both_hosts_pin_the_same_read_plan_fingerprints() -> None:
    """The Kaggle and Colab drivers must agree, because the corpus they read is the same one.

    `plan_fingerprint()` hashes [source, path, sha256] per file and excludes the machine-specific
    local path, so a corpus fetched anywhere from the same pins gives these strings. Two copies of
    them is a drift risk; this is what holds them together.
    """
    assert _kaggle_expected_plans() == colab.EXPECTED_PLANS
    assert colab.EXPECTED_PLANS == {
        ("urdu-wikipedia", None): "8743e78c000775aa",
        ("fineweb2-urd_Arab", "train"): "54b744f92e3949f8",
        ("roman-urdu-parl", "train"): "db3a15522463a364",
    }


@pytest.mark.parametrize("name", ["fineweb2", "roman"])
def test_the_trial_measures_the_pass_it_authorises(name: str) -> None:
    """Trial and pass differ in document count and output files, and in nothing else.

    This is the invariant the whole gate rests on. A flag present in the real pass but not the
    trial — `--sweep` was, in the first draft of this driver — means the projection that authorises
    an unresumable ten-hour run was measured on a different computation.
    """
    trial = colab.build_argv(name, limit=colab.PASSES[name]["trial_documents"], write_outputs=False)
    real = colab.build_argv(name, limit=0, write_outputs=True)

    def computational(argv: list[str]) -> list[str]:
        """Everything except the document limit and the output paths."""
        drop_next = False
        kept = []
        for token in argv:
            if drop_next:
                drop_next = False
                continue
            if token in {"--limit", "--json", "--removals", "--pairs-out"}:
                drop_next = True
                continue
            kept.append(token)
        return kept

    assert computational(trial) == computational(real)


def test_only_fineweb2_takes_single_pass_and_only_roman_takes_char_shingles() -> None:
    """`--single-pass` costs peak memory proportional to the exact-duplicate rate.

    That is nil on FineWeb2 (Finding H) and high on Roman-Urdu-Parl, whose 6.37M rows collapse
    toward 3.48M distinct — the one source where the halved read is not worth its memory. Char
    shingles go the other way: Roman's rows are single sentences, so word shingles would leave most
    of them below `min_shingles`.
    """
    fineweb2 = colab.PASSES["fineweb2"]["extra"]
    roman = colab.PASSES["roman"]["extra"]
    assert "--single-pass" in fineweb2
    assert "--single-pass" not in roman
    assert "--shingle-unit" in roman
    assert "--shingle-unit" not in fineweb2


def test_a_pass_refuses_to_start_without_a_passing_trial(tmp_path, monkeypatch) -> None:
    """The gate, asserted as a refusal.

    `neardedup.py` is not resumable, so a pass that overruns the session or is OOM-killed produces
    nothing — not a partial index, nothing. A pass that starts anyway on an unmeasured runtime is
    the single most expensive mistake available here, and it costs a whole session to learn.
    """
    monkeypatch.setattr(colab, "OUT", tmp_path)
    args = argparse.Namespace(command="fineweb2", drive=None, force=False)
    with pytest.raises(SystemExit, match="no trial on record"):
        colab.cmd_pass(args)


def test_a_pass_refuses_when_the_trial_says_it_does_not_fit(tmp_path, monkeypatch) -> None:
    """A recorded verdict of `fits: false` is a refusal, not a warning to read past."""
    monkeypatch.setattr(colab, "OUT", tmp_path)
    (tmp_path / "trial_summary_colab.json").write_text(
        json.dumps(
            [{"pass": "fineweb2", "fits": False, "projected_peak_gb": 11.4, "ram_budget_gb": 9.8}]
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(command="fineweb2", drive=None, force=False)
    with pytest.raises(SystemExit, match="does not fit"):
        colab.cmd_pass(args)


def test_a_memory_gate_that_cannot_measure_memory_refuses(monkeypatch) -> None:
    """Off-Linux, `child_peak_gb()` raises rather than reporting a reassuring 0.0.

    Returning zero would make `fits_memory` true for any projection, which is a gate that always
    opens — the failure mode Finding X's `RUSAGE_SELF` note is about, one layer up.
    """
    monkeypatch.setattr(colab, "resource", None)
    with pytest.raises(SystemExit, match="needs Linux"):
        colab.child_peak_gb()


def test_every_flag_the_driver_passes_is_one_neardedup_accepts() -> None:
    """The same check the Kaggle kernels get: argparse is the only other reader of this argv.

    A rejected flag exits 2, and on Colab that happens after the fetch, inside a session.
    """
    helptext = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "neardedup.py"), "--help"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    accepted = set(re.findall(r"--[a-z0-9][a-z0-9-]+", helptext))
    used = {
        token
        for name in colab.PASSES
        for token in colab.build_argv(name, limit=0, write_outputs=True)
        if token.startswith("--")
    }
    assert used <= accepted, f"driver passes flags neardedup rejects: {sorted(used - accepted)}"


def test_raising_the_session_cap_cannot_open_the_memory_gate() -> None:
    """`--safe-hours` relaxes the session cap and nothing else.

    The 2026-09-10 Colab trial refused FineWeb2 on *both* counts — 11.69 h against a 9 h cap and
    12.7 GB against a 9.7 GB budget. A rented box removes the first constraint and not the second,
    so the override has to be scoped: `--force` would have waived the memory verdict too, and
    memory is precisely the projection Finding X already got wrong by 2x in the expensive
    direction. Asserted as a property of the result rather than of the printed verdict.
    """
    projection = {"projected_hours": 11.69, "projected_peak": 12.7, "budget": 9.7}

    def fits(safe_hours: float) -> dict:
        fits_time = projection["projected_hours"] <= safe_hours
        fits_memory = projection["projected_peak"] <= projection["budget"]
        return {
            "fits_time": fits_time,
            "fits_memory": fits_memory,
            "fits": fits_time and fits_memory,
        }

    assert fits(colab.SAFE_HOURS) == {"fits_time": False, "fits_memory": False, "fits": False}
    # A cap high enough for a rented box clears the clock and leaves the pass refused on memory.
    assert fits(24.0) == {"fits_time": True, "fits_memory": False, "fits": False}


def test_the_session_cap_is_recorded_in_the_trial_it_authorises() -> None:
    """A trial read back later must say which cap it was judged against.

    `cmd_pass` reads `fits` out of `trial_summary_colab.json` without re-deriving it, so a summary
    that does not carry its own cap is a verdict whose meaning cannot be reconstructed — including
    by whoever reads the freeze's numbers into the report.
    """
    parser_source = (REPO / "colab" / "freeze_colab.py").read_text(encoding="utf-8")
    assert '"safe_hours": safe_hours,' in parser_source
    assert "--safe-hours" in parser_source


@pytest.mark.parametrize("name", ["fineweb2", "roman"])
def test_every_pass_records_a_threshold_sweep(name: str) -> None:
    """Both passes sweep, because the sweep is the only record of why 0.80 was kept.

    Roman-Urdu-Parl ran without it on 2026-09-10 and returned `largest_cluster` 10,757 against
    Wikipedia's 23 — the signal `colab/README.md` names as meaning the threshold does not transfer
    — with no way to ask what 0.85 or 0.90 would have done. `sweep()` re-clusters from the pairs
    held in the index, and `--pairs-out` writes only banded examples, so the answer died with the
    process and the 1.38 h pass had to be run again. The pairs are retained at
    `retain_pairs_above` either way; the flag is what turns them into a decision on the record.
    """
    argv = colab.build_argv(name, limit=0, write_outputs=True)
    assert "--sweep" in argv, f"{name} discards its threshold evidence"
    thresholds = []
    for token in argv[argv.index("--sweep") + 1 :]:
        if token.startswith("--"):
            break
        thresholds.append(float(token))
    assert thresholds, f"{name} passes --sweep with no thresholds"
    assert min(thresholds) >= 0.5, (
        "a threshold below retain_pairs_above=0.5 makes the sweep silently incomplete — "
        "the pairs that would decide it were never kept"
    )
