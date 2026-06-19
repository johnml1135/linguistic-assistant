"""Induce inflection CLASSES (the generative rules) from paradigms — not one entry per surface form.

HC/LibLCM is generative: a lemma belongs to an inflection class (MoInflClass); the class is a table of
rules (feature-bundle → stem transform); irregular cells are per-lemma overrides. This module turns the
flat per-lemma paradigms (from UniMorph) into exactly that: classes + a class per lemma + override cells
+ a per-lemma STEM and a class affix table (stem-relative), so an HC grammar can GENERATE the forms
(root = stem, affixes = class table) instead of memorising them.

A transform is `(kind, remove, add)`: kind "S" = suffixal (share a prefix; replace the differing suffix —
Spanish conjugation), "P" = prefixal (share a suffix; replace the differing prefix — Indonesian meN-).
"""

from __future__ import annotations

from collections import Counter, defaultdict


def canon(feats: dict) -> str:
    """Canonical key for an FsFeatStruc cell, e.g. {Tense:Future,Person:Third} -> 'Person=Third;Tense=Future'."""
    return ";".join(f"{k}={feats[k]}" for k in sorted(feats)) or "BASE"


def transform(lemma: str, surface: str) -> tuple[str, str, str]:
    """How to derive `surface` from `lemma`: the cheaper of a suffixal or prefixal edit."""
    p = 0
    while p < len(lemma) and p < len(surface) and lemma[p] == surface[p]:
        p += 1
    suf = (lemma[p:], surface[p:])
    q = 0
    while q < len(lemma) and q < len(surface) and lemma[len(lemma) - 1 - q] == surface[len(surface) - 1 - q]:
        q += 1
    pre = (lemma[:len(lemma) - q], surface[:len(surface) - q])
    if len(suf[0]) + len(suf[1]) <= len(pre[0]) + len(pre[1]):
        return ("S", suf[0], suf[1])
    return ("P", pre[0], pre[1])


def _common_prefix(words: list[str]) -> str:
    if not words:
        return ""
    s = min(words)
    t = max(words)
    i = 0
    while i < len(s) and i < len(t) and s[i] == t[i]:
        i += 1
    return s[:i]


# enclitic pronoun combinations (ábranme = abran + me) are clitics — syntax, not the verb's inflection
# class. UniMorph lists them; keep them out of class induction so they don't masquerade as irregularity.
def _is_clitic_cell(cell: str) -> bool:
    return "Case=" in cell


def induce(paradigms: dict[str, dict[str, str]], pos_by: dict[str, str],
           *, min_class: int = 12, n_diag: int = 12, conf_frac: float = 0.5):
    """paradigms: lemma -> {cell: surface}. Returns (classes, lemma_class, overrides, stems).

    Clusters WITHIN each POS (so nouns/adjectives form their own classes, not drowned by verb cells),
    seeds a class from an identical transform-signature over that POS's diagnostic cells, and flags an
    override only on a cell the class realises CONFIDENTLY (modal supported by ≥ conf_frac of members),
    so rare/variable cells don't masquerade as irregularity.
    """
    par = {lm: {c: s for c, s in cells.items() if not _is_clitic_cell(c)} for lm, cells in paradigms.items()}
    par = {lm: cells for lm, cells in par.items() if cells}

    by_pos: dict[str, list[str]] = defaultdict(list)
    for lm in par:
        by_pos[pos_by.get(lm, "Unknown")].append(lm)

    classes: list[dict] = []
    lemma_class: dict[str, str] = {}
    idx = 0
    for pos, lms in by_pos.items():
        cf: Counter = Counter()
        for lm in lms:
            cf.update(par[lm].keys())
        diag = [c for c, _ in cf.most_common(n_diag)]
        groups: dict[tuple, list[str]] = defaultdict(list)
        for lm in lms:
            sig = tuple((c, *transform(lm, par[lm][c])) for c in diag if c in par[lm])
            if sig:
                groups[sig].append(lm)
        for _, members in sorted((g for g in groups.items() if len(g[1]) >= min_class), key=lambda g: -len(g[1])):
            idx += 1
            cid = f"{pos.replace(' ', '_')}-{idx}"  # no spaces: class id is used as an HC POS id (space-separated attr)
            cell_trans: dict[str, Counter] = defaultdict(Counter)
            stem_suffix: dict[str, Counter] = defaultdict(Counter)
            for m in members:
                stem_m = _common_prefix([par[m][c] for c in par[m]] + [m])
                for c, surf in par[m].items():
                    cell_trans[c][transform(m, surf)] += 1
                    if surf.startswith(stem_m):
                        stem_suffix[c][surf[len(stem_m):]] += 1
            rules = []
            for c, cc in cell_trans.items():
                t, n = cc.most_common(1)[0]
                # all stem-relative realisations seen for this cell (not just the modal) — so a class with
                # internal variation (había=hab+ía beside other forms) still yields a feature-bearing affix.
                variants = [s for s, _ in stem_suffix[c].most_common(4)] if stem_suffix.get(c) else []
                rules.append({"features": c, "kind": t[0], "remove": t[1], "add": t[2],
                              "suffix": variants[0] if variants else "", "suffixes": variants,
                              "support": n, "members": len(members)})
            classes.append({"class_id": cid, "pos": pos, "size": len(members),
                            "rules": sorted(rules, key=lambda r: -r["support"])})
            for m in members:
                lemma_class[m] = cid

    full = {c["class_id"]: {r["features"]: (r["kind"], r["remove"], r["add"]) for r in c["rules"]} for c in classes}
    by_pos_cls: dict[str, list[str]] = defaultdict(list)
    for c in classes:
        by_pos_cls[c["pos"]].append(c["class_id"])
    for lm, cells in par.items():
        if lm in lemma_class:
            continue
        pos = pos_by.get(lm, "Unknown")
        best, score = None, -1
        for cid in by_pos_cls.get(pos, []):
            cd = full[cid]
            s = sum(1 for c, surf in cells.items() if cd.get(c) == transform(lm, surf))
            if s > score:
                best, score = cid, s
        if best:
            lemma_class[lm] = best

    conf = {c["class_id"]: {r["features"]: (r["kind"], r["remove"], r["add"])
                            for r in c["rules"] if r["support"] >= conf_frac * r["members"]}
            for c in classes}
    overrides: dict[str, list] = defaultdict(list)
    stems: dict[str, str] = {}
    for lm, cells in par.items():
        cid = lemma_class.get(lm)
        cd = conf.get(cid, {}) if cid else {}
        for c, surf in cells.items():
            if c in cd and transform(lm, surf) != cd[c]:
                overrides[lm].append({"features": c, "surface": surf})
        reg = [surf for c, surf in cells.items() if not (c in cd and transform(lm, surf) != cd[c])]
        stems[lm] = _common_prefix(reg + [lm])

    return classes, lemma_class, dict(overrides), stems
