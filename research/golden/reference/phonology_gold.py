"""Phonology layer of the golden set — the segment inventory, natural classes, and phonological rules,
emitted as reviewable JSONL (`phonology.jsonl`) and used to build a feature-bearing HC grammar.

This is the bridge to HC's harder path. The segment/natural-class records are the substrate every
phonological rule needs (vowel, consonant, front, high…); the rule records describe the systematic
alternations in LibLCM/HC terms. A rule's `status` says how far it is wired:
  active   — emitted into the HC grammar and round-trips through `hc`.
  staged   — described here, mechanism known, not yet emitted (needs the rule-emission work + witnesses).

Spanish is a transparent 5-vowel system read straight off the orthography (no audio); harmony is absent.
Indonesian's signature alternation is meN-/peN- nasal assimilation (the prefix's nasal takes the place of
the following consonant, which may delete) — described and staged.
"""

from __future__ import annotations

# grapheme -> phonological features (voc/hi/rnd/back). Mirrors cycle/hc_phonology Spanish inventory.
SPANISH_VOWELS = {
    "a": {"voc": "vow", "hi": "lo", "rnd": "unr", "back": "bk"},
    "e": {"voc": "vow", "hi": "lo", "rnd": "unr", "back": "fr"},
    "i": {"voc": "vow", "hi": "hi", "rnd": "unr", "back": "fr"},
    "o": {"voc": "vow", "hi": "lo", "rnd": "rnd", "back": "bk"},
    "u": {"voc": "vow", "hi": "hi", "rnd": "rnd", "back": "bk"},
}
SPANISH_ACCENTS = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}
FIVE_VOWELS = {v: {"voc": "vow"} for v in "aeiou"}  # minimal inventory for langs without a feature table

NATURAL_CLASSES = [
    {"type": "natural_class", "id": "vowel", "features": {"voc": "vow"}},
    {"type": "natural_class", "id": "cons", "features": {"voc": "cons"}},
    {"type": "natural_class", "id": "front", "features": {"voc": "vow", "back": "fr"}},
    {"type": "natural_class", "id": "high", "features": {"voc": "vow", "hi": "hi"}},
]

RULES = {
    "spa": [
        {"type": "rule", "id": "spa_plural_epenthesis", "kind": "epenthesis", "status": "staged",
         "description": "plural -s → -es after a consonant-final stem (luz→luces, mes→meses): insert e "
                        "before the -s suffix when the stem ends in a consonant.",
         "mechanism": "PhonologicalRule, InsertSegments e / [cons] __ s#", "witnesses": ["luces", "meses", "voces"]},
        {"type": "meta", "vowel_harmony": False,
         "note": "Spanish has no vowel harmony; the inventory is for natural-class conditioning only."},
    ],
    "ind": [
        {"type": "rule", "id": "ind_meN_assimilation", "kind": "assimilation", "status": "staged",
         "description": "meN-/peN- prefix nasal assimilates to the place of the following consonant and "
                        "may delete a voiceless onset: meN+kasih→mengasih, meN+pukul→memukul, meN+tulis→menulis.",
         "mechanism": "PhonologicalRule, nasal place = following C place; voiceless-onset deletion",
         "witnesses": ["mengasihi", "memukul", "menulis", "menyertai"]},
        {"type": "meta", "vowel_harmony": False},
    ],
    "tgl": [{"type": "meta", "vowel_harmony": False,
             "note": "Tagalog infixation (-um-, -in-) is morphological, handled by HC infix rules, not phonology."}],
    "swh": [{"type": "meta", "vowel_harmony": False,
             "note": "Swahili: no vowel harmony; Bantu agreement is morphological (noun-class concord), not phonological."}],
}


def vowel_inventory(pair: str) -> dict[str, dict]:
    return SPANISH_VOWELS if pair == "spa" else FIVE_VOWELS


def phon_feats(pair: str, charset) -> dict[str, dict[str, str]]:
    """grapheme -> features for the live HC grammar (golden.hc.build_grammar_xml `phon_feats`). Only
    vowels get features (incl. accented vowels, folded to base quality); consonants stay identity-only."""
    inv = vowel_inventory(pair)
    feats: dict[str, dict[str, str]] = {}
    for ch in set(charset):
        base = SPANISH_ACCENTS.get(ch, ch)
        if base in inv:
            feats[ch] = dict(inv[base])
    return feats


def phonology_records(pair: str) -> list[dict]:
    """The phonology.jsonl content: one segment record per vowel, the natural classes, and the rules."""
    recs = [{"type": "segment", "grapheme": g, "features": f} for g, f in vowel_inventory(pair).items()]
    recs += NATURAL_CLASSES
    recs += RULES.get(pair, [{"type": "meta", "vowel_harmony": False}])
    return recs
