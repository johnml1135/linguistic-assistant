"""Measure how much of scripture Hermit Crab can parse using a grammar built from the REFERENCE gold.

The hill-climber's job is to reproduce the gold; this is the gauge of "use HC to parse ALL the language"
from the reference side: build an HC `LangModel` straight from the frozen golden set — roots = frequent
scripture words glossed/POS-tagged from the gold, affixes = the gold affix→function inventory — then run
the `hc` CLI over a sample of scripture wordforms and report what fraction parse. The remaining unparsed
forms are the morphology gap to close (more roots/affixes/rules; Apertium morphology; the LLM proposer).

Reads the frozen golden set via `goldio.load_gold` + the pair's scripture corpus. Requires the `hc`
CLI; degrades to a clear message if absent. Run: `python golden/reference/hc_coverage.py --pair spa`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from engine.grammar import Affix, LangModel, LexEntry  # noqa: E402
from engine.hc import HC_EXE, run_parse  # noqa: E402

from gold.build import CACHE  # noqa: E402
from gold.compile import EBIBLE, FROZEN, PAIR_DIR  # noqa: E402
from gold.goldio import load_gold  # noqa: E402
from gold.phonology_gold import phon_feats  # noqa: E402

# Well-known affixes/clitics not always recovered by UniMorph segmentation — the next big miss bucket
# for Indonesian (clitics + the meN-/ber-/di- prefix family, the latter listed by surface allomorph
# since assimilation is the harder phonological-rule path). Injected on top of the gold affixes.
EXTRA_AFFIXES: dict[str, list[tuple[str, str, str]]] = {
    "spa": [  # enclitic object/reflexive pronouns (díjole = dijo+le, díceles = dice+les)
        ("me", "suffix", "1SG"), ("te", "suffix", "2SG"), ("se", "suffix", "REFL"),
        ("le", "suffix", "3SG.DAT"), ("les", "suffix", "3PL.DAT"), ("lo", "suffix", "3SG.M.ACC"),
        ("la", "suffix", "3SG.F.ACC"), ("los", "suffix", "3PL.M.ACC"), ("las", "suffix", "3PL.F.ACC"),
        ("nos", "suffix", "1PL"), ("os", "suffix", "2PL"),
    ],
    "ind": [
        ("nya", "suffix", "3.POSS"), ("mu", "suffix", "2.POSS"), ("ku", "suffix", "1.POSS"),
        ("lah", "suffix", "EMPH"), ("kah", "suffix", "Q"), ("pun", "suffix", "also"),
        ("kan", "suffix", "APPL"), ("an", "suffix", "NMLZ"), ("i", "suffix", "APPL"),
        ("ber", "prefix", "AV"), ("di", "prefix", "PASS"), ("ter", "prefix", "INVOL"),
        ("se", "prefix", "one"), ("ke", "prefix", "to"), ("pe", "prefix", "AGT"),
        ("me", "prefix", "AV"), ("mem", "prefix", "AV"), ("men", "prefix", "AV"),
        ("meng", "prefix", "AV"), ("meny", "prefix", "AV"), ("menge", "prefix", "AV"),
        ("pen", "prefix", "AGT"), ("pem", "prefix", "AGT"), ("peng", "prefix", "AGT"),
    ],
}


def hc_available() -> bool:
    import os
    return os.path.exists(HC_EXE)


def _slug(gloss: str | None) -> str:
    """A single-token morph gloss. HC's output aligns morphs to glosses positionally, so a multi-word
    gloss ("have; forms the perfect aspect") desyncs the alignment and the analysis is dropped — collapse
    it to the first sense word(s), spaces → underscores."""
    import re
    g = re.sub(r"[;,(].*", "", (gloss or "")).strip()
    g = re.sub(r"\s+", "_", g)
    return g or "?"


def _unimorph_paradigm(pair: str) -> dict[str, list[str]]:
    """lemma -> its inflected forms, from the cached UniMorph dump. These supply the irregular STEMS /
    suppletive forms (había, dijo, muchos) we attach as MoStemAllomorph allomorphs."""
    from collections import defaultdict
    path = CACHE / pair / "unimorph.txt"
    para: dict[str, set] = defaultdict(set)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) >= 2 and p[0] and p[1]:
                para[p[0].lower()].add(p[1].lower())
    return {k: sorted(v) for k, v in para.items()}


def _scripture_freqs(pair: str) -> Counter:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    c: Counter = Counter()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c.update(t.lower() for t in json.loads(line)["tgt"])
    return c


def build_reference_model(pair: str, *, n_roots: int = 4000, n_affixes: int = 80) -> LangModel:
    """An HC grammar straight from the gold: reference LEMMAS (true stems) as roots, the gold
    affix→function inventory as affixes.

    Roots must be stems, not inflected forms — otherwise ``hablando`` has no ``habl-`` to attach
    ``-ando`` to. We seed from the gold's lemma list, keeping the lemmas that actually do work in
    scripture (a lemma that equals a scripture form, or is a prefix of one), ranked by how much
    scripture frequency they cover.
    """
    gold = load_gold(pair)
    gpos, gloss = gold.get("pos", {}), gold.get("glosses", {})
    lemset = set(gold.get("lemmas", []))
    freqs = _scripture_freqs(pair)
    scrip = set(freqs)
    para = _unimorph_paradigm(pair)
    suf = [a["affix"] for a in gold.get("affixes", []) if a.get("morph_type") == "suffix"]
    pre = [a["affix"] for a in gold.get("affixes", []) if a.get("morph_type") == "prefix"]
    # Score each lemma by the scripture frequency its WHOLE PARADIGM explains — not its (often rare)
    # citation form. Inverted for speed: walk scripture once, credit each word to the lemma that owns it
    # (paradigm form, regular affix-strip, or itself). This is what makes `haber` rank (via había/habían…)
    # so its irregular forms get attached as allomorphs.
    form2lemma: dict[str, str] = {}
    for lm, forms in para.items():
        for f in forms:
            form2lemma.setdefault(f, lm)
    explains: Counter = Counter()
    for w, c in freqs.items():
        if w in lemset:
            explains[w] += c
        lm = form2lemma.get(w)
        if lm and lm in lemset:
            explains[lm] += c
        for s in suf:
            if s and w.endswith(s) and len(w) > len(s) + 1 and w[: -len(s)] in lemset:
                explains[w[: -len(s)]] += c
        for p in pre:
            if p and w.startswith(p) and len(w) > len(p) + 1 and w[len(p):] in lemset:
                explains[w[len(p):]] += c
    roots = [lm for lm, _ in explains.most_common(n_roots)]
    # Attach each lemma's scripture-attested inflected forms as stem allomorphs (MoStemAllomorph) — this
    # is what lets HC parse the irregular/suppletive forms (había→haber, dijo→decir, muchos→mucho) that a
    # clean concatenative grammar misses, while keeping the lemma's confident gloss on every form.
    lex = []
    for w in roots:
        # keep the MOST FREQUENT scripture forms as allomorphs (not the alphabetically-first — that drops
        # accented irregulars like `había`, which collate after `habiendo`).
        cands = [f for f in para.get(w, []) if f in scrip and f != w and f.isalpha()]
        cands.sort(key=lambda f: -freqs.get(f, 0))
        lex.append(LexEntry(form=w, gloss=_slug(gloss.get(w)), pos=(gpos.get(w) or "Noun"),
                            count=freqs.get(w, 0), allomorphs=tuple(cands[:12])))
    aff = []
    for a in gold.get("affixes", [])[:n_affixes]:
        mt = a["morph_type"] if a["morph_type"] in ("prefix", "suffix", "infix") else "suffix"
        aff.append(Affix(form=a["affix"], gloss=a.get("features", a["affix"]), kind=mt, count=a.get("count", 0)))
    for form, kind, gl in EXTRA_AFFIXES.get(pair, []):
        aff.append(Affix(form=form, gloss=gl, kind=kind, count=0))
    return LangModel(code=pair, lexicon=lex, affixes=aff)


def build_class_model(pair: str, *, restricted: bool = True) -> LangModel:
    """A CLASS-DRIVEN grammar (generative, not memorised): roots are the induced per-lemma STEMS, affixes
    are the inflection classes' stem-relative suffixes, and forms the class CAN'T generate (suppletive
    stems, derivations) are added as stem allomorphs (LibLCM MoStemAllomorph). With ``restricted`` each
    class is encoded as a part of speech (via ``pos_aware``) so an -ar suffix can't attach to an -ir stem.
    HC then *generates* `abrió` = stem `abri` + class suffix `ó`, and only memorises the true exceptions."""
    gold = load_gold(pair)
    glosses = gold.get("glosses", {})
    freqs = _scripture_freqs(pair)
    # class -> its (kind, affix-form) set; affixes carry the class as req_pos so they only attach there
    class_aff: dict[str, list[tuple[str, str]]] = {}
    affixes: list[Affix] = []
    for c in gold.get("inflection_classes", []):
        cid = c["class_id"]
        forms = []
        for r in c.get("rules", []):
            # one affix per cell (the modal stem-relative suffix). Emitting all variants explodes the
            # affix count and HC's search (Spanish went 206→669 affixes → timeouts → recall collapse).
            if r["kind"] == "S" and r.get("suffix"):
                forms.append(("suffix", r["suffix"], r["features"]))
            elif r["kind"] == "P" and r.get("add"):
                forms.append(("prefix", r["add"], r["features"]))
        class_aff[cid] = [(k, f) for k, f, _ in forms]
        for k, f, feat in forms:
            # gloss = the FULL feature cell (canon key, no spaces → one HC gloss token) so the analysis
            # carries the inflection features, not just the lemma — lets us score feature recall.
            affixes.append(Affix(form=f, gloss=(feat or "BASE"), kind=k, req_pos=(cid if restricted else "")))
    for form, kind, gl in EXTRA_AFFIXES.get(pair, []):
        affixes.append(Affix(form=form, gloss=gl, kind=kind))  # req_pos="" → attaches anywhere

    from gold.inflection import canon
    wf_by_lemma: dict[str, dict[str, dict]] = {}
    for w in gold.get("wordforms", []):
        wf_by_lemma.setdefault(w["lemma"], {})[w["surface"]] = w.get("features") or {}

    lex = []
    for e in gold.get("lex_entries", []):
        lm = e["word"]
        stem = e.get("stem") or lm
        cid = e.get("inflection_class")
        lemma_gloss = _slug(glosses.get(lm) or lm)
        sufs = class_aff.get(cid, [])
        generable = {stem} | {stem + f for k, f in sufs if k == "suffix"} | {f + stem for k, f in sufs if k == "prefix"}
        forms = wf_by_lemma.get(lm, {})
        # the stem entry (generates the regular paradigm via class affixes); citation form is an allomorph
        lex.append(LexEntry(form=stem, gloss=lemma_gloss, pos=(cid if (restricted and cid) else "root"),
                            count=freqs.get(lm, 0), allomorphs=((lm,) if lm != stem and lm not in generable else ())))
        # standalone entry glossed lemma|features (an irregularly-inflected wholeform): carries lemma AND
        # cell, no extra affixes. Emitted for every override cell (authoritative) — even one the rules
        # could otherwise make with the WRONG cell (e.g. está = est+á) — plus any non-generable wordform.
        wholes: dict[str, str] = {o["surface"]: o["features"] for o in e.get("irregular", []) if o.get("surface")}
        for surface, feats in forms.items():
            if surface != stem and surface not in generable:
                wholes.setdefault(surface, canon(feats))
        for surface, cell in wholes.items():
            if surface and surface != stem:
                lex.append(LexEntry(form=surface, gloss=f"{lemma_gloss}|{cell}", pos="irregular",
                                    count=freqs.get(surface, 0)))
    return LangModel(code=pair, lexicon=lex, affixes=affixes)


def coverage(pair: str, *, sample: int = 250, n_roots: int = 4000, n_affixes: int = 80) -> dict:
    model = build_reference_model(pair, n_roots=n_roots, n_affixes=n_affixes)
    gold = load_gold(pair)
    known = set(gold.get("lemmas", [])) | set(gold.get("glosses", {})) | set(gold.get("pos", {}))
    freqs = _scripture_freqs(pair)
    # test on frequent scripture forms NOT already seeded as roots (the real parse challenge)
    rootset = {e.form for e in model.lexicon}
    words = [w for w, _ in freqs.most_common() if len(w) >= 2 and w not in rootset][:sample]
    pf = phon_feats(pair, model.charset)  # real phonological feature substrate (vowel/cons/front/high)
    parses = run_parse(model, words, chunk_size=25, chunk_timeout=20, templated=False, phon_feats=pf)
    parsed = [w for w in words if parses.get(w)]
    unparsed = [w for w in words if not parses.get(w)]
    # split the residual: a word no reference knows as a common word is almost always a proper noun /
    # named entity (Jerusalem, Barnabas) — not a morphology gap. The rest is the real gap.
    names = [w for w in unparsed if w not in known]
    real_gap = [w for w in unparsed if w in known]
    return {"pair": pair, "roots": len(model.lexicon), "affixes": len(model.affixes),
            "tested": len(words), "parsed": len(parsed),
            "coverage": round(len(parsed) / len(words), 4) if words else 0.0,
            "likely_names": len(names), "real_gap": len(real_gap),
            "coverage_ex_names": round(len(parsed) / (len(words) - len(names)), 4) if (len(words) - len(names)) else 0.0,
            "real_gap_sample": real_gap[:15], "name_sample": names[:8]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--sample", type=int, default=250)
    args = ap.parse_args(argv)
    if not hc_available():
        print("hc CLI not installed — skipping (this gauge needs Hermit Crab).")
        return 0
    r = coverage(args.pair, sample=args.sample)
    print(f"[{args.pair}] HC parse-coverage from the reference grammar: {r['coverage']} "
          f"({r['parsed']}/{r['tested']} held-out scripture forms; {r['roots']} roots, {r['affixes']} gold affixes)")
    print(f"  {r['coverage_ex_names']} excluding likely proper nouns ({r['likely_names']} of the "
          f"{r['tested'] - r['parsed']} misses are names: {', '.join(r['name_sample'])})")
    print(f"  real morphology gap ({r['real_gap']}): {', '.join(r['real_gap_sample'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
