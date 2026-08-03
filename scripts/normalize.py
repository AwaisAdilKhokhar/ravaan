#!/usr/bin/env python
"""Normalize a text file (corpus pipeline stage 4).

Usage:
    python scripts/normalize.py raw.txt -o clean.txt --log stats.json
    python scripts/normalize.py raw.txt -c configs/data/normalization.json

Equivalent to the ``ravaan-normalize`` console script created by ``pip install -e .``. Exists so
the pipeline is runnable straight from a checkout, without installing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.data.normalization import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
