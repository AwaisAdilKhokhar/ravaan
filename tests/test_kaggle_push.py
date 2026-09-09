"""Engineering invariants for the Kaggle freeze driver (`kaggle/push.py`).

The freeze passes for FineWeb2 and Roman-Urdu-Parl run on Kaggle because stage 7's index needs
~10 GB (Finding X). `kaggle/push.py` is the hand that puts them there, and it is a *driver* — the
class of file Finding W established this project's bugs live in, because a driver's job is to
compose things that are each already tested.

The bug these tests exist for cost five weeks. Kaggle derives a kernel's address by slugifying its
**title** and discards the slug half of `id`; session 15 set the two independently, so all three
kernels landed at addresses `status`, `logs` and `pull` then queried with the *other* string and got
a 403. Kernel 00 errored 1.6 s into its run and nobody could read the log that said so.

The failure that was still ahead is the one worth naming: kernels 01 and 02 mount kernel 00's
output as their corpus by naming it in `kernel_sources`. Under the drift that name pointed at a
kernel that does not exist, so both long passes would have started with no corpus and died at
`find_corpus_root()` — after the ~12 h session and the trial that authorised it had been spent.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest


def _push_module():
    spec = importlib.util.spec_from_file_location(
        "_kaggle_push", Path(__file__).resolve().parents[1] / "kaggle" / "push.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


push = _push_module()


def slugify(title: str) -> str:
    """Kaggle's own rule, as observed on the live kernel: lowercase, non-alphanumeric to hyphen.

    Verified against a real address rather than a docstring — the title
    "ravaan freeze 00 fetch and trial" produced `ravaan-freeze-00-fetch-and-trial` on
    2026-08-06. Finding X's lesson applies to server behaviour too.
    """
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


@pytest.mark.parametrize("key", sorted(push.KERNELS))
def test_every_slug_survives_the_round_trip_through_kaggles_title_rule(key: str) -> None:
    """The invariant the drift broke: the address we ask for is the address Kaggle builds.

    Asserted per kernel rather than in aggregate so a failure names the one that drifted.
    """
    slug = push.KERNELS[key]["slug"]
    assert slugify(push.title_for(slug)) == slug


def test_the_corpus_gate_is_named_by_the_slug_the_status_commands_use() -> None:
    """01 and 02 mount 00's output, and they name it the same way `status 00` looks it up.

    This is the assertion that would have caught the drift before it cost a session: under it,
    `kernel_sources` for the long passes and the ref `cmd_status` polls are one string.
    """
    gate = push.KERNELS["00"]["slug"]
    assert slugify(push.title_for(gate)) == gate
    for key in ("01", "02"):
        assert push.KERNELS[key]["needs_corpus"] is True
    assert push.KERNELS["00"]["needs_corpus"] is False


def test_only_the_fetch_kernel_asks_for_internet() -> None:
    """00 fetches the corpus; 01 and 02 read it from 00's output and must not need the network.

    Not hygiene: a kernel with internet on is a kernel whose run depends on an external service
    staying up for ten hours, and neither long pass has any reason to.
    """
    assert push.KERNELS["00"]["internet"] is True
    assert push.KERNELS["01"]["internet"] is False
    assert push.KERNELS["02"]["internet"] is False


def test_a_title_under_kaggles_minimum_is_refused_rather_than_pushed() -> None:
    with pytest.raises(SystemExit):
        push.title_for("ab")


def test_every_kernel_names_a_script_that_exists() -> None:
    """A missing `code_file` is a push that succeeds and a run that has nothing to execute."""
    here = Path(__file__).resolve().parents[1] / "kaggle"
    for key, spec in sorted(push.KERNELS.items()):
        assert (here / spec["file"]).is_file(), f"{key}: {spec['file']}"


KERNEL_FILES = ("freeze_00_fetch_and_trial.py", "freeze_01_fineweb2.py", "freeze_02_roman.py")
BOOTSTRAP_MARKER = "# --- mount bootstrap: copied verbatim from kaggle/mount_bootstrap.py"


def _bootstrap_block() -> str:
    text = (Path(__file__).resolve().parents[1] / "kaggle" / "mount_bootstrap.py").read_text(
        encoding="utf-8"
    )
    return text[text.index(BOOTSTRAP_MARKER):].rstrip()


@pytest.mark.parametrize("name", KERNEL_FILES)
def test_every_kernel_carries_the_canonical_mount_bootstrap(name: str) -> None:
    """The one copy-paste in this repo that is correct, held together by this assertion.

    A kernel push uploads a single `code_file`, so the code that *locates* the uploaded project
    cannot be imported from it — the bootstrap has to already be in whichever file Kaggle runs.
    `kaggle/mount_bootstrap.py` is the source and this test is what keeps three copies of it from
    becoming three different rules, which is session 14's cp1252 lesson stated as a test rather
    than as a hope.
    """
    kernel = (Path(__file__).resolve().parents[1] / "kaggle" / name).read_text(encoding="utf-8")
    assert _bootstrap_block() in kernel


@pytest.mark.parametrize("name", KERNEL_FILES)
def test_no_kernel_assumes_the_mount_sits_directly_under_kaggle_input(name: str) -> None:
    """The bug itself, asserted as absent.

    Kaggle mounts a dataset at `/kaggle/input/datasets/<owner>/<slug>/`, not the flat
    `/kaggle/input/<slug>/` its documentation describes — measured 2026-09-10 by a kernel that
    printed the tree after kernel 00 had failed twice on the flat form. Any reintroduced
    `glob("*")` against that root is the same failure returning, and it costs a whole session
    because it fires seconds into a run that was authorised hours earlier.
    """
    kernel = (Path(__file__).resolve().parents[1] / "kaggle" / name).read_text(encoding="utf-8")
    assert 'Path("/kaggle/input").glob("*")' not in kernel
    assert "find_mount(" in kernel


def test_kernel_00_checks_the_network_before_it_starts_fetching() -> None:
    """A 7.7 GB fetch should not be how you discover the container has no DNS.

    `enable_internet: True` in the kernel metadata is not evidence of a network — measured
    2026-09-10, Kaggle accepted the flag, reported it back on the live kernel, and ran the notebook
    with no DNS because the account was not phone-verified. The failure arrived 41 s in as
    `socket.gaierror` under thirty lines of urllib traceback naming neither cause nor fix.

    Ordering is the whole assertion: a preflight after the fetch is not a preflight.
    """
    kernel = (
        Path(__file__).resolve().parents[1] / "kaggle" / "freeze_00_fetch_and_trial.py"
    ).read_text(encoding="utf-8")
    assert "def require_internet(" in kernel
    assert kernel.index("require_internet()") < kernel.index("acquire.py")
    assert "Phone Verification" in kernel
