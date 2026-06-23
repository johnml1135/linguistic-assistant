"""Infer a real grammatical gloss for an induced affix from the English inflection it correlates with.

The cycle glosses affixes by their surface form (`-s`, `na-`) — not a morpheme label. But the bilingual
alignment gives an English gloss for *both* a root and root+affix forms; when those English glosses differ
by a regular English inflection (house→houses, walk→walked), that difference names the affix's function
(PL, PST, …). This is a weak, data-driven signal (statistical aligners often gloss to the lemma, so it
fires sparsely), used only where a clear majority emerges; otherwise the surface-form gloss is kept.
See linguistics/skills/propose-from-evidence.md and generalize-not-enumerate.md.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace

from engine.grammar import Affix, LangModel


def en_morph_diff(base: str, infl: str) -> str | None:
    """Grammatical tag if ``infl`` is a regular English inflection of ``base`` (else None)."""
    b, x = base.lower().strip(), infl.lower().strip()
    if not b or not x or b == x:
        return None
    if x in (b + "s", b + "es") or (b.endswith("y") and x == b[:-1] + "ies"):
        return "PL"   # nominal plural / 3SG — PL is the common reading on the noun-heavy lexicon
    if x in (b + "ed", b + "d") or (b.endswith("y") and x == b[:-1] + "ied"):
        return "PST"
    if x == b + "ing":
        return "PROG"
    if x == b + "est" or (b.endswith("y") and x == b[:-1] + "iest"):
        return "SUPL"
    if x == b + "er" or (b.endswith("y") and x == b[:-1] + "ier"):
        return "CMPR"
    if x == b + "ly":
        return "ADVZ"
    return None


def infer_affix_glosses(model: LangModel, freqs: Counter, glosses: dict[str, str]) -> tuple[list[Affix], int]:
    """Relabel each affix with an inferred grammatical gloss where the English diff gives a clear majority.

    Returns (new affixes, #relabelled). Only single-affix words (root + one affix) vote, so the signal is
    clean; ties / no-evidence keep the surface-form gloss.
    """
    rootgloss = {e.form: e.gloss for e in model.lexicon if e.gloss and e.gloss != "?"}
    roots = sorted(rootgloss, key=len, reverse=True)
    suffset = {a.form for a in model.affixes if a.kind == "suffix"}
    prefset = {a.form for a in model.affixes if a.kind == "prefix"}
    votes: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for w, f in freqs.items():
        wg = glosses.get(w)
        if not wg or wg == "?":
            continue
        for r in roots:
            if len(r) < 3 or len(w) <= len(r):
                continue
            if w.startswith(r) and w[len(r):] in suffset:
                tag = en_morph_diff(rootgloss[r], wg)
                if tag:
                    votes[("suffix", w[len(r):])][tag] += f
                break
            if w.endswith(r) and w[: len(w) - len(r)] in prefset:
                tag = en_morph_diff(rootgloss[r], wg)
                if tag:
                    votes[("prefix", w[: len(w) - len(r)])][tag] += f
                break

    out: list[Affix] = []
    relabelled = 0
    for a in model.affixes:
        v = votes.get((a.kind, a.form))
        if v:
            out.append(replace(a, gloss=v.most_common(1)[0][0]))
            relabelled += 1
        else:
            out.append(a)
    return out, relabelled
