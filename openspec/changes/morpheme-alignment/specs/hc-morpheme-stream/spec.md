## ADDED Requirements

### Requirement: HC-parsed words become a verified, marked morpheme stream
The system SHALL parse each target word with the gold Hermit Crab grammar and convert the analysis into an
ordered morpheme list `[(form, gloss, type, slot)]` by mapping each gloss in HC's (reliable) gloss line
back to the grammar construct that produced it (a `LexEntry` root or an `Affix`, carrying its kind and
slot). The morph *forms* SHALL be recovered from the matched grammar constructs (not from HC's corrupted
echoed morph forms).

#### Scenario: A parsed word yields ordered marked morphemes
- **WHEN** the gold grammar parses a word into a root plus affixes
- **THEN** the system emits the morphemes in order, each with its form (from the grammar construct), its
  HC gloss, its type (root/prefix/suffix/infix), and its slot

#### Scenario: Morph forms come from the grammar, not HC's echoed forms
- **WHEN** HC's echoed morph forms are corrupted by the reindexing bug
- **THEN** the recovered morpheme forms still match the grammar constructs' forms (the gloss line is the
  reliable index, the construct supplies the form)

### Requirement: Unparsed words are kept whole and flagged
A word the grammar cannot parse SHALL be emitted as a single morpheme `(form=word, gloss="?",
type="word", unparsed=true)` rather than force-segmented, so its word-level alignment is preserved and
downstream never treats it as analysed.

#### Scenario: No-parse word is flagged, not split
- **WHEN** the grammar produces no analysis for a word
- **THEN** the stream contains one `word`-type morpheme flagged `unparsed`, not a guessed segmentation

### Requirement: Ambiguity is resolved explicitly
When a word has several analyses, the system SHALL select the analysis matching the gold wordform analysis
if one exists, else the first, and SHALL flag the morphemes `ambiguous` when more than one analysis was
available.

#### Scenario: Ambiguous word records the flag
- **WHEN** HC returns more than one analysis for a word
- **THEN** the chosen morphemes are flagged `ambiguous` and the gold-matching analysis is preferred

### Requirement: Per-morpheme back-links
Every morpheme in the stream SHALL carry a back-link `(verse_ref, word_idx, morph_idx)` so an alignment
computed over the flattened morpheme stream maps back to the exact morpheme.

#### Scenario: A morpheme maps back to its source position
- **WHEN** the stream is flattened for alignment
- **THEN** each morpheme can be traced to its verse, word, and position within the word
