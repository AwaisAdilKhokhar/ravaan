"""Make a console safe to print Urdu to. Three lines, in one place, for the fifth time.

Windows picks cp1252 for a console and for a redirected pipe, and cp1252 *raises* on a character it
cannot represent rather than mangling it. The failure is therefore not a mojibake bug but a
traceback — and it lands wherever a program first prints a `→`, a `×`, a `≈` or a word of Urdu,
which for a corpus tool is somewhere in the middle of a report the operator was reading.

This repo has now been bitten by a Windows text default four times: `.gitattributes` (session 2),
`Path.write_text`'s `os.linesep` and `.gitignore` re-inclusion (session 4), and
`scripts/crossover.py` dying on any redirected stdout (session 12). Session 12 diagnosed the
remaining console scripts as one character away from the same failure — `ravaan-splits`,
`ravaan-shards` and `ravaan-normalize` print an em-dash, which *is* in cp1252, and would raise the
day any of them printed a document. Copying the guard into those three would have closed three
instances of a class with twelve members, so it lives here and every entry point calls it.

``errors="replace"`` rather than ``strict``: a console that cannot show a character should show a
question mark, not kill a pass that has been reading a corpus for six hours. Nothing that *decides*
anything goes through here — corpus writes pin ``newline="\\n"`` and ``encoding="utf-8"`` at the
call site, and they are the ones that must never silently substitute.
"""

from __future__ import annotations

import sys

__all__ = ["pin_utf8_streams"]


def pin_utf8_streams() -> None:
    """Reconfigure stdout and stderr to UTF-8. Idempotent; safe on every platform."""
    for stream in (sys.stdout, sys.stderr):
        # Absent when the stream has been replaced by something that is not a TextIOWrapper —
        # pytest's capture, most often. Nothing to pin there, and nothing to fail about.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
