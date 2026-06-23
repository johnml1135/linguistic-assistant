# Skill: generate environment/constraints for a morpheme (the intelligence in the loop)

THOT is a dumb counter and cannot reason about meaning. **You** are the generator: read the dossier for
one morpheme and propose the **environments** (conditioning contexts) that would either (a) split a
homographic morpheme into its distinct senses, or (b) collapse a set of enumerated allomorphs into one
underlying form + a rule. The deterministic judge (`review.judge`) then re-parses and scores each proposal
by information gain (does the right sense align to the right English word?) and constrainedness — so
propose freely, but propose **encodable, falsifiable** environments.

## You are given (the dossier, JSON)
- `morpheme`, `kind` (prefix|suffix), `n_occ`.
- `conflated_distribution`: the morpheme's current THOT distribution over English words — if this is
  **mushy** (probability spread across unrelated words), the morpheme is likely homographic.
- `distinct_sources`: the English words it co-occurs with, with counts.
- `adjacent_right_classes` / `examples`: each occurrence's adjacent segment + its natural class + the host
  word + the English word THOT scored highest for that verse.
- `seed_environments`: deterministic starting candidates (vowel/consonant edge, frequent adjacent
  segments). Refine or replace them.

## Return STRICT JSON (no prose, no fences)
```json
{
  "is_ambiguous": true|false,
  "hypothesis": "<one sentence: how many senses/allomorphs, and what conditions each>",
  "environments": [
    {"kind": "right_in",  "set": ["p","b","m"], "label": "before a labial",     "sense": "<gloss/UR for this bucket>"},
    {"kind": "right_class","value": "vowel",     "label": "before a vowel",      "sense": "<…>"}
  ],
  "confidence": "high|medium|low"
}
```

`kind` ∈ `right_in` | `left_in` (a concrete segment set — name place classes the orthography can't, e.g.
labials `p,b,m`) · `right_class` | `left_class` (`vowel` | `consonant`) · `host_pos` (a POS the morpheme
attaches to).

## Rules
- **Propose the TIGHTEST environment that could explain the split.** A narrow `before {p,b,m}` beats a
  vague `before a consonant` if the data supports it — the judge rewards constrainedness (subset
  principle). List candidates tightest-first.
- **Only split what the environment can predict.** If `conflated_distribution` is already sharp (one
  dominant English word) and environments don't co-vary with the source, set `is_ambiguous:false` and
  return `environments: []` — it is one morpheme; do not invent a split.
- **Ground each environment in the examples**, not in prior knowledge of the language — the judge tests
  against THOT counts, so an environment that doesn't co-vary with the aligned English word will score
  zero however plausible it sounds.
- **Name the sense/UR per bucket** (`"you" (2sg subject)`, `meN→mem`) so an accepted split maps back to a
  lexical/grammatical entry — this is the disambiguation index, the meaningful version of `u1…u5`.
- You propose; the judge's **re-parse + information-gain + ΔMDL** decides. Never assert a split is real —
  that is measured, not claimed.
