"""Backend-dispatching word-gloss aligner: eflomal -> THOT -> co-occurrence (offline)."""

from __future__ import annotations

from . import backends, cooccur
from .contract import GlossTable, ParallelRow
from .glosses import build_gloss_table


def align(
    rows: list[ParallelRow],
    *,
    backend: str = "auto",
    allow_cooccur_fallback: bool = True,
) -> tuple[GlossTable, str]:
    """Align a verse-aligned parallel corpus and return (GlossTable, backend_used).

    backend: "auto" | "eflomal" | "thot" | "cooccur". "auto" prefers eflomal, then THOT, then the
    dependency-free co-occurrence baseline (the offline/CI path).
    """
    used, alignments = _run(rows, backend, allow_cooccur_fallback)
    return build_gloss_table(rows, alignments), used


def _run(rows: list[ParallelRow], backend: str, allow_fallback: bool):
    if backend == "cooccur":
        return "cooccur", cooccur.cooccur_align(rows)
    if backend == "eflomal" or (backend == "auto" and backends.eflomal_available()):
        if backends.eflomal_available():
            return "eflomal", backends.eflomal_align(rows)
        raise RuntimeError("eflomal backend requested but not installed (Linux-only; `uv sync --extra align`).")
    if backend == "thot" or (backend == "auto" and backends.thot_available()):
        if backends.thot_available():
            return "thot", backends.thot_align(rows)
        raise RuntimeError("thot backend requested but sil-machine[thot] not installed.")
    if backend == "auto" and allow_fallback:
        return "cooccur", cooccur.cooccur_align(rows)
    raise RuntimeError(f"no alignment backend available for {backend!r} (and fallback disabled)")
