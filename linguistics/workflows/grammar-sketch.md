# Grammar Sketch

> Let FLEx auto-assemble an HTML grammar overview from the lexicon, texts, and grammar, then enrich the
> prose and flag where the data is too thin to describe — word-level morphology only.

**Primary tool(s):** FLEx (Grammar → Sketch, HTML generation)  ·  **Mode:** investigate  ·  **Stage in our loop:** review  ·
**Parallel-aware:** no

## Goal & when it runs

The **Grammar Sketch** tool gathers grammatical data from across the project into one generated HTML
document — phoneme inventory, [[inflection-class]]es, [[affix-template-and-slot|affix templates]],
[[inflection-feature|feature system]], and example sentences from texts. It runs once there is enough
analyzed data to be worth summarizing, as a draft for a grammar consultant or a quick share. For this
repo it is a **lower-priority output** ("to a lesser extent, grammars").

## The human process (in FLEx today)

1. Build up the grammar through [[morphological-parser-setup]] and [[interlinearization]] so the
   project actually holds inflection classes, templates, features, and parsed examples.
2. Open **Grammar Sketch** and generate the HTML, which pulls those pieces together automatically.
3. Use it **as-is** to share, or as the **basis for a hand-edited** prose grammar.

## How the assistant supports it

- **Review** the generated sketch and **propose** connective prose and well-chosen
  [[example-sentence]]s from the corpus to illustrate each [[inflection-class]]/template.
- **Flag** thin sections ("insufficient data for this paradigm") and decide *draft prose now / ask a
  native speaker for examples / defer until more text is analyzed*.
- **Emit** prose/example suggestions and gap flags — and respect the **scope boundary**: this documents
  *word-level [[morphosyntactic-analysis|morphology]]*, never syntactic induction (out of scope).

## Inputs

The lexicon, analyzed texts (for examples), and the grammar (phonemes, inflection classes, affix
templates, feature system) — i.e. the accumulated output of the morphology workflows.

## Primitives involved

[[affix-template-and-slot]], [[inflection-class]], [[morphosyntactic-analysis]], [[inflection-feature]],
[[phoneme]].

## Oracle / gold / metrics

- **Deterministic:** the sketch's morphological claims trace back to objects the Hermit Crab `word→gloss`
  golden set exercises — generated paradigms must match attested forms.
- **Parallel-QA:** not applicable; coverage is measured as documented-vs-undocumented categories.

## Outputs

An enriched grammar sketch (generated HTML + proposed prose/examples) and a list of data-scarcity gaps
needing more elicitation or analysis.

## Pitfalls

- **Data-scarcity gaps:** sparse paradigms produce empty or misleading sections — flag, don't fabricate.
- **Brittle templating:** the auto-layout can misrender unusual configurations; review the rendered HTML.
- **Discourse and syntax are underrepresented** — and are explicitly **out of our scope**; do not pad
  the sketch beyond word-level morphology.

## References

FLEx "Grammar / Sketch" feature docs; Payne (1997) *Describing Morphosyntax* as the prose template.
See [../References.md](../References.md).
