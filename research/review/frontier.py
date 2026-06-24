"""The frontier finder — auto-identify a language's NEXT CHUNK of work from the data.

The product is a system that, on an unknown language, works out what to look at next on its own. For each
chunk type in the catalog (`docs/chunk-types.md`) it computes an **unexplained fraction** (the share of
corpus mass the chunk would account for) and a **readiness** flag (are its prerequisites met?), then ranks
the ready chunks and presents the biggest — with evidence and the action to take. The metric is corpus
mass, so the same machinery yields a different next chunk per language, with no hand-tuning.

This replaces hand-picking ("agreement is next for swh"): the finder computes it. Honest about reach —
chunk types with no cheap probe yet are listed as `probe: pending`, not silently scored 0.

CLI:  uv run python -m review.frontier --pair swh        (or --all)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

# catalog order = dependency tiers (docs/chunk-types.md); id → (name, tier)
CATALOG = [
    ("orthography", "Orthography & segmentation", 0),
    ("switches", "Switches (typological frame)", 0),
    ("proper_nouns", "Proper nouns / names (NER tail)", 1),
    ("word_classes", "Word classes (POS)", 1),
    ("additive_affixes", "Additive morphology (affixes)", 1),
    ("morphotactics", "Morphotactics (slots/templates)", 1),
    ("classes", "Classes (gender/noun-class)", 2),
    ("agreement", "Agreement / concord", 2),
    ("allomorphy", "Allomorphy (conditioned variants)", 3),
    ("morphophonology", "Morphophonological rules", 3),
    ("nonconcatenative", "Non-concatenative (redup/infix)", 3),
    ("exceptions", "Exceptions / irregulars", 4),
    ("homographs", "Homographs / syncretism", 4),
]


def _build_ctx(pair: str, sample: int = 0) -> dict:
    """One shared pass: corpus types + token counts, the gold lexicon/POS, the profile + class schema."""
    from align.morph_align_hc import _verses
    from gold.goldio import load_gold
    from review.deferrals import profile as P
    types: Counter = Counter()
    for _ref, _src, tgt in _verses(pair, sample):
        for w in tgt:
            if w.isalpha():
                types[w] += 1
    gold = load_gold(pair)
    pos = gold.get("pos", {})
    gold_affixes = [a for a in gold.get("affixes", [])]
    # induce affixes from the corpus so morphology is visible even when the gold affix list is thin (tgl);
    # effective affixes = gold ∪ induced, and a "known stem" = gold lexicon ∪ recurring corpus words.
    from review.affixes import induced_affix_forms
    induced = induced_affix_forms(pair) if len(gold_affixes) < 60 else []
    seen = {(a["affix"], a.get("morph_type")) for a in gold_affixes}
    eff = gold_affixes + [a for a in induced if (a["affix"], a["morph_type"]) not in seen]
    attested = {w for w, c in types.items() if c >= 2 and len(w) > 2}
    return {"pair": pair, "types": types, "n_tokens": sum(types.values()) or 1, "n_types": len(types) or 1,
            "pos": pos, "lexicon": set(pos), "nouns": {w for w, p in pos.items() if str(p).lower() == "noun"},
            "affixes": gold_affixes, "affixes_eff": eff, "n_induced": len(eff) - len(gold_affixes),
            "stems": set(pos) | attested, "profile": P.load(pair)}


# ── probes (each → unexplained ∈ [0,1], readiness, evidence, action) ─────────────────────────────────────
def _switches(ctx) -> dict:
    prof = ctx["profile"]
    feats = []
    for sec in ("affix_processes", "phon_processes", "feature_space"):
        feats += list(getattr(prof, sec).values())
    low = [f for f in feats if getattr(f, "conf", 1.0) < 0.7]
    frac = len(low) / (len(feats) or 1)
    return {"unexplained": round(frac, 3), "ready": True,
            "evidence": f"{len(low)}/{len(feats)} typological calls below 0.7 confidence",
            "action": "confirm/override low-confidence switches (profile_detect → review)"}


def _word_classes(ctx) -> dict:
    # the STRUCTURAL gap is RECURRING unknown words; hapax OOV is mostly the name/rare-borrowing tail
    # (names can't be separated by case — both sides are lowercased — so frequency is the cheap proxy).
    oov = [w for w in ctx["types"] if w not in ctx["lexicon"]]
    recurring = [w for w in oov if ctx["types"][w] >= 3]
    frac = sum(ctx["types"][w] for w in recurring) / ctx["n_tokens"]
    hapax = len(oov) - len(recurring)
    return {"unexplained": round(frac, 3), "ready": True,
            "evidence": f"{len(recurring)} RECURRING OOV types ({frac:.0%} of tokens) — likely structural; "
                        f"{hapax} hapax OOV set aside as the name/rare tail",
            "action": "POS + lexicon induction (distributional + alignment)"}


def _proper_nouns(ctx) -> dict:
    # a recognised SEPARATE tail (W6 NER tail), not structure — shown so the name mass is accounted, but
    # flagged so it never becomes the structural recommendation. The unknown-name tail needs NER/gazetteer.
    pn = {w for w, p in ctx["pos"].items() if str(p).lower() == "proper noun"}
    known = sum(c for w, c in ctx["types"].items() if w in pn)
    frac = known / ctx["n_tokens"]
    return {"unexplained": round(frac, 3), "ready": True, "proxy": True,
            "evidence": f"{frac:.0%} of tokens are KNOWN names; the unknown-name tail hides in OOV "
                        f"(can't be split by case — needs NER/gazetteer)",
            "action": "NER / Bible-name gazetteer pass (handled separately from structure)"}


def _additive(ctx) -> dict:
    # REAL morphology gap: RECURRING unknown words that strip a known affix down to a KNOWN stem — i.e.
    # genuine inflections of known lexemes we haven't segmented yet (excludes names: a name won't strip to
    # a known stem). Measured in token mass, so it's comparable to the other coverage probes.
    pre = [a["affix"] for a in ctx["affixes_eff"] if a.get("morph_type") == "prefix" and 1 <= len(a["affix"]) <= 4]
    suf = [a["affix"] for a in ctx["affixes_eff"] if a.get("morph_type") == "suffix" and 1 <= len(a["affix"]) <= 4]
    lex = ctx["stems"]
    harvestable = []
    for w, c in ctx["types"].items():
        if w in lex or c < 3:                      # known, or hapax (name/rare tail) → skip
            continue
        ok = (any(len(w) > len(p) + 2 and w.startswith(p) and w[len(p):] in lex for p in pre) or
              any(len(w) > len(s) + 2 and w.endswith(s) and w[:-len(s)] in lex for s in suf))
        if not ok:                                  # circumfix (di-…-kan): strip a prefix AND a suffix
            for p in pre:
                if not w.startswith(p):
                    continue
                for s in suf:
                    if w.endswith(s) and len(w) > len(p) + len(s) + 2 and w[len(p):-len(s)] in lex:
                        ok = True; break
                if ok:
                    break
        if ok:
            harvestable.append(w)
    tok = sum(ctx["types"][w] for w in harvestable)
    frac = tok / ctx["n_tokens"]
    return {"unexplained": round(frac, 3), "ready": bool(pre or suf),
            "evidence": f"{len(harvestable)} recurring types ({frac:.0%} of tokens) = known affix + known "
                        f"stem, not yet segmented (e.g. {sorted(harvestable, key=lambda w: -ctx['types'][w])[:5]})",
            "action": "affix induction + morpheme alignment (induce/* + align/*)"}


def _peel(word: str, pre: list, suf: list, lex: set, maxd: int = 5) -> tuple[int, str, bool]:
    """Greedily strip known affixes (longest-first, prefixes then suffixes) until a known stem or no move.
    Returns (depth, residual, residual_is_known)."""
    cur, depth, moved = word, 0, True
    while moved and depth < maxd and cur not in lex:
        moved = False
        for p in sorted(pre, key=len, reverse=True):
            if cur.startswith(p) and len(cur) > len(p) + 1:
                cur, depth, moved = cur[len(p):], depth + 1, True; break
        if moved:
            continue
        for s in sorted(suf, key=len, reverse=True):
            if cur.endswith(s) and len(cur) > len(s) + 1:
                cur, depth, moved = cur[:-len(s)], depth + 1, True; break
    return depth, cur, cur in lex


def _morphotactics(ctx) -> dict:
    # how much MULTI-affix stacking there is — words that peel to a known stem only after ≥2 affixes
    # (ni-na-ku-penda). High = a real slot/template system to model; ~0 = mostly single-affix or isolating.
    pre = [a["affix"] for a in ctx["affixes_eff"] if a.get("morph_type") == "prefix" and 1 <= len(a["affix"]) <= 4]
    suf = [a["affix"] for a in ctx["affixes_eff"] if a.get("morph_type") == "suffix" and 1 <= len(a["affix"]) <= 4]
    lex = ctx["stems"]
    deep, examples = 0, []
    for w, c in ctx["types"].items():
        if w in lex or c < 3:
            continue
        depth, _stem, known = _peel(w, pre, suf, lex)
        if known and depth >= 2:
            deep += c
            if len(examples) < 6:
                examples.append(f"{w}({depth})")
    frac = deep / ctx["n_tokens"]
    return {"unexplained": round(frac, 3), "ready": bool(pre or suf),
            "evidence": f"{frac:.0%} of tokens peel to a known stem only after ≥2 affixes (slot/template "
                        f"depth) e.g. {examples}",
            "action": "induce affix ordering / position classes (morphotactic template)"}


def _has_classes(ctx) -> bool:
    fs = ctx["profile"].feature_space
    return bool(getattr(fs.get("gender"), "value", False) or getattr(fs.get("noun_class"), "value", False))


def _agreement_induce(ctx) -> dict:
    """Cached concord induction (one corpus pass, shared by the agreement + classes probes — so the
    nouns cracked by agreement feed back into class coverage)."""
    if "_ag" not in ctx:
        from review import agreement as AG
        from review.classes import declared_schema
        ctx["_ag"] = AG.induce(ctx["pair"]) if (_has_classes(ctx) and declared_schema(ctx["pair"])) else {}
    return ctx["_ag"]


def _classes(ctx) -> dict:
    if not _has_classes(ctx):
        return {"unexplained": 0.0, "ready": False, "evidence": "no gender/noun-class system (typology)",
                "action": "—"}
    from review import classes as CL
    schema = CL.declared_schema(ctx["pair"])
    if not schema:
        return {"unexplained": 0.6, "ready": True, "evidence": "class system not yet declared",
                "action": "review.classes suggest → declare"}
    persisted = CL.persisted_noun_classes(ctx["pair"])     # golden byproduct: prefix+agreement+projection
    if persisted:
        total = len(ctx["nouns"]) or 1
        classed = len({n for n in persisted if n in ctx["nouns"]})
        frac = max(0.0, 1 - classed / total)
        from collections import Counter
        src = Counter(d.get("source") for d in persisted.values())
        return {"unexplained": round(frac, 3), "ready": True,
                "evidence": f"{classed}/{total} nouns have a DEFINITE class (golden set: {dict(src)}); "
                            f"{total - classed} residue (default cl9/10 / needs more signal)",
                "action": "extend signal (more projection) or accept cl9/10 default for the residue"}
    r = CL.assign(ctx["pair"])
    if r.get("strategy") == "bantu-prefix":
        cracked = _agreement_induce(ctx).get("zero_prefix_classified", 0)   # feedback: agreement closed these
        eff = max(0, r["n_unassigned_nouns"] - cracked)
        frac = eff / (eff + r["n_assigned"] + cracked or 1)
        ev = f"{eff} nouns still unassigned ({r['n_unassigned_nouns']} no-prefix − {cracked} cracked by agreement)"
    else:
        frac = 0.1 if r.get("n_assigned") else 0.5
        ev = f"{r.get('n_assigned',0)} nouns assigned; {r.get('n_coverage_gaps',0)} coverage-gap candidates"
    return {"unexplained": round(frac, 3), "ready": True, "evidence": ev,
            "action": "review.classes utilize (assign + flag)"}


def _agreement(ctx) -> dict:
    if not _has_classes(ctx):
        return {"unexplained": 0.0, "ready": False, "evidence": "no class system → no concord", "action": "—"}
    from review import classes as CL
    schema = CL.declared_schema(ctx["pair"])
    if not schema:
        return {"unexplained": 0.0, "ready": False, "evidence": "blocked: declare the class system first",
                "action": "—"}
    # concord cells already DECLARED (the gender strategy fills el/la at declaration) count as filled;
    # for prefix systems with empty cells we INDUCE from data. (Was: always ran Bantu induction → spa 100%.)
    classes = schema.get("classes", [])
    total = len(classes) or 1
    declared_filled = sum(1 for c in classes if c.get("concord"))
    ind = _agreement_induce(ctx) if declared_filled < total else {}
    induced = ind.get("cells_filled", 0)
    filled = max(declared_filled, induced)
    r = CL.assign(ctx["pair"])
    unassigned = r.get("n_unassigned_nouns", 0) if r.get("strategy") == "bantu-prefix" else 0
    only_by_agreement = max(0, unassigned - ind.get("zero_prefix_classified", 0))   # minus the cracked ones
    frac = max((total - filled) / total, only_by_agreement / (ctx["n_types"] or 1))
    return {"unexplained": round(min(frac, 1.0), 3), "ready": True,
            "evidence": f"{filled}/{total} concord cells induced; "
                        f"{only_by_agreement} nouns still classifiable only by the agreement they trigger",
            "action": "induce concord (controller↔target co-variation) → classify zero-marked nouns"}


def _allomorphy(ctx) -> dict:
    # ROUGH structural proxy (count-based, not corpus-mass): share of the affix inventory that has a
    # within-one-edit neighbour of the same polarity. Over-reads on rich inflectional paradigms (Spanish
    # conjugation), so it is weaker evidence than the coverage-based probes — flagged as `proxy`.
    from review.allomorph import levenshtein
    by_kind: dict = {}
    for a in ctx["affixes_eff"]:
        f = a["affix"]
        if len(f) <= 4:
            by_kind.setdefault(a.get("morph_type", "?"), []).append(f)
    members = set()
    for kind, affs in by_kind.items():
        for i, a in enumerate(affs):
            for b in affs[i + 1:]:
                if abs(len(a) - len(b)) <= 1 and 0 < levenshtein(a, b) <= 1:
                    members.add((kind, a)); members.add((kind, b))
    total = sum(len(v) for v in by_kind.values()) or 1
    frac = len(members) / total                       # bounded [0,1]: fraction of affixes that are near-variants
    return {"unexplained": round(frac, 3), "ready": bool(total > 1), "proxy": True,
            "evidence": f"{len(members)}/{total} affixes have a one-edit neighbour (collapse candidates — rough)",
            "action": "review.allomorph → promote (collapse to UR + rule)"}


def _morphophonology(ctx) -> dict:
    # PHONOLOGICAL alternations among affixes (vocalic/glide near-variants — mu/mw, vi/vy) that have NO
    # active rule yet — the enumeration debt the collapse engine pays down. Count-proxy (flagged).
    from review.allomorph import levenshtein
    vowels = set("aeiou")
    by_kind: dict = {}
    for a in ctx["affixes_eff"]:
        f = a["affix"]
        if len(f) <= 4:
            by_kind.setdefault(a.get("morph_type", "?"), []).append(f)
    vocalic = set()
    for affs in by_kind.values():
        for i, a in enumerate(affs):
            for b in affs[i + 1:]:
                if abs(len(a) - len(b)) <= 1 and 0 < levenshtein(a, b) <= 1:
                    changed = (set(a) ^ set(b))
                    if changed & vowels:                # the alternating segment is a vowel → glide/harmony
                        vocalic.add(a); vocalic.add(b)
    try:
        from gold.phonology_gold import active_phon_rules
        active = len(active_phon_rules(ctx["pair"]))
    except Exception:
        active = 0
    total = sum(len(v) for v in by_kind.values()) or 1
    frac = (len(vocalic) / total) if active == 0 else 0.0
    return {"unexplained": round(frac, 3), "ready": bool(total > 1), "proxy": True,
            "evidence": f"{len(vocalic)} affixes in vocalic (glide/harmony) alternations, {active} active rules "
                        f"— enumeration debt for the collapse engine",
            "action": "review.allomorph + promote (collapse to UR + ordered rule)"}


def _exceptions(ctx) -> dict:
    # the irreducible residue: RECURRING unknowns that resist BOTH segmentation and reduplication (and
    # aren't the hapax name tail) — suppletion / irregulars / unanalysable loans.
    from review.reduplication import is_reduplicated
    pre = [a["affix"] for a in ctx["affixes_eff"] if a.get("morph_type") == "prefix" and 1 <= len(a["affix"]) <= 4]
    suf = [a["affix"] for a in ctx["affixes_eff"] if a.get("morph_type") == "suffix" and 1 <= len(a["affix"]) <= 4]
    lex = ctx["stems"]
    residue = []
    for w, c in ctx["types"].items():
        if w in lex or c < 3:
            continue
        _d, _stem, known = _peel(w, pre, suf, lex)
        if not known and not is_reduplicated(w):
            residue.append(w)
    tok = sum(ctx["types"][w] for w in residue)
    frac = tok / ctx["n_tokens"]
    return {"unexplained": round(frac, 3), "ready": True,
            "evidence": f"{len(residue)} recurring types ({frac:.0%}) resist segmentation + reduplication "
                        f"— irreducible tail (suppletion/irregular/loan), e.g. {sorted(residue, key=lambda w:-ctx['types'][w])[:5]}",
            "action": "list as lexical irregulars / route to the deferral queue"}


def _orthography(ctx) -> dict:
    # candidate digraphs (cohesive bigrams) not yet declared in the profile — the only open orthography
    # question for these Latin scripts; tokenization is otherwise clean.
    from collections import Counter
    uni, bi = Counter(), Counter()
    for w, c in ctx["types"].items():
        for ch in w:
            uni[ch] += c
        for a, b in zip(w, w[1:]):
            bi[a + b] += c
    declared = set(getattr(ctx["profile"], "orthography", {}).get("digraphs", []))
    n = sum(uni.values()) or 1
    cands = []
    for g, c in bi.most_common(60):
        a, b = g
        pmi = (c / n) / ((uni[a] / n) * (uni[b] / n) + 1e-9)
        if c >= 200 and pmi > 3 and g not in declared:
            cands.append(g)
    frac = min(1.0, len(cands) / 10)
    return {"unexplained": round(frac, 3), "ready": True, "proxy": True,
            "evidence": f"{len(cands)} undeclared cohesive bigrams (digraph candidates): {cands[:8]}; "
                        f"declared: {sorted(declared)}",
            "action": "confirm digraphs in the orthography profile"}


def _homographs(ctx) -> dict:
    multi = sum(1 for w in ctx["types"] if isinstance(ctx["pos"].get(w), (list, tuple)) and len(ctx["pos"][w]) > 1)
    frac = multi / ctx["n_types"]
    return {"unexplained": round(frac, 3), "ready": True,
            "evidence": f"{multi} forms carry multiple categories (syncretism candidates)",
            "action": "review.constraints (split by environment)"}


def _nonconcatenative(ctx) -> dict:
    from review.reduplication import scan, is_infixed
    r = scan(ctx["pair"])
    stems = ctx["stems"]
    infixed = [w for w, c in ctx["types"].items() if c >= 3 and is_infixed(w, stems)]
    redup_tok = sum(ctx["types"][w] for w in r["examples"])  # approx; full rate from scan
    inf_tok = sum(ctx["types"][w] for w in infixed)
    frac = round(r["type_rate"] + inf_tok / ctx["n_tokens"], 3)
    return {"unexplained": min(1.0, frac), "ready": True,
            "evidence": f"reduplication {r['type_rate']:.0%} (e.g. {r['examples'][:4]}); "
                        f"{len(infixed)} infixed types (e.g. {sorted(infixed, key=lambda w:-ctx['types'][w])[:4]}) "
                        f"— both unparseable by concatenation",
            "action": "reduplication + infix detectors → emit copy/infix rules"}


PROBES = {
    "orthography": _orthography, "switches": _switches, "proper_nouns": _proper_nouns,
    "word_classes": _word_classes, "additive_affixes": _additive, "morphotactics": _morphotactics,
    "classes": _classes, "agreement": _agreement, "allomorphy": _allomorphy,
    "morphophonology": _morphophonology, "nonconcatenative": _nonconcatenative, "exceptions": _exceptions,
    "homographs": _homographs,
}


def frontier(pair: str, *, sample: int = 0) -> dict:
    """Probe every chunk type, rank the READY ones by unexplained mass, and name the next chunk."""
    ctx = _build_ctx(pair, sample=sample)
    rows = []
    for cid, name, tier in CATALOG:
        probe = PROBES.get(cid)
        if probe is None:
            rows.append({"id": cid, "name": name, "tier": tier, "probe": "pending"})
            continue
        r = probe(ctx)
        rows.append({"id": cid, "name": name, "tier": tier, "probe": "ok", **r})
    ready = [r for r in rows if r.get("probe") == "ok" and r.get("ready")]
    ready.sort(key=lambda r: -(r["unexplained"] * (0.6 if r.get("proxy") else 1.0)))
    # the NEXT chunk is the biggest TRUE corpus-coverage gap; rough count-proxies (allomorphy) are shown
    # in the ranked list but never drive the recommendation (they conflate paradigm density with the signal).
    robust = [r for r in ready if not r.get("proxy")]
    return {"pair": pair, "rows": rows, "ranked": ready, "next": robust[0] if robust else None}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Auto-find the next chunk of work for a language.")
    ap.add_argument("--pair")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    pairs = ["spa", "ind", "tgl", "swh"] if a.all else [a.pair]
    for pair in pairs:
        f = frontier(pair, sample=a.sample)
        nxt = f["next"]
        print(f"\n=== {pair} — NEXT CHUNK: {nxt['name'] if nxt else '—'} "
              f"({nxt['unexplained']:.0%} unexplained)" if nxt else f"\n=== {pair}: nothing ready")
        if nxt:
            print(f"    why: {nxt['evidence']}\n    do : {nxt['action']}")
        print("    ranked frontier (ready chunks):")
        for r in f["ranked"][:6]:
            tag = " [proxy]" if r.get("proxy") else ""
            print(f"      {r['unexplained']:.0%}  {r['name']:32}{tag} — {r['evidence']}")
        pend = [r["name"] for r in f["rows"] if r.get("probe") == "pending"]
        notready = [r["name"] for r in f["rows"] if r.get("probe") == "ok" and not r.get("ready")]
        if notready:
            print(f"    not-ready (deps unmet / N/A): {', '.join(notready)}")
        if pend:
            print(f"    probe pending: {', '.join(pend)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
