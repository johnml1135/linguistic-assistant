"""LibLCM terminology + converters — the DESTINATION dialect (FieldWorks HC-parsable data).

The online references speak their own dialects (UD **UPOS**, UniMorph **feature bundles**); the product
is **LibLCM** (FieldWorks Language Explorer / Hermit Crab): `LexEntry` (lexeme form + `MoMorphType`),
`MoStemMsa`/`MoInflAffMsa` (a `PartOfSpeech` + an `FsFeatStruc` of inflection features), `PartOfSpeech`,
`MoInflAffixTemplate`/`MoInflAffixSlot`, and HC phonological rules / natural classes. This module is the
single place that maps each source dialect ONTO LibLCM terms, so the gold, the cycle, and the change-set
deltas all speak the destination format.

Nothing here parses or writes FLEx; it is the vocabulary + the conversions. See the change-set vocab
(`proposal.change_set`: `lexical.*` mirror MiniLcm/LibLCM, `morphophonology.*` are HC) and `deltas/`.
"""

from __future__ import annotations

# LibLCM / FLEx grammatical categories (PartOfSpeech names; FLEx's default list derives from GOLD).
LIBLCM_POS = (
    "Noun", "Proper noun", "Verb", "Adjective", "Adverb", "Pronoun", "Adposition",
    "Coordinating connective", "Subordinating connective", "Determiner", "Numeral",
    "Particle", "Interjection", "Auxiliary verb", "Classifier", "Unknown",
)

# LibLCM MoMorphType names (the morph-type list a LexEntry / allomorph carries).
MORPH_TYPES = (
    "stem", "root", "bound root", "prefix", "suffix", "infix", "circumfix",
    "enclitic", "proclitic", "particle", "phrase",
)

# UD UPOS  -> LibLCM PartOfSpeech
_UPOS_TO_LIBLCM = {
    "NOUN": "Noun", "PROPN": "Proper noun", "VERB": "Verb", "ADJ": "Adjective", "ADV": "Adverb",
    "PRON": "Pronoun", "ADP": "Adposition", "CCONJ": "Coordinating connective",
    "SCONJ": "Subordinating connective", "DET": "Determiner", "NUM": "Numeral", "PART": "Particle",
    "INTJ": "Interjection", "AUX": "Auxiliary verb", "X": "Unknown", "SYM": "Unknown", "PUNCT": "Unknown",
}
# the cycle's internal POS ids (cycle/pos.py) -> LibLCM PartOfSpeech
_CYCLE_TO_LIBLCM = {
    "noun": "Noun", "verb": "Verb", "adj": "Adjective", "adv": "Adverb", "pron": "Pronoun",
    "prep": "Adposition", "conj": "Coordinating connective", "det": "Determiner", "num": "Numeral",
    "ptcl": "Particle",
}
# UniMorph dimension value -> (LibLCM inflection feature, value)  [an FsFeatStruc cell]
_UNIMORPH_INFL = {
    "SG": ("Number", "Singular"), "PL": ("Number", "Plural"), "DU": ("Number", "Dual"),
    "1": ("Person", "First"), "2": ("Person", "Second"), "3": ("Person", "Third"),
    "PRS": ("Tense", "Present"), "PST": ("Tense", "Past"), "FUT": ("Tense", "Future"),
    "PFV": ("Aspect", "Perfective"), "IPFV": ("Aspect", "Imperfective"), "PROG": ("Aspect", "Progressive"),
    "IND": ("Mood", "Indicative"), "SBJV": ("Mood", "Subjunctive"), "IMP": ("Mood", "Imperative"),
    "MASC": ("Gender", "Masculine"), "FEM": ("Gender", "Feminine"), "NEUT": ("Gender", "Neuter"),
    "NOM": ("Case", "Nominative"), "ACC": ("Case", "Accusative"), "GEN": ("Case", "Genitive"),
    "DAT": ("Case", "Dative"), "DEF": ("Definiteness", "Definite"), "INDF": ("Definiteness", "Indefinite"),
}


def pos_from_upos(upos: str) -> str:
    return _UPOS_TO_LIBLCM.get(upos, "Unknown")


def pos_from_cycle(pos_id: str) -> str:
    return _CYCLE_TO_LIBLCM.get(pos_id, "Unknown")


# Wiktionary/kaikki POS string -> LibLCM PartOfSpeech
_WIKTIONARY_TO_LIBLCM = {
    "noun": "Noun", "name": "Proper noun", "proper noun": "Proper noun", "verb": "Verb",
    "adj": "Adjective", "adv": "Adverb", "pron": "Pronoun", "prep": "Adposition", "adp": "Adposition",
    "postp": "Adposition", "conj": "Coordinating connective", "det": "Determiner", "article": "Determiner",
    "num": "Numeral", "particle": "Particle", "intj": "Interjection", "prefix": "Unknown",
    "suffix": "Unknown", "infix": "Unknown",
}


def pos_from_wiktionary(pos: str) -> str:
    return _WIKTIONARY_TO_LIBLCM.get((pos or "").lower(), "Unknown")


def inflection_features(unimorph_feats: str) -> dict[str, str]:
    """A UniMorph bundle (e.g. ``V;IND;PST;1;SG``) → a LibLCM inflection FsFeatStruc {feature: value}."""
    out: dict[str, str] = {}
    for tag in unimorph_feats.split(";"):
        cell = _UNIMORPH_INFL.get(tag.strip())
        if cell:
            out[cell[0]] = cell[1]
    return out
