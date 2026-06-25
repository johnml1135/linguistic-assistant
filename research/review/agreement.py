"""Agreement / concord induction — Cycle 1 of the frontier build-out.

Bantu concord: a noun of class K makes its modifiers carry K's agreement prefix (watu wazuri = cl2 noun +
cl2 adjective). We induce the concord table from controller(noun)→target(adjective) co-variation in the
corpus and fill the declared schema's concord cells. This turns the frontier's `agreement` probe from a
placeholder ("all cells empty") into a real measure (cells filled vs still empty, from data).

Honest reach: many gold adjectives are listed as bare stems, so only the clear alliterative concord
(wa→wa, m→m, ki→ki, vi→vy, mi→mi) is recoverable now; predicative/bare adjectives give no class signal.
Reported, not hidden. Pure builders are unit-tested; the corpus scan is the slow part.
"""

from __future__ import annotations

from collections import Counter

from review import langknow                     # per-language reference knowledge (loaded from data, not hardcoded)
from review.classes import declared_schema


def _prefix(word: str, lang: str) -> str:
    for p in langknow.class_prefix_set(lang):   # noun-class prefix inventory for THIS language (data-loaded)
        if word.startswith(p) and len(word) > len(p) + 1:
            return p
    return "Ø"


def concord_votes(pair: str, *, sample: int = 0) -> dict[str, Counter]:
    """{noun_prefix -> Counter(adjective_prefix)} from noun+adjective adjacency (Bantu N-A order)."""
    from align.morph_align_hc import _verses
    from gold.goldio import load_gold
    pos = load_gold(pair).get("pos", {})
    nouns = {w for w, p in pos.items() if str(p).lower() == "noun"}
    adjs = {w for w, p in pos.items() if str(p).lower() == "adjective"}
    votes: dict[str, Counter] = {}
    for _ref, _src, tgt in _verses(pair, sample):
        t = [w for w in tgt if w.isalpha()]
        for i in range(len(t) - 1):
            if t[i] in nouns and t[i + 1] in adjs:
                votes.setdefault(_prefix(t[i], pair), Counter())[_prefix(t[i + 1], pair)] += 1
    return votes


def build_concord(votes: dict[str, Counter], schema: dict, *, min_support: int = 20,
                  min_share: float = 0.5) -> dict:
    """Pure: fill each declared class's adjective-concord cell with the dominant adjective prefix among its
    nouns — accepting only a well-supported, non-Ø, majority signal (else the cell stays empty, honestly)."""
    pref_to_class = {p: c["id"] for c in schema.get("classes", []) for p in c.get("prefixes", [])}
    by_class: dict[str, Counter] = {}
    for noun_pfx, adj_counter in votes.items():
        cid = pref_to_class.get(noun_pfx)
        if cid:
            by_class.setdefault(cid, Counter()).update(adj_counter)
    filled = {}
    for cid, counter in by_class.items():
        non_o = Counter({k: v for k, v in counter.items() if k != "Ø"})
        total = sum(counter.values()) or 1
        if non_o:
            adj_pfx, support = non_o.most_common(1)[0]
            if support >= min_support and support / total >= min_share:
                filled[cid] = {"adjective": adj_pfx, "support": support, "share": round(support / total, 2)}
    return filled


# The Bantu associative ("X wa Y" = "X of Y") agrees with X's class and is far more cleanly class-marked than
# bare adjectives. The marker inventories below are LOADED per language from golden_sets/_reference/<lang>.json
# (review.langknow), NOT hardcoded here. Markers that map UNAMBIGUOUSLY to a class let us classify zero-prefix
# nouns by the agreement they trigger (Corbett) — wa/kwa are shared across classes, so excluded.
def _concord_marker(word: str, lang: str) -> str | None:
    """The class-concord marker carried by an associative or possessive word ('wake'→'wa', 'lake'→'la').
    Marker/possessive/concord inventories are per-language reference data, loaded by review.langknow."""
    if word in langknow.associative_markers(lang):
        return word
    concord = langknow.concord_prefixes(lang)
    for st in langknow.possessive_stems(lang):
        if word.endswith(st):
            pre = word[:-len(st)]
            if pre in concord:
                return pre
    return None


def associative_votes(pair: str, *, sample: int = 0):
    """(noun_prefix → Counter(assoc)), plus per zero-prefix noun its associative markers (for classifying
    the no-visible-prefix nouns by the concord they trigger)."""
    from align.morph_align_hc import _verses
    from gold.goldio import load_gold
    nouns = {w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "noun"}
    by_pfx: dict[str, Counter] = {}
    zero: dict[str, Counter] = {}
    for _ref, _src, tgt in _verses(pair, sample):
        t = [w for w in tgt if w.isalpha()]
        for i in range(len(t) - 1):
            if t[i] in nouns:
                marker = _concord_marker(t[i + 1], pair)   # associative OR possessive concord
                if marker:
                    p = _prefix(t[i], pair)
                    by_pfx.setdefault(p, Counter())[marker] += 1
                    if p == "Ø":
                        zero.setdefault(t[i], Counter())[marker] += 1
    return by_pfx, zero


def classify_zero_prefix(zero: dict[str, Counter], lang: str, *, min_count: int = 2) -> dict:
    """Assign each zero-prefix noun to a class via its dominant unambiguous associative marker (the
    associative→class map is per-language reference data, loaded by review.langknow)."""
    assoc_to_class = langknow.associative_to_class(lang)
    out = {}
    for noun, c in zero.items():
        if c.total() < min_count:
            continue
        marker, n = c.most_common(1)[0]
        cid = assoc_to_class.get(marker)
        if cid:
            out[noun] = {"class": cid, "via": marker, "support": n, "confidence": round(n / c.total(), 3)}
    return out


def build_associative_concord(by_pfx: dict[str, Counter], schema: dict, *, min_support: int = 20,
                              min_share: float = 0.4) -> dict:
    pref_to_class = {p: c["id"] for c in schema.get("classes", []) for p in c.get("prefixes", [])}
    by_class: dict[str, Counter] = {}
    for npfx, counter in by_pfx.items():
        cid = pref_to_class.get(npfx)
        if cid:
            by_class.setdefault(cid, Counter()).update(counter)
    filled = {}
    for cid, counter in by_class.items():
        total = sum(counter.values()) or 1
        marker, support = counter.most_common(1)[0]
        if support >= min_support and support / total >= min_share:
            filled[cid] = {"associative": marker, "support": support, "share": round(support / total, 2)}
    return filled


def induce(pair: str, *, sample: int = 0) -> dict:
    """Induce concord for the declared schema (adjective + the stronger associative signal) and classify
    zero-prefix nouns by the agreement they trigger. Reports cell coverage + nouns cracked."""
    schema = declared_schema(pair)
    if not schema:
        return {"error": "no declared class schema", "pair": pair}
    adj = build_concord(concord_votes(pair, sample=sample), schema)
    by_pfx, zero = associative_votes(pair, sample=sample)
    assoc = build_associative_concord(by_pfx, schema)
    cracked = classify_zero_prefix(zero, pair)
    cells = set(adj) | set(assoc)                       # classes with at least one concord cell induced
    n_classes = len(schema.get("classes", [])) or 1
    # residue: zero-prefix nouns seen but NOT agreement-confirmed default to cl9/10 (Bantu's default/residue
    # class for unmarked & loan nouns) — LOW confidence, flagged needs-confirmation, NOT counted as cracked.
    seen_zero = {n for n, c in zero.items() if c.total() >= 1}
    default_residue = sorted(seen_zero - set(cracked))
    return {"pair": pair, "adjective_concord": adj, "associative_concord": assoc,
            "cells_filled": len(cells), "n_classes": n_classes, "coverage": round(len(cells) / n_classes, 3),
            "zero_prefix_classified": len(cracked), "zero_examples": dict(list(cracked.items())[:8]),
            "default_residue_cl9_10": len(default_residue), "default_confidence": 0.4,
            "verb_concord": "unreliable from adjacency — needs syntactic subject identification (finding)",
            "examples": {cid: f"cl{cid} → assoc '{d['associative']}' ({d['support']}×, {d['share']:.0%})"
                         for cid, d in sorted(assoc.items())}}
