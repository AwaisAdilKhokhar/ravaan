"""Kaggle kernel — print what is actually mounted under /kaggle/input, and nothing else.

Kernel 00 failed twice with `no code dataset found under /kaggle/input` while its own metadata
listed `dataset_sources: [awaisbinadil/ravaan-code]` and the dataset reported `ready`. Both
explanations available from here — a processing race, an unextracted archive — are guesses, and
this project's own rule is that a guess about real data gets measured before it gets acted on
(Finding D, and Finding X on a projection taken from a docstring).

So this kernel asserts nothing and decides nothing. It lists the mount.
"""

import os
import sys
from pathlib import Path

ROOT = Path("/kaggle/input")


def main() -> int:
    print(f"python {sys.version}")
    print(f"{ROOT} exists: {ROOT.exists()}")
    if not ROOT.exists():
        print("nothing is mounted at all — the kernel has no sources attached")
        return 0

    entries = sorted(ROOT.iterdir())
    print(f"{ROOT} holds {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}:")
    for entry in entries:
        kind = "dir " if entry.is_dir() else "file"
        size = "" if entry.is_dir() else f"  {entry.stat().st_size:,} bytes"
        print(f"  {kind} {entry.name}{size}")

    # Two levels is enough to tell an extracted repo tree from a mounted archive.
    for entry in entries:
        if not entry.is_dir():
            continue
        print(f"\n--- {entry} ---")
        for child in sorted(entry.iterdir())[:40]:
            kind = "dir " if child.is_dir() else "file"
            print(f"  {kind} {child.name}")
            if child.is_dir():
                for grand in sorted(child.iterdir())[:12]:
                    print(f"        {grand.name}")

    # The exact test kernel 00 makes, reported rather than raised.
    hits = sorted(ROOT.glob("*/scripts/neardedup.py"))
    print(f"\nkernel 00's test — */scripts/neardedup.py: {[str(h) for h in hits]}")
    print(f"anywhere at all: {[str(h) for h in sorted(ROOT.glob('**/neardedup.py'))][:5]}")
    print(f"\nos.listdir raw: {os.listdir(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
