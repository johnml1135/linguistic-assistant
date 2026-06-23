"""Pre-written, non-linguist explanations for the language-profile features.

The machine-readable form of `openspec/changes/deferral-packages/feature-explanations.md`. Each entry is
written for a fluent speaker who is NOT a trained linguist: a jargon-free meaning, a "how to spot it in
your own language" cue, and open-licensed source links (so they can be embedded with attribution).

Sources: WALS / Grambank are CC-BY-4.0; Wikipedia is CC-BY-SA-4.0; the SIL Glossary of Linguistic Terms
is SIL's own resource (usable in-house). `explain(slug)` returns the block for a feature; the profile and
the ticket renderer surface it beside the feature/question so a reviewer understands the term first.
"""

from __future__ import annotations

WALS = "CC-BY-4.0"
WIKI = "CC-BY-SA-4.0"
SIL = "SIL (in-house)"


def _s(title, url, lic):
    return {"title": title, "url": url, "license": lic}


# slug -> {plain, spot, sources:[...]}
EXPLANATIONS: dict[str, dict] = {
    # --- morphological type --------------------------------------------------------------------
    "type:isolating": {
        "plain": "Words mostly don't change shape; grammar is shown by separate small words and word order.",
        "spot": "“Past tense” is a separate word, not a different ending on the verb.",
        "sources": [_s("WALS 20A — Fusion", "https://wals.info/feature/20A", WALS),
                    _s("Wikipedia: Isolating language", "https://en.wikipedia.org/wiki/Isolating_language", WIKI)]},
    "type:agglutinative": {
        "plain": "Words are built by gluing on clearly separable pieces, each adding one meaning — beads on a string.",
        "spot": "You can chop a long word into a stem + several prefixes/suffixes, each with one job.",
        "sources": [_s("WALS 21A — Exponence", "https://wals.info/feature/21A", WALS),
                    _s("Wikipedia: Agglutinative language", "https://en.wikipedia.org/wiki/Agglutinative_language", WIKI)]},
    "type:fusional": {
        "plain": "One ending packs several meanings at once that you can't cleanly separate.",
        "spot": "A single verb ending tells you person AND number AND tense together (Spanish hablé = I + past).",
        "sources": [_s("WALS 21A — Exponence", "https://wals.info/feature/21A", WALS),
                    _s("Wikipedia: Fusional language", "https://en.wikipedia.org/wiki/Fusional_language", WIKI)]},
    "type:polysynthetic": {
        "plain": "A single very long word can express what other languages need a whole sentence for.",
        "spot": "One “word” includes the verb plus its subject, object, and more.",
        "sources": [_s("WALS 22A — Inflectional Synthesis", "https://wals.info/feature/22A", WALS),
                    _s("Wikipedia: Polysynthetic language", "https://en.wikipedia.org/wiki/Polysynthetic_language", WIKI)]},
    # --- affix processes -----------------------------------------------------------------------
    "affix:prefix": {
        "plain": "A piece added to the FRONT of a word changes its meaning (English un-happy).",
        "spot": "The start of the word changes while the rest stays the same.",
        "sources": [_s("WALS 26A — Prefixing vs Suffixing", "https://wals.info/feature/26A", WALS),
                    _s("Wikipedia: Prefix", "https://en.wikipedia.org/wiki/Prefix", WIKI)]},
    "affix:suffix": {
        "plain": "A piece added to the END of a word (English cats, walked).",
        "spot": "The ending changes while the start stays the same.",
        "sources": [_s("WALS 26A — Prefixing vs Suffixing", "https://wals.info/feature/26A", WALS),
                    _s("Wikipedia: Suffix", "https://en.wikipedia.org/wiki/Suffix", WIKI)]},
    "affix:infix": {
        "plain": "A piece inserted INSIDE a word, splitting the root (Tagalog s‹um›ulat from sulat).",
        "spot": "The extra piece appears in the middle, not the front or end. Most languages do NOT do this.",
        "sources": [_s("SIL Glossary: Infix", "https://glossary.sil.org/term/infix", SIL),
                    _s("Wikipedia: Infix", "https://en.wikipedia.org/wiki/Infix", WIKI)]},
    "affix:circumfix": {
        "plain": "A two-part piece wrapping a word — part on the front AND part on the back, as one unit.",
        "spot": "A front piece and an end piece always show up together for one meaning (Indonesian ke-…-an).",
        "sources": [_s("Wikipedia: Circumfix", "https://en.wikipedia.org/wiki/Circumfix", WIKI)]},
    "affix:reduplication": {
        "plain": "Repeating all or part of a word to change its meaning — often 'many', 'very', or ongoing action.",
        "spot": "Part of the word is doubled (Indonesian buku → buku-buku 'books').",
        "sources": [_s("WALS 27A — Reduplication", "https://wals.info/feature/27A", WALS),
                    _s("Wikipedia: Reduplication", "https://en.wikipedia.org/wiki/Reduplication", WIKI)]},
    "affix:compounding": {
        "plain": "Two whole words joined to make a new one (tooth + brush = toothbrush).",
        "spot": "A longer word is really two smaller meaningful words stuck together.",
        "sources": [_s("Wikipedia: Compound", "https://en.wikipedia.org/wiki/Compound_(linguistics)", WIKI)]},
    # --- phonology -----------------------------------------------------------------------------
    "phon:vowel_harmony": {
        "plain": "Vowels in a word must 'match', so an ending changes its vowel to fit the stem.",
        "spot": "The same ending sounds slightly different (a different vowel) depending on the word it joins.",
        "sources": [_s("SIL Glossary: Vowel harmony", "https://glossary.sil.org/term/vowel-harmony", SIL),
                    _s("Wikipedia: Vowel harmony", "https://en.wikipedia.org/wiki/Vowel_harmony", WIKI)]},
    "phon:nasal_assimilation": {
        "plain": "A nasal sound (m/n/ng) changes to match the consonant right after it.",
        "spot": "A prefix-ending nasal is spelled differently before different letters (Indonesian meN-).",
        "sources": [_s("SIL Glossary: Assimilatory process", "https://glossary.sil.org/term/assimilatory-process", SIL),
                    _s("Wikipedia: Assimilation", "https://en.wikipedia.org/wiki/Assimilation_(phonology)", WIKI)]},
    "phon:tone": {
        "plain": "The pitch you say a word with changes its meaning — same letters, different 'tune'.",
        "spot": "Two words look identical but mean different things by a high/low/rising pitch.",
        "sources": [_s("WALS 13A — Tone", "https://wals.info/feature/13A", WALS),
                    _s("Wikipedia: Tone", "https://en.wikipedia.org/wiki/Tone_(linguistics)", WIKI)]},
    # --- feature space -------------------------------------------------------------------------
    "feat:gender": {
        "plain": "Nouns fall into a few classes (often masculine/feminine) and nearby words change to agree.",
        "spot": "Adjectives/articles change form to match the noun (Spanish el gato / la gata).",
        "sources": [_s("WALS 31A — Sex-based Gender", "https://wals.info/feature/31A", WALS),
                    _s("Wikipedia: Grammatical gender", "https://en.wikipedia.org/wiki/Grammatical_gender", WIKI)]},
    "feat:noun_class": {
        "plain": "Like gender but with MANY classes, not tied to sex, each with its own agreement markers.",
        "spot": "Verbs and adjectives carry a marker matching the noun's class (Swahili m-/wa-, ki-/vi-).",
        "sources": [_s("WALS 30A — Number of Genders", "https://wals.info/feature/30A", WALS),
                    _s("Wikipedia: Noun class", "https://en.wikipedia.org/wiki/Noun_class", WIKI)]},
    "feat:case": {
        "plain": "A noun changes its ending depending on its job in the sentence (subject, object, to/of/with).",
        "spot": "The same noun takes different endings for 'the dog' vs 'to the dog' vs 'of the dog'.",
        "sources": [_s("WALS 49A — Number of Cases", "https://wals.info/feature/49A", WALS),
                    _s("Wikipedia: Grammatical case", "https://en.wikipedia.org/wiki/Grammatical_case", WIKI)]},
    "feat:tense_aspect_mood": {
        "plain": "Verbs mark WHEN (tense), HOW it unfolds — finished vs ongoing (aspect), and attitude — fact vs wish (mood).",
        "spot": "The verb changes form for past/present/future, or for 'was doing' vs 'did'.",
        "sources": [_s("WALS 65A — Perfective/Imperfective", "https://wals.info/feature/65A", WALS),
                    _s("Wikipedia: Grammatical aspect", "https://en.wikipedia.org/wiki/Grammatical_aspect", WIKI)]},
    "feat:person_number": {
        "plain": "Words mark WHO (I/you/he-she-it) and HOW MANY (one vs more than one), often on the verb.",
        "spot": "The verb ending alone tells you the subject; or nouns mark singular vs plural.",
        "sources": [_s("Wikipedia: Grammatical number", "https://en.wikipedia.org/wiki/Grammatical_number", WIKI)]},
    "feat:definiteness": {
        "plain": "The language marks 'a/some' (new) vs 'the' (already-known).",
        "spot": "There's a little word or ending meaning 'the specific one we both know'.",
        "sources": [_s("WALS 37A — Definite Articles", "https://wals.info/feature/37A", WALS),
                    _s("Wikipedia: Definiteness", "https://en.wikipedia.org/wiki/Definiteness", WIKI)]},
    "feat:agreement": {
        "plain": "Words must 'match' each other — a verb or adjective changes to agree with its noun.",
        "spot": "Changing the noun forces other words in the phrase to change too.",
        "sources": [_s("Wikipedia: Agreement", "https://en.wikipedia.org/wiki/Agreement_(linguistics)", WIKI)]},
    "feat:word_order": {
        "plain": "The usual order of subject, verb, and object (English is Subject-Verb-Object).",
        "spot": "In a plain statement, does the doer, the action, or the thing-acted-on come first?",
        "sources": [_s("WALS 81A — Order of S, O, V", "https://wals.info/feature/81A", WALS),
                    _s("Wikipedia: Word order", "https://en.wikipedia.org/wiki/Word_order", WIKI)]},
    # --- building blocks -----------------------------------------------------------------------
    "morph:clitic": {
        "plain": "A little word that leans on its neighbour and attaches like an ending (Spanish dá-me-lo).",
        "spot": "A pronoun or particle that can't stand alone and sticks onto another word.",
        "sources": [_s("SIL Glossary: Clitic", "https://glossary.sil.org/term/clitic", SIL),
                    _s("Wikipedia: Clitic", "https://en.wikipedia.org/wiki/Clitic", WIKI)]},
    "morph:derivation": {
        "plain": "Derivation makes a NEW word (teach → teacher); inflection just changes the form (teach → teaches).",
        "spot": "Does the piece create a different dictionary word, or just a grammatical variant of the same one?",
        "sources": [_s("SIL Glossary: Derivation", "https://glossary.sil.org/term/derivation", SIL),
                    _s("Wikipedia: Morphological derivation", "https://en.wikipedia.org/wiki/Morphological_derivation", WIKI)]},
    "morph:allomorph": {
        "plain": "The SAME piece showing up in more than one shape depending on its surroundings.",
        "spot": "An ending has predictable variants (English -s sounds like 's' in cats, 'z' in dogs).",
        "sources": [_s("SIL Glossary: Allomorph", "https://glossary.sil.org/term/allomorph", SIL),
                    _s("Wikipedia: Allomorph", "https://en.wikipedia.org/wiki/Allomorph", WIKI)]},
    "morph:suppletion": {
        "plain": "A word's forms are completely different from each other, not just an ending swap (go/went).",
        "spot": "The past or plural looks nothing like the base.",
        "sources": [_s("Wikipedia: Suppletion", "https://en.wikipedia.org/wiki/Suppletion", WIKI)]},
    "morph:archiphoneme": {
        "plain": "One underlying form that covers several surface variants which a rule then adjusts.",
        "spot": "Technical — the tool proposes it; you mainly judge whether the variants share one meaning.",
        "sources": [_s("Wikipedia: Archiphoneme", "https://en.wikipedia.org/wiki/Archiphoneme", WIKI)]},
}


def explain(slug: str) -> dict | None:
    """The explanation block for a feature slug, or None if we have no pre-written one."""
    return EXPLANATIONS.get(slug)
