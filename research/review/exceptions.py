"""Layered-exception carving — Cycle 4 of the frontier build-out.

A flat list of exceptions isn't the truth; real exceptions are layered ("i before e, except after c, except
neighbor/weigh, except seize"). This carves a set of flagged exceptions into ordered sub-CLASSES (a shared
environment that captures ≥k of them) plus an individual residue — the recursive structure from
`docs/workflow.md §3`, applied to the exceptions a class/rule throws.

Greedy recursive carve: repeatedly extract the largest coherent subgroup (shared initial letter or shared
ending) until only individuals remain. Pure + offline-testable.
"""

from __future__ import annotations

from collections import Counter


def _features(noun: str) -> list[tuple[str, str]]:
    """Candidate shared environments — linguistically meaningful ones, not raw initial letters: a
    PHONOLOGICAL trigger (stressed a-initial → the *el agua* class) and DERIVATIONAL endings (2–3 chars,
    e.g. -ista/-eta common-gender). Raw single initials are noise and excluded."""
    feats = []
    if noun[:1] in "aá" or noun[:2] == "ha":
        feats.append(("phon", "a-initial"))          # el agua / el alma / el águila
    if len(noun) >= 3:
        feats.append(("ends", noun[-3:]))
    if len(noun) >= 2:
        feats.append(("ends", noun[-2:]))
    return feats


def carve(nouns: list[str], *, min_class: int = 3) -> dict:
    """Carve a list of exception nouns into ordered sub-classes (shared environment, ≥ min_class members)
    + an individual residue. Most-specific (largest coherent) first — the Elsewhere ordering."""
    items = list(dict.fromkeys(nouns))
    classes = []
    while len(items) >= min_class:
        counts = Counter()
        for n in items:
            for kind, val in _features(n):
                counts[(kind, val)] += 1
        (kind, val), cov = counts.most_common(1)[0]
        if cov < min_class:
            break
        members = [n for n in items if (kind, val) in _features(n)]
        label = (f"begins with '{val}'" if kind == "initial" else f"ends in '-{val}'")
        classes.append({"environment": label, "kind": kind, "value": val,
                        "members": sorted(members), "n": len(members)})
        items = [n for n in items if n not in members]
    return {"classes": classes, "individuals": sorted(items),
            "n_classes": len(classes), "n_individuals": len(items)}
