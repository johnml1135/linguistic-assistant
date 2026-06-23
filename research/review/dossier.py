"""The constraint dossier — assemble, for one morpheme, the evidence a constraint-generator (LLM) and the
deterministic judge both read.

THOT is used only as a *counter*: per occurrence of the morpheme, we ask THOT which English word it scores
highest among the words actually present in that verse (`_source_for`) — a raw count, no "opinion". The
dossier then bundles those occurrences with their **environment** (adjacent segment + its natural class,
the host word, position) so the judge can test whether conditioning on an environment makes the aligned
English word predictable (see `judge.py`).

`prepare()` runs HC + THOT once (slow, gated). Everything else is pure dict-shuffling and testable offline.
Lives in review/ (contract: imports engine/gold/align — never induce).
"""

from __future__ import annotations

from collections import Counter

# ── environment predicates (the encodable hypothesis the LLM emits / the judge tests) ───────────────────
# A spec is a small dict; `compile_env` turns it into (label, predicate). Specs are HC-encodable: a
# segment-set or natural-class membership on the left/right edge, or a host-POS context.

def compile_env(spec: dict):
    """spec → (label, env_fn). env_fn(occurrence_dict) → a hashable bucket (usually True/False)."""
    kind = spec.get("kind")
    if kind in ("right_in", "left_in"):
        side = "right" if kind == "right_in" else "left"
        members = set(spec.get("set", []))
        lbl = spec.get("label") or f"{side} ∈ {{{','.join(sorted(members))}}}"
        return lbl, (lambda o, s=side, m=members: o.get(s, "") in m)
    if kind in ("right_class", "left_class"):
        side = "right" if kind == "right_class" else "left"
        val = spec.get("value", "")
        lbl = spec.get("label") or f"{side} is {val}"
        return lbl, (lambda o, s=side, v=val: o.get(f"{s}_class", "") == v)
    if kind == "host_pos":
        val = spec.get("value", "")
        return spec.get("label") or f"host POS={val}", (lambda o, v=val: o.get("host_pos", "") == v)
    if kind == "position":
        # morphotactic slot — the disambiguator for Bantu prefix homographs (word-initial infinitive `ku`
        # vs medial object-marker `ku`). value ∈ initial | medial | final.
        val = spec.get("value", "")
        return spec.get("label") or f"position={val}", (lambda o, v=val: o.get("position", "") == v)
    raise ValueError(f"unknown environment kind: {kind!r}")


def _classify(pair: str, seg: str) -> str:
    """Coarse natural class of a segment, from the vowel inventory (consonants are identity-only today)."""
    if not seg:
        return "#"                       # word edge
    from gold.phonology_gold import vowel_inventory, SPANISH_ACCENTS
    inv = vowel_inventory(pair)
    base = SPANISH_ACCENTS.get(seg, seg)
    return "vowel" if base in inv else "consonant"


def seed_environments(pair: str, occ: list[dict]) -> list[dict]:
    """Deterministic candidate environments to seed the judge (and prime the LLM): the right/left edge as
    vowel-vs-consonant, plus each frequently-adjacent single segment. The LLM proposes richer place-based
    sets (e.g. labials={p,b,m}) the orthography can't class on its own."""
    specs: list[dict] = [
        {"kind": "right_class", "value": "vowel", "label": "before a vowel"},
        {"kind": "right_class", "value": "consonant", "label": "before a consonant"},
        {"kind": "left_class", "value": "vowel", "label": "after a vowel"},
        {"kind": "position", "value": "initial", "label": "word-initial (first morph)"},
        {"kind": "position", "value": "medial", "label": "word-medial morph"},
    ]
    right_segs = Counter(o["right"] for o in occ if o.get("right"))
    for seg, n in right_segs.most_common(6):
        if n >= 3:
            specs.append({"kind": "right_in", "set": [seg], "label": f"before '{seg}'"})
    return specs


# ── occurrence extraction (needs a parsed + THOT-aligned corpus from prepare()) ─────────────────────────

def _prob_of(table, token: str, src: str) -> float:
    for c in table.table.get(token, []):
        if c.source_word == src:
            return c.prob
    return 0.0


def _source_for(table, token: str, english: list[str]) -> str:
    """THOT-best English word AMONG those present in this verse — a per-occurrence count, not an opinion."""
    best, bp = "", 0.0
    for e in english:
        p = _prob_of(table, token, e)
        if p > bp:
            bp, best = p, e
    return best


def morpheme_occurrences(pair: str, morpheme: str, kind: str, streams, english_by_ref: dict, table,
                         pos_of: dict | None = None) -> list[dict]:
    """Build one occurrence record per appearance of `morpheme` (as a `kind` morph): its environment
    (adjacent segment + class), host word/POS, and the THOT-best English for that verse."""
    pos_of = pos_of or {}
    occ: list[dict] = []
    for ref, _widx, morphs in streams:
        for mi, m in enumerate(morphs):
            if m.get("form") != morpheme:
                continue
            w = m.get("_word", "")
            left = right = ""
            if kind == "prefix" and w.startswith(morpheme):
                right = w[len(morpheme):len(morpheme) + 1]
            elif kind == "suffix" and w.endswith(morpheme) and len(w) > len(morpheme):
                left = w[-len(morpheme) - 1:-len(morpheme)]
            occ.append({
                "ref": ref, "host": w, "left": left, "right": right,
                "left_class": _classify(pair, left), "right_class": _classify(pair, right),
                "host_pos": pos_of.get(w, ""), "position": _position(mi, len(morphs)),
                "source": _source_for(table, morpheme, english_by_ref.get(ref, [])),
            })
    return occ


def _position(mi: int, n: int) -> str:
    """Morphotactic slot of a morph within its word — the disambiguator for prefix homographs."""
    if mi == 0:
        return "initial"
    return "final" if mi == n - 1 else "medial"


def conflated_distribution(table, morpheme: str, top: int = 8) -> list[tuple[str, float]]:
    """The morpheme's current (un-conditioned) THOT distribution — the mushy 'before' picture the
    constraint is meant to sharpen."""
    return [(c.source_word, round(c.prob, 3)) for c in table.table.get(morpheme, [])[:top]]


def build_dossier(pair: str, morpheme: str, kind: str, occ: list[dict], table) -> dict:
    """The LLM-facing evidence bundle: the conflated distribution (is this morpheme ambiguous?), the
    environments present, and worked examples. No decision here — that's the judge's."""
    src_counts = Counter(o["source"] for o in occ if o["source"])
    right_classes = Counter(o["right_class"] for o in occ)
    examples = [{"host": o["host"], "right": o["right"], "right_class": o["right_class"],
                 "source": o["source"]} for o in occ[:12]]
    return {
        "pair": pair, "morpheme": morpheme, "kind": kind, "n_occ": len(occ),
        "conflated_distribution": conflated_distribution(table, morpheme),
        "conflated_entropy_signal": len([s for s, n in src_counts.items() if n >= 2]),
        "distinct_sources": src_counts.most_common(10),
        "adjacent_right_classes": right_classes.most_common(),
        "seed_environments": seed_environments(pair, occ),
        "examples": examples,
    }


def prepare(pair: str, morpheme: str, kind: str = "prefix", *, sample: int = 0) -> dict:
    """SLOW/GATED: parse the corpus with HC and align with THOT once, then extract this morpheme's
    occurrences. Returns a context dict (occ, table, dossier, + the cached HC parse so the confirmatory
    re-align in constraints.py only re-runs THOT). Reuses align.morph_align_hc — no duplication."""
    from align import align
    from align.morph_align_hc import _verses, build_streams
    from gold.goldio import load_gold
    from gold.hc_coverage import build_reference_model

    gold = load_gold(pair)
    pos_of = gold.get("pos", {})
    model = build_reference_model(pair)
    verses = _verses(pair, sample)
    english_by_ref = {ref: src for ref, src, _tgt in verses}
    streams, _morph_rows = build_streams(pair, model, verses)
    table, _used = align(_morph_rows, backend="hmm", allow_cooccur_fallback=False)
    occ = morpheme_occurrences(pair, morpheme, kind, streams, english_by_ref, table, pos_of)
    return {"pair": pair, "morpheme": morpheme, "kind": kind, "occ": occ, "table": table,
            "streams": streams, "english_by_ref": english_by_ref, "pos_of": pos_of,
            "dossier": build_dossier(pair, morpheme, kind, occ, table)}


def _dist_of(table, token: str) -> dict:
    """P(source | token) as a plain {source: prob} dict from a GlossTable."""
    return {c.source_word: c.prob for c in table.table.get(token, [])}


def realign_distributions(ctx: dict, env_spec: dict, *, align_fn=None) -> dict:
    """The real measurement: APPLY a candidate environment by splitting the morpheme token into
    `m␁in` / `m␁out` per occurrence, re-run THOT (HC parse reused from ctx — only THOT re-runs), and return
    the TWO resulting THOT distributions + bucket counts. The judge's `information_gain_dist` then asks
    whether the split sharpened the alignment (did the right sense go to the right English word?).

    `align_fn` is injectable for tests (defaults to the real THOT aligner). Returns
    {label, spec, dist_in, dist_out, n_in, n_out, coverage}."""
    if align_fn is None:
        from align import align as _al
        align_fn = lambda rows: _al(rows, backend="hmm", allow_cooccur_fallback=False)[0]  # noqa: E731
    pair, morpheme, kind = ctx["pair"], ctx["morpheme"], ctx["kind"]
    label, fn = compile_env(env_spec)
    streams, english_by_ref, pos_of = ctx["streams"], ctx["english_by_ref"], ctx["pos_of"]

    def occ_of(w: str, mi: int, n: int) -> dict:
        right = w[len(morpheme):len(morpheme) + 1] if (kind == "prefix" and w.startswith(morpheme)) else ""
        left = w[-len(morpheme) - 1:-len(morpheme)] if (kind == "suffix" and w.endswith(morpheme) and len(w) > len(morpheme)) else ""
        return {"left": left, "right": right, "left_class": _classify(pair, left),
                "right_class": _classify(pair, right), "host_pos": pos_of.get(w, ""),
                "position": _position(mi, n)}

    tok_in, tok_out = f"{morpheme}␁in", f"{morpheme}␁out"
    n_in = n_out = 0
    morph_rows, by_ref = [], {}
    for ref, _widx, morphs in streams:
        by_ref.setdefault(ref, []).append(morphs)
    for ref, src in english_by_ref.items():
        forms = []
        for morphs in by_ref.get(ref, []):
            for mi, m in enumerate(morphs):
                f = m.get("form", "")
                if f == morpheme:
                    inside = fn(occ_of(m.get("_word", ""), mi, len(morphs)))
                    f = tok_in if inside else tok_out
                    if inside:
                        n_in += 1
                    else:
                        n_out += 1
                forms.append(f)
        morph_rows.append((src, forms))
    table2 = align_fn(morph_rows)
    n = n_in + n_out or 1
    return {"label": label, "spec": env_spec, "n_in": n_in, "n_out": n_out,
            "coverage": round(n_in / n, 3), "dist_in": _dist_of(table2, tok_in),
            "dist_out": _dist_of(table2, tok_out)}
