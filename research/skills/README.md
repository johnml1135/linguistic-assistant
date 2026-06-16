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

TODO:
- [ ] `segment_word/` — propose a morpheme segmentation for an unparsed word.
- [ ] `propose_rule/` — propose a HermitCrab phonological rule from evidence.
- [ ] `triage/` — decide guess-now / ask-a-speaker / defer, with confidence + impact.
