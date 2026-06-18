# audio/

Optional **audio evidence add-on** for the research pipeline. It is deliberately secondary to the
existing text/parallel workflow: no audio is assumed, no `audio/*` first-class change-set family is
introduced, and Allosaurus output is stored as review-only evidence rather than parser input.

The add-on now covers both whole-pair enrichment and sample-driven word-candidate localization plus
preview playback.

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
If `faster-whisper` is not installed, candidate localization still runs and records that the backend
was unavailable.

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

For candidate localization, only `local_path` and `text_anchor` are required. In v1 preview playback
expects local 16-bit PCM WAV assets.

## Run

```bash
cd research
python audio/run.py \
  --pair-dir golden/_sources/ebible/eng-engwebp__tur-turytc \
  --target tur \
  --samples path/to/samples.json \
  --catalog path/to/catalog.json \
  --timestamps

python -m audio.candidates locate \
  --pair-dir golden/_sources/ebible/eng-engwebp__tur-turytc \
  --target tur \
  --samples path/to/samples.json \
  --catalog path/to/catalog.json \
  --stem tanrı \
  --phone-cues

python -m audio.candidates play \
  --artifact golden/_sources/ebible/eng-engwebp__tur-turytc/audio/word_occurrences.json \
  --occurrence tanrı:ytc-local:1:1100
```

## Outputs

Under the chosen pair directory's `audio/` folder:

- `samples.resolved.json` — sample words with matched/unresolved status
- `catalog.status.json` — explicit source availability and recognition readiness
- `word_occurrences.json` — ranked candidate occurrences with stored offsets, context, provenance, and optional review-only phone cues
- `phone_evidence.json` — raw Allosaurus runs and any successful evidence records
- `reports.json` — pronunciation candidates, orthography alerts, triangulation summaries

Preview playback renders a temporary faded WAV from a stored occurrence and either plays it locally or
returns a playback-unavailable status plus the preview path.

## Feature grounding (`features.py`)

Phase 2 of the `phonology-induction-loop` change. Review-only, provenance-bearing, and decoupled from
`research/cycle/` (distribution facts are passed in as plain data):

- `map_phones_to_features` — maps recognized vowel phones to distinctive features ([±back], [±round],
  [±high]); unknown phones are skipped.
- `confirm_conditioning` — confirms or refutes a harmony family's hypothesized conditioning feature
  from per-member phone evidence; conflicts are flagged, never auto-applied.
- `triangulate_family` — combines orthography + distribution + optional phones into one agreement
  summary; with no audio it still emits a distribution-only summary.

Stem-aware sample resolution (`samples.py`) optionally matches a sample word's inflected occurrences via
an induced-stem list, preserving the matched/unresolved contract.

## Pronunciation promotion & consistency (`promotion.py`)

Phases 3–4 of the `phonology-induction-loop` change — the deliberately-last, human-gated tail:

- `promote_pronunciations` — emits `lexical.pronunciation.create` change-set ops **only** for
  analyst-confirmed candidates (form per writing system, rationale, confidence, provenance); validated
  against `research/proposal/change_set.py`. Unconfirmed candidates emit nothing.
- `check_recorded_consistency` — flags an HC-generated surface that disagrees with a recorded
  pronunciation (reviewable signal, never an automatic edit).
- `feature_mismatch_count` / `compare_generated_to_phones` — the phone↔grapheme vowel-feature distance
  metric + threshold; a generated surface that diverges from observed phones beyond the threshold is a
  review-only consistency flag. Producing the generated surface needs the `hc.exe` generate path; the
  comparison and metric are pure and offline-tested.

## Verification

```bash
cd research
python audio/tests_smoke.py
```