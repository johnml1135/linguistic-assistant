"""The fixed, versioned catalog of the 12 typological "master switches".

Each entry pins: the non-linguist `presentation` (the question/claim shown to a speaker), the `contours`
(allowed values), the `evidence` to assemble from the corpus, the downstream `constraint` it sets, and the
`profile_target` (which `LanguageProfile` field a confirmed value writes to — so the decision *binds* later
analysis). Detection lives in `profile_detect.py`; recording + constraining in `profile.py`; presentation
in `present_switch` below. See the OpenSpec `language-switches` change.
"""

from __future__ import annotations

from dataclasses import dataclass

CATALOG_VERSION = 1


@dataclass(frozen=True)
class SwitchDef:
    id: str
    presentation: str                 # the plain-language question/claim (non-linguist)
    contours: tuple                   # allowed values
    evidence: str                     # what corpus data to assemble
    constraint: str                   # what it enables/prunes downstream
    profile_target: tuple             # (section, name) in the LanguageProfile a confirmed value writes to
    explanation_slug: str = ""        # feature_explanations key for the deeper note


CATALOG: tuple[SwitchDef, ...] = (
    SwitchDef("synthesis",
              "How are words built — mostly separate small words (isolating), a stem plus clearly separable "
              "pieces (agglutinative), or endings that fuse several meanings at once (fusional)?",
              ("isolating", "agglutinative", "fusional", "polysynthetic"),
              "type:token ratio; mean morphemes/word; induced-affix count; longest frequent words segmented",
              "affix-stacking depth; inflection-classes (fusional) vs per-morpheme glossing (agglutinative)",
              ("morph_type", "morph_type"), "type:agglutinative"),
    SwitchDef("affix_polarity",
              "Do the meaning-changing pieces attach mostly to the FRONT of a word, the END, or both?",
              ("prefixing", "suffixing", "both", "little-affixation"),
              "induced affixes by side, frequency-weighted; base→derived examples each side",
              "where the segmenter / search looks first", ("_meta", "affix_polarity"), "affix:prefix"),
    SwitchDef("infixation",
              "Does your language ever insert a piece INSIDE a word, splitting the root "
              "(Tagalog s‹um›ulat 'wrote' from sulat 'write')?",
              ("present", "absent"),
              "internal-insertion minimal pairs; recurring internal chunks; distinct stems per chunk",
              "turns infix hypotheses on/off (a hard prune when absent)",
              ("affix_processes", "infix"), "affix:infix"),
    SwitchDef("reduplication",
              "Do you repeat all or part of a word to change its meaning (buku-buku 'books')?",
              ("absent", "partial", "full", "both"),
              "word types with a doubled syllable/CV whose de-doubled base is attested; distinct stems",
              "turns the copy-rule on/off",
              ("affix_processes", "reduplication"), "affix:reduplication"),
    SwitchDef("vowel_harmony",
              "Do vowels in a word have to 'match', so an ending changes its vowel to fit the stem?",
              ("absent", "present"),
              "suffix-vowel alternations conditioned by stem vowel class, with support + examples",
              "one harmony rule vs listing allomorph variants",
              ("phon_processes", "vowel_harmony"), "phon:vowel_harmony"),
    SwitchDef("nasal_assimilation",
              "Does a nasal (m/n/ng) at the end of a prefix change to match the next consonant "
              "(meN- → mem/men/meng)?",
              ("absent", "present"),
              "prefix-final nasal alternations conditioned by the following consonant's place; families",
              "archiphoneme-collapse (one underlying form + rule) vs an allomorph list",
              ("phon_processes", "nasal_assimilation"), "phon:nasal_assimilation"),
    SwitchDef("tone",
              "Does the pitch you say a word with change its meaning (same letters, different 'tune')?",
              ("absent", "simple", "complex"),
              "tone diacritics in the orthography; minimal-pair check if marked",
              "whether pitch is contrastive", ("phon_processes", "tone"), "phon:tone"),
    SwitchDef("gender_or_noun_class",
              "Do nouns fall into classes that make nearby words agree — a few (like masculine/feminine), "
              "many (like Bantu noun classes), or none?",
              ("none", "gender", "noun-class"),
              "systematic singular/plural prefix-pairs; modifiers/verbs co-varying with the noun; class count",
              "the FsFeatStruc dimension — gender vs noun-class (never invent gender for a noun-class language)",
              ("feature_space", "noun_class"), "feat:noun_class"),
    SwitchDef("case",
              "Does a noun change its ending depending on its job in the sentence "
              "(subject / object / 'to' it / 'of' it)?",
              ("absent", "present"),
              "role-correlated noun-suffix alternations (vs an invariant noun + word order); absence is evidence",
              "whether to propose case endings at all", ("feature_space", "case"), "feat:case"),
    SwitchDef("tam_locus",
              "Where is tense/aspect marked — a prefix on the verb, an ending on the verb, or a separate "
              "word before it?",
              ("verb-prefix", "verb-suffix", "auxiliary/particle", "mixed", "unmarked"),
              "morpheme-alignment of verb affixes to source tense words (will / -ed / have); which side",
              "where the grammar looks for TAM morphemes",
              ("_meta", "tam_locus"), "feat:tense_aspect_mood"),
    SwitchDef("agreement_head_marking",
              "Does the verb itself carry who-did-it (and to-whom) — like a prefix meaning 'I' / 'you' / 'we'?",
              ("none", "subject", "subject+object"),
              "morpheme-alignment of verb-edge morphemes to source pronouns (I/you/we); counts; examples",
              "subject/object agreement affixes; whether concord is head-marked",
              ("feature_space", "agreement"), "feat:agreement"),
    SwitchDef("articles",
              "Is there a word or ending for 'the' (already-known) vs 'a' (new)?",
              ("none", "definite-only", "indefinite-only", "both"),
              "a high-frequency function word/affix aligning to 'the'/'a' — or nothing aligning",
              "whether to model articles at all",
              ("feature_space", "definiteness"), "feat:definiteness"),
)

BY_ID = {s.id: s for s in CATALOG}

# The linguistic-theory grounding for each switch (basis + the detector's rationale + a citation). This is
# what makes the catalog "well-grounded": each switch corresponds to an established typological parameter,
# and its detector measures the corpus correlate the theory predicts.
THEORY: dict[str, str] = {
    "synthesis":
        "Greenberg (1960) quantitative typology: the SYNTHETIC index = morphemes/word (M/W) places a "
        "language isolating→synthetic→polysynthetic; the AGGLUTINATION index (clean morpheme boundaries) "
        "separates agglutinative from fusional. Detector: estimate M/W by stripping induced affixes.",
    "affix_polarity":
        "Greenberg (1963) Universal 27 (a strong cross-linguistic suffixing preference) and WALS 26A "
        "(Dryer 2013, Prefixing vs. Suffixing). Detector: the side balance of the induced affix inventory.",
    "infixation":
        "Yu (2007) typology of infixation (rare, prosodically anchored); productivity by the Tolerance "
        "Principle (Yang 2016) — a real infix recurs across many distinct stems, a coincidence does not.",
    "reduplication":
        "Inkelas & Zoll (2005); WALS 27A (Rubino 2013). Reduplication copies phonological material that is "
        "morphologically meaningful — so the DE-DOUBLED base must exist independently (the detector's gate).",
    "vowel_harmony":
        "Autosegmental harmony (Clements 1976): vowels agree in a feature within a word domain, so a "
        "suffix vowel co-varies with the stem. Detector: stem-conditioned suffix-vowel alternations.",
    "nasal_assimilation":
        "Place assimilation (Trubetzkoy's archiphoneme; an underspecified nasal takes the place of the "
        "following consonant). Detector: prefix-final nasal alternations conditioned by the next consonant.",
    "tone":
        "Yip (2002); WALS 13A (Maddieson 2013): lexically/grammatically contrastive pitch. Detector: "
        "orthographic tone diacritics (a near-universal correlate in written tone languages).",
    "gender_or_noun_class":
        "Corbett (1991): gender and noun-class are AGREEMENT-class systems differing in size/basis; the "
        "Bantu hallmark is alliterative concord across a small set of recurring class prefixes; Romance "
        "gender shows the -o/-a alternation. Detector: -o/-a pairs vs recurring class-prefix systems.",
    "case":
        "Blake (2001): case marks a noun's syntactic role, the dependent-marking strategy (Nichols 1986). "
        "Detector: role-correlated noun-suffix alternation (hard from text alone → conservative default).",
    "tam_locus":
        "Bybee (1985) Morphology: tense/aspect/mood is marked on the verb (prefix or suffix) or by an "
        "auxiliary. Detector: which side's verb affixes align to source tense/aspect words.",
    "agreement_head_marking":
        "Nichols (1986) head- vs dependent-marking: a head-marking language carries subject/object "
        "agreement ON the verb. Detector: verb-edge morphemes aligning to source pronouns (either edge).",
    "articles":
        "WALS 37A (Dryer 2013); Lyons (1999) Definiteness: a closed, high-frequency (in)definite marker. "
        "Detector: a DOMINANT morpheme aligning to 'the'/'a' (diffuse alignment ⇒ no article system).",
}


def get(switch_id: str) -> SwitchDef:
    return BY_ID[switch_id]


def theory(switch_id: str) -> str:
    return THEORY.get(switch_id, "")


def present_switch(detected) -> dict:
    """Render a detected `Switch` (from profile_detect) as a falsifiable, non-linguist claim:
    the question, the best-guess + confidence, the evidence, the contour options, and any internet
    conflict. `detected` is a `profile_detect.Switch`."""
    sd = BY_ID.get(detected.name)
    claim = {
        "id": detected.name,
        "question": sd.presentation if sd else detected.name,
        "best_guess": detected.value,
        "confidence": detected.confidence,
        "evidence": detected.evidence,
        "options": list(sd.contours) if sd else [],
        "constrains": sd.constraint if sd else "",
        "theory": THEORY.get(detected.name, ""),
    }
    if detected.internet is not None:
        claim["reference_says"] = detected.internet
        claim["conflict"] = (detected.agrees is False)
    return claim
