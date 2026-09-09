"""The canonical mount-discovery block, copied verbatim into every freeze kernel.

**This module is never imported.** It cannot be: it is the code that *finds* the uploaded project,
so it has to already be inside whichever single file Kaggle is running. A kernel push uploads one
`code_file` and nothing else.

That makes it the one place in this repo where a copy-paste is correct, and session 14's lesson
applies anyway — three copies of a rule is how the rule comes back wrong in session 17. So the
block below is the source, and `tests/test_kaggle_push.py` asserts every kernel contains it
character for character. Edit here; the test names any kernel that drifted.

Everything below the marker line is the copied text.
"""

from pathlib import Path

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
