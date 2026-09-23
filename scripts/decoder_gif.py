#!/usr/bin/env python
"""Render the decode as a looping GIF — the asset a post actually carries.

`scripts/decoder_demo.py` builds a page you interact with. A social post cannot be interacted
with, so the same trace has to become a picture that moves on its own. This is that: one frame per
forward pass, both arms on the same clock, from the same `reports/demo_trace.json`.

**One browser launch, not one per frame.** The obvious implementation screenshots the live page
once per tick, which means N cold starts and N re-downloads of a 600 KB Nastaliq font. Instead
this writes a tall page holding *every* frame stacked, screenshots it once, and slices the result
with Pillow. Frames are a fixed height so the slice offsets are exact — which is also why the AR
panel is given the height its finished text needs from frame 0, rather than growing into it and
shifting every subsequent slice by a few pixels.

**No JavaScript.** Each frame's markup is generated here with the reveal already applied, so what
is captured cannot depend on a script having run before the screenshot fired.

    python scripts/decoder_gif.py --sample health      # -> reports/decoder_demo.gif
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

CHROME = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
RAMP = ("#1F6B44", "#217E50", "#21935C", "#20A768", "#1EBD75", "#1AD282", "#12E88F", "#00FF9C")
DIFF, AR, GROUND = "#00FF9C", "#FF4D9D", "#07090A"

WIDTH = 1000
FRAME_H = 412
#: Frames per screenshot. Chrome will render a very tall viewport but gets unreliable past a few
#: thousand pixels, so the capture is chunked and the chunks are sliced independently.
CHUNK = 8

STYLE = f"""
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400&family=JetBrains+Mono:wght@400;500;700;800&family=Noto+Nastaliq+Urdu:wght@400&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ background: {GROUND}; font-family: "IBM Plex Sans", sans-serif; }}
  .frame {{
    width: {WIDTH}px; height: {FRAME_H}px; background: {GROUND};
    padding: 18px 22px; display: flex; flex-direction: column; gap: 11px;
    font-size: 14px; overflow: hidden;
  }}
  .fhead {{ display: flex; justify-content: space-between; align-items: baseline;
           font-family: "JetBrains Mono", monospace; }}
  .fhead .t {{ font-weight: 800; font-size: 19px; color: #E4F1EA; letter-spacing: -.03em; }}
  .fhead .t i {{ font-style: normal; color: {DIFF}; }}
  .fhead .p {{ font-size: 12px; color: #6E8077; letter-spacing: .1em; text-transform: uppercase; }}
  .arm {{ border: 1px solid #1C2422; border-top-width: 2px; border-radius: 6px;
         background: #0D1110; padding: 11px 14px 13px; flex: 1;
         display: flex; flex-direction: column; }}
  .arm.d {{ border-top-color: {DIFF}; }}
  .arm.a {{ border-top-color: {AR}; }}
  .hd {{ display: flex; justify-content: space-between; align-items: baseline; gap: 14px;
        font-family: "JetBrains Mono", monospace; font-size: 11.5px; }}
  .hd .l {{ display: flex; align-items: baseline; gap: 9px; min-width: 0; }}
  .hd .n {{ font-weight: 700; letter-spacing: .04em; }}
  .hd .c {{ color: #94A79D; font-variant-numeric: tabular-nums; }}
  .hd .c b {{ font-weight: 700; }}
  .cv {{ display: flex; flex-wrap: wrap; gap: 3px; direction: rtl; padding: 7px;
        background: #121716; border-radius: 4px; margin: 9px 0 3px; }}
  .cv i {{ width: 11px; height: 11px; border-radius: 1.5px; background: #1A211E; display: block; }}
  .cv i.g {{ background: transparent; box-shadow: inset 0 0 0 1px #6E8077; opacity: .5; }}
  .ur {{ font-family: "Noto Nastaliq Urdu", serif; direction: rtl; text-align: right;
        font-size: 17px; line-height: 2.45; color: #E4F1EA; }}
  .ur .g {{ color: #6E8077; }}
  .ur .p {{ display: inline-block; background: #1A211E; border-radius: 3px;
           color: transparent; transform: translateY(-.35em); }}
</style>
"""


def frame_html(sample: dict, tick: int, total: int) -> str:
    parts = [
        '<div class="frame"><div class="fhead">',
        '<span class="t">Ravaan <i>//</i> one clock, two factorizations</span>',
        f'<span class="p">forward pass {tick}</span></div>',
    ]
    for arm, css, name, sub, colour in (
        ("diff", "d", "RAVAAN-DIFF", "masked diffusion", DIFF),
        ("ar", "a", "RAVAAN-AR", "autoregressive", AR),
    ):
        d = sample[arm]
        budget = len(RAMP) if arm == "diff" else d["forwards"]
        done = min(tick, budget)
        count = (
            f'<span style="color:#6E8077">done in</span> <b style="color:{colour}">{budget}</b>'
            f' <span style="color:#6E8077">passes</span>'
            if done >= budget
            else f'pass <b style="color:{colour}">{done}</b> / {budget}'
        )
        cells = "".join(
            '<i class="g"></i>' if s < 0
            else f'<i style="background:{RAMP[min(s, 7)] if arm == "diff" else AR}"></i>'
            if s < tick else "<i></i>"
            for s in d["cells"]
        )
        words = []
        for w in d["words"]:
            text = html.escape(w["t"])
            if w["s"] < 0:
                words.append(f'<span class="g">{text}</span>')
            elif w["s"] < tick:
                words.append(f"<span>{text}</span>")
            elif arm == "diff":
                # The canvas exists from pass 1, so an unwritten diffusion position is a blank
                # slab. The AR sequence does not exist yet, so it is nothing at all.
                words.append(f'<span class="p">{text}</span>')
        parts.append(
            f'<div class="arm {css}"><div class="hd"><span class="l">'
            f'<span class="n" style="color:{colour}">{name}</span>'
            f'<span style="color:#6E8077">{sub}</span></span>'
            f'<span class="c">{count}</span></div>'
            f'<div class="cv">{cells}</div>'
            f'<div class="ur">{" ".join(words)}</div></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def chrome() -> str:
    for path in CHROME:
        if Path(path).exists():
            return path
    raise SystemExit("no Chrome or Edge found — install one, or pass --chrome")


def capture(binary: str, page: Path, out: Path, height: int) -> None:
    subprocess.run(
        [binary, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-color-profile=srgb", f"--window-size={WIDTH},{height}",
         "--virtual-time-budget=12000", f"--screenshot={out}", page.as_uri()],
        check=True, capture_output=True, timeout=180,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--trace", type=Path, default=REPO / "reports" / "demo_trace.json")
    ap.add_argument("--sample", default="health", help="which prompt to animate")
    ap.add_argument("--out", type=Path, default=REPO / "reports" / "decoder_demo.gif")
    ap.add_argument("--ms", type=int, default=190, help="milliseconds per forward pass")
    ap.add_argument("--hold", type=int, default=14, help="frames to hold on the finished text")
    ap.add_argument("--chrome", default=None)
    args = ap.parse_args()

    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("this needs Pillow: pip install pillow")

    sys.path.insert(0, str(REPO / "scripts"))
    from decoder_demo import arm_payload

    payload = json.loads(args.trace.read_text(encoding="utf-8"))
    rec = next((s for s in payload["samples"] if s["id"] == args.sample), None)
    if rec is None:
        raise SystemExit(f"no sample {args.sample!r} in {args.trace}")
    sample = {"diff": arm_payload(rec["diff"]), "ar": arm_payload(rec["ar"])}
    total = max(payload["meta"]["steps"], sample["ar"]["forwards"])
    ticks = list(range(total + 1))

    binary = args.chrome or chrome()
    work = Path(tempfile.mkdtemp(prefix="ravaan-gif-"))
    frames: list = []
    try:
        for start in range(0, len(ticks), CHUNK):
            group = ticks[start:start + CHUNK]
            page = work / f"c{start}.html"
            page.write_text(
                STYLE + "".join(frame_html(sample, t, total) for t in group), encoding="utf-8"
            )
            shot = work / f"c{start}.png"
            capture(binary, page, shot, FRAME_H * len(group))
            sheet = Image.open(shot).convert("RGB")
            for i in range(len(group)):
                frames.append(sheet.crop((0, i * FRAME_H, WIDTH, (i + 1) * FRAME_H)))
            print(f"  captured passes {group[0]}–{group[-1]}", file=sys.stderr)

        # Hold on the finished text, so a reader who arrives mid-loop still gets to read it.
        durations = [args.ms] * len(frames) + [args.ms] * args.hold
        frames = frames + [frames[-1]] * args.hold
        quantized = [f.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
                     for f in frames]
        quantized[0].save(
            args.out, save_all=True, append_images=quantized[1:],
            duration=durations, loop=0, optimize=True, disposal=2,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    size = args.out.stat().st_size
    print(f"\nwrote {args.out} — {len(frames)} frames, {WIDTH}×{FRAME_H}, "
          f"{size / 1024 / 1024:.2f} MB", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
