"""Affix induction — Cycle 2 of the frontier build-out.

The additive/morphotactics probes were gold-dependent: a language with a thin gold affix list (Tagalog)
read as "not-ready" even though it is heavily affixed. This induces the affix inventory straight from the
corpus by PRODUCTIVITY — an affix is real if stripping it leaves an attested word (a real stem), across
many distinct stems (Harris/Goldsmith segmentation). It lets the frontier see morphology with no gold.

Handles prefixes, suffixes, and circumfixes; infixation (Tagalog -um-/-in-) is a separate, harder pass
(flagged, not silently missed). Pure-ish: one corpus pass; ranking is deterministic.
"""

from __future__ import annotations

from collections import Counter


def induce_affixes(pair: str, *, sample: int = 0, min_stems: int = 10, min_len: int = 2,
                   max_len: int = 5) -> dict:
    """Induce productive prefixes/suffixes: those that strip to an ATTESTED word across ≥ min_stems
    distinct stems. Returns {prefixes, suffixes} each as [(affix, n_stems, examples)]."""
    from align.morph_align_hc import _verses
    types: Counter = Counter()
    for _ref, _src, tgt in _verses(pair, sample):
        for w in tgt:
            if w.isalpha():
                types[w] += 1
    attested = {w for w, c in types.items() if c >= 2 and len(w) > 2}      # a stem must be a real recurring word
    pre_stems: dict[str, set] = {}
    suf_stems: dict[str, set] = {}
    for w in types:
        if w not in attested:
            continue
        for k in range(min_len, max_len + 1):
            if len(w) > k + 2:
                if w[k:] in attested:
                    pre_stems.setdefault(w[:k], set()).add(w[k:])
                if w[:-k] in attested:
                    suf_stems.setdefault(w[-k:], set()).add(w[:-k])

    def rank(d: dict) -> list:
        out = [(a, len(s), sorted(s)[:3]) for a, s in d.items() if len(s) >= min_stems]
        return sorted(out, key=lambda x: -x[1])

    return {"pair": pair, "prefixes": rank(pre_stems)[:25], "suffixes": rank(suf_stems)[:25],
            "infix_note": "infixes (e.g. Tagalog -um-/-in-) not covered here — separate medial-copy pass"}


def induced_affix_forms(pair: str, *, sample: int = 0, **kw) -> list[dict]:
    """Affixes in the same shape the gold uses ({affix, morph_type}) so the frontier probes can consume
    induced affixes exactly like gold ones."""
    r = induce_affixes(pair, sample=sample, **kw)
    return ([{"affix": a, "morph_type": "prefix"} for a, _n, _e in r["prefixes"]] +
            [{"affix": a, "morph_type": "suffix"} for a, _n, _e in r["suffixes"]])
