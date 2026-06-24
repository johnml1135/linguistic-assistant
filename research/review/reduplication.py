"""Reduplication detection — Cycle 2 of the frontier build-out (the non-concatenative chunk type).

Tagalog (and Austronesian generally) marks aspect by reduplication: sulat→susulat, takbo→tatakbo,
bili→bibili — an initial CV(C)V copy. Pure concatenative segmentation can't see this, so it has been a
blind spot (the frontier listed `non-concatenative` as `pending`). This detector flags initial-copy
reduplication and feeds a real frontier probe, making Tagalog's actual frontier visible.

Cheap + honest: detects an initial repeated unit of length 1–3 (`W[:k] == W[k:2k]`); it catches productive
CV/CVC reduplication and over-counts accidental initial repeats (reported as a rate, not a claim per word).
Full/root reduplication across a space or hyphen (araw-araw) is a separate, easy follow-on.
"""

from __future__ import annotations


def is_reduplicated(word: str) -> int | None:
    """Return the copy length k if `word` begins with a repeated unit (k∈1..3), else None.
    e.g. susulat→2 (su·su), tatakbo→2 (ta·ta), bibili→2, aalis→1 (a·a)."""
    for k in (3, 2, 1):
        if len(word) > 2 * k and word[:k] == word[k:2 * k] and word[k - 1] not in "":
            # require the copy to be a plausible syllable (contains a vowel) to cut noise
            if any(ch in "aeiou" for ch in word[:k]):
                return k
    return None


INFIXES = ("um", "in")        # Tagalog actor/perfective infixes, inserted after the initial consonant


def is_infixed(word: str, stems: set) -> str | None:
    """Return the infix if `word` = C + infix + rest where C+rest is an attested stem (s-um-ulat→'um',
    b-in-ili→'in'). Infixation is non-concatenative — invisible to edge-stripping segmentation."""
    if len(word) < 4 or word[0] in "aeiou":
        return None
    for inf in INFIXES:
        if word[1:1 + len(inf)] == inf and (word[0] + word[1 + len(inf):]) in stems:
            return inf
    return None


def scan(pair: str, *, sample: int = 0, min_count: int = 2) -> dict:
    """Reduplication rate over corpus types (recurring types only, so the name/hapax tail doesn't inflate)."""
    from align.morph_align_hc import _verses
    from collections import Counter
    types: Counter = Counter()
    for _ref, _src, tgt in _verses(pair, sample):
        for w in tgt:
            if w.isalpha() and len(w) > 3:
                types[w] += 1
    recurring = [w for w, c in types.items() if c >= min_count]
    redup = [w for w in recurring if is_reduplicated(w)]
    rate = len(redup) / (len(recurring) or 1)
    redup_tok = sum(types[w] for w in redup)
    return {"pair": pair, "n_recurring_types": len(recurring), "n_reduplicated": len(redup),
            "type_rate": round(rate, 3), "token_rate": round(redup_tok / (sum(types.values()) or 1), 3),
            "examples": sorted(redup, key=lambda w: -types[w])[:12]}
