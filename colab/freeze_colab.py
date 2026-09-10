"""Run the stage 6+7 freeze passes on Google Colab.

Why Colab rather than Kaggle: the Kaggle path is built and tested (`kaggle/`), but its notebooks get
no network on an account without phone verification, which is not available here. Colab has
internet, so `acquire.py fetch` reproduces the pinned corpus from HuggingFace and nothing has to be
uploaded from a home connection.

**What is genuinely riskier here than on Kaggle: memory.** Finding X measured stage 7's index at
~2,010 bytes per document, so FineWeb2's ~4.98M documents project to ~9-10 GB. A Colab CPU runtime
gives roughly 12.7 GB, and when it is exhausted the process is killed outright — there is no
pagefile to absorb the overrun the way the local Windows machine had. So this driver does not assume
the figure fits:

* `env` reports the RAM the runtime actually has, rather than the number a doc quotes;
* `trial` measures both rate and peak RSS on a prefix, projects them to the full pass, and
  **refuses** rather than warns when either does not fit;
* every pass runs as a subprocess, so `RUSAGE_CHILDREN` measures the pass and not the notebook.

`neardedup.py` is not resumable — the shard reader checkpoints, the MinHash index does not — so a
pass that is killed produces nothing at all. That is the whole reason `trial` is a gate.

Usage, from the repo root after unzipping it (see colab/README.md):

    python colab/freeze_colab.py env
    python colab/freeze_colab.py trial                      # the gate. Read its verdict
    python colab/freeze_colab.py fineweb2 --drive /content/drive/MyDrive/ravaan
    python colab/freeze_colab.py roman    --drive /content/drive/MyDrive/ravaan
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

# `resource` and /proc/meminfo are Linux-only, and this driver runs on Colab. But an import-time
# failure on Windows would mean nothing here could import it — no test, no argument check, nothing
# until an hour into a session on a machine that is not this one. Today's lesson is that nothing
# validates uploaded code, so the Linux parts are deferred to their call sites instead.
try:
    import resource
except ModuleNotFoundError:  # pragma: no cover — the runtime this drives always has it
    resource = None  # type: ignore[assignment]

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "reports" / "freeze"

# Full-corpus sizes, to project the trial rates against. FineWeb2 is both train shards;
# Roman-Urdu-Parl is the train CSV, whose rows are single sentences.
FINEWEB2_DOCUMENTS = 4_980_000
ROMAN_ROWS = 6_370_000

# A Colab session is nominally up to ~12 h and disconnects when idle. There is no resume, so leave
# headroom rather than discovering the cap at 95%.
SAFE_HOURS = 9.0

# Of the RAM the runtime reports available, how much a pass may be projected to use. The rest is the
# interpreter, pyarrow's read buffers, and the fact that a projection from a 200k prefix is a
# projection. Finding X was wrong by 2x in the direction that costs a day.
RAM_HEADROOM = 0.80

# Read-plan fingerprints measured on the local machine 2026-09-10. Copied from
# kaggle/freeze_00_fetch_and_trial.py, and a test asserts the two agree — `plan_fingerprint()`
# hashes [source, path, sha256] per file and deliberately excludes the machine-specific local path,
# so every machine reading the same pinned corpus must produce these strings.
#
# A mismatch means the corpus here is not the corpus the laptop pinned, and every removal list this
# session would write is refused by name when `--exclude` reads it back home.
EXPECTED_PLANS = {
    ("urdu-wikipedia", None): "8743e78c000775aa",
    ("fineweb2-urd_Arab", "train"): "54b744f92e3949f8",
    ("roman-urdu-parl", "train"): "db3a15522463a364",
}

PASSES = {
    "fineweb2": {
        "source": "fineweb2-urd_Arab",
        "split": "train",
        # --single-pass halves the read and costs peak memory proportional to the exact-duplicate
        # rate, which is nil on FineWeb2 (Finding H). Verified equivalent to the two-pass form on
        # the complete Wikipedia dump: 47 of 48 report fields identical, removed ids byte-identical.
        # The sweep re-clusters from the retained pairs of the one pass, so it is cheap — and it
        # is in this list rather than a pass-only list because a trial exists to measure what the
        # real pass does. Any flag in one and not the other invalidates the projection that
        # authorises a ten-hour unresumable run, so there is exactly one flag set.
        "extra": ["--single-pass", "--sweep", "0.7", "0.8", "0.9"],
        "documents": FINEWEB2_DOCUMENTS,
        "trial_documents": 200_000,
    },
    "roman": {
        "source": "roman-urdu-parl",
        "split": "train",
        # Char shingles because the rows are single sentences. NOT --single-pass: its memory cost is
        # proportional to the exact-duplicate rate, and 6.37M rows collapse toward 3.48M distinct.
        "extra": ["--shingle-unit", "char"],
        "documents": ROMAN_ROWS,
        "trial_documents": 500_000,
    },
}


def meminfo() -> dict[str, float]:
    """Total and available RAM in GB, read from the kernel rather than assumed."""
    if not Path("/proc/meminfo").exists():
        raise SystemExit("no /proc/meminfo — this driver sizes its passes against real RAM")
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in {"MemTotal", "MemAvailable"}:
            values[key] = int(rest.split()[0]) / 1e6
    return values


def child_peak_gb() -> float:
    """Peak RSS of subprocesses, in GB.

    RUSAGE_CHILDREN, not RUSAGE_SELF: every pass runs in a subprocess, so SELF measures this
    process, reports a reassuring ~0, and looks exactly like the memory problem having gone away.

    Raises where `resource` is absent rather than returning 0.0 — a memory gate that cannot measure
    memory must refuse, not pass.
    """
    if resource is None:
        raise SystemExit("no `resource` module — this driver measures memory and needs Linux")
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e6


def cmd_env(_args: argparse.Namespace) -> int:
    mem = meminfo()
    total, free = shutil.disk_usage(REPO)[0] / 1e9, shutil.disk_usage(REPO)[2] / 1e9
    print("runtime")
    print(f"  RAM total      {mem.get('MemTotal', 0):6.1f} GB")
    print(f"  RAM available  {mem.get('MemAvailable', 0):6.1f} GB")
    budget = mem.get("MemAvailable", 0.0) * RAM_HEADROOM
    print(f"  a pass may be projected to use up to {budget:.1f} GB")
    print(f"  cores          {os.cpu_count()}")
    print(f"  disk           {free:.1f} GB free of {total:.1f} GB")
    print(f"  python         {sys.version.split()[0]}")
    print(
        "\nFinding X projects FineWeb2's stage-7 index at ~9-10 GB. If 'RAM available' above"
        "\nis not comfortably past that, `trial` will refuse the pass — the correct outcome, not"
        "\na bug: the pass is unresumable, so an OOM at 90% produces nothing."
    )
    return 0


def require_internet(host: str = "huggingface.co") -> None:
    """Fail in one line if there is no network, before a 7.7 GB fetch tries."""
    try:
        socket.getaddrinfo(host, 443)
    except OSError as exc:
        raise SystemExit(f"no network — {host} does not resolve ({exc})") from exc
    print(f"network: {host} resolves", flush=True)


def run(argv: list[str]) -> None:
    print(f"$ {' '.join(str(a) for a in argv)}", flush=True)
    subprocess.run(argv, cwd=REPO, check=True)


def driver(source: str, split: str | None, *extra: str) -> list[str]:
    argv = [sys.executable, str(REPO / "scripts" / "neardedup.py"), "--source", source]
    if split:
        argv += ["--split", split]
    return argv + list(extra)


def build_argv(name: str, *, limit: int, write_outputs: bool) -> list[str]:
    """The argv for one pass, in the two forms that must agree on every computational flag.

    A trial differs from the real pass in exactly two ways — how many documents it reads, and
    whether it writes removal lists — and in nothing else. Both forms come from here so that stays
    true: a flag that reached the pass but not the trial would invalidate the projection that
    authorises spending an unresumable session on it.
    """
    spec = PASSES[name]
    argv = [*spec["extra"], "--limit", str(limit)]
    if write_outputs:
        argv += [
            "--removals", str(OUT / f"removals_67_{name}.txt"),
            "--pairs-out", str(OUT / f"pairs_67_{name}.jsonl"),
            "--json", str(OUT / f"neardedup_{name}.json"),
        ]
    else:
        argv += ["--json", str(OUT / f"trial_{name}.json")]
    return driver(spec["source"], spec["split"], *argv)


def read_plan(source: str, split: str | None) -> str:
    """The read-plan fingerprint for one source, from a one-document pass."""
    result = subprocess.run(
        driver(source, split, "--limit", "1"),
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"plan ([0-9a-f]{16})", result.stdout)
    if not match:
        raise SystemExit(f"no plan fingerprint in {source}'s output:\n{result.stdout[:400]}")
    return match.group(1)


def check_read_plans() -> None:
    """Refuse to spend a session on a corpus that is not the one the laptop pinned."""
    print("\nread-plan fingerprints", flush=True)
    wrong = []
    for (source, split), expected in EXPECTED_PLANS.items():
        actual = read_plan(source, split)
        verdict = "ok" if actual == expected else f"MISMATCH, expected {expected}"
        print(f"  {source:<22} {actual}  {verdict}")
        if actual != expected:
            wrong.append((source, expected, actual))
    if wrong:
        raise SystemExit(
            "read plans differ from the local corpus, so any removal list written here would be "
            f"refused by --exclude back home: {wrong}"
        )


def cmd_fetch(_args: argparse.Namespace) -> int:
    require_internet()
    acquire = str(REPO / "scripts" / "acquire.py")
    run([sys.executable, acquire, "fetch"])
    run([sys.executable, acquire, "verify"])
    check_read_plans()
    return 0


def one_trial(name: str) -> dict:
    """Time and measure a prefix of one pass, then project both to full size."""
    spec = PASSES[name]
    documents, total = spec["trial_documents"], spec["documents"]
    print(f"\n{'=' * 70}\ntrial: {name} — {documents:,} documents\n{'=' * 70}", flush=True)

    before = child_peak_gb()
    start = time.time()
    run(build_argv(name, limit=documents, write_outputs=False))
    elapsed = time.time() - start
    peak = child_peak_gb()

    available = meminfo().get("MemAvailable", 0.0)
    per_document = elapsed / documents
    bytes_per_document = (peak * 1e9) / documents
    projected_hours = per_document * total / 3600
    projected_peak = bytes_per_document * total / 1e9
    budget = available * RAM_HEADROOM

    result = {
        "pass": name,
        "trial_documents": documents,
        "trial_seconds": round(elapsed, 1),
        "trial_peak_gb": round(peak, 2),
        "bytes_per_document": round(bytes_per_document),
        "full_documents": total,
        "projected_hours": round(projected_hours, 2),
        "projected_peak_gb": round(projected_peak, 1),
        "ram_available_gb": round(available, 1),
        "ram_budget_gb": round(budget, 1),
        "fits_time": projected_hours <= SAFE_HOURS,
        "fits_memory": projected_peak <= budget,
    }
    result["fits"] = result["fits_time"] and result["fits_memory"]
    if before > 0.01:
        result["peak_carried_in_gb"] = round(before, 2)
    print(json.dumps(result, indent=2), flush=True)
    return result


def cmd_trial(_args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = [one_trial(name) for name in PASSES]
    (OUT / "trial_summary_colab.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"\n{'=' * 70}\nverdict\n{'=' * 70}")
    for r in results:
        why = []
        if not r["fits_time"]:
            why.append(f"{r['projected_hours']:.1f} h > {SAFE_HOURS} h")
        if not r["fits_memory"]:
            why.append(f"{r['projected_peak_gb']:.1f} GB > {r['ram_budget_gb']:.1f} GB budget")
        verdict = "FITS" if r["fits"] else "DOES NOT FIT — " + ", ".join(why)
        print(
            f"  {r['pass']:<10} {r['projected_hours']:>6.2f} h  "
            f"{r['projected_peak_gb']:>6.1f} GB peak   {verdict}"
        )

    if not all(r["fits"] for r in results):
        print(
            "\nDo not run a pass that does not fit. It is unresumable, so an overrun or an\n"
            "OOM at 90% produces nothing at all. In preference order:\n"
            "  1. Make neardedup.py resumable — the shard reader already checkpoints with\n"
            "     a plan fingerprint; what is missing is serializing MinHashDeduplicator's\n"
            "     parallel arrays and ExactDeduplicator._best. Bounded, and worth having\n"
            "     regardless: today a pass that dies at 80% restarts from zero.\n"
            "  2. Band-partition to disk — write (band key, doc id), sort, compare within\n"
            "     buckets. Colab has ~100 GB of disk, the resource this runtime has spare.\n"
            "  3. Rent a 32 GB box for a day (~$2-8 against a $150 cap with $0 spent).\n"
            "Sampling is NOT an option — Finding G, a pair statistic sampled at rate r is\n"
            "measured at r squared, and these passes exist to measure self-similarity."
        )
        return 1
    return 0


def cmd_pass(args: argparse.Namespace) -> int:
    name = args.command
    OUT.mkdir(parents=True, exist_ok=True)

    trial_file = OUT / "trial_summary_colab.json"
    if not args.force:
        if not trial_file.is_file():
            raise SystemExit(
                "no trial on record — run `python colab/freeze_colab.py trial` first.\n"
                "It is a gate, not a formality: this pass is unresumable, so a projection that\n"
                "does not fit costs a whole session. Use --force only to override deliberately."
            )
        recorded = {r["pass"]: r for r in json.loads(trial_file.read_text(encoding="utf-8"))}
        verdict = recorded.get(name)
        if not verdict or not verdict["fits"]:
            raise SystemExit(f"the trial says {name} does not fit: {verdict}")

    # limit 0 is unsampled: Finding G forbids sampling a pair statistic, since one sampled at
    # rate r is measured at r squared.
    argv = build_argv(name, limit=0, write_outputs=True)
    start = time.time()
    run(argv)
    hours = (time.time() - start) / 3600
    print(f"\ncompleted in {hours:.2f} h, peak child RSS {child_peak_gb():.2f} GB")
    print(
        "\nCheck `largest_cluster` in the report. Nothing caps a component's size; the only\n"
        "reason to believe 0.80 does not chain is a measurement on Wikipedia (23). A source\n"
        "with heavier templating can chain, and that is the number that would say the\n"
        "threshold does not transfer."
    )

    if args.drive:
        destination = Path(args.drive)
        destination.mkdir(parents=True, exist_ok=True)
        for pattern in (
            f"removals_67_{name}.txt",
            f"pairs_67_{name}.jsonl",
            f"neardedup_{name}.json",
        ):
            source_file = OUT / pattern
            if source_file.is_file():
                shutil.copy2(source_file, destination / pattern)
                print(f"copied to Drive: {destination / pattern}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("env", help="what this runtime actually has")
    sub.add_parser("fetch", help="fetch, verify and check read plans")
    sub.add_parser("trial", help="measure both passes and decide whether they fit — the gate")
    for name in PASSES:
        run_parser = sub.add_parser(name, help=f"the real {name} pass, unsampled")
        run_parser.add_argument(
            "--drive", help="copy results here when done (a mounted Drive path)"
        )
        run_parser.add_argument(
            "--force", action="store_true", help="run without a passing trial on record"
        )

    args = parser.parse_args(argv)
    if args.command in PASSES:
        return cmd_pass(args)
    return {"env": cmd_env, "fetch": cmd_fetch, "trial": cmd_trial}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
