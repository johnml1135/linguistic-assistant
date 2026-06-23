## ADDED Requirements

### Requirement: A fixed, versioned catalog of the 12 master switches
The system SHALL define a fixed, versioned catalog of the 12 typological master switches, each entry
declaring: a stable `id`, a non-linguist **presentation** string (the question/claim), its **contours**
(the allowed values), the **corpus evidence** to assemble, and the **downstream constraint** it sets. The
12 are: synthesis, affix_polarity, infixation, reduplication, vowel_harmony, nasal_assimilation, tone,
gender_or_noun_class, case, tam_locus, agreement_head_marking, articles.

#### Scenario: The catalog enumerates exactly the 12 switches
- **WHEN** the catalog is loaded
- **THEN** it contains the 12 switches above, each with id / presentation / contours / evidence-spec / constraint

#### Scenario: Each switch declares its contours
- **WHEN** a switch is read (e.g. `synthesis`)
- **THEN** its allowed values are enumerated (e.g. isolating | agglutinative | fusional | polysynthetic)

### Requirement: Each switch declares the corpus evidence to assemble
Each catalog entry SHALL declare what corpus data to assemble so a speaker can judge the claim (e.g. for
infixation: internal-insertion minimal pairs + the recurring internal chunks + the count of distinct stems
each chunk appears in). The evidence specification SHALL name the source pieces (cycle affixes, phonology
induction, morpheme alignment, orthography, corpus statistics).

#### Scenario: Infixation declares its evidence
- **WHEN** the `infixation` switch is presented
- **THEN** its evidence includes internal-insertion minimal pairs, the top internal chunks, and the
  distinct-stem count per chunk

### Requirement: Each switch declares its downstream constraint
Each catalog entry SHALL declare the constraint it sets on later analysis (what it enables/prunes), so the
configuration layer can apply it (e.g. infixation=absent prunes infix hypotheses; gender vs noun-class sets
the FsFeatStruc dimension).

#### Scenario: A switch maps to a downstream constraint
- **WHEN** `gender_or_noun_class` is resolved to noun-class
- **THEN** the declared constraint selects the noun-class feature dimension (never gender) for later analysis

### Requirement: The catalog is additive-stable
The catalog SHALL be versioned and SHALL NOT silently drop or renumber switches; additional switches (e.g.
word order, clitics) SHALL be added as new entries, not by mutating the core 12.

#### Scenario: Adding a switch does not renumber the core
- **WHEN** a follow-on switch (word_order) is added
- **THEN** the existing 12 ids are unchanged and the catalog version increments
