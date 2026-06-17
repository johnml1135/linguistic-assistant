## ADDED Requirements

### Requirement: Hermit Crab → Apertium stream adapter
The system SHALL render Hermit Crab analyses of vernacular tokens in **Apertium stream format**
(`^surface/lemma<tag>…$`), so the vernacular side participates in the bidix/FLExTrans world *through HC*
— without introducing a second vernacular morphology. Tags SHALL be mapped via the tag crosswalk.

#### Scenario: Emit an analyzed token
- **WHEN** HC analyzes a vernacular surface form to a lemma + features
- **THEN** the adapter emits `^surface/lemma<…tags…>$` with features mapped to Apertium `sdef` tags via
  the crosswalk

### Requirement: Versioned tag crosswalk
The system SHALL maintain a versioned crosswalk between the project's POS / inflection-feature
inventory and Apertium `sdef` tags, used by both the stream adapter and `.dix` export/import. The
crosswalk SHALL be an explicit, reviewable contract (not inferred per run).

#### Scenario: Round-trip a tag through the crosswalk
- **WHEN** a project feature is exported to an Apertium tag and later imported back
- **THEN** it maps to the same project feature (lossless for crosswalked tags; uncrosswalked tags are
  reported, not silently dropped)

### Requirement: Apertium .dix export (derived artifact)
The system SHALL generate an Apertium **bidix `.dix`** from the `bilingual/*` sense-link tier, and
optionally a vernacular **monodix** from the lexicon + HC, as **derived, content-addressed build
artifacts** under an exports path. It SHALL NOT generate `.t1x/.t2x/.t3x` transfer rules.

#### Scenario: Generate a bidix from sense links
- **WHEN** export is run
- **THEN** a valid Apertium bidix is written whose `<l>`/`<r>` lemma+tag pairs correspond exactly to the
  sense links, and no transfer-rule files are produced

### Requirement: FLExTrans direct import/export
The system SHALL import a FLExTrans `bilingual.dix` and its sense links into the `bilingual/*` tier, and
export the same artifacts in the layout FLExTrans consumes — covering **bidix + sense links + the
vernacular lexicon/monolingual data only** (not transfer rules). Import SHALL be lossless for data that
maps through the crosswalk and SHALL report anything it cannot map.

#### Scenario: Round-trip a FLExTrans bilingual lexicon
- **WHEN** a FLExTrans `bilingual.dix` is imported and then re-exported
- **THEN** the re-exported bidix is equivalent to the original for all crosswalked entries, and any
  unmappable entries are listed rather than dropped

#### Scenario: Transfer rules are left to FLExTrans
- **WHEN** a FLExTrans project also contains `.t1x/.t2x/.t3x` files
- **THEN** import/export ignores them (out of scope), touching only bidix / sense links / lexicon data

### Requirement: Apertium binary is an optional interop dependency
Core alignment and `.dix` *format* read/write SHALL work without the native Apertium toolchain. The
Apertium binary (`lttoolbox`/`lt-proc`) SHALL be required only for using off-the-shelf
reference-language analyzers or compiling `.dix` to FSTs, and its absence SHALL degrade gracefully with
a clear message — never a hard failure of the core loop.

#### Scenario: Run without the toolchain
- **WHEN** `lttoolbox` is not installed
- **THEN** sense-link editing, bidix `.dix` read/write, the HC→stream adapter, and the fixture-based
  reference finder all still work; only off-the-shelf-analyzer features are reported unavailable
