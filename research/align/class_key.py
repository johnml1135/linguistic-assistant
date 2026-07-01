"""P3: class-constrained token identity for the thot-on-morphs paradigm study.

Canonicalizes target-morpheme tokens to their harmony-class **archiphoneme** (reusing
`induce/phonology.py`'s already-built collapse machinery) BEFORE they are handed to the aligner, so THOT
pools evidence across allomorphs (Swahili causative `-ish-`/`-esh-`) as one type instead of splintering an
already-scarce count across surface variants — the concrete mechanism behind "use known classes/phonemes
to constrain the statistics" (see `thot-on-morphs.md` §1, §4).

Deliberately operates on the TOKEN STREAM (pre-alignment canonicalization), not on the resulting
`GlossTable` post hoc: `GlossTable` is keyed by surface form, so merging after the fact would mean
re-keying every table lookup site; canonicalizing the stream once, before `align()` ever sees it, gets the
same pooling effect for free through THOT's own frequency counting.
"""

from __future__ import annotations


def canonical_map(model, pair: str) -> dict[str, str]:
    """surface affix form -> its archiphoneme, for every form in a collapsible harmony family. Forms with
    no known harmony family are simply absent (callers fall back to the raw surface form)."""
    from induce.tdd import harmony_families
    from induce.phonology import HARMONY_CLASSES, collapse_families

    affix_forms = [a.form for a in model.affixes]
    fams = harmony_families(affix_forms)
    classes = HARMONY_CLASSES.get(pair, {})
    report = collapse_families(fams, classes)
    canon: dict[str, str] = {}
    for p in report.collapsed:
        for m in p.members:
            canon[m] = p.archiphoneme
    return canon


def canonicalize_stream(morph_rows_tgt: list[list[str]], canon: dict[str, str]) -> list[list[str]]:
    """Apply a `canonical_map()` result to a target-morpheme stream (one list of morph forms per verse)."""
    return [[canon.get(tok, tok) for tok in row] for row in morph_rows_tgt]


# --------------------------------------------------------------------------- P6: factored (Koehn & Hoang)
def factored_map(model) -> dict[str, str]:
    """affix surface form -> its morphosyntactic factor key ("{kind}:{req_pos}"), for every affix with a
    learned POS/MSA restriction (`induce.tdd.assign_slots`' `req_pos`). Affixes with no learned restriction,
    and all roots, are absent (callers fall back to the raw surface form) — only grammatical morphemes
    with a known attaching-POS are pooled by class; content morphemes keep their lexical identity
    (Koehn & Hoang 2007's factored-translation idea, applied to alignment evidence instead of translation
    streams). The best-performing paradigm in the thot-on-morphs study — see thot-on-morphs-report.md §5.5."""
    return {a.form: f"{a.kind}:{a.req_pos}" for a in model.affixes if a.req_pos}
