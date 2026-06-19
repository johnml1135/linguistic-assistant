"""External reference-gold sources per target language (fetch-on-box, license-aware).

Three complementary references validate different layers of the induced grammar:
  * **UniMorph** — (lemma, inflected form, UniMorph feature bundle): validates morphology / affix
    function. CC-BY-SA. github.com/unimorph/<code>.
  * **Universal Dependencies** — CoNLL-U (FORM, LEMMA, UPOS, FEATS) from annotated text: validates
    POS. Mostly CC-BY-SA/NC. github.com/UniversalDependencies/UD_<Lang>-<TB>.
  * **unfoldingWord / Door43 translationWords** — controlled English biblical key-term vocabulary
    (god, lord, grace, …): validates that high-confidence English glosses are real domain terms.
    github.com/unfoldingWord/en_tw. CC-BY-SA.

Coverage is uneven (Tagalog UD is tiny; Swahili UniMorph/UD are thin/absent) — the fetcher skips a
missing source gracefully and the evaluator scores only what exists. Raw downloads land under
`golden/_sources/reference/<pair>/`; nothing here is committed (regenerable).
"""

from __future__ import annotations

# UniMorph language-data raw URLs (the single big tab file in each repo).
UNIMORPH: dict[str, str] = {
    "spa": "https://raw.githubusercontent.com/unimorph/spa/master/spa",
    "swh": "https://raw.githubusercontent.com/unimorph/swc/master/swc",  # Swahili UniMorph code = swc
    "ind": "https://raw.githubusercontent.com/unimorph/ind/master/ind",
    # tgl: no UniMorph repo
}

# Universal Dependencies — ALL readily-available treebanks per language (combined for coverage).
UD: dict[str, list[str]] = {
    "spa": [
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Spanish-GSD/master/es_gsd-ud-train.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Spanish-AnCora/master/es_ancora-ud-train.conllu",
    ],
    "ind": [
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Indonesian-GSD/master/id_gsd-ud-train.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Indonesian-CSUI/master/id_csui-ud-train.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Indonesian-PUD/master/id_pud-ud-test.conllu",
    ],
    "tgl": [
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Tagalog-Ugnayan/master/tl_ugnayan-ud-test.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Tagalog-TRG/master/tl_trg-ud-test.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Tagalog-NewsCrawl/master/tl_newscrawl-ud-test.conllu",
    ],
    # swh: no standard UD Swahili treebank
}

# UniMorph dimension-1 (POS) tag → UD UPOS, for converting morphology entries into a POS gold.
UNIMORPH_POS_TO_UPOS: dict[str, str] = {
    "N": "NOUN", "PROPN": "PROPN", "V": "VERB", "V.PTCP": "VERB", "V.CVB": "VERB", "V.MSDR": "VERB",
    "ADJ": "ADJ", "ADV": "ADV", "PRO": "PRON", "DET": "DET", "ART": "DET", "NUM": "NUM", "ADP": "ADP",
    "CONJ": "CCONJ", "COMP": "SCONJ", "INTJ": "INTJ", "PART": "PART", "AUX": "AUX", "CLF": "X",
}

# Wiktionary via kaikki.org — machine-readable extracts of the ENGLISH Wiktionary's entries for each
# language: word → POS + English sense glosses + inflected forms. The only source here that gives a
# bilingual (target→English) GLOSS, and it lifts the thin Tagalog/Swahili coverage. Big files (Spanish
# especially) → the fetcher streams with a byte cap. CC-BY-SA.
KAIKKI: dict[str, str] = {
    "spa": "https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl",
    "ind": "https://kaikki.org/dictionary/Indonesian/kaikki.org-dictionary-Indonesian.jsonl",
    "tgl": "https://kaikki.org/dictionary/Tagalog/kaikki.org-dictionary-Tagalog.jsonl",
    "swh": "https://kaikki.org/dictionary/Swahili/kaikki.org-dictionary-Swahili.jsonl",
}

# unfoldingWord translationWords — directory listings of controlled English key terms, via the Door43
# Gitea API (the canonical host). Language-independent (English side); checks gloss validity per pair.
UW_TW_DIRS = [
    "https://git.door43.org/api/v1/repos/unfoldingWord/en_tw/contents/bible/kt?ref=master",
    "https://git.door43.org/api/v1/repos/unfoldingWord/en_tw/contents/bible/names?ref=master",
    "https://git.door43.org/api/v1/repos/unfoldingWord/en_tw/contents/bible/other?ref=master",
]

# our POS ids -> UD UPOS, for the POS-accuracy check.
POS_TO_UPOS: dict[str, str] = {
    "noun": "NOUN", "verb": "VERB", "adj": "ADJ", "adv": "ADV", "pron": "PRON",
    "prep": "ADP", "conj": "CCONJ", "det": "DET", "num": "NUM", "ptcl": "PART",
}
