# Writing system

> A defined way of writing a language — identified by a BCP-47 tag, with script, font, sort, and
> direction — that every multilingual field stores its text *per*.

**LibLCM class:** `CoreWritingSystemDefinition` (libpalaso)  ·  **FLEx UI:** "Writing System"
·  **Tier:** lexical (foundational / cross-cutting)  ·  **In MiniLcm:** yes

## What it is (linguistics)

A writing system is a concrete orthography-plus-conventions for a language: which script, which sort
order, left-to-right or right-to-left, which font. One language often needs several — a practical
**vernacular** orthography, an **IPA / vernacular-phonetic** form for [[pronunciation]] and [[phoneme]]
work, maybe a second script. The **analysis** writing system(s) are the metalanguage(s) used for
glosses and definitions (often English/French). This vernacular-vs-analysis split is the backbone of
the whole data model: a vernacular word, an English gloss, and an IPA transcription are *the same field*
in different writing systems.

## How LibLCM models it

FLEx uses SIL's **libpalaso** writing-system stack; the runtime object is
`CoreWritingSystemDefinition`, identified by an **IETF BCP-47 / RFC 5646** language tag (e.g.
`seh`, `seh-fonipa`, `en`). A project keeps two ordered lists: **vernacular** and **analysis** writing
systems (`LangProject.CurrentVernacularWritingSystems` / `CurrentAnalysisWritingSystems`). A WS carries
`RightToLeftScript`, default font, and **sort/collation rules**.

The key consequence: every **`MultiString`** (rich) and **`MultiUnicode`** (plain) field — lexeme form,
gloss, definition, [[pronunciation]] form, [[etymology]] form — is a *bundle of per-WS strings*, not a
single string. There is no "the word"; there is the word *in* a writing system.

**`CoreWritingSystemDefinition` is not in `MasterLCModel.xml`** — it is a libpalaso class, and the LCM
model has no `<class>` for it. Instead LCM stores a writing system as a **BCP-47 tag string / integer
handle**: e.g. `ReversalIndex.WritingSystem` is a plain `Unicode` field holding the tag, and every
per-WS string is keyed by WS handle. So the WS *definitions* (script, font, collation) live in
libpalaso/LDML; LCM only references them by tag. (Verified: searched `MasterLCModel.xml` — no
`CoreWritingSystemDefinition` class; `ReversalIndex.WritingSystem` is `sig="Unicode"`.)

## Hermit Crab mapping

HC parses over the **vernacular underlying form** in a specific writing system; the grammar's
[[phoneme]] inventory and [[phonological-rule]]s are defined in terms of that orthography/encoding.
Getting the WS wrong (mixing IPA and practical orthography) silently feeds HC the wrong character set
and breaks parsing. Glosses HC emits are written in the analysis WS.

## In our change-sets

Most ops never edit a WS directly; they *select* one when writing a multilingual value (the `{ seh: …}`
keys in every example are WS tags). A rare structural op:

```yaml
op: lexical.writing_system.add
tag: "seh-fonipa"                  # BCP-47: Sena, phonetic (IPA)
kind: vernacular
right_to_left: false
rationale: "Project records pronunciations but has no IPA writing system."
confidence: 0.9
```

Ops carry rationale/confidence/impact/provenance like all `lexical/*` edits.

## QA & parallel relevance

A huge class of data-quality issues is *text in the wrong writing system*: an IPA form typed into the
orthographic WS, a gloss left in the vernacular WS. The assistant flags these in
[[lexeme-and-lexicon-building]] and before [[dictionary-publishing]]. In [[parallel-translation-qa]],
correct analysis vs vernacular WS tagging is what lets source and target text be compared at all.

## Pitfalls

- **Wrong-WS text** sorts, searches, and spell-checks incorrectly — and is invisible unless you look in
  the right WS slot (a classic silent failure).
- **Ad-hoc tags.** Non-conformant BCP-47 tags break interchange (LIFT, Harmony/CRDT sync).
- **Sort-rule drift** makes "the same" word order differently across machines.

## Related & references

[[lexical-entry]], [[sense]], [[pronunciation]], [[phoneme]], [[etymology]]. — FLEx docs (Writing
Systems); SIL **libpalaso** (`CoreWritingSystemDefinition`); IETF BCP-47 / RFC 5646. See
[../References.md](../References.md).
