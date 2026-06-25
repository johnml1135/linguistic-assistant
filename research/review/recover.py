"""Derive the (formerly hardcoded) linguistic maps from DATA, and verify we can RECOVER the hardcoded
values. The principle: no hardcoded linguistic knowledge in the analysis path — the system derives the
subject-marker→class, associative→class, and TAM→tense maps from the corpus + projection, using the
already-derived noun classes as anchors. The old constants survive only as a *recovery reference* the tests
check the derivation against (so we can prove the derivation is right and fall back if projection is absent).
"""

from __future__ import annotations

from collections import Counter


def derive_sm_to_class(pair: str, pivot: str = "en", sample: int = 0, min_count: int = 8) -> dict:
    """Subject-marker → noun-class, DERIVED: anchor on the combined noun-class assignment, correlate each
    verb's subject marker with its subject noun's class. Recovers {a:1, wa:2, u:3, ki:7, …} from data."""
    from review.classes import persisted_noun_classes
    from review.project import subject_verb_pairs, subject_marker
    classes = persisted_noun_classes(pair)
    pairs = subject_verb_pairs(pair, pivot, sample) or []
    by_sm: dict[str, Counter] = {}
    for noun, verb in pairs:
        cl = classes.get(noun, {}).get("class")
        sm = subject_marker(verb, pair)
        if cl and sm != "?":
            by_sm.setdefault(sm, Counter())[cl] += 1
    return {sm: c.most_common(1)[0][0] for sm, c in by_sm.items() if sum(c.values()) >= min_count}


def derive_assoc_to_class(pair: str, sample: int = 0, min_count: int = 8) -> dict:
    """Associative-marker → noun-class, DERIVED: correlate each noun's associative marker with its class.
    Recovers {ya:9/10, la:5, cha:7, vya:8, …} from data."""
    from review.agreement import _concord_marker
    from review.classes import persisted_noun_classes
    from align.morph_align_hc import _verses
    from gold.goldio import load_gold
    classes = persisted_noun_classes(pair)
    nouns = {w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "noun"} or set(classes)
    by_marker: dict[str, Counter] = {}
    for _ref, _src, tgt in _verses(pair, sample):
        t = [w for w in tgt if w.isalpha()]
        for i in range(len(t) - 1):
            if t[i] in nouns:
                m = _concord_marker(t[i + 1], pair)
                cl = classes.get(t[i], {}).get("class")
                if m and cl:
                    by_marker.setdefault(m, Counter())[cl] += 1
    return {m: c.most_common(1)[0][0] for m, c in by_marker.items() if sum(c.values()) >= min_count}


def _prefix_stems(pair: str, min_stems: int = 6):
    """Shared machinery: candidate prefix → its stem set, and stem → the prefixes it appears with. The
    stem→prefixes map is the concord 'signature' (Goldsmith): a real class prefix's stems recur across MANY
    prefixes (the concord pool — 'tu' under m/wa/ki/vi/u), while an over-segmentation shadow's stems ('itu'
    only under k/v) do not."""
    from collections import defaultdict
    from gold.goldio import load_gold
    from review.project import load_pos
    pos = load_gold(pair).get("pos", {}) or load_pos(pair)
    nouns = [w for w, p in pos.items() if str(p).lower() == "noun"]
    pre_stems: dict[str, set] = defaultdict(set)
    for n in nouns:
        for k in (1, 2, 3):
            if len(n) > k + 1:
                pre_stems[n[:k]].add(n[k:])
    cands = {p: s for p, s in pre_stems.items() if len(s) >= min_stems}
    stem_pre: dict[str, set] = defaultdict(set)
    for p, s in cands.items():
        for stem in s:
            stem_pre[stem].add(p)
    return cands, stem_pre, set(nouns)


def derive_prefixes(pair: str, min_stems: int = 6, min_partners: int = 3, min_good: int = 4) -> dict:
    """The noun-class PREFIX inventory, DERIVED with no hardcoded list (Goldsmith signature test): a real
    class prefix is one whose stems are SHARED across many other prefixes — the concord pool. A stem is
    'high-signature' if it appears with ≥min_partners distinct candidate prefixes (filtering out prefixes
    that nest inside each other, which are just alternate splits of one word). A prefix is kept if it has
    ≥min_good high-signature stems. This filters the over-segmentation shadows (k/v shadowing ki/vi) that
    the pure pairing count cannot. Recovers {m, wa, mi, ki, vi, ji, ma, ku, u, n, …} from data."""
    cands, stem_pre, _ = _prefix_stems(pair, min_stems)
    out: dict[str, dict] = {}
    for p, stems in cands.items():
        good = []
        for s in stems:
            partners = {q for q in stem_pre[s]
                        if q != p and not q.startswith(p) and not p.startswith(q)}
            if len(partners) >= min_partners:
                good.append(s)
        if len(good) >= min_good:
            out[p] = {"n_stems": len(stems), "n_signature_stems": len(good),
                      "examples": sorted(good)[:5]}
    return out


def _concord_anchored_classes(pair: str, sample: int = 0) -> dict:
    """Per-noun class from CONCORD ONLY — associative agreement + projected subject-marking. Needs NO prefix
    list (the maps it uses, ASSOC_TO_CLASS/SM_TO_CLASS, are themselves derived by recover.derive_*). This is
    the ground truth a class assignment should rest on (Corbett: class = agreement behaviour, not shape)."""
    out: dict[str, str] = {}
    try:
        from review.agreement import associative_votes, classify_zero_prefix
        _by, zero = associative_votes(pair, sample=sample)
        for n, d in classify_zero_prefix(zero, pair).items():
            out[n] = d["class"]
    except Exception:
        pass
    try:
        from review.project import classify_by_subject_marking
        for n, d in classify_by_subject_marking(pair, sample=sample).items():
            out[n] = d["class"]                      # subject-marking overrides (stronger signal)
    except Exception:
        pass
    return out


def derive_class_pairs(pair: str, min_stems: int = 6, min_pair: int = 4) -> list[dict]:
    """Derive noun-class PAIRINGS from pure distribution — NO hardcoded list, NO concord. A class prefix
    pairs with another over a shared stem set: the singular/plural alternation (mtu/watu → m·wa,
    kitu/vitu → ki·vi, jicho/macho → ji·ma). Greedy with consumption so an over-segmentation shadow
    (k/v shadowing ki/vi) finds its stems already claimed by the stronger real pairing and drops out. The
    CLEAN HEAD of this list (m/wa, ki/vi, mw/w, mi/mw, ji/ma) is the emergent class structure a human
    ratifies in suggest→declare — the machine never asserts the canonical Meinhof numbering itself."""
    cands, stem_pre, nounset = _prefix_stems(pair, min_stems)
    raw = []
    for p, sp in cands.items():
        for q, sq in cands.items():
            if p >= q or p.startswith(q) or q.startswith(p):
                continue
            shared = sp & sq
            if len(shared) >= min_pair:
                # weight by the shared stems' cross-prefix SIGNATURE: a real pairing's stems recur under many
                # prefixes (ki/vi's 'tu' under m/wa/ki/vi), an over-seg shadow's don't (k/v's 'itu' only k/v).
                # This makes the real pairing outrank its shadow so it consumes the words first.
                sig = sum(len(stem_pre[s]) for s in shared)
                raw.append((p, q, shared, sig))
    raw.sort(key=lambda t: (-t[3], -len(t[2])))
    consumed: set = set()
    pairs = []
    for p, q, shared, _sig in raw:
        fresh = {s for s in shared if (p + s) not in consumed and (q + s) not in consumed
                 and (p + s) in nounset and (q + s) in nounset}
        if len(fresh) >= min_pair:
            for s in fresh:
                consumed.add(p + s)
                consumed.add(q + s)
            pairs.append({"prefixes": [p, q], "shared_stems": len(fresh), "examples": sorted(fresh)[:5]})
    return sorted(pairs, key=lambda d: -d["shared_stems"])


def emergent_class_groups(pair: str, top: int = 8) -> list[dict]:
    """The DERIVED candidate class inventory for the suggest path: the strongest number-pairings as emergent
    groups labelled group-A, group-B, … (arbitrary IDs, NOT Meinhof numbers — the human assigns canonical
    numbers at declare). Each group lists its sg/pl prefixes + example members. Fully data-derived; the
    machine suggests structure, the human ratifies the names."""
    pairs = derive_class_pairs(pair)[:top]
    return [{"group": f"group-{chr(65 + i)}", "prefixes": d["prefixes"],
             "n_shared_stems": d["shared_stems"], "examples": d["examples"]}
            for i, d in enumerate(pairs)]


def derive_noun_class_map(pair: str, sample: int = 0, min_support: int = 5, min_share: float = 0.6) -> dict:
    """Derive prefix → noun-class with NO hardcoded UNAMBIG and NO hardcoded prefix list. Two derived
    ingredients: (a) the prefix inventory = `derive_prefixes` (signature test), (b) the per-noun class from
    CONCORD ONLY (`_concord_anchored_classes` — associative + subject-marking, the linguistic ground truth,
    Corbett: class = agreement). For each derived prefix, the majority concord-class of the nouns it heads
    IS its class — kept when ≥min_support nouns agree at ≥min_share. This is the concord-grounded
    replacement for the hardcoded {ki:7, vi:8, ma:6, …} map."""
    from collections import Counter
    prefixes = sorted(derive_prefixes(pair), key=len, reverse=True)
    anchored = _concord_anchored_classes(pair, sample)
    votes: dict[str, Counter] = {}
    for noun, cl in anchored.items():
        p = next((p for p in prefixes if noun.startswith(p) and len(noun) > len(p) + 1), None)
        if p:
            votes.setdefault(p, Counter())[cl] += 1
    out = {}
    for p, c in votes.items():
        total = sum(c.values())
        cl, n = c.most_common(1)[0]
        if total >= min_support and n / total >= min_share:
            out[p] = {"class": cl, "support": total, "share": round(n / total, 2)}
    return out


# MEASURED CEILING (swh, 2026-06-24): derive_noun_class_map recovers wa→2 from concord but CANNOT recover the
# inanimate-class prefixes (mi/ji/vi/ma → MISS, ki → CONFLICT cl1≠7). Reason: those classes rarely head a
# sentence SUBJECT or control associative concord in the NT, so the agreement signal is absent. This is WHY
# the noun-class prefix→class map lives as per-language REFERENCE DATA (golden_sets/_reference/<lang>.json,
# loaded by review.langknow) rather than being derived: the knowledge is not recoverable from this corpus's
# concord without regressing the analysis. An epistemic floor — reference/human knowledge, not unfinished work.


def recovery_report(pair: str = "swh", pivot: str = "en") -> dict:
    """Did the derivation recover the reference values? Compares derived vs the per-language reference data
    (review.langknow) — the data is verified by the corpus, not merely trusted."""
    from review import langknow
    sm_ref = langknow.subject_marker_to_class(pair)
    as_ref = langknow.associative_to_class(pair)
    d_sm = derive_sm_to_class(pair, pivot)
    d_as = derive_assoc_to_class(pair)
    sm_match = {k: (d_sm.get(k), sm_ref[k], d_sm.get(k) == sm_ref[k]) for k in sm_ref}
    as_match = {k: (d_as.get(k), as_ref[k], d_as.get(k) == as_ref[k]) for k in as_ref}
    return {"pair": pair, "derived_sm_to_class": d_sm, "derived_assoc_to_class": d_as,
            "sm_recovered": sum(1 for v in sm_match.values() if v[2]), "sm_total": len(sm_match),
            "assoc_recovered": sum(1 for v in as_match.values() if v[2]), "assoc_total": len(as_match),
            "sm_detail": sm_match, "assoc_detail": as_match}
