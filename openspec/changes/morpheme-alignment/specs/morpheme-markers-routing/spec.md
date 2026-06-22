## ADDED Requirements

### Requirement: Each morpheme carries a full marker set
The system SHALL assemble, per morpheme, a marker record carrying: `form`, `type`
(root|prefix|suffix|infix|clitic|word), `slot`, `hc_gloss` (the grammar's stored gloss), `source_tokens`
(the THOT pivot links + probability), `features` (the FsFeatStruc bundle for an affix, from the gold
affix→function table), `pos` (for roots), a `confidence`, and `agrees_with_hc`.

#### Scenario: A suffix marker carries its function
- **WHEN** an object-marker suffix aligns to the source word "you"
- **THEN** its marker records type=suffix, slot, hc_gloss, source_tokens=["you"], the feature bundle
  (e.g. 2SG.OBJ) from the affix→function table, and a confidence

#### Scenario: A root marker carries its sense + POS
- **WHEN** a root aligns to a content source word
- **THEN** its marker records type=root, the aligned source word as its context sense, its POS, and a confidence

### Requirement: Accept only on two concurring signals
A marker SHALL be accepted (used to raise the gold) only when the THOT link is high-probability AND it
agrees with the HC stored gloss (the pivot source corroborates the gloss, or — for an affix — matches the
grammatical word its function predicts). An accepted marker SHALL emit a confidence-routed op into the
`deltas/` ledger (raise an affix gloss or a root sense); the gold SHALL be written only through that path.

#### Scenario: Concurring signals raise the gold
- **WHEN** THOT links a morpheme with high probability and it agrees with the HC gloss
- **THEN** a `deltas/` op is emitted to raise the corresponding affix gloss / root sense

### Requirement: Defer on disagreement or weak evidence — never a silent wrong marker
When the signals do not concur (low probability, empty alignment, or pivot⊥HC-gloss), the system SHALL
defer: emit a deferral record (consumed by the `deferrals/` ticket pipeline) rather than accept a marker.
The system SHALL NOT emit a confident marker on a single weak signal.

#### Scenario: Disagreement becomes a deferral
- **WHEN** the THOT pivot for a morpheme contradicts its HC stored gloss
- **THEN** no gold-raising op is emitted and a deferral record is produced for review

#### Scenario: Weak alignment defers
- **WHEN** a morpheme's best alignment probability is below the accept threshold
- **THEN** the marker is deferred, not accepted

### Requirement: Accepted affix-function markers are HC-verified
Before an accepted affix-function marker raises the gold, the system SHALL (by default) round-trip it
through the gold grammar — confirming the affix gloss re-glosses the attested forms with no regression —
and SHALL downgrade to a deferral any marker that fails the round-trip.

#### Scenario: A marker that fails round-trip is downgraded
- **WHEN** an accepted affix gloss does not round-trip through HC
- **THEN** it is not applied to the gold and is deferred instead
