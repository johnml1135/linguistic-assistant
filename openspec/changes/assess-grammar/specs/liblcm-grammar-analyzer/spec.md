## ADDED Requirements

The C# phase: compute the **same** measure definitions over **LibLCM** objects (a real FieldWorks
project) so the assessment runs on production data, not only on golden/`hc` inputs. The measures are
defined once in `assess-grammar-metrics`; this capability is an alternate *implementation surface*, not
a new set of metrics. Aligns with the maturity-stages plan (core measures as a packable .NET library;
Python defines and validates against gold first).

### Requirement: Single measure definition, two implementations
The C# analyzer SHALL compute the measures of `assess-grammar-metrics` using the identical formulas and
emit the identical scorecard JSON schema as the Python implementation; the definitions in
`assess-grammar-metrics` are authoritative for both. A shared golden fixture SHALL be used to assert the
two implementations agree on the same inputs.

#### Scenario: Parity on a shared fixture
- **WHEN** the Python and C# analyzers score the same grammar+corpus fixture
- **THEN** the two scorecards match on every measure within a documented tolerance (exact for counts)

### Requirement: Read-only LibLCM analysis (no DB writes)
The analyzer SHALL read a FieldWorks/LibLCM project to enumerate the constructs (lexical entries,
allomorphs, MSAs, inflection features, phonological rules, natural classes, affix templates, ad-hoc
rules) needed for the size, generalization, dead-construct, and productivity measures, and SHALL NOT
write to `.fwdata` or modify the project (per project scope: emit assessments/change-sets, not DB
writes).

#### Scenario: Analysis leaves the project unchanged
- **WHEN** the analyzer runs over a FieldWorks project
- **THEN** it produces a scorecard and the project files are unmodified

### Requirement: Phase ordering
Python SHALL define and validate the measures against the golden set first; the C# analyzer SHALL be
built only after the Python measure definitions are stable, and SHALL track the same spec version. Until
then this capability is documented-but-deferred.

#### Scenario: C# tracks the validated Python definitions
- **WHEN** the C# analyzer is implemented
- **THEN** it implements the then-current `assess-grammar-metrics` requirements and references the spec version
