"""Alignment-table construction modes for the two production pipelines that build a THOT table over
HC-segmented target morphemes (`induce.cotrain.cotrain`, `align.morph_align_hc.run`).

Three modes, per the thot-on-morphs study (`thot-on-morphs.md` -> `thot-on-morphs-report.md`, 8 language
pairs x 6 paradigms, all real runs):

  factored  (P6, DEFAULT) - target affixes with a learned POS/MSA restriction (`induce.tdd.assign_slots`'
            `req_pos`) are canonicalized to their grammatical class before alignment; roots and English
            stay literal. Best-or-tied performer in most of the 8 pairs tested (mean coverage delta vs.
            identity: -0.004), at identity's ambiguity and wall-clock cost, with no new tokenizer -
            Koehn & Hoang (2007)'s factored-translation idea, applied to alignment evidence.
  guided    (P4) - English is split only where the target side already gives repeated cross-lingual
            evidence a word is doing two jobs (mean delta vs. identity: -0.011) - a simplified version of
            Fraser (2009)'s guided-segmentation idea.
  identity  (P1, the pre-study default) - target HC-morphemes vs whole English words, no transform.

Naive unsupervised English segmentation (BPE) and the guided+BPE hybrid were also tested (P2/P3/P5) and
regressed coverage sharply (mean delta vs. identity: -0.15 to -0.19) at this corpus scale - deliberately
NOT offered here; see the report's recommendation before reconsidering them.
"""

from __future__ import annotations

from collections import Counter

DEFAULT_ALIGN_MODE = "factored"


def _en_freqs(morph_rows: list[tuple[list[str], list[str]]]) -> Counter:
    c: Counter = Counter()
    for src, _tgt in morph_rows:
        c.update(src)
    return c


def build_table_identity(morph_rows: list[tuple[list[str], list[str]]], *, backend: str = "eflomal"):
    from align.aligner import align

    table, _used = align(morph_rows, backend=backend, allow_cooccur_fallback=False)
    return table


def build_table_guided(morph_rows: list[tuple[list[str], list[str]]], *, backend: str = "eflomal"):
    from align import segment_en
    from align.aligner import align

    rev_rows = [(tgt, src) for src, tgt in morph_rows]
    rev_table, _used = align(rev_rows, backend=backend, allow_cooccur_fallback=False)
    split_map = segment_en.guided_split_map(_en_freqs(morph_rows), rev_table)
    rows = [(segment_en.guided_segment(src, split_map), tgt) for src, tgt in morph_rows]
    table, _used = align(rows, backend=backend, allow_cooccur_fallback=False)
    return table


def build_table_factored(morph_rows: list[tuple[list[str], list[str]]], model, *, backend: str = "eflomal"):
    from align import class_key
    from align.aligner import align

    factor = class_key.factored_map(model)
    rows = [(src, [factor.get(t, t) for t in tgt]) for src, tgt in morph_rows]
    table, _used = align(rows, backend=backend, allow_cooccur_fallback=False)
    return table


_BUILDERS = {
    "identity": lambda morph_rows, model, backend: build_table_identity(morph_rows, backend=backend),
    "guided": lambda morph_rows, model, backend: build_table_guided(morph_rows, backend=backend),
    "factored": lambda morph_rows, model, backend: build_table_factored(morph_rows, model, backend=backend),
}


def build_table(align_mode: str, morph_rows: list[tuple[list[str], list[str]]], model, *,
                backend: str = "eflomal"):
    """Dispatch on an already-built (src, target-morphs) row list — for callers (`morph_align_hc.run`)
    that have already paid for `build_streams`/HC parsing and shouldn't redo it."""
    fn = _BUILDERS.get(align_mode)
    if fn is None:
        raise ValueError(f"unknown align_mode {align_mode!r} (choices: {sorted(_BUILDERS)})")
    return fn(morph_rows, model, backend)


def align_table(pair: str, model, sample: int, *, align_mode: str = DEFAULT_ALIGN_MODE,
                backend: str = "eflomal"):
    """Convenience wrapper for callers (`cotrain.cotrain`) that don't already have `morph_rows` built —
    fetches verses + builds the HC-segmented morpheme stream itself, then dispatches via `build_table`."""
    from align.morph_align_hc import _verses, build_streams

    verses = _verses(pair, sample)
    _streams, morph_rows = build_streams(pair, model, verses)
    return build_table(align_mode, morph_rows, model, backend=backend)
