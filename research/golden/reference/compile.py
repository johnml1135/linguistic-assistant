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
sys.path.insert(0, str(_THIS.parents[2]))

import liblcm  # noqa: E402  (the destination dialect: convert UD/UniMorph terms → LibLCM)
from golden.reference import goldio  # noqa: E402
from golden.reference.build import CACHE, _get, _parse_uw_terms, fetch_kaikki  # noqa: E402
from golden.reference.orthography import classify, is_word, writing_system  # noqa: E402
from golden.reference.phonology_gold import phonology_records  # noqa: E402
from golden.reference.sources import UD, UNIMORPH, UNIMORPH_POS_TO_UPOS  # noqa: E402

EBIBLE = _THIS.parents[2] / "golden" / "_sources" / "ebible"
# FROZEN, committed evaluation target — deliberately OUTSIDE _sources (raw cache) and cycle/out (the
# hill-climber's working copy), so reproducing the gold can never overwrite the gold.
FROZEN = _THIS.parents[2] / "golden_sets"
PAIR_DIR = {"swh": "eng-engwebp__swh-swhulb", "ind": "eng-engwebp__ind-indags",
            "tgl": "eng-engwebp__tgl-tglulb", "spa": "eng-engwebp__spa-spaRV1909"}


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
            lemmas.add(w)  # a Wiktionary headword is a lemma → a candidate HC root/stem
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
    roots_needed: set[str] = set()
    for f in scrip:
        lm = form2lemma.get(f)
        if lm in known:
            roots_needed.add(lm)
        for s in suf:
            if f.endswith(s) and len(f) > len(s) + 1 and f[: -len(s)] in known:
                roots_needed.add(f[: -len(s)])
        for p in pre:
            if f.startswith(p) and len(f) > len(p) + 1 and f[len(p):] in known:
                roots_needed.add(f[len(p):])
    # WORDS ONLY: numbers, punctuation and symbols are not lemmas. HC parses phonological segments, so
    # digits/punctuation have no representation; in LibLCM they are the writing system's job (tokenizer
    # strips punctuation; numerals are a token TYPE, not morphologically parsed). Keep them out of the
    # lexicon entirely; classify the corpus vocabulary so we can report/handle the non-word tokens.
    ws = writing_system(pair)
    token_classes = Counter(classify(t, ws) for t in scrip)
    attested = sorted(w for w in (scrip & known) if is_word(w))   # scripture WORDS a reference knows
    lexicon = {w for w in (set(attested) | roots_needed) if is_word(w)}   # biblical-domain word lexicon
    uncovered = sorted(w for w in (scrip - known) if is_word(w))  # scripture words NO reference knows
    # prune the per-word gold to the biblical domain
    pos = {w: v for w, v in pos.items() if w in lexicon}
    glosses = {w: v for w, v in glosses.items() if w in lexicon}
    lemmas = roots_needed | {lm for lm in lemmas if lm in lexicon}  # every needed stem counts as a root
    attested_pos = {w: pos[w] for w in attested if w in pos}

    # Sense inventory (multiple senses + homograph flag) for the scripture-attested words — the
    # "confident definitions on everything, knowing there are multiple senses / homophones" layer.
    senses_gold = {w: sense_inv[w] for w in attested if w in sense_inv and sense_inv[w]["senses"]}
    homograph_n = sum(1 for v in senses_gold.values() if v["homograph"])

    # write the curated gold to the FROZEN, committed target as reviewable JSONL (raw downloads stay in
    # `out` = _sources cache). The scripture-attested validation slice stays a TSV (already tabular).
    frozen = FROZEN / pair
    frozen.mkdir(parents=True, exist_ok=True)
    with (frozen / "golden_scripture.tsv").open("w", encoding="utf-8") as f:
        f.write("word\tpos_liblcm\tn_senses\thomograph\tgloss\tin_lexicon\tin_ud\n")
        for w in attested:
            inv = sense_inv.get(w, {})
            f.write(f"{w}\t{pos.get(w, '')}\t{len(inv.get('senses', []))}\t{int(bool(inv.get('homograph')))}\t"
                    f"{glosses.get(w, '')}\t{int(w in forms or w in lemmas)}\t{int(w in pos_ud)}\n")

    stats = {
        "pos_words": len(pos), "pos_verified": verified, "pos_conflicts": len(conflicts),
        "lexicon_size": len(lexicon), "unimorph_pairs": morph_n, "affixes": len(affixes),
        "glosses": len(glosses), "key_terms": len(terms),
        "scripture_senses": len(senses_gold), "scripture_homographs": homograph_n,
        "scripture_vocab": len(scrip), "scripture_attested": len(attested),
        "scripture_coverage": round(len(attested) / len(scrip), 4) if scrip else 0.0,
        "scripture_uncovered": len(uncovered),
    }
    meta = {
        "pair": pair, "sources": sources, "stats": stats,
        "destination": "LibLCM / FieldWorks HC: LexEntry(+MoMorphType) · MoStemMsa/MoInflAffMsa(PartOfSpeech+FsFeatStruc) · AffixTemplate",
        # The writing system: locale + number format (group/decimal separators). Numbers and punctuation
        # are NOT lemmas — numerals are recognised as a token type by this format; punctuation is stripped
        # at tokenization. `token_classes` = how the scripture vocabulary classifies (lexicon keeps `word`).
        "writing_system": {**ws, "numerals": "token type (not HC-parsed)", "punctuation": "stripped at tokenization"},
        "token_classes": dict(token_classes),
        "files": ["lexicon.jsonl", "grammar_rules.jsonl", "senses.jsonl", "key_terms.jsonl",
                  "phonology.jsonl", "golden_scripture.tsv"],
        "pos_conflicts_sample": conflicts[:40], "scripture_uncovered_sample": uncovered[:40],
    }
    counts = goldio.write_gold(
        pair, lexicon=lexicon, pos=pos, glosses=glosses, lemmas=lemmas,
        in_scripture=scrip, affixes=affixes, senses=senses_gold, key_terms=terms, meta=meta,
        phonology=phonology_records(pair))
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
    print(f"  glosses:    {s['glosses']} bilingual (Wiktionary); key terms {s['key_terms']}")
    print(f"  senses:     {s['scripture_senses']} scripture words with a sense inventory "
          f"({s['scripture_homographs']} homographs)")
    print(f"  lexicon:    {s['lexicon_size']} real words")
    print(f"  scripture:  {s['scripture_attested']}/{s['scripture_vocab']} of NT vocab covered "
          f"({s['scripture_coverage']}); {s['scripture_uncovered']} uncovered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
