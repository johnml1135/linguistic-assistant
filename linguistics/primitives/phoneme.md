# Phoneme

> A contrastive sound unit of a language — modelled in Hermit Crab as a bundle of phonological
> features, not an atomic symbol.

**LibLCM class:** `PhPhoneme`  ·  **FLEx UI:** "Phoneme" (Phonemes list, Grammar area)  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

A phoneme is the smallest sound unit that distinguishes meaning in a language: English /p/ vs /b/
contrast (*pat* ≠ *bat*), so they are separate phonemes, while the aspirated [pʰ] and unaspirated [p]
of *pin* vs *spin* are allophones of one phoneme. Phonemes are defined by their **distinctive
features** — /p/ is [−voice, +labial, −sonorant, −continuant], /b/ differs only in [+voice]. This
feature analysis is what lets [[natural-class]]es and [[phonological-rule]]s generalise over sounds
instead of listing them one by one.

## How LibLCM models it

`PhPhoneme` (subclass of the abstract `PhTerminalUnit`) lives in a `PhPhonemeSet`, which is owned by
the singleton phonology object `PhPhonData` (its `MasterLCModel.xml` id; the comment notes it was
renamed from `PhPhonologicalData` for the Firebird port, which is why FLEx/SIL.Machine docs still call
it "phonological data"). Key fields:
- **`Codes`** — an owning sequence of `PhCode` (inherited from `PhTerminalUnit`), the orthographic/graph
  representations that map text to this phoneme (handles multigraphs like *ng* → /ŋ/). Each `PhCode`
  holds a `Representation` (a `MultiUnicode` string).
- **`Features`** — an owning atomic `FsFeatStruc` (phonological feature structure) giving the phoneme's
  feature specification; this is what HC consumes. The model is explicit that these features must come
  from `LangProject.PhFeatureSystem`.
- **`BasicIPASymbol`** — a `String` holding the basic-form IPA symbol; the model says FLEx uses it to
  seed a *first guess* at features and the English description, and shows it in the Grammar Sketch.
- **`Name`** (`MultiUnicode`) / **`Description`** (`MultiString`) — documentation fields, both inherited
  from `PhTerminalUnit`.

Phonological features themselves are defined in a separate `FsFeatureSystem` (`PhFeatureSystem`,
distinct from the inflectional one — see [[inflection-feature]]).

## Hermit Crab mapping

HC represents every segment as a **feature bundle**, so each `PhPhoneme` exports as an HC character
with a complete feature matrix. This is the crux: a phoneme with an *incomplete* `Features`
specification produces an under-specified HC segment that can match too broadly (over-generation) or
fail to unify (silent parse failure). HC's character definition table is generated from the phoneme
set; rules and natural classes then refer to features rather than symbols.

## In our change-sets

Phoneme edits are `morphophonology/*` ops over HC constructs:

```yaml
op: morphophonology.phoneme.set_features
phoneme: "b"
features: { voice: "+", sonorant: "-", continuant: "-", labial: "+" }
rationale: "/b/ lacked [continuant]; blocked the spirantization rule from matching."
confidence: 0.8
impact: { rules_affected: ["spirantization"], wordforms_reparsed: 31 }
provenance: { source: "phonology sketch §3.2" }
```

## QA & parallel relevance

The headline check is **feature completeness**: every phoneme must carry every feature the feature
system declares, or HC behaves unpredictably. Other checks: orphan `Codes` (graphs that map to no
phoneme → tokenization gaps), and phonemes never referenced by any [[natural-class]] or
[[phonological-rule]] (possibly spurious contrasts).

## Pitfalls

- **Under-specified features** are the silent killer — see Hermit Crab mapping above.
- **Symbol ≠ phoneme.** `BasicIPASymbol` is documentation; HC matches on `Features`. Editing the IPA
  string changes nothing about parsing.
- **Multigraph `Codes` collisions** (e.g. *ng* vs *n*+*g*) cause ambiguous tokenization.

## Related & references

[[natural-class]], [[phonological-rule]], [[pronunciation]], [[inflection-feature]]. — FLEx Phonology
docs ("Natural Classes"; "Parsing words (Hermit Crab Parser)"); LibLCM `MasterLCModel.xml`
(`PhPhoneme`, `PhTerminalUnit`, `PhCode`, `PhPhonData`); Maxwell (1998, 2003) on HC feature bundles
(HC "takes a phonetic feature-based view"); Hayes (2009), Kenstowicz (1994), SPE (1968) on distinctive
features. See [../References.md](../References.md).
