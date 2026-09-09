"""Kaggle kernel 02 — stage 6+7 over Roman-Urdu-Parl train, char shingles, unsampled.

Push this ONLY after kernel 00's trial says it fits. Roman-Urdu-Parl had no runtime projection at
all before that trial: 6.37M rows of ~74 characters is a different shape from anything measured,
and a two-point cost model fitted to Wikipedia and FineWeb2 produced a negative per-document cost.

Two deliberate differences from kernel 01:

* `--shingle-unit char`, because the rows are single sentences. Word shingles on a 74-character
  row leave too few shingles to estimate Jaccard from.
* No `--single-pass`. It halves the read, but at a peak-memory cost proportional to the
  exact-duplicate rate — nil on FineWeb2, high on these collapsing rows.

Never run concurrently with kernel 01.
"""

import os
import resource
import subprocess
import sys
import time
from pathlib import Path

WORKING = Path("/kaggle/working")


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


def find_corpus_root() -> Path:
    """Kernel 00's output, which holds the fetched corpus and its manifest."""
    return find_mount("data/manifest.json", what="kernel 00's output holding the corpus")


def bootstrap_corpus() -> None:
    corpus = find_corpus_root()
    print(f"corpus dataset: {corpus}", flush=True)

    (WORKING / "data").mkdir(parents=True, exist_ok=True)
    link = WORKING / "data" / "raw"
    if not link.exists():
        os.symlink(corpus / "data" / "raw", link, target_is_directory=True)

    manifest = WORKING / "data" / "manifest.json"
    if not manifest.exists():
        manifest.write_bytes((corpus / "data" / "manifest.json").read_bytes())

    print(f"corpus linked: {link} -> {os.readlink(link)}", flush=True)


def main() -> int:
    code = find_code_root()
    print(f"code dataset: {code}", flush=True)

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "pyarrow>=17", "zstandard>=0.23"],
        cwd=WORKING,
        check=True,
    )
    bootstrap_corpus()

    (WORKING / "reports" / "freeze").mkdir(parents=True, exist_ok=True)

    argv = [
        sys.executable,
        str(code / "scripts" / "neardedup.py"),
        "--source", "roman-urdu-parl",
        "--split", "train",
        "--limit", "0",
        "--shingle-unit", "char",
        "--removals", "reports/freeze/removals_67_roman.txt",
        "--pairs-out", "reports/freeze/pairs_67_roman.jsonl",
        "--json", "reports/freeze/neardedup_roman.json",
    ]
    print(f"$ {' '.join(argv)}", flush=True)

    start = time.time()
    subprocess.run(argv, cwd=WORKING, check=True)
    elapsed = time.time() - start

    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e6
    print(f"\ncompleted in {elapsed / 3600:.2f} h, peak child RSS {peak:.2f} GB", flush=True)
    print(
        "\nThis pass also settles the one number session 8 left as an estimate: the exact "
        "post-dedup character count of the Roman column, which needs a two-phase run rather "
        "than --index-only.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
