# data_prep/

One-time extraction of gold morphology/phonology data from a real FieldWorks project.

## Why this is isolated

`flexlibs` is **Windows-only and requires a FieldWorks install** (Python.NET → LibLCM).
That collides with the project's cross-platform, no-FLEx-dependency rule for the core
loop. So extraction is a **one-time data-prep step run on a Windows box** that emits
**portable JSON**; everything downstream (the harness, benchmarks) consumes that JSON
and stays cross-platform. Nothing here is imported by the core loop.

Install the extra only on the Windows machine: `pip install -e ".[data-prep]"`.

## What we extract

`flexlibs` / [`FlexToolsMCP`](https://github.com/MattGyverLee/FlexToolsMCP) can read
interlinear text with **gold morpheme segmentation and glosses** (the `Texts & Words`
domain; `MoStemMsa` / `MoInflAffMsa`; allomorph environments). Target output, one record
per attested wordform:

```json
{
  "word": "ninakupenda",
  "segmentation": ["ni", "na", "ku", "penda"],
  "gloss": ["1SG.SUBJ", "PRES", "2SG.OBJ", "love"],
  "language": "swh",
  "provenance": {"project": "...", "text_id": "...", "ref": "..."}
}
```

TODO:
- [ ] Extraction script (flexlibs) → the record schema above.
- [ ] Provenance capture (project / text / reference) for traceability.
- [ ] Split into eval-gold vs. allowed-for-data-gen (firewall — see `../data_gen/`).
