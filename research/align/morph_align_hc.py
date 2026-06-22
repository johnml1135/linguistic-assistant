"""Align THOT over HC-parsed words — morpheme-level alignment with verified segmentation + markers.

Word-level alignment glosses a whole target word to a source word; but a source word often maps to a
*morpheme inside* the target word (`ni-na-ku-penda` = I-PRES-you-love). This module uses the **HC parse**
of each word as the (verified) segmentation, then aligns THOT over the morpheme stream so each morpheme
gets its pivot source token + probability, and carries a full marker set (boundary type, slot, gloss,
function/features, confidence, agrees-with-HC). Concurring signals (THOT ∩ HC) raise the gold via
`deltas/`; everything else defers — never a silent wrong marker.

HC's echoed morph *forms* are corrupted (the reindexing bug) but its **gloss line is exact**, so the
segmentation is recovered by mapping each gloss back to the grammar construct that produced it (a
`LexEntry` root / an `Affix`), and the root surface form is recovered by peeling the known affixes off the
word. See the OpenSpec `morpheme-alignment` change.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align import align  # noqa: E402
from golden.grammar import LangModel  # noqa: E402

ACCEPT_PROB = 0.5          # min alignment probability to consider accepting a marker


# --------------------------------------------------------------------------- segmentation from HC
def gloss_index(model: LangModel) -> dict[str, tuple[str, str, int]]:
    """`gloss -> (form, type, slot)` over the grammar constructs. On a duplicate gloss, prefer a root,
    then the higher-count construct (so the gloss line maps back to the most likely construct)."""
    idx: dict[str, tuple[str, str, int, int]] = {}   # gloss -> (form, type, slot, rank)
    for e in model.lexicon:
        rank = 1_000_000 + e.count                   # roots win ties
        cur = idx.get(e.gloss)
        if cur is None or rank > cur[3]:
            idx[e.gloss] = (e.form, "root", 0, rank)
    for a in model.affixes:
        cur = idx.get(a.gloss)
        rank = a.count
        if cur is None or (cur[1] != "root" and rank > cur[3]):
            idx[a.gloss] = (a.form, a.kind, a.slot_ord, rank)
    return {g: (f, t, s) for g, (f, t, s, _) in idx.items()}


def morphemes_of(word: str, gloss_line: tuple[str, ...], index: dict[str, tuple[str, str, int]]) -> list[dict]:
    """Map a HC gloss line to ordered morphemes `[{form, gloss, type, slot}]`.

    Affix forms come from the grammar constructs; the root's surface form is recovered by peeling the
    known affix forms off the word (so the root token used for alignment is the real surface root).
    """
    constructs = [(g, index.get(g)) for g in gloss_line]
    if any(c is None for _, c in constructs):        # a gloss we can't map → keep the word whole, flagged
        return [{"form": word, "gloss": "?", "type": "word", "slot": 0, "unparsed": False, "unmapped": True}]
    # peel known affix forms to recover the root surface form
    residual = word
    for g, (form, typ, _slot) in constructs:
        if typ == "prefix" and residual.startswith(form) and len(residual) > len(form):
            residual = residual[len(form):]
    for g, (form, typ, _slot) in reversed(constructs):
        if typ == "suffix" and residual.endswith(form) and len(residual) > len(form):
            residual = residual[: -len(form)]
    morphs = []
    for g, (form, typ, slot) in constructs:
        surface = residual if typ == "root" else form
        morphs.append({"form": surface, "gloss": g, "type": typ, "slot": slot})
    return morphs


def word_morphemes(word: str, analyses: list, index: dict, gold_line: tuple | None = None) -> list[dict]:
    """Choose an analysis (gold-matching if present, else first), map it to morphemes, set flags.

    `analyses` is a list of HC gloss lines (tuples). Empty → a single `unparsed` word morpheme."""
    if not analyses:
        return [{"form": word, "gloss": "?", "type": "word", "slot": 0, "unparsed": True}]
    chosen = next((a for a in analyses if gold_line is not None and a == gold_line), analyses[0])
    morphs = morphemes_of(word, chosen, index)
    if len(analyses) > 1:
        for m in morphs:
            m["ambiguous"] = True
    return morphs


# --------------------------------------------------------------------------- the marker record
@dataclass
class MorphMarker:
    verse: str
    word: str
    word_idx: int
    morph_idx: int
    form: str
    gloss: str                       # the HC stored gloss
    type: str                        # root|prefix|suffix|infix|clitic|word
    slot: int = 0
    source_tokens: list = field(default_factory=list)   # [(source_word, prob)]
    features: dict = field(default_factory=dict)         # FsFeatStruc for affixes (gold table)
    pos: str = ""
    confidence: float = 0.0
    agrees_with_hc: bool = False
    decision: str = "defer"          # accept | defer
    flags: dict = field(default_factory=dict)            # unparsed / ambiguous / unmapped

    def to_dict(self) -> dict:
        return asdict(self)


def _agrees(marker_type: str, hc_gloss: str, source_word: str) -> bool:
    """Does the pivot source corroborate the HC gloss? Root: token overlaps the gloss. Affix: a coarse
    overlap of the source word with the stored function label (function morphemes are the hard case —
    when they don't clearly overlap we deliberately let it fall to 'defer')."""
    if not source_word:
        return False
    g = (hc_gloss or "").lower()
    s = source_word.lower()
    gt = {t for t in g.replace("|", " ").replace(";", " ").replace("=", " ").split() if t}
    return s in gt or s == g or any(s in t or t in s for t in gt if len(t) > 2)


def assemble_markers(streams: list[tuple[str, int, list[dict]]], table, affix_feats: dict[str, dict],
                     pos_of: dict[str, str] | None = None, *, accept_prob: float = ACCEPT_PROB) -> list[MorphMarker]:
    """Join the morpheme streams with the alignment table + the gold affix→function features into routed
    markers. `streams` is [(verse_ref, word_idx, [morpheme dicts])]; `table` is the `GlossTable`."""
    pos_of = pos_of or {}
    out: list[MorphMarker] = []
    for verse, widx, morphs in streams:
        for mi, m in enumerate(morphs):
            best = table.best(m["form"]) if m["form"] else None
            src = [(best.source_word, round(best.prob, 4))] if best else []
            prob = best.prob if best else 0.0
            agrees = _agrees(m["type"], m["gloss"], best.source_word if best else "")
            decision = "accept" if (prob >= accept_prob and agrees and not m.get("unparsed")
                                    and not m.get("unmapped")) else "defer"
            out.append(MorphMarker(
                verse=verse, word=m.get("_word", ""), word_idx=widx, morph_idx=mi,
                form=m["form"], gloss=m["gloss"], type=m["type"], slot=m.get("slot", 0),
                source_tokens=src, features=affix_feats.get(m["form"], {}) if m["type"] != "root" else {},
                pos=pos_of.get(m["form"], "") if m["type"] == "root" else "",
                confidence=round(prob, 4), agrees_with_hc=agrees, decision=decision,
                flags={k: m[k] for k in ("unparsed", "ambiguous", "unmapped") if m.get(k)}))
    return out


# --------------------------------------------------------------------------- the run (HC + THOT)
def _pair_dir(pair: str):
    from golden.reference.compile import EBIBLE, PAIR_DIR
    return EBIBLE / PAIR_DIR[pair]


def _verses(pair: str, sample: int) -> list[tuple[str, list[str], list[str]]]:
    rows = []
    p = _pair_dir(pair) / "parallel.jsonl"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            rows.append((d.get("ref", ""), list(d["src"]),
                         [t.lower() for t in d["tgt"] if t.isalpha()]))
        if sample and len(rows) >= sample:
            break
    return rows


def build_streams(pair: str, model: LangModel, verses, *, chunk_timeout: int = 20):
    """Parse all target words once with HC, then map each word's analysis to morphemes (with back-links).
    Returns (streams, morph_rows) where morph_rows are `(src, [morpheme-form tokens])` for the aligner."""
    from golden.hc import gloss_seq, run_parse
    from golden.reference.phonology_gold import phon_feats
    index = gloss_index(model)
    all_words = sorted({w for _, _, tgt in verses for w in tgt})
    pf = phon_feats(pair, model.charset)
    parses = run_parse(model, all_words, templated=False, phon_feats=pf, chunk_timeout=chunk_timeout)
    analyses = {w: [gloss_seq(a) for a in parses.get(w, [])] for w in all_words}
    streams, morph_rows = [], []
    for ref, src, tgt in verses:
        verse_morphs: list[str] = []
        for widx, w in enumerate(tgt):
            morphs = word_morphemes(w, analyses.get(w, []), index)
            for m in morphs:
                m["_word"] = w
            streams.append((ref, widx, morphs))
            verse_morphs.extend(m["form"] for m in morphs)
        morph_rows.append((src, verse_morphs))
    return streams, morph_rows


def run(pair: str, *, backend: str = "hmm", sample: int = 0, apply: bool = False) -> dict:
    """Full pipeline: HC parse → morpheme stream → THOT align → markers → route. Writes JSONL + summary."""
    from golden.reference.goldio import FROZEN, load_gold
    from golden.reference.hc_coverage import build_reference_model
    gold = load_gold(pair)
    affix_feats = {a["affix"]: (a.get("features") or {}) for a in gold.get("affixes", [])
                   if isinstance(a.get("features"), dict)}
    pos_of = gold.get("pos", {})
    model = build_reference_model(pair)
    verses = _verses(pair, sample)
    streams, morph_rows = build_streams(pair, model, verses)
    table, used = align(morph_rows, backend=backend, allow_cooccur_fallback=False)
    markers = assemble_markers(streams, table, affix_feats, pos_of)

    accepted = [m for m in markers if m.decision == "accept"]
    deferred = [m for m in markers if m.decision == "defer"]
    out = FROZEN / pair / "morph_alignments.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for m in markers:
            f.write(json.dumps(m.to_dict(), ensure_ascii=False) + "\n")
    applied = _apply(pair, accepted) if apply else {"ops": 0}
    affix_glosses = {m.form: m.source_tokens[0][0] for m in accepted if m.type != "root" and m.source_tokens}
    return {"pair": pair, "backend": used, "verses": len(verses), "markers": len(markers),
            "accepted": len(accepted), "deferred": len(deferred),
            "affixes_glossed": len(affix_glosses), "affix_glosses": dict(list(affix_glosses.items())[:20]),
            "applied": applied}


def to_deferral_records(deferred: list[MorphMarker], *, top: int = 50) -> list[dict]:
    """Turn the highest-confidence-but-not-accepted morpheme markers into `defer` records the
    `deferrals/` ticket pipeline can build into packages. Roots → a lexeme_gloss deferral; affixes → an
    affix_function deferral. Capped + frequency-ordered so the pipeline tickets the high-value tail first."""
    ranked = sorted((m for m in deferred if not m.flags.get("unparsed") and m.source_tokens),
                    key=lambda m: -m.confidence)
    recs = []
    for m in ranked[:top]:
        src = m.source_tokens[0][0]
        if m.type == "root":
            recs.append({"word": m.form, "gloss": "", "aligner_top1": src, "conf": "low",
                         "decision": "defer", "source": "morph-align-hc"})
        else:
            recs.append({"affix": m.form, "kind": m.type, "function": src, "feature": m.features,
                         "conf": "low", "source": "morph-align-hc"})
    return recs


def _apply(pair: str, accepted: list[MorphMarker]) -> dict:
    """Emit confidence-routed deltas for accepted markers (affix gloss / root sense)."""
    from deltas.store import DeltaStore
    store = DeltaStore.load(_RESEARCH / "deltas" / "store" / f"{pair}.deltas.jsonl")
    ops = []
    prov = {"source": "morph-align-hc", "pair": pair}
    for m in accepted:
        src = m.source_tokens[0][0] if m.source_tokens else None
        if not src:
            continue
        if m.type == "root":
            ops.append({"op": "lexical.sense.create", "entry": f"entry:{pair}:{m.form}",
                        "gloss": {"en": src}, "confidence": round(m.confidence, 3), "provenance": prov})
        else:
            ops.append({"op": "morphophonology.affix.add", "form": m.form, "gram": src,
                        "kind": m.type, "confidence": round(m.confidence, 3), "provenance": prov})
    if ops:
        store.add(ops)
        store.route()
        store.save()
    return {"ops": len(ops)}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=["spa", "ind", "tgl", "swh"])
    ap.add_argument("--backend", default="hmm", help="hmm (THOT, required) | cooccur (offline tests only)")
    ap.add_argument("--sample", type=int, default=0, help="cap verses (0 = all)")
    ap.add_argument("--apply", action="store_true", help="emit deltas for accepted markers")
    args = ap.parse_args(argv)
    s = run(args.pair, backend=args.backend, sample=args.sample, apply=args.apply)
    print(f"[{args.pair}] morpheme alignment ({s['backend']}): {s['markers']} markers over {s['verses']} verses")
    print(f"  ACCEPT (THOT ∩ HC): {s['accepted']}   DEFER: {s['deferred']}   "
          f"affixes glossed: {s['affixes_glossed']}")
    print("  sample affix glosses: " + ", ".join(f"{m}={g}" for m, g in s["affix_glosses"].items()))
    if args.apply:
        print(f"  applied {s['applied']['ops']} deltas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
