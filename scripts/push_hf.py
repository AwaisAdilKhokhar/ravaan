"""Push the staged release pair to the Hugging Face Hub.

Publishing is outward-facing and effectively permanent — a model card is indexed and mirrored
within minutes, and deleting a repository does not un-publish what was already crawled. So this
driver does nothing without ``--yes``, prints exactly what it is about to do, and refuses to push
a release that has not passed :mod:`scripts.verify_release`.

    huggingface-cli login                       # a WRITE token
    python scripts/push_hf.py --user <name> --dry-run
    python scripts/push_hf.py --user <name> --yes

``--private`` creates the repos unlisted, which is the reversible version of this operation and
worth doing first if you have not seen the rendered card yet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

RELEASES = ("ravaan-diff-70m", "ravaan-ar-70m")

#: Never uploaded, whatever is sitting in the staging directory.
IGNORE = ("*.pt", "*.log", "__pycache__/*", "*.pyc", ".ipynb_checkpoints/*")


def preflight(root: Path, names: list[str]) -> list[Path]:
    """Refuse to push anything that has not been shown to run, or that has no card."""
    verdicts_path = REPO / "reports/eval/release_verify.json"
    if not verdicts_path.exists():
        raise SystemExit(
            "✗ reports/eval/release_verify.json is missing — run:\n"
            "    python scripts/verify_release.py --root " + str(root) + " "
            "--out reports/eval/release_verify.json"
        )
    verdicts = json.loads(verdicts_path.read_text(encoding="utf-8"))

    ready = []
    for name in names:
        path = root / name
        # Importing the vendored package to verify it leaves __pycache__ behind. It is on the
        # ignore list, but deleting it here means the file count printed below is the file count
        # uploaded, rather than the ignore list quietly making up the difference.
        for cache in path.rglob("__pycache__"):
            for pyc in cache.iterdir():
                pyc.unlink()
            cache.rmdir()
        problems = []
        if not path.exists():
            problems.append("not staged")
        else:
            if not (path / "README.md").exists():
                problems.append("no model card — run scripts/cards.py")
            if not (path / "model.safetensors").exists():
                problems.append("no weights")
            verdict = verdicts.get(name)
            if verdict is None:
                problems.append("not in release_verify.json")
            elif not verdict.get("ok"):
                problems.append(f"failed verification: {verdict.get('reason', 'see the json')}")
        if problems:
            raise SystemExit(f"✗ {name}: {'; '.join(problems)}")
        ready.append(path)
    return ready


def describe(path: Path) -> str:
    files = [p for p in path.rglob("*") if p.is_file() and p.suffix != ".pt"]
    total = sum(p.stat().st_size for p in files)
    return f"{len(files)} files, {total / 1e6:,.0f} MB"


def main() -> int:
    pin_utf8_streams()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="D:/ravaan-release")
    ap.add_argument("--user", required=True, help="your Hugging Face username or org")
    ap.add_argument("--only", choices=RELEASES, help="push just one")
    ap.add_argument("--private", action="store_true", help="create unlisted (reversible)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="actually push")
    args = ap.parse_args()

    from huggingface_hub import HfApi

    api = HfApi()
    try:
        who = api.whoami()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"✗ not authenticated ({type(exc).__name__}).\n"
            "  Run `huggingface-cli login` with a token that has WRITE access.\n"
            "  A stale read token on disk fails exactly here."
        ) from exc
    print(f"authenticated as {who['name']}")

    root = Path(args.root)
    names = [args.only] if args.only else list(RELEASES)
    ready = preflight(root, names)

    print(f"\nabout to push to {'PRIVATE' if args.private else 'PUBLIC'} repos under {args.user}:")
    for path in ready:
        print(f"  {args.user}/{path.name}   ({describe(path)})")
    if not args.private:
        print(
            "\n  ⚠ public repos are indexed and mirrored within minutes. Deleting one later\n"
            "    does not retract what has been crawled. --private is the reversible version."
        )

    if args.dry_run or not args.yes:
        print("\n(dry run — pass --yes to push)")
        return 0

    for path in ready:
        repo_id = f"{args.user}/{path.name}"
        print(f"\n→ {repo_id}")
        api.create_repo(repo_id, repo_type="model", private=args.private, exist_ok=True)
        api.upload_folder(
            repo_id=repo_id,
            folder_path=str(path),
            repo_type="model",
            ignore_patterns=list(IGNORE),
            commit_message="Ravaan 70M — matched AR/diffusion Urdu release",
        )
        print(f"  ✓ https://huggingface.co/{repo_id}")

    print("\ndone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
