# Feature explanations — plain-language seed glossary

**Audience:** a fluent speaker of the language who is *not* a trained linguist. They know how their language
works; they may not know the technical name for it. Every explanation avoids jargon, gives a "how would I
notice this in my own language?" cue, and says what the feature lets the tool do or stops it from doing.

**How this is used.** Each `language_profile` feature carries an `explanation` block keyed by the slugs
below. The deferral ticket renderer (and any UI over the profile) shows the plain meaning + the "how to
spot it" cue + the source links next to the question, so a reviewer choosing "does your language have
reduplication?" sees what that means before answering.

**Licensing of the sources.** Our prose here is original (project-owned). The reference links are to
open-licensed resources so they can be embedded/quoted with attribution:

| Source | License | Link form | Note |
|---|---|---|---|
| WALS — World Atlas of Language Structures | **CC-BY-4.0** | `https://wals.info/feature/<id>` | per-feature chapter, citable/quotable with attribution |
| Grambank | **CC-BY-4.0** | `https://grambank.clld.org/parameters/<GBid>` | binary morphosyntax features |
| Wikipedia | **CC-BY-SA-4.0** | `https://en.wikipedia.org/wiki/<Article>` | covers features WALS/Grambank don't (harmony, infix, assimilation) |
| SIL *Glossary of Linguistic Terms* | © SIL Global — **we are SIL, so this is usable in-house** | `https://glossary.sil.org/term/<slug>` | first-class source; SIL's own field-linguist definitions, often the clearest for the speaker-reviewer |

WALS citation form: *Author. 2013. Feature Name. In Dryer & Haspelmath (eds.), WALS Online. MPI-EVA.*
(`wals.info/chapter/<n>`). Grambank: *The Grambank Consortium 2023, CC-BY-4.0.*

---

## 1. Morphological type — how words are built from parts

### `type:isolating`
**Plain meaning:** Words mostly don't change shape; grammar is shown by separate little words and by word
order, not by endings. *(Vietnamese, Mandarin lean this way.)*
**How to spot it:** "Past tense" is a separate word, not a different ending on the verb.
**Why it matters here:** if your language is strongly isolating, the tool should expect few affix rules and
lean on word order / function words instead.
**Sources:** [WALS 20A — Fusion of Selected Inflectional Formatives](https://wals.info/feature/20A) (CC-BY-4.0) · [Wikipedia: Isolating language](https://en.wikipedia.org/wiki/Isolating_language) (CC-BY-SA-4.0)

### `type:agglutinative`
**Plain meaning:** Words are built by gluing on clearly separable pieces, each piece adding one meaning, like
beads on a string. *(Swahili, Turkish, Tagalog, Indonesian lean this way.)*
**How to spot it:** you can usually chop a long word into a stem + several prefixes/suffixes, and each chunk
has one job (one means "we", one means "past", etc.).
**Why it matters here:** the tool should expect to segment words into stacked morphemes and learn many small,
reusable affixes (rather than memorising whole word-forms).
**Sources:** [WALS 21A — Exponence of Selected Inflectional Formatives](https://wals.info/feature/21A) (CC-BY-4.0) · [Wikipedia: Agglutinative language](https://en.wikipedia.org/wiki/Agglutinative_language) (CC-BY-SA-4.0)

### `type:fusional`
**Plain meaning:** One ending packs several meanings at once that you can't cleanly separate. *(Spanish,
Russian.)*
**How to spot it:** a single verb ending tells you person *and* number *and* tense all together — e.g.
Spanish *-é* on *hablé* means "I" + "past" + "completed" fused into one.
**Why it matters here:** the tool should expect inflection *classes* and whole-paradigm patterns, not tidy
one-meaning-per-piece segmentation.
**Sources:** [WALS 21A — Exponence](https://wals.info/feature/21A) (CC-BY-4.0) · [Wikipedia: Fusional language](https://en.wikipedia.org/wiki/Fusional_language) (CC-BY-SA-4.0)

### `type:polysynthetic`
**Plain meaning:** A single very long word can express what other languages need a whole sentence for.
**How to spot it:** one "word" includes the verb plus its subject, object, and more.
**Why it matters here:** signals very heavy affix stacking; relevant for follow-on languages, not the four
current ones.
**Sources:** [WALS 22A — Inflectional Synthesis of the Verb](https://wals.info/feature/22A) (CC-BY-4.0) · [Wikipedia: Polysynthetic language](https://en.wikipedia.org/wiki/Polysynthetic_language) (CC-BY-SA-4.0)

---

## 2. Affix processes — where and how pieces attach

### `affix:prefix`
**Plain meaning:** A piece added to the **front** of a word changes its meaning. *(English "**un**-happy".)*
**How to spot it:** the start of the word changes while the rest stays the same.
**Sources:** [WALS 26A — Prefixing vs. Suffixing](https://wals.info/feature/26A) (CC-BY-4.0) · [Wikipedia: Prefix](https://en.wikipedia.org/wiki/Prefix) (CC-BY-SA-4.0)

### `affix:suffix`
**Plain meaning:** A piece added to the **end** of a word. *(English "cat**s**", "walk**ed**".)*
**How to spot it:** the ending changes while the start stays the same.
**Sources:** [WALS 26A — Prefixing vs. Suffixing](https://wals.info/feature/26A) (CC-BY-4.0) · [Wikipedia: Suffix](https://en.wikipedia.org/wiki/Suffix) (CC-BY-SA-4.0)

### `affix:infix`
**Plain meaning:** A piece inserted **inside** a word, splitting the root. *(Tagalog s‹um›ulat "wrote" from
sulat "write".)*
**How to spot it:** the extra piece appears in the *middle*, not at the front or end. Most languages do NOT
do this — so if yours doesn't, the tool can rule it out and search less.
**Why it matters here:** a locked "no infix" saves the tool from proposing nonsense splits.
**Sources:** [SIL Glossary: Infix](https://glossary.sil.org/term/infix) (SIL) · [Wikipedia: Infix](https://en.wikipedia.org/wiki/Infix) (CC-BY-SA-4.0)

### `affix:circumfix`
**Plain meaning:** A two-part piece that wraps a word — part on the front *and* part on the back, working as
one unit. *(Indonesian ke‑…‑an, German ge‑…‑t.)*
**How to spot it:** a front piece and an end piece always show up together for one meaning.
**Sources:** [Wikipedia: Circumfix](https://en.wikipedia.org/wiki/Circumfix) (CC-BY-SA-4.0)

### `affix:reduplication`
**Plain meaning:** Repeating all or part of a word to change its meaning — often for "many", "very", or
ongoing action. *(Indonesian buku "book" → buku-buku "books"; Tagalog repeats a syllable for tense.)*
**How to spot it:** part of the word is doubled.
**Why it matters here:** if present, the tool needs a copy-rule, not a fixed affix list.
**Sources:** [WALS 27A — Reduplication](https://wals.info/feature/27A) (CC-BY-4.0) · [Wikipedia: Reduplication](https://en.wikipedia.org/wiki/Reduplication) (CC-BY-SA-4.0)

### `affix:compounding`
**Plain meaning:** Two whole words joined to make a new one. *(English "tooth" + "brush" = "toothbrush".)*
**How to spot it:** a longer word is really two smaller meaningful words stuck together.
**Sources:** [Wikipedia: Compound (linguistics)](https://en.wikipedia.org/wiki/Compound_(linguistics)) (CC-BY-SA-4.0)

---

## 3. Sound patterns (phonology)

### `phon:vowel_harmony`
**Plain meaning:** Vowels in a word must "match" in some way, so an ending changes its vowel to fit the
stem. *(Turkish; Swahili has a milder version where some suffix vowels shift to match.)*
**How to spot it:** the same ending sounds slightly different (a different vowel) depending on the word it's
attached to.
**Why it matters here:** lets the tool write one rule that predicts the vowel instead of listing every variant.
**Sources:** [SIL Glossary: Vowel harmony](https://glossary.sil.org/term/vowel-harmony) (SIL) · [Wikipedia: Vowel harmony](https://en.wikipedia.org/wiki/Vowel_harmony) (CC-BY-SA-4.0)

### `phon:nasal_assimilation`
**Plain meaning:** A nasal sound (m/n/ng) changes to match the consonant right after it. *(Indonesian meN-:
men-, mem-, meng- before different letters — meng+kira → mengira.)*
**How to spot it:** a prefix-ending nasal is spelled/pronounced differently depending on the next sound.
**Why it matters here:** one assimilation rule replaces a pile of look-alike prefixes.
**Sources:** [SIL Glossary: Assimilatory process](https://glossary.sil.org/term/assimilatory-process) (SIL) · [Wikipedia: Assimilation (phonology)](https://en.wikipedia.org/wiki/Assimilation_(phonology)) (CC-BY-SA-4.0)

### `phon:tone`
**Plain meaning:** The pitch you say a word with changes its meaning — same letters, different "tune",
different word. *(Mandarin, Yoruba. None of the four current languages use tone.)*
**How to spot it:** two words look identical but mean different things depending on a high/low/rising pitch.
**Sources:** [WALS 13A — Tone](https://wals.info/feature/13A) (CC-BY-4.0) · [Wikipedia: Tone (linguistics)](https://en.wikipedia.org/wiki/Tone_(linguistics)) (CC-BY-SA-4.0)

---

## 4. Grammar categories words carry (the feature space)

### `feat:gender`  *(vs `feat:noun_class`)*
**Plain meaning — gender:** Nouns fall into a small number of classes (often "masculine/feminine") and the
words around them change to agree. *(Spanish el gat**o** / la gat**a**, un**a** cas**a** blanc**a**.)*
**Plain meaning — noun class:** Same idea but with *many* classes, not tied to sex, each with its own
agreement markers. *(Swahili has ~15 noun classes — m-/wa-, ki-/vi-, etc. — that ripple onto verbs and
adjectives.)*
**How to spot it:** adjectives/verbs/articles change form to "match" the noun.
**Why it matters here:** the tool must use the *right* system — Spanish gets gender (M/F), Swahili gets
noun-class, and it should never invent gender for a noun-class language or vice-versa.
**Sources:** [WALS 30A — Number of Genders](https://wals.info/feature/30A) (CC-BY-4.0) · [WALS 31A — Sex-based and Non-sex-based Gender Systems](https://wals.info/feature/31A) (CC-BY-4.0) · [Wikipedia: Noun class](https://en.wikipedia.org/wiki/Noun_class) (CC-BY-SA-4.0) · [Wikipedia: Grammatical gender](https://en.wikipedia.org/wiki/Grammatical_gender) (CC-BY-SA-4.0)

### `feat:case`
**Plain meaning:** A noun changes its ending depending on its *job* in the sentence (subject, object,
"to/of/with" it). *(Latin, Russian, Turkish. Spanish & Indonesian have essentially none on nouns.)*
**How to spot it:** the *same* noun takes different endings for "the dog" vs "to the dog" vs "of the dog".
**Why it matters here:** if your language has no case, the tool shouldn't propose case endings at all.
**Sources:** [WALS 49A — Number of Cases](https://wals.info/feature/49A) (CC-BY-4.0) · [Wikipedia: Grammatical case](https://en.wikipedia.org/wiki/Grammatical_case) (CC-BY-SA-4.0)

### `feat:tense_aspect_mood`
**Plain meaning:** Verbs mark *when* something happened (tense), *how* it unfolds — finished vs ongoing
(aspect), and *attitude* — fact vs wish vs command (mood).
**How to spot it:** the verb changes form for past/present/future, or for "was doing" vs "did".
**Sources:** [WALS 65A — Perfective/Imperfective Aspect](https://wals.info/feature/65A) (CC-BY-4.0) · [Wikipedia: Grammatical tense](https://en.wikipedia.org/wiki/Grammatical_tense) · [Wikipedia: Grammatical aspect](https://en.wikipedia.org/wiki/Grammatical_aspect) · [Wikipedia: Grammatical mood](https://en.wikipedia.org/wiki/Grammatical_mood) (all CC-BY-SA-4.0)

### `feat:person_number`
**Plain meaning:** Words mark *who* (I / you / he-she-it) and *how many* (one vs more than one), often on
the verb. *(Spanish habl**o** "I speak" vs habl**amos** "we speak".)*
**How to spot it:** the verb ending alone tells you the subject; or nouns mark singular vs plural.
**Sources:** [Wikipedia: Grammatical number](https://en.wikipedia.org/wiki/Grammatical_number) · [Wikipedia: Grammatical person](https://en.wikipedia.org/wiki/Grammatical_person) (CC-BY-SA-4.0)

### `feat:definiteness`
**Plain meaning:** The language marks "a/some" (new) vs "the" (already-known). *(English a/the; many
languages use no word at all, or an ending.)*
**How to spot it:** there's a little word or ending meaning "the specific one we both know".
**Sources:** [WALS 37A — Definite Articles](https://wals.info/feature/37A) (CC-BY-4.0) · [Wikipedia: Definiteness](https://en.wikipedia.org/wiki/Definiteness) (CC-BY-SA-4.0)

### `feat:agreement`  *(concord)*
**Plain meaning:** Words must "match" each other — a verb or adjective changes to agree with its noun's
person/number/class. *(Swahili: the noun class shows up again on the verb and the adjective.)*
**How to spot it:** changing the noun forces other words in the phrase to change too.
**Sources:** [Wikipedia: Agreement (linguistics)](https://en.wikipedia.org/wiki/Agreement_(linguistics)) (CC-BY-SA-4.0)

### `feat:word_order`
**Plain meaning:** The usual order of subject, verb, and object. *(English is Subject-Verb-Object: "Mary
sees the dog".)*
**How to spot it:** in a plain statement, does the doer, the action, or the thing-acted-on come first?
**Sources:** [WALS 81A — Order of Subject, Object and Verb](https://wals.info/feature/81A) (CC-BY-4.0) · [Wikipedia: Word order](https://en.wikipedia.org/wiki/Word_order) (CC-BY-SA-4.0)

---

## 5. Other building blocks the tool reasons about

### `morph:clitic`
**Plain meaning:** A little word that leans on its neighbour and attaches to it like an ending. *(Spanish
dá**melo** = "give"+"me"+"it"; English "I'**m**", "they'**re**".)*
**How to spot it:** a pronoun or particle that can't stand alone and sticks onto another word.
**Sources:** [SIL Glossary: Clitic](https://glossary.sil.org/term/clitic) (SIL) · [Wikipedia: Clitic](https://en.wikipedia.org/wiki/Clitic) (CC-BY-SA-4.0)

### `morph:derivation` *(vs inflection)*
**Plain meaning:** **Derivation** makes a *new word* (often a new part of speech) — "teach" → "teach**er**".
**Inflection** just changes the *form* of the same word — "teach" → "teach**es**".
**How to spot it:** does the piece create a different dictionary word (derivation) or just a grammatical
variant of the same one (inflection)?
**Why it matters here:** they're stored differently (a derived word gets its own entry; an inflected form is
generated by rule).
**Sources:** [SIL Glossary: Derivation](https://glossary.sil.org/term/derivation) (SIL) · [Wikipedia: Morphological derivation](https://en.wikipedia.org/wiki/Morphological_derivation) (CC-BY-SA-4.0)

### `morph:allomorph`
**Plain meaning:** The *same* piece that shows up in more than one shape depending on its surroundings.
*(English plural -s sounds like "s" in "cats" but "z" in "dogs" — one ending, two shapes.)*
**How to spot it:** an ending or prefix has predictable variant forms.
**Sources:** [SIL Glossary: Allomorph](https://glossary.sil.org/term/allomorph) (SIL) · [Wikipedia: Allomorph](https://en.wikipedia.org/wiki/Allomorph) (CC-BY-SA-4.0)

### `morph:suppletion`
**Plain meaning:** A word's forms are completely different from each other, not just an ending swap. *(English
"go/went", "good/better"; Spanish "ir/fui".)*
**How to spot it:** the past or plural looks nothing like the base.
**Sources:** [Wikipedia: Suppletion](https://en.wikipedia.org/wiki/Suppletion) (CC-BY-SA-4.0)

### `morph:archiphoneme`
**Plain meaning:** A single underlying form that *covers* several surface variants which a rule then
adjusts. (This is the tidy way to store nasal-assimilation prefixes as one item — see
`phon:nasal_assimilation`.)
**How to spot it:** technical — the tool proposes it; the reviewer mainly judges whether the variants really
share one meaning.
**Sources:** [Wikipedia: Archiphoneme](https://en.wikipedia.org/wiki/Archiphoneme) (CC-BY-SA-4.0)
