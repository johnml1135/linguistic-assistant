"""machine.py-backed aligners (eflomal / THOT), guarded so the package imports without them.

Install with `uv sync --extra align` (research/). eflomal is Linux-only (CPU); THOT (fast_align/IBM1)
is cross-platform. When neither is installed, callers fall back to the co-occurrence baseline.
"""

from __future__ import annotations

from .contract import Alignment, ParallelRow


def _eflomal_bin_dir() -> str | None:
    """Directory holding the compiled `eflomal` binary the pip wheel ships in eflomal/bin/.

    sil-machine's EflomalAligner shells out to `$EFLOMAL_PATH/eflomal` (default `./eflomal`), but the
    wheel installs the binary under site-packages/eflomal/bin/ — not on PATH. Point EFLOMAL_PATH there.
    """
    try:
        import os

        import eflomal  # noqa: F401

        bin_dir = os.path.join(os.path.dirname(eflomal.__file__), "bin")
        return bin_dir if os.path.exists(os.path.join(bin_dir, "eflomal")) else None
    except Exception:
        return None


def eflomal_available() -> bool:
    try:
        from machine.jobs.eflomal_aligner import EflomalAligner  # noqa: F401

        return _eflomal_bin_dir() is not None  # the importable module is useless without the binary
    except Exception:
        return False


def thot_available() -> bool:
    try:
        from machine.translation.thot import ThotSymmetrizedWordAlignmentModel  # noqa: F401

        return True
    except Exception:
        return False


def eflomal_align(rows: list[ParallelRow]) -> list[Alignment]:
    """Symmetrized (grow-diag-final-and) eflomal alignment via machine.py. Linux-only."""
    import tempfile
    from pathlib import Path

    from machine.jobs import eflomal_aligner as _efa  # type: ignore
    from machine.jobs.eflomal_aligner import EflomalAligner  # type: ignore

    # Point sil-machine at the wheel's bundled binary. It execs `$EFLOMAL_PATH/eflomal`, but reads
    # EFLOMAL_PATH into a module constant AT IMPORT TIME — so set the env var is too late; patch the
    # already-bound constant directly.
    bin_dir = _eflomal_bin_dir()
    if bin_dir:
        _efa.EFLOMAL_PATH = Path(bin_dir, "eflomal")

    src_toks = [src for src, _ in rows]
    tgt_toks = [tgt for _, tgt in rows]
    with tempfile.TemporaryDirectory() as d:
        aligner = EflomalAligner(Path(d))
        aligner.train(src_toks, tgt_toks)
        giza = aligner.align()  # ["0-0 1-1", ...] grow-diag-final-and
    return [_parse_giza(line) for line in giza]


def thot_align(rows: list[ParallelRow], model_type: str = "fast_align") -> list[Alignment]:
    """Symmetrized THOT alignment via machine.py (cross-platform)."""
    from machine.corpora import MemoryText, StandardParallelTextCorpus, TextRow  # type: ignore
    from machine.translation import SymmetrizationHeuristic, word_align_corpus  # type: ignore

    src = MemoryText("src", [TextRow("src", str(i), s) for i, (s, _) in enumerate(rows)])
    tgt = MemoryText("tgt", [TextRow("tgt", str(i), t) for i, (_, t) in enumerate(rows)])
    corpus = StandardParallelTextCorpus(src, tgt)
    aligned = word_align_corpus(
        corpus, aligner=model_type, symmetrization_heuristic=SymmetrizationHeuristic.GROW_DIAG_FINAL_AND
    )
    return [[(p.source_index, p.target_index) for p in row.aligned_word_pairs] for row in aligned]


def _parse_giza(line: str) -> Alignment:
    out: Alignment = []
    for tok in line.split():
        if "-" in tok:
            s, t = tok.split("-", 1)
            if s.isdigit() and t.isdigit():
                out.append((int(s), int(t)))
    return out
