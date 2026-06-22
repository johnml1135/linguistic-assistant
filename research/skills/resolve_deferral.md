# Skill: resolve-or-defer a deferred wordform

You are shown a vernacular word the automatic pipeline could not confidently analyse, with its meaning
evidence (an aligned translation word) and nearby context. Decide the **single best** action — and
crucially, **defer when the evidence is insufficient**. Guessing wrong is worse than deferring.

## You are given (JSON)
- `language`, `form` (the word), `pivot_gloss` (aligned translation word, may be absent/"?"),
- `near_lemma` (the closest existing dictionary word, or null), `context` (a short phrase it appears in),
- `profile` (morphological type + allowed processes — respect it; never propose a locked-off mechanism).

## Return STRICT JSON only — no prose, no code fences
```json
{
  "decision": "resolve" | "defer",
  "edit": {"kind": "add_lexentry|add_allomorph|add_affix|split_homograph", "params": { ... }},
  "confidence": "high" | "medium" | "low",
  "rationale": "one short sentence"
}
```

## Rules
- `decision: "resolve"` ONLY when you are genuinely confident. Then `edit` must be a typed edit:
  - `add_lexentry` → {"form": "<word>", "gloss": "<english>", "pos": "Noun|Verb|Adjective|..."}
  - `add_allomorph` → {"entry_form": "<existing lemma>", "allomorph": "<word>"}  (the word is another
    form of an existing dictionary word)
  - `add_affix` → {"form": "<affix>", "gloss": "<function>", "kind": "prefix|suffix|infix"}
  - `split_homograph` → {"form": "<word>", "gloss": "<the second meaning>", "pos": "..."}
- `decision: "defer"` when the meaning is unclear, the pivot gloss is missing/contradictory, the form is
  an isolated unknown with no near lemma, or a speaker is genuinely needed. Leave `edit` as `{}`.
- Prefer `add_allomorph` when the word is clearly an inflected form of `near_lemma` (same meaning,
  shared stem). Prefer `add_lexentry` for a genuinely new word.
- Respect the profile: do not propose an infix for a non-infixing language, etc.
- Be conservative: when in doubt, **defer**.
