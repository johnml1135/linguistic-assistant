# ParseGym coverage report

**600 scenarios** across {'ind': 200, 'spa': 200, 'swh': 100, 'tgl': 100}.

## What it assesses

- **lexical_bootstrapping** (200) — recognise an unknown word and decide add-root / elicit / defer.
- **sense_disambiguation** (200) — one form, several senses/POS — choose the right meaning or the right question.
- **irregular_morphology** (100) — see that a form belongs to a known lemma despite an irregular stem (allomorph).
- **segmentation_precision** (100) — reject spurious over-segmentation; keep only the licit analysis.

## Difficulty rubric

- **medium** (347) — evidence points one way but needs a judgement call (which sense, which split).
- **hard** (180) — evidence is thin or conflicting; the answer is often 'ask the speaker' or 'I don't know'.
- **easy** (73) — the reference gives a confident answer; one obvious move.

## Distributions
- stage: {'cold_start': 200, 'homophone': 200, 'hidden_rule': 100, 'overparse': 100}
- phase: {'late': 400, 'early': 200}
- answer kind: {'ask_speaker': 409, 'fix': 143, 'unknown': 48}
- skills: {'parsegym_resolve': 600, 'gloss_reference': 400, 'propose_rule': 200}

## LLM-readiness
- self-contained: 600/600
- prompt size: ~1088 tokens median, 5637 chars max
