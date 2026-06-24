"""Allomorph detector — find sets of morpheme forms that MEAN THE SAME THING but live in DIFFERENT
ENVIRONMENTS (complementary distribution), and emit each as a candidate rule + environment (a change-set)
with its supporting data. The dual of the homograph judge (`constraints.py`): there, one form's senses
SPLIT by environment; here, several forms MERGE into one underlying form + a conditioning rule.

Generic — no glide special-casing. `u→w`, `mu→mw`, `ku→kw`, `meN→mem/men`, `-li/-le` all fall out of the
same three complementary checks:

  C  phon-neighbor proposal  — forms within a small edit distance (cheap candidate generation; also names
                               the segment that alternates → the rule's focus). `phon_neighbors`.
  A  same-meaning + complementary distribution — meaning via English WORD VECTORS (synonyms count:
                               big~large) with a string-overlap fallback (`wordvec`, optional); plus
                               environment-overlap ≈ 0 (each form in its own environment). `meaning_score`,
                               `complementary_score`.
  B  conditioning extraction  — which environment dimension (preceding/following natural class) predicts
                               which form → the rule's environment. `conditioning`.

Each surviving family is emitted as an `allomorph-collapse` candidate compatible with `promote.py`
(raise→verify→classify); the final gate is promote's MDL + HC round-trip. Contract-clean: review imports
engine/gold/align (+ optional wordvec). Needs THOT to survey; vectors are optional.

CLI:  uv run python -m review.allomorph --pair swh --sample 400 [--min-count 8]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

MEANING_AT = 0.55       # min meaning similarity (vector cosine, or string overlap) to call two forms synonymous
COMPLEMENTARY_AT = 0.70  # min (1 − environment-overlap): each form must mostly own its environment
MAX_EDIT = 1            # phonological-neighbor radius for candidate generation


# ── C: phonological-neighbor candidate generation ───────────────────────────────────────────────────────
def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return len(a) + len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def phon_neighbors(forms: list[str], max_edit: int = MAX_EDIT) -> list[tuple[str, str]]:
    """Candidate pairs within `max_edit` edits and ≤1 length difference — cheap O(N²) over the inventory,
    catches segmental alternants (u/w, mu/mw, men/mem). Suppletion (go/went) is intentionally NOT proposed
    here; run meaning-clustering directly to catch those."""
    pairs = []
    for i, a in enumerate(forms):
        for b in forms[i + 1:]:
            if abs(len(a) - len(b)) <= 1 and 0 < levenshtein(a, b) <= max_edit:
                pairs.append((a, b))
    return pairs


def alternating_segment(a: str, b: str, vowels: set) -> dict:
    """The segment(s) that differ between the two forms + whether the alternation is vocalic (glide-like)."""
    sa, sb = set(a), set(b)
    changed = sorted((sa - sb) | (sb - sa))
    vocalic = any(c in vowels for c in changed)
    return {"changed": changed, "vocalic": vocalic,
            "note": "high-vowel/glide-like (vocalic)" if vocalic else "segmental"}


# ── A: same-meaning ─────────────────────────────────────────────────────────────────────────────────────
# Two meaning signals, each valid where the other isn't:
#  - GRAMMATICAL morphemes (most affixal allomorphy): gold FEATURE overlap (mu≡mw share ADJ;PL;LGSPEC9;
#    hu differs → rejected). Word vectors fail here (to~him 0.79).
#  - CONTENT morphemes: English WORD VECTORS (big~large), when a THOT alignment exists. Vectors fail for
#    grammatical morphemes, so they only ever ADD, never gate.
def feature_jaccard(fa, fb) -> float:
    sa = set(str(fa or "").replace(";", " ").split())
    sb = set(str(fb or "").replace(";", " ").split())
    return round(len(sa & sb) / len(sa | sb), 3) if sa and sb else 0.0


def meaning_score(prof_a: dict, prof_b: dict, vectors=None) -> tuple[float, str]:
    """Same-meaning score = gold-feature overlap (grammatical), raised by English vectors / string-overlap
    when a THOT alignment is present (content). Returns (score, method)."""
    score = feature_jaccard(prof_a.get("features"), prof_b.get("features"))
    method = "features"
    ea, eb = prof_a.get("english"), prof_b.get("english")
    if ea and eb:
        if vectors is not None and vectors.available:
            from review.wordvec import cosine
            v = cosine(vectors.meaning_vector(ea), vectors.meaning_vector(eb))
            if v and v > score:
                score, method = round(v, 3), "vector"
        else:
            ov = sum(min(ea.get(w, 0.0), eb.get(w, 0.0)) for w in set(ea) | set(eb))
            if ov > score:
                score, method = round(ov, 3), "string-overlap"
    return score, method


# ── A + B: complementary distribution + which environment conditions the choice ─────────────────────────
def _overlap(pa: dict, pb: dict) -> float:
    pa = {k: v for k, v in pa.items() if k != "#"}     # drop word-edge/unknown — not a conditioning env
    pb = {k: v for k, v in pb.items() if k != "#"}
    keys = set(pa) | set(pb)
    ta, tb = sum(pa.values()) or 1, sum(pb.values()) or 1
    return sum(min(pa.get(k, 0) / ta, pb.get(k, 0) / tb) for k in keys)


def complementary_score(prof_a: dict, prof_b: dict) -> tuple[float, str]:
    """1 − environment-overlap, taking the environment DIMENSION (preceding vs following natural class)
    that best separates the two forms. High ⇒ complementary distribution ⇒ allomorph-like. A dimension is
    only scored if BOTH forms have data there (an empty dimension is not evidence of complementarity)."""
    best_score, best_dim = -1.0, ""
    for dim in ("right_class", "left_class"):
        pa = {k: v for k, v in prof_a.get(dim, {}).items() if k != "#"}
        pb = {k: v for k, v in prof_b.get(dim, {}).items() if k != "#"}
        if sum(pa.values()) == 0 or sum(pb.values()) == 0:    # need REAL adjacent-segment support on both
            continue
        score = 1.0 - _overlap(pa, pb)
        if score > best_score:
            best_score, best_dim = score, dim
    return (round(best_score, 3), best_dim) if best_dim else (0.0, "")


def conditioning(prof_a: dict, prof_b: dict, dim: str, form_a: str, form_b: str) -> dict:
    """The rule's environment: each form's dominant bucket on the discriminating dimension."""
    def dom(prof):
        d = prof.get(dim, {})
        return max(d, key=d.get) if d else "?"
    edge = "following" if dim == "right_class" else "preceding"
    return {"dimension": dim, "edge": edge, form_a: dom(prof_a), form_b: dom(prof_b)}


# ── survey: one HC+THOT pass → per-form profiles (English dist + environment profiles) ───────────────────
def survey(pair: str, *, sample: int = 0, min_count: int = 8) -> dict:
    """Parse + align the corpus once; return {form: {count, kind, english, right_class, left_class, hosts}}
    for every non-root morpheme with ≥ min_count occurrences. Reuses align.morph_align_hc."""
    from align import align
    from align.morph_align_hc import _verses, build_streams, gloss_index
    from engine.grammar import LangModel  # noqa: F401
    from gold.goldio import load_gold
    from gold.hc_coverage import build_reference_model
    from gold.phonology_gold import SPANISH_ACCENTS, vowel_inventory

    model = build_reference_model(pair)
    verses = _verses(pair, sample)
    streams, morph_rows = build_streams(pair, model, verses)
    table, _used = align(morph_rows, backend="hmm", allow_cooccur_fallback=False)
    inv = vowel_inventory(pair)

    def cls(seg: str) -> str:
        if not seg:
            return "#"
        return "vowel" if SPANISH_ACCENTS.get(seg, seg) in inv else "consonant"

    forms: dict = {}
    for _ref, _widx, morphs in streams:
        n = len(morphs)
        for mi, m in enumerate(morphs):
            if m.get("type") == "root":
                continue
            f = m.get("form", "")
            if not f:
                continue
            w = m.get("_word", "")
            rec = forms.setdefault(f, {"count": 0, "kind": m.get("type", ""), "right_class": {},
                                       "left_class": {}, "hosts": {}, "_first": 0, "_last": 0})
            rec["count"] += 1
            rec["hosts"][w] = rec["hosts"].get(w, 0) + 1
            left = right = ""
            if mi == 0 and w.startswith(f):
                right = w[len(f):len(f) + 1]; left = "#"; rec["_first"] += 1
            elif mi == n - 1 and w.endswith(f) and len(w) > len(f):
                left = w[-len(f) - 1:-len(f)]; right = "#"; rec["_last"] += 1
            rec["right_class"][cls(right)] = rec["right_class"].get(cls(right), 0) + 1
            rec["left_class"][cls(left)] = rec["left_class"].get(cls(left), 0) + 1

    gold = load_gold(pair)
    feats = {a["affix"]: a.get("features", "") for a in gold.get("affixes", [])}
    out = {}
    for f, rec in forms.items():
        if rec["count"] < min_count:
            continue
        rec["english"] = {c.source_word: c.prob for c in table.table.get(f, [])}
        rec["features"] = feats.get(f, "")
        rec["kind"] = "prefix" if rec["_first"] >= rec["_last"] else "suffix"
        rec["n_hosts"] = len(rec["hosts"])
        out[f] = rec
    return out


def survey_raw(pair: str, *, sample: int = 0, min_count: int = 8) -> dict:
    """RAW word-edge survey — the source the user chose. Reads the alternation directly off the corpus
    (NOT the segmented stream that fuses mw/kw away). Candidate prefixes = the gold's enumerated prefix
    inventory (the list we want to collapse); environment = the following-segment natural class of the
    words each prefix begins, by LONGEST match (so `mw` claims `mwana`, not `m`). Meaning = gold features.
    No THOT needed."""
    from align.morph_align_hc import _verses
    from gold.goldio import load_gold
    from gold.phonology_gold import SPANISH_ACCENTS, vowel_inventory

    gold = load_gold(pair)
    inv = set(vowel_inventory(pair))
    cands = {a["affix"]: a for a in gold.get("affixes", [])
             if a.get("morph_type") == "prefix" and 1 <= len(a["affix"]) <= 3}
    by_len = sorted(cands, key=len, reverse=True)        # longest-match assignment

    def cls(seg: str) -> str:
        if not seg:
            return "#"
        return "vowel" if SPANISH_ACCENTS.get(seg, seg) in inv else "consonant"

    prof = {f: {"features": a.get("features", ""), "kind": "prefix", "right_class": {}, "left_class": {},
                "hosts": {}, "count": 0} for f, a in cands.items()}
    for _ref, _src, tgt in _verses(pair, sample):
        for w in tgt:
            for f in by_len:
                if len(w) > len(f) and w.startswith(f):
                    c = cls(w[len(f):len(f) + 1])
                    if c != "#":
                        p = prof[f]
                        p["right_class"][c] = p["right_class"].get(c, 0) + 1
                        p["count"] += 1
                        p["hosts"][w] = p["hosts"].get(w, 0) + 1
                    break                                 # longest match only
    out = {}
    for f, p in prof.items():
        if p["count"] >= min_count:
            p["n_hosts"] = len(p["hosts"])
            p["english"] = {}                            # raw mode has no per-morpheme THOT alignment
            out[f] = p
    return out


# ── detect: C → A → B → candidate change-sets ───────────────────────────────────────────────────────────
def member_words(pair: str, prefix: str, *, sample: int = 0, cap: int = 400) -> list[str]:
    """All DISTINCT raw words beginning with `prefix` — used to verify a collapse rule against its own
    counterexamples (the rare `mu`+vowel forms that falsify u→w live in the tail, so distinct-word
    collection includes them where a top-k-by-frequency sample would not)."""
    from align.morph_align_hc import _verses
    seen: dict = {}
    for _ref, _src, tgt in _verses(pair, sample):
        for w in tgt:
            if w.startswith(prefix) and len(w) > len(prefix):
                seen[w] = seen.get(w, 0) + 1
    return [w for w, _ in sorted(seen.items(), key=lambda x: -x[1])][:cap]


def detect(pair: str, *, source: str = "raw", sample: int = 0, min_count: int = 8, use_vectors: bool = True,
           meaning_at: float = MEANING_AT, complementary_at: float = COMPLEMENTARY_AT) -> dict:
    from gold.phonology_gold import vowel_inventory
    vectors = None
    if use_vectors:
        from review.wordvec import get_vectors
        vectors = get_vectors()
    vowels = set(vowel_inventory(pair))

    profiles = (survey_raw if source == "raw" else survey)(pair, sample=sample, min_count=min_count)
    forms = sorted(profiles)
    pairs = phon_neighbors(forms)

    candidates = []
    for a, b in pairs:
        pa, pb = profiles[a], profiles[b]
        if pa["kind"] != pb["kind"]:                     # both prefixes or both suffixes
            continue
        m_score, m_method = meaning_score(pa, pb, vectors)
        c_score, dim = complementary_score(pa, pb)
        if m_score < meaning_at or c_score < complementary_at:
            continue
        cond = conditioning(pa, pb, dim, a, b)
        alt = alternating_segment(a, b, vowels)
        ur = min(a, b, key=len) if len(a) != len(b) else sorted([a, b])[0]
        combined = round(0.5 * m_score + 0.5 * c_score, 3)
        candidates.append({
            "id": f"{pair}_{a}_{b}_collapse", "pair": pair, "kind": "allomorph-collapse",
            "members": [a, b], "underlying": ur,
            "rule": f"{a}~{b}: {cond[a]}→'{a}', {cond[b]}→'{b}' on the {cond['edge']} segment "
                    f"({alt['note']}; alternates {alt['changed']})",
            "environment": cond, "alternating": alt, "combined_score": combined,
            "evidence": {
                "meaning_similarity": m_score, "meaning_method": m_method,
                "complementary_score": c_score,
                "support": {a: pa["count"], b: pb["count"]},
                "host_diversity": {a: pa["n_hosts"], b: pb["n_hosts"]},
                "english": {a: sorted(pa["english"].items(), key=lambda x: -x[1])[:4],
                            b: sorted(pb["english"].items(), key=lambda x: -x[1])[:4]},
                "env_profiles": {a: {dim: pa[dim]}, b: {dim: pb[dim]}},
                "examples": {a: [w for w, _ in sorted(pa.get("hosts", {}).items(), key=lambda x: -x[1])[:8]],
                             b: [w for w, _ in sorted(pb.get("hosts", {}).items(), key=lambda x: -x[1])[:8]]},
            },
            "recommended": "raise-to-promote",      # → promote.verify (MDL + HC round-trip) is the gate
        })
    candidates.sort(key=lambda c: -c["combined_score"])
    return {"pair": pair, "source": source, "forms_surveyed": len(profiles), "neighbor_pairs": len(pairs),
            "candidates": candidates,
            "vectors": (vectors.available if vectors else False),
            "vectors_reason": ("" if (vectors and vectors.available) else
                               (vectors.reason if vectors else "disabled"))}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Detect allomorph families (same meaning, different environment).")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--source", default="raw", choices=["raw", "segmented"],
                    help="raw word-edges (sees fused alternants like mw/kw) | segmented morpheme stream")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--min-count", type=int, default=8)
    ap.add_argument("--no-vectors", action="store_true", help="skip word vectors (features/string meaning)")
    ap.add_argument("--out", default="", help="write candidates JSONL here")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    res = detect(a.pair, source=a.source, sample=a.sample, min_count=a.min_count, use_vectors=not a.no_vectors)
    print(f"\n{res['pair']} [{res['source']}]: surveyed {res['forms_surveyed']} forms, "
          f"{res['neighbor_pairs']} phon-neighbor pairs, "
          f"vectors={'on' if res['vectors'] else 'off'}")
    print(f"{len(res['candidates'])} allomorph candidate(s):\n")
    for c in res["candidates"]:
        e = c["evidence"]
        print(f"  [{c['combined_score']:.2f}] {c['members']}  UR=/{c['underlying']}/  ({c['kind']})")
        print(f"        meaning={e['meaning_similarity']} ({e['meaning_method']})  "
              f"complementary={e['complementary_score']}  support={e['support']}  hosts={e['host_diversity']}")
        print(f"        rule: {c['rule']}")
        print(f"        english: {e['english']}")
    if a.out:
        Path(a.out).write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in res["candidates"]),
                               encoding="utf-8")
        print(f"\nwrote {len(res['candidates'])} candidates → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
