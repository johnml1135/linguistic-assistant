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
    return {"pair": pair, "types": types, "n_tokens": sum(types.values()) or 1, "n_types": len(types) or 1,
            "pos": pos, "lexicon": set(pos), "nouns": {w for w, p in pos.items() if str(p).lower() == "noun"},
            "affixes": [a for a in gold.get("affixes", [])], "profile": P.load(pair)}


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
    oov = sum(c for w, c in ctx["types"].items() if w not in ctx["lexicon"])
    frac = oov / ctx["n_tokens"]
    oov_types = sum(1 for w in ctx["types"] if w not in ctx["lexicon"])
    return {"unexplained": round(frac, 3), "ready": True,
            "evidence": f"{oov_types} word types ({frac:.0%} of tokens) have no POS/lexicon entry",
            "action": "POS + lexicon induction (distributional + alignment)"}


def _additive(ctx) -> dict:
    # rough morphology-gap proxy: OOV types that look complex (long) and share a known affix edge
    affs = [a["affix"] for a in ctx["affixes"]]
    pre = [a for a in affs if len(a) <= 4]
    oov = [w for w in ctx["types"] if w not in ctx["lexicon"] and len(w) > 5]
    looks_affixed = sum(1 for w in oov if any(w.startswith(p) or w.endswith(p) for p in pre))
    frac = looks_affixed / ctx["n_types"]
    return {"unexplained": round(frac, 3), "ready": bool(affs),
            "evidence": f"~{looks_affixed} OOV types carry a known affix edge (likely unsegmented inflections)",
            "action": "affix induction + morpheme alignment (induce/* + align/*)"}


def _has_classes(ctx) -> bool:
    fs = ctx["profile"].feature_space
    return bool(getattr(fs.get("gender"), "value", False) or getattr(fs.get("noun_class"), "value", False))


def _classes(ctx) -> dict:
    if not _has_classes(ctx):
        return {"unexplained": 0.0, "ready": False, "evidence": "no gender/noun-class system (typology)",
                "action": "—"}
    from review import classes as CL
    schema = CL.declared_schema(ctx["pair"])
    if not schema:
        return {"unexplained": 0.6, "ready": True, "evidence": "class system not yet declared",
                "action": "review.classes suggest → declare"}
    r = CL.assign(ctx["pair"])
    if r.get("strategy") == "bantu-prefix":
        frac = r["n_unassigned_nouns"] / (r["n_unassigned_nouns"] + r["n_assigned"] or 1)
        ev = f"{r['n_unassigned_nouns']} nouns unassigned (no visible class prefix)"
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
    empty = sum(1 for c in schema.get("classes", []) if not c.get("concord"))
    total = len(schema.get("classes", [])) or 1
    r = CL.assign(ctx["pair"])
    only_by_agreement = r.get("n_unassigned_nouns", 0) if r.get("strategy") == "bantu-prefix" else 0
    frac = max(empty / total, only_by_agreement / (ctx["n_types"] or 1))
    return {"unexplained": round(min(frac, 1.0), 3), "ready": True,
            "evidence": f"{empty}/{total} classes have empty concord; "
                        f"{only_by_agreement} nouns classifiable only by the agreement they trigger",
            "action": "induce concord (controller↔target co-variation) → classify zero-marked nouns"}


def _allomorphy(ctx) -> dict:
    # ROUGH structural proxy (count-based, not corpus-mass): share of the affix inventory that has a
    # within-one-edit neighbour of the same polarity. Over-reads on rich inflectional paradigms (Spanish
    # conjugation), so it is weaker evidence than the coverage-based probes — flagged as `proxy`.
    from review.allomorph import levenshtein
    by_kind: dict = {}
    for a in ctx["affixes"]:
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


def _homographs(ctx) -> dict:
    multi = sum(1 for w in ctx["types"] if isinstance(ctx["pos"].get(w), (list, tuple)) and len(ctx["pos"][w]) > 1)
    frac = multi / ctx["n_types"]
    return {"unexplained": round(frac, 3), "ready": True,
            "evidence": f"{multi} forms carry multiple categories (syncretism candidates)",
            "action": "review.constraints (split by environment)"}


PROBES = {
    "switches": _switches, "word_classes": _word_classes, "additive_affixes": _additive,
    "classes": _classes, "agreement": _agreement, "allomorphy": _allomorphy, "homographs": _homographs,
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
