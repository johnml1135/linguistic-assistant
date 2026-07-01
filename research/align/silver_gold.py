"""Silver (alignment-derived) word->gloss pseudo-gold for the thot-on-morphs paradigm study.

`induce/gold.py::load_gold` reads `induce/gold/<pair>.jsonl` (a small hand-verified word->gloss set) as
the TDD cycle's correctness gate. As of this study, that directory does not exist for ANY of the 8 pairs
(`induce/README.md`'s claim that Spanish ships one is stale) — see thot-on-morphs-report.md, Blocker #1.

This is the substitute: a word->gloss set built from the THOT-derived `glosses.tsv` already produced by
the eBible build (`induce/tdd.py::load_glosses`), restricted to words in the FROZEN HELD-OUT set (never
promoted to roots) so scoring isn't tautological with the roots' own glosses. It is NOT independent of the
statistical pipeline under test (glosses.tsv comes from the same THOT alignment `cotrain.py` uses), so
weaker than a real hand-verified gate — but real, available, and uniform across all 8 pairs, where the
hand-verified gate the README describes is available for zero.
"""

from __future__ import annotations


def build_silver_gold(held_out: list[str], glosses: dict[str, str], *, n: int = 40,
                      pivot: str = "en") -> list[tuple[str, str]]:
    """[(word, gloss)] for up to `n` held-out words with a real (non-"?", non-function-word) gloss."""
    from review import langknow

    function = langknow.function_words(pivot)
    out: list[tuple[str, str]] = []
    for w in held_out:
        g = (glosses.get(w, "?") or "?").lower().strip()
        if g in ("", "?") or g in function or not g.isalpha() or len(g) < 3:
            continue
        out.append((w, g))
        if len(out) >= n:
            break
    return out
