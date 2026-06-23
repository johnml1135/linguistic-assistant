## Context

`profile.py` already holds a per-language profile (seeded from WALS/Grambank) that gates the hypothesis
space; `profile_detect.py` already detects ~10 switches from the corpus and cross-checks the seed;
`feature_explanations.py` holds non-linguist explanations. This change pins those into a **fixed 12-switch
catalog**, adds the productivity gate, and makes the confirmed switches the recorded configuration every
later step reads. The guiding shape (from the user): *detect → present as a falsifiable claim with evidence
→ cross-check the internet → record → constrain everything after.*

## Goals / Non-Goals

**Goals:** a stable catalog of 12 switches; corpus detection with evidence + a productivity gate;
internet cross-check; a non-linguist confirmation surface; the decision recorded in config and **binding**
on all successive analysis.
**Non-Goals:** perfect classification (the human confirms); inducing syntax; covering every WALS feature
(12 high-leverage switches, not 192).

## D1. The 12 master switches (the catalog)

Each switch defines: **Present** (the plain-language claim shown to a speaker), **Contours** (allowed
values), **Evidence** (corpus data to assemble so the speaker can judge), **Constrains** (what it
enables/prunes downstream), **Detector** (the pieces + current status).

### 1. Morphological synthesis
- **Present:** "How are words built — mostly separate small words (isolating), a stem plus clearly
  separable pieces (agglutinative), or endings that fuse several meanings at once (fusional)?"
- **Contours:** `isolating | agglutinative | fusional | polysynthetic`
- **Evidence:** type:token ratio; mean morphemes/word (HC/cycle); induced-affix count; the longest frequent
  words shown segmented.
- **Constrains:** affix-stacking depth; inflection-classes (fusional) vs per-morpheme glossing (agglut.).
- **Detector:** `profile_detect.detect_synthesis` (TTR + affix inventory). ✅

### 2. Affix polarity
- **Present:** "Do the meaning-changing pieces attach mostly to the FRONT of a word, the END, or both?"
- **Contours:** `prefixing | suffixing | both | little-affixation`
- **Evidence:** induced affixes by side, frequency-weighted; 3–5 base→derived examples each side.
- **Constrains:** where the segmenter/search looks first.
- **Detector:** `detect_affix_polarity` (cycle affixes). ✅

### 3. Infixation
- **Present:** "Does your language ever insert a piece INSIDE a word, splitting the root (Tagalog
  s‹um›ulat 'wrote' from sulat 'write')?"
- **Contours:** `present | absent`
- **Evidence:** internal-insertion minimal pairs (base + base-with-internal-chunk both attested); the top
  recurring internal chunks with counts + examples; **how many distinct stems** each chunk appears in.
- **Constrains:** turns infix hypotheses on/off (a hard prune when absent).
- **Detector:** `detect_infixation` + **productivity gate** (needs many distinct stems — kills swh `lakini`). ✅/⚠

### 4. Reduplication
- **Present:** "Do you repeat all or part of a word to change its meaning (buku-buku 'books')?"
- **Contours:** `absent | partial | full | both`
- **Evidence:** word types with a doubled syllable/CV or hyphenated doubling; counts; examples; distinct-stem productivity.
- **Constrains:** turns the copy-rule on/off.
- **Detector:** `detect_reduplication` + productivity gate. ✅/⚠

### 5. Vowel harmony
- **Present:** "Do vowels in a word have to 'match', so an ending changes its vowel to fit the stem?"
- **Contours:** `absent | present` (+ type: front/back, height, rounding)
- **Evidence:** suffix-vowel alternations conditioned by stem vowel class, with support counts + example sets.
- **Constrains:** one harmony rule vs listing allomorph variants.
- **Detector:** `golden/reference/phonology_induce.vowel_harmony`. ✅

### 6. Nasal / place assimilation
- **Present:** "Does a nasal (m/n/ng) at the end of a prefix change to match the next consonant
  (meN- → mem/men/meng)?"
- **Contours:** `absent | present`
- **Evidence:** prefix-final nasal alternations conditioned by following-consonant place; example families.
- **Constrains:** archiphoneme-collapse (one underlying form + rule) vs an allomorph list.
- **Detector:** `phonology_induce.nasal_assimilation`. ✅

### 7. Tone
- **Present:** "Does the pitch you say a word with change its meaning (same letters, different 'tune')?"
- **Contours:** `absent | simple | complex`
- **Evidence:** tone diacritics in the orthography (absence in a plain Latin NT → likely none); minimal-pair check if marked.
- **Constrains:** whether pitch is contrastive (mostly informational for the 4 non-tonal targets).
- **Detector:** `detect_tone` (orthography). ✅

### 8. Gender vs noun-class
- **Present:** "Do nouns fall into classes that make nearby words agree — a few (like masculine/feminine),
  many (like Bantu noun classes), or none?"
- **Contours:** `none | gender(N) | noun-class(N)` (with an estimated class count)
- **Evidence:** systematic singular/plural prefix-pairs (swh m-/wa-, ki-/vi-); modifiers/verbs whose form
  co-varies with the noun (concord); the candidate class count.
- **Constrains:** the FsFeatStruc dimension (gender ≠ noun-class — never invent gender for a noun-class
  language); the concord checks.
- **Detector:** prefix-pair clustering + concord covariance. ⚠ (partial — needs build-out)

### 9. Case
- **Present:** "Does a noun change its ending depending on its job in the sentence (subject / object /
  'to' it / 'of' it)?"
- **Contours:** `absent | present(N cases)`
- **Evidence:** do nouns take role-correlated suffix alternations (vs an invariant noun + word order)?
  absence is itself the evidence.
- **Constrains:** whether to propose case endings at all.
- **Detector:** noun-suffix-by-role covariance (or attested absence). ⚠ (partial)

### 10. TAM locus (tense / aspect / mood)
- **Present:** "Where is tense/aspect marked — a prefix on the verb, an ending on the verb, or a separate
  word before it?"
- **Contours:** `verb-prefix | verb-suffix | auxiliary/particle | mixed | unmarked`
- **Evidence:** morpheme-alignment of verb affixes to source tense words (will / -ed / have); which side
  they sit on; examples (swh na-/li-/me- = present/past/perfect).
- **Constrains:** where the grammar looks for TAM morphemes.
- **Detector:** `align/morph_align_hc` markers (cached). ✅ (swh)

### 11. Person/number agreement (head-marking)
- **Present:** "Does the verb itself carry who-did-it (and to-whom) — like a prefix meaning 'I' / 'you' /
  'we'?"
- **Contours:** `none | subject | subject+object`
- **Evidence:** morpheme-alignment of verb-edge morphemes to source pronouns (I/you/we); counts; examples
  (swh ni-/u-/tu- ; nili/nime/nina).
- **Constrains:** subject/object agreement affixes; whether concord is head-marked.
- **Detector:** `morph_align_hc` markers. ✅ (swh: 87)

### 12. Articles / definiteness
- **Present:** "Is there a word or ending for 'the' (already-known) vs 'a' (new)?"
- **Contours:** `none | definite-only | indefinite-only | both`
- **Evidence:** a high-frequency function word/affix aligning to 'the'/'a' across the corpus — or **nothing**
  aligning (swh has no articles → nothing aligns to 'the').
- **Constrains:** whether to model articles at all.
- **Detector:** alignment to the/a. ✅

> **Additional switches (follow-on contours, not in the core 12):** basic **word order** (SVO/SOV/VSO — via
> aligning S/V/O to the source backbone) and **clitics** (function words that lean/attach — spa dámelo).
> Documented here so they aren't lost; added once the core 12 are stable.

## D2. Detection is productivity-gated (kills coincidental false positives)
A real morphological process recurs across **many distinct stems**; a coincidental substring does not. Each
detector (esp. infix/reduplication) SHALL apply the **Tolerance Principle** productivity test from
`research/assess/`: a chunk is only proposed `present` if it appears in ≥ the tolerance threshold of
distinct stems. This is what removes swh `lakini`→"`-ak-` infix" and spa `dejando`→"`-ej-` infix".

## D3. Internet cross-check (second opinion, not source)
Each detected value is compared to the WALS/Grambank seed (`profile._seed`). **Agreement** raises
confidence; **conflict** is flagged for the human (and recorded), never silently resolved either way — the
detector can be wrong (swh `lakini`) and the seed can be wrong/too-coarse (spa nasal assimilation).

## D4. Presentation = a falsifiable, non-linguist claim
Each switch is shown as: the **Present** question, the system's **current best guess** + **confidence**,
the **evidence** assembled from the corpus (counts + concrete examples the speaker recognizes), and the
**contour options** to pick from. The speaker confirms or corrects — the answer space is the contours plus
"I don't know" (defer). This rides the existing `deferrals/` review surface as a Phase-0 "switch-
confirmation" item, distinct from per-word tickets.

## D5. Recorded in configuration, binding on all successive steps (the load-bearing requirement)
A confirmed switch is written to `golden_sets/<pair>/profile.json` with `value / confidence / provenance
(detected | internet | linguist) / evidence / locked`. **Every successive step SHALL read the profile and
be constrained by it:**
- A `locked` switch is a **hard prune** — the disallowed mechanism is never enumerated (no Spanish infix
  hypothesis, no gender feature for a noun-class language).
- An unconfirmed/uncertain switch is a **soft prior** — deprioritized, still probe-eligible (D18 of the
  deferral-packages design: toggle + ΔMDL).
- The taxonomy/segmenter/induction/gold-raise already consult `profile.allowed_affix_kinds()` etc.; this
  change makes the *source* of those settings the detected+confirmed switches.

## Risks / Trade-offs
- **Detector wrong, human rubber-stamps** → always show the evidence + the internet cross-check so a wrong
  guess is visible; default uncertain switches to soft (not locked).
- **Productivity threshold mis-set** → expose it; calibrate on the four known languages (spa/ind/tgl/swh)
  where the right answers are known.
- **Over-constraining** → a locked switch can be wrong (a thin corpus missing a rare process); locking
  requires human confirmation, and the profile is editable + the feature is probe-falsifiable.

## Migration Plan
1. Pin the catalog (`switches.py`) + the presentation text; add the productivity gate to the detectors.
2. Add the gender/noun-class + case detectors (currently partial).
3. Write confirmed switches → profile with provenance; assert successive steps read them (a test).
4. Add the Phase-0 switch-confirmation review item; run on spa/ind/tgl/swh and record the (human-confirmed)
   switch sets as the languages' configuration.

## Open Questions
- Concord detection for noun-class without a parse: prefix-pair clustering may over/under-count classes —
  start with "≥K systematic sg/pl pairs ⇒ noun-class present," refine the count later.
- Should a confirmed switch auto-lock, or stay soft until a second confirmation? Propose: human confirm =
  lock; detector-only = soft.
