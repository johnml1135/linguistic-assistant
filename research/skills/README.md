# skills/

Portable skill assets: the prompts and JSON tool/output **contracts** that drive the
linguistic tasks, authored model-agnostically (markdown + JSON Schema, no provider SDK
calls).

These are the **durable artifacts** of the research track. The Python harness is
throwaway experimentation; these assets — and the `LLMClient` interface in `../harness/`
— are what carry forward into the C# product runtime. Authoring them here, against a
swappable endpoint, is how we keep "works on Opus" from quietly becoming "only works on
Opus."

Each skill should be self-contained enough to evaluate on its own: an instruction block,
the input/output JSON contract, and a few-shot exemplar set kept separate from any eval
gold (firewall).

Skills:
- `gloss_reference.md` — read IGT and fill the missing morpheme+gloss.
- `parsegym_resolve.md` — resolve a ParseGym scenario: choose `fix` (edit, in LibLCM/HC
  terms) vs `unknown` ("I don't know") vs `ask_speaker` (which scripted question). This is
  the triage skill below, and the judgment the `../parsegym/` suite tests on local models.

- `propose_rule.md` — propose a HermitCrab **phonological rule** (vs per-stem allomorphs) for a
  systematic alternation: harmony / epenthesis / assimilation / deletion. The harder-path skill;
  pairs with the rule-emission work in `golden/hc.py` (machinery prototyped in `cycle/hc_phonology.py`).

TODO:
- [ ] `segment_word/` — propose a morpheme segmentation for an unparsed word.
- [x] `propose_rule/` — → `propose_rule.md` (skill done; porting rule emission into the main
      `golden/hc.py` builder is the next code step).
- [x] `triage/` — guess-now / ask-a-speaker / defer → `parsegym_resolve.md`.
