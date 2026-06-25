"""Compile pristine, cross-source-verified golden references for a language.

Combines + converts the online resources into typed gold, restricted to the BIBLICAL DOMAIN — the
scripture vocabulary plus the lemmas/stems needed to parse those forms (we drop the rest of Wiktionary;
it isn't needed to parse scripture, run the golden tests, or verify the TDD process):

  * **POS gold** — word → UPOS, merged from ALL UD treebanks + UniMorph (features converted to UPOS).
    A word whose UD and UniMorph POS **agree** is marked `verified`; disagreements are recorded.
  * **Affix → function gold** — derived by segmenting every UniMorph (lemma, form) pair (two-sided
    common-affix alignment) and aggregating each affix to its modal feature bundle (`-s` → `N;PL`, …).
  * **Lexicon gold** — biblical-domain real words: scripture words a reference knows + the roots needed
    to parse scripture forms (e.g. `haber`, because `había` occurs even if `haber` doesn't).
  * **Key terms** — unfoldingWord/Door43 controlled English biblical vocabulary.
  * **Scripture cross-check** — every gold word is flagged for occurrence in the pair's NT corpus; the
    scripture-attested subset is written separately as the directly-usable validation gold, and we
    report how much of scripture the reference covers (and which scripture words NO reference knows).

Outputs reviewable JSONL under golden_sets/<pair>/ (see goldio.py): lexicon.jsonl, grammar_rules.jsonl,
senses.jsonl, phonology.jsonl, key_terms.jsonl, meta.json, golden_scripture.tsv. Raw downloads stay
cached under golden/_sources/reference/<pair>/. Run: `python golden/reference/compile.py --pair spa`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

import liblcm  # noqa: E402  (the destination dialect: convert UD/UniMorph terms → LibLCM)
from gold import goldio  # noqa: E402
from gold import inflection, morphology  # noqa: E402
from gold.build import CACHE, _get, _parse_uw_terms, fetch_kaikki  # noqa: E402
from gold.orthography import classify, is_word, writing_system  # noqa: E402
from gold.phonology_gold import phonology_records  # noqa: E402
from gold.sources import UD, UNIMORPH, UNIMORPH_POS_TO_UPOS  # noqa: E402

EBIBLE = _THIS.parents[1] / "_sources" / "ebible"
# FROZEN, committed evaluation target — deliberately OUTSIDE _sources (raw cache) and cycle/out (the
# hill-climber's working copy), so reproducing the gold can never overwrite the gold.
FROZEN = _THIS.parents[1] / "golden_sets"
# derived from the corpus config (single source of truth — no duplicated language map)
try:
    from corpus.ebible.config import ENGLISH_ID, TARGETS
    PAIR_DIR = {k: f"{ENGLISH_ID}__{v}" for k, v in TARGETS.items()}
except Exception:                                    # fallback to the original four
    PAIR_DIR = {"swh": "eng-engwebp__swh-swhulb", "ind": "eng-engwebp__ind-indags",
                "tgl": "eng-engwebp__tgl-tglulb", "spa": "eng-engwebp__spa-spaRV1909"}


# Clitics / bound morphemes UniMorph doesn't segment — a scripture form built from one of these on a real
# lemma is that lemma's WORDFORM, not a new lemma. Longest first so the most specific strip wins.
CLITICS = {
    "spa": {"suffix": ["mela", "selo", "sela", "nos", "les", "los", "las", "me", "te", "se", "le", "lo", "la", "os"],
            "prefix": []},
    "ind": {"suffix": ["kannya", "annya", "inya", "nya", "lah", "kah", "pun", "mu", "ku", "kan", "an", "i"],
            "prefix": ["memper", "menge", "meng", "meny", "mem", "men", "peng", "peny", "pem", "pen",
                       "ber", "ter", "di", "ke", "se", "pe", "me"]},
}


def _strip_to_lemma(word: str, lemmas: set, pair: str) -> str | None:
    """If `word` is a clitic/affixed form of a real lemma, return that lemma (longest valid strip)."""
    cl = CLITICS.get(pair, {})
    for s in cl.get("suffix", []):
        if word.endswith(s) and len(word) - len(s) >= 3 and word[: -len(s)] in lemmas:
            return word[: -len(s)]
    for p in cl.get("prefix", []):
        if word.startswith(p) and len(word) - len(p) >= 3 and word[len(p):] in lemmas:
            return word[len(p):]
    return None


def unimorph_pos(feats: str) -> str:
    return UNIMORPH_POS_TO_UPOS.get(feats.split(";")[0], "X")


def segment(lemma: str, form: str) -> tuple[str, str] | None:
    """Two-sided common-affix alignment → (side, affix). Handles suffixing (casa→casa**s**), prefixing
    (soma→**nina**soma), and replacive endings (hablar→habl**é**). None if no clean single affix."""
    i = 0
    while i < len(lemma) and i < len(form) and lemma[i] == form[i]:
        i += 1
    j = 0
    while j < len(lemma) - i and j < len(form) - i and lemma[-1 - j] == form[-1 - j]:
        j += 1
    form_mid = form[i:len(form) - j]
    if not form_mid or len(form_mid) > 5:
        return None
    if i > 0:  # shared material on the left → suffix/ending (incl. replacive)
        return ("suffix", form_mid)
    if j > 0:  # shared material only on the right → prefix
        return ("prefix", form_mid)
    return None


def _iter_ud(text: str):
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) >= 4 and "-" not in c[0] and "." not in c[0]:
            yield c[1].lower(), c[2].lower(), c[3]  # form, lemma, UPOS


def _scripture_vocab(pair: str) -> set[str]:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    vocab: set[str] = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                vocab.update(t.lower() for t in json.loads(line)["tgt"])
    return vocab


def compile_gold(pair: str) -> dict:
    out = CACHE / pair
    out.mkdir(parents=True, exist_ok=True)
    pos_ud: dict[str, Counter] = defaultdict(Counter)
    pos_um: dict[str, str] = {}
    lemmas: set[str] = set()
    forms: set[str] = set()
    form2lemma: dict[str, str] = {}  # inflected form -> its lemma (to find the roots scripture needs)
    form2feats: dict[str, str] = {}  # inflected form -> its UniMorph feature bundle (the analysis)
    affix: dict[tuple[str, str], Counter] = defaultdict(Counter)
    sources: list[str] = []

    # UD treebanks (combined)
    ud_urls = UD.get(pair, [])
    got_ud = False
    for k, url in enumerate(ud_urls):
        t = _get(url, out / f"ud_{k}.conllu")
        if t:
            got_ud = True
            for form, lemma, upos in _iter_ud(t):
                pos_ud[form][upos] += 1
                if lemma and lemma != "_":
                    lemmas.add(lemma)
    if got_ud:
        sources.append("ud")

    # UniMorph → POS (converted), lexicon, affix→function gold
    morph_n = 0
    if pair in UNIMORPH:
        t = _get(UNIMORPH[pair], out / "unimorph.txt")
        if t:
            sources.append("unimorph")
            for line in t.splitlines():
                p = line.split("\t")
                if len(p) >= 3 and p[0] and p[1]:
                    lemma, form, feats = p[0].lower(), p[1].lower(), p[2]
                    lemmas.add(lemma); forms.add(form); morph_n += 1
                    form2lemma.setdefault(form, lemma)
                    form2feats.setdefault(form, feats)
                    pos_um.setdefault(form, unimorph_pos(feats))
                    pos_um.setdefault(lemma, unimorph_pos(feats))
                    seg = segment(lemma, form)
                    if seg:
                        affix[seg][feats] += 1

    # Wiktionary (kaikki) → POS + bilingual GLOSS (with full sense inventory + homographs) + more forms.
    pos_wik: dict[str, str] = {}
    glosses: dict[str, str] = {}      # primary sense per word (compact gloss gold)
    sense_inv: dict[str, dict] = {}   # word -> {pos:[LibLCM...], senses:[...], homograph:bool}
    kk = fetch_kaikki(pair)
    if kk:
        sources.append("wiktionary")
        for w, info in kk["words"].items():
            libpos = [liblcm.pos_from_wiktionary(p) for p in info.get("pos", [])]
            libpos = [p for p in libpos if p != "Unknown"]
            if libpos:
                pos_wik[w] = libpos[0]
            sns = info.get("senses", [])
            if sns:
                glosses.setdefault(w, sns[0])
            # homograph = the same surface form carries >1 distinct part of speech (e.g. noun + verb)
            sense_inv[w] = {"pos": sorted(set(libpos)), "senses": sns, "homograph": len(set(libpos)) > 1}
            forms.add(w)
            if morphology.real_senses(sns):
                lemmas.add(w)  # only a TRUE lexeme (has a real sense) is a lemma — not a form-of-only entry
        forms.update(kk.get("forms", []))

    # merge POS in LibLCM terms by a 3-way vote (UD, UniMorph, Wiktionary); verified = ≥2 sources agree
    pos: dict[str, str] = {}
    verified = 0
    conflicts: list[list[str]] = []
    for w in set(pos_ud) | set(pos_um) | set(pos_wik):
        cand = []
        if pos_ud.get(w):
            cand.append(liblcm.pos_from_upos(pos_ud[w].most_common(1)[0][0]))
        if w in pos_um:
            cand.append(liblcm.pos_from_upos(pos_um[w]))
        if w in pos_wik:
            cand.append(pos_wik[w])
        cand = [c for c in cand if c and c != "Unknown"]
        if not cand:
            continue
        top, n = Counter(cand).most_common(1)[0]
        pos[w] = top  # destination LibLCM PartOfSpeech
        if n >= 2:
            verified += 1
        elif len(cand) >= 2:
            conflicts.append([w] + cand)

    # unfoldingWord key terms
    terms = _parse_uw_terms(out)
    if terms:
        sources.append("unfoldingword")

    # affix → function gold, in LibLCM terms: morph_type + an inflection FsFeatStruc (converted from
    # the UniMorph bundle), alongside the raw source features for traceability.
    affixes = sorted(
        ({"morph_type": sd, "affix": af, "features": c.most_common(1)[0][0],
          "inflection": liblcm.inflection_features(c.most_common(1)[0][0]), "count": sum(c.values())}
         for (sd, af), c in affix.items() if sum(c.values()) >= 3),
        key=lambda a: -a["count"])

    # Restrict to the BIBLICAL DOMAIN: scripture words the references know, PLUS the lemmas/stems needed
    # to parse those forms (e.g. keep `haber` because `había` is in scripture, even if `haber` itself is
    # not a surface token). We deliberately drop the rest of Wiktionary — it isn't needed to parse
    # scripture, run the golden tests, or verify the TDD process, and it bloats the gold.
    known = lemmas | forms | set(pos) | set(glosses)
    scrip = _scripture_vocab(pair)
    suf = {af for (sd, af), c in affix.items() if sd == "suffix" and sum(c.values()) >= 3}
    pre = {af for (sd, af), c in affix.items() if sd == "prefix" and sum(c.values()) >= 3}
    # the roots scripture needs must be REAL lemmas (a citation form a source lists), never an arbitrary
    # affix-strip stem like "abajad" — those polluted the lexicon as senseless pseudo-lemmas.
    roots_needed: set[str] = set()
    for f in scrip:
        lm = form2lemma.get(f)
        if lm in lemmas:
            roots_needed.add(lm)
        for s in suf:
            if f.endswith(s) and len(f) > len(s) + 1 and f[: -len(s)] in lemmas:
                roots_needed.add(f[: -len(s)])
        for p in pre:
            if f.startswith(p) and len(f) > len(p) + 1 and f[len(p):] in lemmas:
                roots_needed.add(f[len(p):])
    # WORDS ONLY: numbers, punctuation and symbols are not lemmas. HC parses phonological segments, so
    # digits/punctuation have no representation; in LibLCM they are the writing system's job (tokenizer
    # strips punctuation; numerals are a token TYPE, not morphologically parsed). Keep them out of the
    # lexicon entirely; classify the corpus vocabulary so we can report/handle the non-word tokens.
    ws = writing_system(pair)
    token_classes = Counter(classify(t, ws) for t in scrip)

    # --- separate LEXEMES from WORDFORMS ------------------------------------------------------------
    # A scripture word is COVERED if it resolves to a known lemma — directly (a reference knows it) or by
    # analysis: UniMorph form→lemma, a Wiktionary form-of gloss, or a clitic/affix strip (mengasihinya →
    # kasih). That is the right notion of coverage for "HC can parse it"; agglutinated forms whose root is
    # known count as covered even though the surface isn't a dictionary headword. Each covered word becomes
    # a wordform (lemma + FsFeatStruc); the lexicon keeps only lemmas. Uncovered = no reference + no analysis
    # (proper-noun names, genuine gaps).
    wordforms: list[dict] = []
    lemma_set: set[str] = set(roots_needed)
    attested: list[str] = []
    uncovered: list[str] = []
    for w in sorted({x for x in scrip if is_word(x)}):
        lemma = feats = src = None
        if w in form2lemma and form2lemma[w] != w and form2lemma[w] in known and is_word(form2lemma[w]):
            lemma, feats, src = form2lemma[w], liblcm.inflection_features(form2feats.get(w, "")), "unimorph"
        else:
            wl, wf = morphology.analyze_wordform(sense_inv.get(w, {}).get("senses", []))
            if wl and wl != w and wl in known and is_word(wl):
                lemma, feats, src = wl, wf, "wiktionary"
        if not lemma:
            # clitic/affix strip: a clitic-attached form (ajarlah=ajar+lah, díjole=dijo+le) is a WORDFORM
            # of its root lemma, not a new lemma. Keeps inflected/clitic forms out of the lexicon.
            root = _strip_to_lemma(w, lemmas, pair)
            if root:
                lemma, feats, src = root, {}, "clitic"
        if not lemma and w not in known:
            uncovered.append(w)            # no reference knows it and we can't analyse it → genuinely uncovered
            continue
        attested.append(w)
        if lemma:
            wordforms.append({"surface": w, "lemma": lemma, "pos": pos.get(lemma) or pos.get(w) or "Unknown",
                              "features": feats or {}, "source": src})
            lemma_set.add(lemma)
        else:  # w is its own citation form (a lexeme) — also a trivial (base) wordform
            wordforms.append({"surface": w, "lemma": w, "pos": pos.get(w) or "Unknown", "features": {}, "source": "base"})
            lemma_set.add(w)
    lemma_set = {lm for lm in lemma_set if is_word(lm)}

    # INDUCE INFLECTION CLASSES (the generative rules) instead of enumerating surface forms. Build each
    # lemma's paradigm from UniMorph, cluster into classes (the -ar/-er/-ir conjugations, etc.), and
    # record per-lemma overrides for irregular cells. This is what we want generated/found — the rules.
    paradigms: dict[str, dict[str, str]] = defaultdict(dict)
    for form, lemma in form2lemma.items():
        if lemma in lemma_set and is_word(form):
            cell = inflection.canon(liblcm.inflection_features(form2feats.get(form, "")))
            paradigms[lemma][cell] = form
    pos_by = {lm: pos.get(lm, "Unknown") for lm in lemma_set}
    classes, lemma_class, overrides, stems = inflection.induce(paradigms, pos_by)

    # LEXEME entries (lexicon.jsonl): lemma -> POS + REAL senses + its inflection class + irregular cells
    lex_entries: list[dict] = []
    for lm in sorted(lemma_set):
        inv = sense_inv.get(lm, {})
        rs = morphology.real_senses(inv.get("senses", []))
        lex_entries.append({"word": lm, "pos": pos.get(lm) or (inv.get("pos") or ["Unknown"])[0],
                            "pos_all": inv.get("pos", []), "senses": rs,
                            "homograph": bool(inv.get("homograph")), "in_scripture": lm in scrip,
                            "inflection_class": lemma_class.get(lm), "stem": stems.get(lm, lm),
                            "irregular": overrides.get(lm, [])})

    # CORPUS ALIGNMENT pass: resolve the words Wiktionary can't (proper-noun names absent from every
    # dictionary) from the parallel scripture itself — fill no-gloss lemmas, add Proper-noun entries for
    # confidently-resolved uncovered words (babilonia→babylon). Gets sharper as more is glossed.
    from gold import align_gloss  # local import: align_gloss imports this module
    align_stats = align_gloss.apply(pair, lex_entries, wordforms, attested, uncovered)

    glosses = {e["word"]: e["senses"][0] for e in lex_entries if e["senses"]}
    homograph_n = sum(1 for e in lex_entries if e["homograph"])
    lexicon = {e["word"] for e in lex_entries} | {wf["surface"] for wf in wordforms}

    frozen = FROZEN / pair
    frozen.mkdir(parents=True, exist_ok=True)
    # the scripture validation slice is now a wordform view: surface → lemma + analysis
    with (frozen / "golden_scripture.tsv").open("w", encoding="utf-8") as f:
        f.write("surface\tlemma\tpos\tfeatures\tsource\n")
        for wf in sorted(wordforms, key=lambda x: x["surface"]):
            feat = ";".join(f"{k}={v}" for k, v in wf["features"].items())
            f.write(f"{wf['surface']}\t{wf['lemma']}\t{wf['pos']}\t{feat}\t{wf['source']}\n")

    regular = sum(1 for e in lex_entries if e["inflection_class"] and not e["irregular"])
    classed = sum(1 for e in lex_entries if e["inflection_class"])
    stats = {
        "pos_words": len(pos), "pos_verified": verified, "pos_conflicts": len(conflicts),
        "lexemes": len(lex_entries), "wordforms": len(wordforms), "unimorph_pairs": morph_n,
        "affixes": len(affixes), "glosses": len(glosses), "key_terms": len(terms),
        "homographs": homograph_n, "inflection_classes": len(classes),
        "lemmas_classed": classed, "lemmas_regular": regular,
        "aligned_glosses_filled": align_stats["glosses_filled"], "aligned_names_added": align_stats["names_added"],
        "scripture_vocab": len(scrip), "scripture_attested": len(attested),
        "scripture_coverage": round(len(attested) / len(scrip), 4) if scrip else 0.0,
        "scripture_uncovered": len(uncovered),
    }
    meta = {
        "pair": pair, "sources": sources, "stats": stats,
        "destination": "LibLCM / FieldWorks HC: LexEntry(+MoMorphType) · MoStemMsa/MoInflAffMsa(PartOfSpeech+FsFeatStruc) · AffixTemplate",
        "writing_system": {**ws, "numerals": "token type (not HC-parsed)", "punctuation": "stripped at tokenization"},
        "token_classes": dict(token_classes),
        "files": ["lexicon.jsonl", "lexicon.lift", "inflection_classes.jsonl", "wordforms.jsonl",
                  "grammar_rules.jsonl", "phonology.jsonl", "key_terms.jsonl", "meta.json",
                  "golden_scripture.tsv"],
        "pos_conflicts_sample": conflicts[:40], "scripture_uncovered_sample": uncovered[:40],
    }
    counts = goldio.write_gold(
        pair, lex_entries=lex_entries, wordforms=wordforms, affixes=affixes, inflection_classes=classes,
        key_terms=terms, meta=meta, phonology=phonology_records(pair))
    return stats | {"pair": pair, "sources": sources, "files": counts}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    args = ap.parse_args(argv)
    s = compile_gold(args.pair)
    print(f"[{args.pair}] golden set ({'+'.join(s['sources'])}):")
    print(f"  POS gold:   {s['pos_words']} words ({s['pos_verified']} cross-verified ≥2 sources, "
          f"{s['pos_conflicts']} conflicts)")
    print(f"  affixes:    {s['affixes']} affix→function entries from {s['unimorph_pairs']} UniMorph pairs")
    print(f"  lexemes:    {s['lexemes']} lemma entries ({s['glosses']} with real senses, "
          f"{s['homographs']} homographs); key terms {s['key_terms']}")
    print(f"  inflection: {s['inflection_classes']} classes (the generative rules); "
          f"{s['lemmas_regular']}/{s['lemmas_classed']} classed lemmas fully regular")
    print(f"  alignment:  {s['aligned_names_added']} proper-noun names + {s['aligned_glosses_filled']} "
          f"glosses resolved from the parallel corpus (no Wiktionary)")
    print(f"  wordforms:  {s['wordforms']} surface→analysis (the TEST ORACLE, derivable from the rules)")
    print(f"  scripture:  {s['scripture_attested']}/{s['scripture_vocab']} of NT vocab covered "
          f"({s['scripture_coverage']}); {s['scripture_uncovered']} uncovered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
