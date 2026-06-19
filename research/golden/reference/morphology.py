"""Turn flat word data into a true morphology: separate lexemes from wordforms.

A Wiktionary "form-of" gloss like "third-person singular future indicative of abrir" is NOT a sense — it
is a morphological analysis: lemma `abrir` + the FsFeatStruc {Person:Third, Number:Singular, Tense:Future,
Mood:Indicative}. This module classifies senses (real vs form-of) and parses form-of glosses into
(lemma, features) in the SAME LibLCM vocabulary as `liblcm.inflection_features`, so the inflected forms
leave the lexicon (which keeps only lemmas + real senses) and become a wordform-analysis gold.
"""

from __future__ import annotations

import re

# token -> (LibLCM feature, value); same vocabulary as liblcm._UNIMORPH_INFL, plus the Romance tenses and
# the non-finite forms Wiktionary names in prose.
_PERSON = {"first": "First", "second": "Second", "third": "Third"}
_NUMBER = {"singular": "Singular", "plural": "Plural", "dual": "Dual"}
_TENSE = {"present": "Present", "past": "Past", "future": "Future",
          "preterite": "Preterite", "imperfect": "Imperfect", "conditional": "Conditional"}
_MOOD = {"indicative": "Indicative", "subjunctive": "Subjunctive", "imperative": "Imperative"}
_GENDER = {"masculine": "Masculine", "feminine": "Feminine", "neuter": "Neuter"}
_NONFINITE = {"past participle": ("NonFinite", "Participle"), "present participle": ("NonFinite", "Participle"),
              "gerund": ("NonFinite", "Gerund"), "infinitive": ("NonFinite", "Infinitive")}

# the regular Wiktionary "form-of" templates (English metalanguage). If a gloss matches, it is morphology.
_FORM_OF = re.compile(
    r"(person|\bsingular\b|\bplural\b|participle|gerund|infinitive of|inflection of|"
    r"indicative|subjunctive|imperative|preterite|imperfect|conditional|"
    r"plural of|feminine of|masculine of|(past|present) tense of)", re.I)
_LEMMA = re.compile(r"\bof ([a-záéíóúñüäöA-Z']+)\b\.?:?\s*$", re.I)


def is_form_of(gloss: str) -> bool:
    """True if the gloss is a morphological form-of description, not a lexical meaning."""
    return bool(_FORM_OF.search(gloss or ""))


def parse_form_of(gloss: str) -> tuple[str | None, dict[str, str]]:
    """A single form-of gloss → (lemma | None, FsFeatStruc). lemma is None for a feature-only line
    (e.g. the "third-person singular present indicative" lines under an "inflection of X:" header)."""
    g = (gloss or "").lower().strip()
    m = _LEMMA.search(g)
    lemma = m.group(1).lower() if m else None
    feats: dict[str, str] = {}
    for k, v in _NONFINITE.items():     # multiword first (past participle) before single tokens
        if k in g:
            feats[v[0]] = v[1]
    for k, v in _PERSON.items():
        if re.search(rf"{k}-person", g):
            feats["Person"] = v
    for k, v in _NUMBER.items():
        if re.search(rf"\b{k}\b", g):
            feats["Number"] = v
    for k, v in _TENSE.items():
        if re.search(rf"\b{k}\b", g):
            feats["Tense"] = v
    for k, v in _MOOD.items():
        if re.search(rf"\b{k}\b", g):
            feats["Mood"] = v
    for k, v in _GENDER.items():
        if re.search(rf"\b{k}\b", g):
            feats["Gender"] = v
    return lemma, feats


def analyze_wordform(senses: list[str]) -> tuple[str | None, dict[str, str]]:
    """All of a form's senses → its (lemma, FsFeatStruc). Threads the lemma from whichever sense names it
    (incl. an "inflection of LEMMA:" header) across the feature-only lines, and merges the features of the
    most-specified analysis. Returns (None, {}) if no form-of sense is present (i.e. it's a real lexeme)."""
    if not any(is_form_of(s) for s in senses):
        return None, {}
    lemma = None
    best: dict[str, str] = {}
    for s in senses:
        if not is_form_of(s):
            continue
        lm, feats = parse_form_of(s)
        lemma = lemma or lm
        if len(feats) > len(best):
            best = feats
    return lemma, best


# "meta" senses are not translations — Wiktionary often lists them FIRST (pan→"initialism of PAN",
# amor→"a surname"), which made them the gold's primary gloss even though the eBible alignment has the
# real meaning (bread, love). Recognise them so they sink below real senses (and can be corrected).
_META = re.compile(
    r"\b(initialism|abbreviation|acronym|surname|given name|roman numeral|symbol (for|of)|"
    r"alternative (spelling|form) of|obsolete (spelling|form)|misspelling of|the name of|a (male|female) )\b",
    re.I)


def is_meta_sense(gloss: str) -> bool:
    """True if the gloss is a name/abbreviation/spelling note rather than a translatable meaning."""
    return bool(_META.search(gloss or ""))


def real_senses(senses: list[str]) -> list[str]:
    """Lexical senses only (form-of dropped), with translatable meanings BEFORE meta senses (names,
    initialisms…) so the primary gloss is a real translation, not Wiktionary's incidental first sense."""
    rs = [s for s in (senses or []) if not is_form_of(s)]
    return sorted(rs, key=is_meta_sense)  # stable: non-meta (False) first
