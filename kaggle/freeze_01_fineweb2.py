"""Kaggle kernel 01 — stage 6+7 over FineWeb2 urd_Arab, both train shards, unsampled.

Push this ONLY after kernel 00's trial says FineWeb2 fits inside the session cap. `neardedup.py`
is not resumable, so an overrun produces nothing.

Mounts kernel 00's output for the corpus, so nothing is re-fetched. Internet: Off, Accelerator:
None. Run as a committed run (Save & Run All) — a committed run continues headlessly after the
browser closes, which an interactive session does not.

Never run this concurrently with kernel 02: session 11 measured two passes over one file at ~50
minutes where either alone was ~20, and here they would also contend for the 30 GB.
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
    """Make the corpus reachable at the relative path the manifest records.

    `local_path` in the manifest is relative (`data/raw/<source>/...`) and resolved against the
    working directory, so the corpus only has to appear there. Symlink rather than copy: the
    corpus is ~7.7 GB and /kaggle/working has a quota.
    """
    corpus = find_corpus_root()
    print(f"corpus dataset: {corpus}", flush=True)

    (WORKING / "data").mkdir(parents=True, exist_ok=True)
    link = WORKING / "data" / "raw"
    if not link.exists():
        os.symlink(corpus / "data" / "raw", link, target_is_directory=True)

    # The manifest itself must be writable-adjacent, so copy the small JSON rather than link it.
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
        "--source", "fineweb2-urd_Arab",
        "--split", "train",
        "--limit", "0",           # unsampled: Finding G forbids sampling a pair statistic
        "--single-pass",          # halves the read; its memory cost is nil at FineWeb2's
                                  # exact-duplicate rate (Finding H)
        "--sweep", "0.7", "0.8", "0.9",
        "--removals", "reports/freeze/removals_67_fineweb2.txt",
        "--pairs-out", "reports/freeze/pairs_67_fineweb2.jsonl",
        "--json", "reports/freeze/neardedup_fineweb2.json",
    ]
    print(f"$ {' '.join(argv)}", flush=True)

    start = time.time()
    subprocess.run(argv, cwd=WORKING, check=True)
    elapsed = time.time() - start

    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e6
    print(f"\ncompleted in {elapsed / 3600:.2f} h, peak child RSS {peak:.2f} GB", flush=True)
    print(
        "\nCheck `largest_cluster` in the report above. Nothing caps a component's size; the "
        "only reason to believe 0.80 does not chain is a measurement on Wikipedia (23). A source "
        "with heavier templating can chain, and that is the number that would say the threshold "
        "does not transfer.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
