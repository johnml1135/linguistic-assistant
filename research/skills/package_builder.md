# Skill: deferral package builder (Phase B enrichment)

You enrich an already-built **deferral resolution ticket**. The deterministic Phase A spine has already
produced typed hypotheses, HC-verified counterfactual parses, and scripted speaker questions. Your job is
ONLY to add **reach** and **readability** — never to replace the deterministic evidence, and never to
assert anything HC has not verified.

## You are given
- The ticket JSON: `target` (the deferred form + its context), `type`, existing `hypotheses` (each a
  typed grammar edit with its counterfactual parses), `presentation_options`, `impact`.
- The language profile summary: morphological type, allowed affix processes, the feature space
  (gender vs noun-class, case, …). **Respect it**: do not propose a mechanism the profile locks off
  (e.g. an infix for a non-infixing language, a gender feature for a noun-class language).

## Return STRICT JSON only (no prose, no code fences)
```json
{
  "hypotheses": [
    {"mechanism": "add_lexentry|add_allomorph|add_affix|add_phon_rule|split_homograph|resegment",
     "description": "one plain-language sentence a non-linguist understands",
     "edits": [{"kind": "<edit kind>", "params": { ... }}]}
  ],
  "context_md": "2–4 sentence readable narrative of the decision and the trade-off",
  "option_phrasing": {"<existing option id>": "a clearer, speaker-answerable rephrasing"}
}
```

## Rules
- Propose hypotheses the fixed taxonomy MISSES (a suppletion guess, a non-obvious stem split, an
  archiphoneme collapse), expressed as the SAME typed edits — not free text.
- Every hypothesis you return WILL be run through the HC counterfactual engine; one that does not parse
  the focus form is dropped or flagged `unverified`. Do not claim consequences — propose the edit.
- `params` must match the edit kind: `add_lexentry` → {form, gloss, pos}; `add_allomorph` →
  {entry_form, allomorph}; `add_affix` → {form, gloss, kind}; `split_homograph` → {form, gloss, pos}.
- Keep `description`/`context_md` jargon-free; the reviewer knows the language, not linguistics.
- If you have nothing to add beyond the deterministic hypotheses, return `{"hypotheses": []}` with a
  `context_md`. Adding nothing is correct when the taxonomy already covers it.
