# audio/

Optional **audio evidence add-on** for the research pipeline. It is deliberately secondary to the
existing text/parallel workflow: no audio is assumed, no `audio/*` first-class change-set family is
introduced, and Allosaurus output is stored as review-only evidence rather than parser input.

## Scope

- Targets: **Turkish** (`tur`) and **Hungarian** (`hun`) only
- Purpose: enrich lexical work with opt-in sample words, pronunciation evidence, conservative
  orthography / misspelling alerts, and triangulation summaries
- Non-goals: Finnish, automatic lexicon mutation, direct HC phoneme-feature updates, mandatory audio
  processing during the base eBible build

## Install

```bash
cd research
uv sync --extra audio
```

If Allosaurus is not installed, the workflow still runs and records that recognition was unavailable.

## Inputs

### Sample-word manifest

```json
{
  "samples": [
    {"target_key": "tur", "word": "tanrı", "gloss": "god"},
    {"target_key": "hun", "word": "isten", "note": "track this through enrichment"}
  ]
}
```

### Audio catalog

```json
{
  "entries": [
    {
      "target_key": "tur",
      "source_id": "ytc-local",
      "local_path": "C:/audio/tur/mat1.wav",
      "text_anchor": "MAT 1:1",
      "word": "tanrı",
      "segmentation": "chapter",
      "license_note": "operator supplied"
    }
  ]
}
```

Only entries that provide `local_path`, `text_anchor`, and `word` are considered ready for optional
recognition. Other catalog entries still contribute availability/status metadata.

## Run

```bash
cd research
python audio/run.py \
  --pair-dir golden/_sources/ebible/eng-engwebp__tur-turytc \
  --target tur \
  --samples path/to/samples.json \
  --catalog path/to/catalog.json \
  --timestamps
```

## Outputs

Under the chosen pair directory's `audio/` folder:

- `samples.resolved.json` — sample words with matched/unresolved status
- `catalog.status.json` — explicit source availability and recognition readiness
- `phone_evidence.json` — raw Allosaurus runs and any successful evidence records
- `reports.json` — pronunciation candidates, orthography alerts, triangulation summaries

## Verification

```bash
cd research
python audio/tests_smoke.py
```