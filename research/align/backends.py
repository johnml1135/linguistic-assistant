"""machine.py-backed word aligner (THOT HMM), guarded so the package imports without it.

Install with `uv sync --extra align` (research/). THOT (via `sil-machine[thot]`) is cross-platform
(Windows/macOS/Linux, CPU). When it is not installed, callers fall back to the dependency-free
co-occurrence baseline.
"""

from __future__ import annotations

from .contract import Alignment, ParallelRow


def hmm_available() -> bool:
    try:
        from machine.translation.thot import ThotSymmetrizedWordAlignmentModel  # noqa: F401

        return True
    except Exception:
        return False


def hmm_align(rows: list[ParallelRow]) -> list[Alignment]:
    """Symmetrized (grow-diag-final-and) THOT HMM alignment via machine.py (cross-platform)."""
    from machine.corpora import DictionaryTextCorpus, MemoryText, StandardParallelTextCorpus, TextRow  # type: ignore
    from machine.translation import SymmetrizationHeuristic, word_align_corpus  # type: ignore

    src_text = MemoryText("text", [TextRow("text", str(i), s) for i, (s, _) in enumerate(rows)])
    tgt_text = MemoryText("text", [TextRow("text", str(i), t) for i, (_, t) in enumerate(rows)])
    corpus = StandardParallelTextCorpus(DictionaryTextCorpus([src_text]), DictionaryTextCorpus([tgt_text]))
    aligned = word_align_corpus(
        corpus, aligner="hmm", symmetrization_heuristic=SymmetrizationHeuristic.GROW_DIAG_FINAL_AND
    )
    return [[(p.source_index, p.target_index) for p in row.aligned_word_pairs] for row in aligned]
