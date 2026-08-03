#!/usr/bin/env python
"""Acquire the pinned corpus sources (pipeline stage 1).

Usage:
    python scripts/acquire.py plan
    python scripts/acquire.py plan --max-bytes 3e9
    python scripts/acquire.py --source urdu-wikipedia fetch
    python scripts/acquire.py --max-bytes 3e9 fetch
    python scripts/acquire.py verify --skip-missing

Equivalent to the ``ravaan-acquire`` console script created by ``pip install -e .``. Exists so
the pipeline is runnable straight from a checkout, without installing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.data.acquisition import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
