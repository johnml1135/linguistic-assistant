## 1. Package and contract scaffolding

- [x] 1.1 Create the `research/audio/` package with data models for audio catalogs, sample-word
  manifests, evidence records, and derived report records.
- [x] 1.2 Add optional audio dependencies and command documentation in the research docs without making
  them part of the default install path.

## 2. Sample-word and catalog ingestion

- [x] 2.1 Implement loaders and validators for Turkish/Hungarian audio catalogs and opt-in sample-word
  manifests.
- [x] 2.2 Implement pair-output resolution that persists sample words under the existing eBible pair
  directory with matched or unresolved status.

## 3. Optional Allosaurus evidence generation

- [x] 3.1 Implement an Allosaurus wrapper that records runtime provenance, supports optional timestamp
  capture, and degrades gracefully when the runtime or audio asset is unavailable.
- [x] 3.2 Add fixture-based smoke tests for no-audio, no-Allosaurus, and successful raw evidence
  capture paths.

## 4. Derived enrichment reports and workflow docs

- [x] 4.1 Implement derived pronunciation-candidate, orthography-alert, and triangulation-report
  outputs from pair data plus optional phone evidence.
- [x] 4.2 Document the add-on workflow in repo docs, including its Turkish/Hungarian scope, optional
  sample-word path, and explicit non-first-class status.