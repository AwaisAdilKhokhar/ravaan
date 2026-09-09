"""Kaggle kernel 00 — fetch the corpus, then measure whether the long passes fit the session cap.

Run this FIRST, as a committed run (Save & Run All). It does two jobs:

1. Fetches and verifies the pinned corpus into /kaggle/working, so it becomes this kernel's
   output and every later kernel mounts it instead of re-fetching against the 12 h cap.
2. Runs timed prefixes of both long passes and projects them to full size.

Step 2 is a decision gate, not a formality. `neardedup.py` is not resumable — the shard reader
checkpoints but the MinHash index lives in memory — so a pass that overruns the cap produces
nothing at all. Do not push kernel 01 or 02 until this one says they fit.

Needs Internet: On (the fetch) and Accelerator: None (this job never touches a GPU, and a GPU
session has a shorter cap).
"""

import json
import re
import resource
import socket
import subprocess
import sys
import time
from pathlib import Path

WORKING = Path("/kaggle/working")

# Full-corpus sizes, to project the trial rates against.
# FineWeb2 is both train shards; Roman-Urdu-Parl is the train CSV.
FINEWEB2_DOCUMENTS = 4_980_000
ROMAN_ROWS = 6_370_000

# The cap is ~12 h. Leave headroom: there is no resume, so overrunning costs the whole pass.
CAP_HOURS = 12.0
SAFE_HOURS = 10.0

# Read-plan fingerprints, measured on the local machine 2026-09-10 (`neardedup.py --limit 1` prints
# one per source on its first line). `plan_fingerprint()` hashes [source, path, sha256] per file
# plus layout, order, seed and sample rate, and deliberately excludes the machine-specific
# `local_path` — so Kaggle must produce these exact strings from the same pinned corpus.
#
# A difference is not cosmetic: it means the corpus here is not the corpus there, and every removal
# list this session goes on to write would be refused by name when `--exclude` reads it back home.
# Better to learn that in the minute after the fetch than at the end of a ten-hour pass.
EXPECTED_PLANS = {
    ("urdu-wikipedia", None): "8743e78c000775aa",
    ("fineweb2-urd_Arab", "train"): "54b744f92e3949f8",
    ("roman-urdu-parl", "train"): "db3a15522463a364",
}


# --- mount bootstrap: copied verbatim from kaggle/mount_bootstrap.py --------------------------
MAX_MOUNT_DEPTH = 4


def find_mount(marker: str, *, what: str) -> Path:
    """Locate a mounted dataset by a file it must contain, without assuming the mount's depth.

    Kaggle's layout is **not** the flat `/kaggle/input/<slug>` that its own documentation and every
    tutorial describe. Measured 2026-09-10 by a kernel that did nothing but print the tree: a
    dataset attached to a script kernel arrives at `/kaggle/input/datasets/<owner>/<slug>/`, two
    levels deeper than the glob every kernel here was built around. Kernel 00 failed on it twice —
    the first failure unread for five weeks behind a wrong slug — with the dataset correctly
    attached and reporting `ready` the whole time.

    So the depth is not ours to assume. Search breadth-first for the marker and return the
    shallowest directory holding it. `iterdir` over a mount is cheap: a mount holds a corpus, not a
    filesystem, and this stops before it could become a walk of one.
    """
    root = Path("/kaggle/input")
    if not root.exists():
        raise SystemExit(f"nothing is mounted at {root} — attach {what} to this kernel")
    frontier = [root]
    for _ in range(MAX_MOUNT_DEPTH):
        deeper = []
        for directory in frontier:
            if (directory / marker).is_file():
                return directory
            try:
                deeper.extend(child for child in sorted(directory.iterdir()) if child.is_dir())
            except PermissionError:
                continue
        frontier = deeper
    raise SystemExit(
        f"no {what} under {root} — looked for {marker!r} to depth {MAX_MOUNT_DEPTH}.\n"
        f"mounted: {[str(p) for p in sorted(root.rglob('*')) if p.is_dir()][:20]}"
    )


def find_code_root() -> Path:
    """The uploaded project tree, wherever Kaggle chose to mount it."""
    return find_mount("scripts/neardedup.py", what="the ravaan-code dataset")


def require_internet(host: str = "huggingface.co") -> None:
    """Fail in one legible line if this container has no network, before the fetch tries.

    **`enable_internet: True` in the kernel metadata is not evidence that the container has a
    network.** Measured 2026-09-10: Kaggle accepted the flag, reported it back on the live kernel,
    and still ran the notebook with no DNS because the account was not phone-verified. The fetch
    died 41 s in on `socket.gaierror: [Errno -3] Temporary failure in name resolution` under thirty
    lines of urllib traceback that name neither the internet nor verification.

    So the check is here, at the top, where the message can say what to actually do.
    """
    try:
        socket.getaddrinfo(host, 443)
    except OSError as exc:
        raise SystemExit(
            f"no network in this container — {host} does not resolve ({exc}).\n"
            "Kaggle records `enable_internet: True` and still gives an unverified account no DNS.\n"
            "Fix: kaggle.com -> Settings -> Phone Verification (one-time, and it is the only\n"
            "irreducibly manual step in reports/freeze_on_kaggle.md), then re-push:\n"
            "    python kaggle/push.py push 00"
        ) from exc
    print(f"network: {host} resolves", flush=True)


def run(argv: list[str], *, cwd: Path = WORKING) -> None:
    print(f"$ {' '.join(str(a) for a in argv)}", flush=True)
    subprocess.run(argv, cwd=cwd, check=True)


def child_peak_rss_gb() -> float:
    """Peak RSS of subprocesses, in GB.

    RUSAGE_CHILDREN, not RUSAGE_SELF: the pass runs in a subprocess, so SELF would measure this
    notebook and report a reassuring ~0. On Linux ru_maxrss is in kilobytes.
    """
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e6


def trial(code: Path, label: str, extra: list[str], documents: int, total: int) -> dict:
    """Time a prefix of one source and project it to the full pass."""
    print(f"\n{'=' * 70}\ntrial: {label} — {documents:,} documents\n{'=' * 70}", flush=True)
    rss_before = child_peak_rss_gb()
    start = time.time()
    run(
        [
            sys.executable,
            str(code / "scripts" / "neardedup.py"),
            *extra,
            "--limit",
            str(documents),
            "--json",
            str(WORKING / f"trial_{label}.json"),
        ]
    )
    elapsed = time.time() - start
    rss = child_peak_rss_gb()

    per_document = elapsed / documents
    projected_hours = per_document * total / 3600
    # The index is the memory that does not fit locally; measure its real per-document cost.
    bytes_per_document = (rss * 1e9) / documents

    result = {
        "label": label,
        "trial_documents": documents,
        "trial_seconds": round(elapsed, 1),
        "seconds_per_document": round(per_document, 6),
        "full_documents": total,
        "projected_hours": round(projected_hours, 2),
        "trial_peak_rss_gb": round(rss, 2),
        "bytes_per_document": round(bytes_per_document),
        "projected_peak_gb": round(bytes_per_document * total / 1e9, 1),
        "fits": projected_hours <= SAFE_HOURS,
    }
    print(json.dumps(result, indent=2), flush=True)
    if rss_before > 0.01:
        print(f"note: {rss_before:.2f} GB peak carried in from an earlier child", flush=True)
    return result


def read_plan(code: Path, source: str, split: str | None) -> str:
    """The read-plan fingerprint for one source, from a one-document pass.

    `neardedup.py` prints it on its first line — `reading <source>: plan <hex> over N file(s)`.
    """
    argv = [
        sys.executable,
        str(code / "scripts" / "neardedup.py"),
        "--source",
        source,
        "--limit",
        "1",
    ]
    if split:
        argv += ["--split", split]
    result = subprocess.run(argv, cwd=WORKING, check=True, capture_output=True, text=True)
    match = re.search(r"plan ([0-9a-f]{16})", result.stdout)
    if not match:
        raise SystemExit(
            f"no plan fingerprint in {source}'s output — the driver's first line has changed:\n"
            f"{result.stdout[:400]}"
        )
    return match.group(1)


def check_read_plans(code: Path) -> None:
    """Refuse to spend a session on a corpus that is not the one the laptop pinned.

    This replaces a line that read `neardedup.py --limit 1` with no `--source`, which is a required
    argument — so it would have exited 2 under `check=True` and killed the kernel immediately after
    the 7.7 GB fetch. Found locally on 2026-09-10 by running it, which is the only way it was ever
    going to be found: nothing in a push validates the code it uploads.
    """
    print(f"\n{'=' * 70}\nread-plan fingerprints\n{'=' * 70}", flush=True)
    wrong = []
    for (source, split), expected in EXPECTED_PLANS.items():
        actual = read_plan(code, source, split)
        verdict = "ok" if actual == expected else f"MISMATCH, expected {expected}"
        print(f"  {source:<22} {actual}  {verdict}", flush=True)
        if actual != expected:
            wrong.append((source, expected, actual))
    if wrong:
        raise SystemExit(
            "read plans differ from the local corpus, so any removal list written here would be "
            f"refused by --exclude back home: {wrong}"
        )


def main() -> int:
    code = find_code_root()
    print(f"code dataset: {code}", flush=True)

    # pyarrow is needed to read parquet; everything that *decides* anything is stdlib-only, so
    # there is no project install step and nothing to build on the read-only mount.
    run([sys.executable, "-m", "pip", "install", "-q", "pyarrow>=17", "zstandard>=0.23"])

    # Checked before the fetch rather than discovered inside it: the corpus is ~7.7 GB and the
    # session cap is the binding constraint, so a network failure should cost seconds.
    require_internet()

    print(f"\n{'=' * 70}\nfetch + verify\n{'=' * 70}", flush=True)
    acquire = str(code / "scripts" / "acquire.py")
    run([sys.executable, acquire, "fetch"])
    run([sys.executable, acquire, "verify"])

    check_read_plans(code)

    results = [
        trial(
            code,
            "fineweb2",
            ["--source", "fineweb2-urd_Arab", "--split", "train", "--single-pass"],
            200_000,
            FINEWEB2_DOCUMENTS,
        ),
        # Roman-Urdu-Parl gets char shingles (its rows are single sentences) and NOT --single-pass:
        # single-pass costs peak memory proportional to the exact-duplicate rate, which is nil on
        # FineWeb2 but high on these collapsing rows.
        trial(
            code,
            "roman",
            ["--source", "roman-urdu-parl", "--split", "train", "--shingle-unit", "char"],
            500_000,
            ROMAN_ROWS,
        ),
    ]

    (WORKING / "trial_summary.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"\n{'=' * 70}\nverdict\n{'=' * 70}", flush=True)
    for r in results:
        verdict = "FITS" if r["fits"] else "DOES NOT FIT"
        print(
            f"{r['label']:<10} {r['projected_hours']:>6.2f} h  "
            f"{r['projected_peak_gb']:>6.1f} GB peak   {verdict}",
            flush=True,
        )
    print(f"\nsafe budget {SAFE_HOURS} h against a ~{CAP_HOURS} h cap; no resume, so an "
          f"overrun produces nothing.", flush=True)
    if not all(r["fits"] for r in results):
        print(
            "\nAt least one pass does not fit. Do not push kernel 01/02 for it. In preference "
            "order: make neardedup.py resumable, band-partition to disk, or rent a 32 GB box. "
            "Sampling is not an option — Finding G, a pair statistic sampled at rate r is "
            "measured at r squared, and this pass exists to measure self-similarity.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
