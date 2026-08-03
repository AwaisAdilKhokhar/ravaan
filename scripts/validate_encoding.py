#!/usr/bin/env python
"""Validate document encoding (corpus pipeline stage 2).

Usage:
    python scripts/validate_encoding.py raw.txt -o clean.txt --log stage2.json
    python scripts/validate_encoding.py shard.jsonl --jsonl --field text -o clean.jsonl
    python scripts/validate_encoding.py raw.txt -c configs/data/encoding.json

Equivalent to the ``ravaan-validate-encoding`` console script created by ``pip install -e .``.
Exists so the pipeline is runnable straight from a checkout, without installing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.data.encoding import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
