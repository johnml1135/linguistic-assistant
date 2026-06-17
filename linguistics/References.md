# References

Annotated bibliography for this repo's linguistic work. Organized by area. **SIL / FieldWorks sources
are primary** (they define the data model and tooling we target); the general literature gives the
theory the skills reason with. Primitives and workflows cite back here by short author–year or by the
SIL doc name.

> Verified against online sources June 2026. URLs may rot — prefer the DOI/publisher page or the SIL
> documentation root if a deep link breaks. Items flagged *(unverified)* could not be fully confirmed.

---

## 1. SIL / FieldWorks / LibLCM / tooling (primary)

- **FieldWorks Language Explorer (FLEx) documentation.** SIL. <https://software.sil.org/fieldworks/>
  and the help/task docs at <https://downloads.languagetechnology.org/fieldworks/Documentation/> —
  the authoritative description of the Lexicon and Grammar areas, parsing, and publishing.
- **LibLCM — SIL Language & Culture Model.** <https://github.com/sillsdev/liblcm>; the authoritative
  class definitions live in `src/SIL.LCModel/MasterLCModel.xml`. The storage model behind `.fwdata`.
- **A Conceptual Introduction to Morphological Parsing (FLEx).**
  <https://downloads.languagetechnology.org/fieldworks/Documentation/Intro%20to%20Parsing/ConceptualIntroduction.htm>
  — stem-level vs root-level parsing; the inflection/derivation split as FLEx implements it.
- **Black, Andrew & Gary Simons (2006). "The SIL FieldWorks Language Explorer approach to
  morphological parsing."** *Texas Linguistics Society / UPenn Working Papers.* The design of FLEx's
  parsing pipeline.
- **Maxwell, Michael B. (2003). *Hermit Crab: parsing and generating with classical generative
  phonology and morphology.*** SIL International (LinguaLinks). <https://www.sil.org/resources/archives/5746>
  — the canonical Hermit Crab reference. **Our engine.**
- **Maxwell, Michael (1994). "Parsing Using Linearly Ordered Phonological Rules." arXiv:cmp-lg/9411015.**
  <https://arxiv.org/pdf/cmp-lg/9411015> — the generate-and-test algorithm (reverse the ordered rules
  to analyze) that makes HC both parse and generate.
- **Maxwell, Michael B. (1998). "Two Theories of Morphology, One Implementation." SILEWP 1998-001.**
  <https://www.sil.org/system/files/reapdata/.../SILEWP1998_001.pdf> — Item-and-Arrangement vs
  Item-and-Process; how HC encodes affixes as processes, and head vs rule features.
- **SIL.Machine.** <https://github.com/sillsdev/machine> — the maintained managed-C# implementation of
  Hermit Crab (`SIL.Machine.Morphology.HermitCrab`) and the `SIL.Machine.Tool` CLI we drive.
- **Machine Parsing of Gilaki Verbs with FieldWorks Language Explorer (Lockwood, 2011).**
  <https://software.sil.org/fieldworks/wp-content/uploads/sites/38/2017/01/Machine-Parsing-of-Gilaki-Verbs-with-Fieldworks-Language-Explorer.pdf>
  — worked example of affix templates, MSAs, ad hoc rules on a real language.
- **Moe, Ron (2001+). Rapid Word Collection (RWC) methodology & Semantic Domains.** SIL.
  <https://www.sil.org/dictionaries-lexicography/rapid-word-collection-methodology>; The Combine
  <https://software.sil.org/thecombine/>; WeSay <https://software.sil.org/wesay/>. The
  semantic-domain elicitation method behind `CmSemanticDomain`.
- **PC-PATR / XAmple (CARLA).** <https://software.sil.org/pc-patr/> — FLEx's default (non-HC) parser
  stack; context for why we chose HC. *We do not use these.*
- **FLExTrans (Lockwood).** <https://software.sil.org/flextrans/> — rule-based MT on FLEx data
  (Apertium + STAMP/HC). **Context only — translation generation is out of scope here.**
- **Serval / AQuA / Scripture Forge (SIL AI).** <https://ai.sil.org/> — SIL's NLP stack: NLLB-200 MT
  (Serval), translation QA (AQuA), collaborative translation (Scripture Forge). Our sibling
  translation model is Serval; **AQuA** (<https://ai.sil.org/projects/AQuA>, <https://aqua.sil.org/>)
  is prior art for parallel-translation QA — AI-assisted assessment across **accuracy, clarity, and
  naturalness**; not MT and not a syntactic parser.
- **Paratext Biblical Terms / key-term consistency.** <https://manual.paratext.org/> and the **4-step
  process** at <https://manual.paratext.org/10.BT/> (list renderings → check coverage → make consistent
  → approve) — the established workflow for key-term and consistency checking we complement.
- **LIFT (Lexicon Interchange FormaT).** the XML interchange format for lexical data FLEx imports/exports.
- **FLEx vernacular spell-checking (Hunspell).** "Spell Checking vernacular words" and "Vernacular
  spelling dictionary files"
  <https://downloads.languagetechnology.org/fieldworks/Documentation/en/Basic_Tasks/Spell_Checking/vernacular_spell_checking.htm>
  — FLEx writes Hunspell `.dic`/`.aff` files from wordforms whose Spelling Status is *Correct*.
- **FLEx dictionary publishing.** "Publishing Your Data" / "How to Create a Dictionary Using FieldWorks"
  <https://software.sil.org/fieldworks/help/publishing-your-data/>; Ken Zook, "Technical Notes on FLEx
  Dictionary Printing and Export"
  <https://downloads.languagetechnology.org/fieldworks/Documentation/Technical%20Notes%20on%20FLEx%20Dictionary%20Printing%20and%20Export.pdf>.
  Configured views/reversal indexes; Webonary one-button publish (since **FLEx 8.3**); built-in Word
  `.docx` export (since **FLEx 9.2**); the older **Pathway** export path to PDF/OpenOffice/InDesign
  (*deprecation status unverified*).
- **Webonary.** <https://www.webonary.org/> — SIL's WordPress-based online-dictionary host; FLEx
  publishes to it directly since 8.3.
- **flexlibs.** <https://github.com/cdfarrow/flexlibs> (fork <https://github.com/MattGyverLee/flexlibs>)
  — Python wrapper over LibLCM giving programmatic read/write to a FLEx project (`FLExProject`,
  `OpenProject(..., writeEnabled=…)`). The **base (cdfarrow)** is lexicon-write-only; the
  morphology/phonology write layer (natural-class creation, compound rules, phonological rules, affix
  templates) exists only in the **MattGyverLee `flexlibs2` fork**. Genuine gaps absent everywhere:
  **MSA-type conversion** and **inflection-class slot configuration**. Writes run in a **non-undoable**
  unit of work (no rollback). The capability substrate for downstream ingestion; **not a core-loop
  dependency** here.
- **flextools.** <https://github.com/cdfarrow/flextools> (fork <https://github.com/MattGyverLee/flextools>)
  — framework that runs "modules" over a FLEx project; each module is a packaged workflow. Modules
  declare `FTM_ModifiesDB` (report-only vs DB-modifying) and stage edits through a preview (the
  *FTFlags* custom field) — the canonical **investigate-then-change** pattern. Catalog of real
  workflows (duplicates, reports/stats, integrity checks, bulk edits, export). "Python for FlexTools
  and FLEx 9.1" guide on languagetechnology.org.
- **FlexToolsMCP.** <https://github.com/MattGyverLee/FlexToolsMCP> — an MCP server exposing FLEx
  data/operations to an LLM; discovery-first, with a mandatory **dry-run (`write_enabled=False`) →
  write** two-phase guard (`if modifyAllowed:`) and an undo stack. Model for safe, gated
  investigate→change execution; lexicon-reachable, morphology/phonology grammar largely not writable.

## 2. Morphology (theory)

- **Haspelmath, Martin & Andrea D. Sims (2010). *Understanding Morphology* (2nd ed.).** Routledge.
  Accessible standard; inflection/derivation, morphology–syntax and morphology–phonology interfaces.
- **Aronoff, Mark & Kirsten Fudeman (2011). *What is Morphology?* (2nd ed.).** Wiley-Blackwell.
- **Matthews, P. H. (1991). *Morphology* (2nd ed.).** Cambridge UP. Classic; paradigms, IA vs IP.
- **Booij, Geert (2010). *Construction Morphology.*** Oxford UP. Form–meaning pairings.
- **Spencer, Andrew (1991). *Morphological Theory.*** Blackwell. Generative morphology, nonconcatenative.
- **Bauer, Laurie (2003). *Introducing Linguistic Morphology* (2nd ed.).** Edinburgh UP. Productivity.
- **Stump, Gregory T. (2001). *Inflectional Morphology: A Theory of Paradigm Structure.*** Cambridge UP.
  Realizational/Paradigm Function Morphology — the theory closest to HC's realizational view of affixes.
- **Hockett, Charles F. (1954). "Two Models of Grammatical Description." *Word* 10(2–3): 210–234.**
  The Item-and-Arrangement vs Item-and-Process distinction HC sits on.

## 3. Phonology & morphophonology

- **Hayes, Bruce (2009). *Introductory Phonology.*** Wiley-Blackwell. Features, rules, natural classes.
- **Kenstowicz, Michael (1994). *Phonology in Generative Grammar.*** Blackwell. Post-SPE generative
  phonology — the tradition HC implements.
- **Odden, David (2013). *Introducing Phonology* (2nd ed.).** Cambridge UP. Rule-writing practice.
- **Goldsmith, John (1976/1990). *Autosegmental Phonology.*** Tone/harmony on separate tiers.
- **Chomsky, Noam & Morris Halle (1968). *The Sound Pattern of English (SPE).*** Harper & Row. The
  ordered-rewrite-rule framework HC's phonology is built on.

## 4. Field linguistics & language documentation

- **Bowern, Claire (2015). *Linguistic Fieldwork: A Practical Guide* (2nd ed.).** Palgrave Macmillan.
- **Payne, Thomas E. (1997). *Describing Morphosyntax: A Guide for Field Linguists.*** Cambridge UP.
  The practical template for morphosyntactic description; maps well onto FLEx categories.
- **Dixon, R. M. W. (2010–2012). *Basic Linguistic Theory* (Vols. 1–3).** Oxford UP.
- **Chelliah, Shobhana & Willem de Reuse (2011). *Handbook of Descriptive Linguistic Fieldwork.*** Springer.
- **Crowley, Terry (2007). *Field Linguistics: A Beginner's Guide.*** Oxford UP.
- **Gippert, Himmelmann & Mosel (eds.) (2006). *Essentials of Language Documentation.*** Mouton de Gruyter.
- **Himmelmann, Nikolaus (1998). "Documentary and descriptive linguistics." *Linguistics* 36: 161–195.**

## 5. Lexicography

- **Atkins, B. T. S. & Michael Rundell (2008). *The Oxford Guide to Practical Lexicography.*** Oxford UP.
  Corpus-driven dictionary-making; sense division, entry structure — directly relevant to sense QA.
- **Svensén, Bo (2009). *A Handbook of Lexicography.*** Cambridge UP.
- **Zgusta, Ladislav (1971). *Manual of Lexicography.*** Mouton.
- **Landau, Sidney I. (2001). *Dictionaries: The Art and Craft of Lexicography* (2nd ed.).** Cambridge UP.
- **Louw, Johannes P. & Eugene A. Nida (1988). *Greek-English Lexicon of the New Testament Based on
  Semantic Domains.*** United Bible Societies (2 vols.). The semantic-domain classification of NT Greek
  vocabulary that Ron Moe's Semantic Domains list is loosely aligned to; referenced by
  `CmSemanticDomain.LouwNidaCodes`.

## 6. Computational & finite-state morphology

- **Beesley, Kenneth R. & Lauri Karttunen (2003). *Finite State Morphology.*** CSLI. The FST canon
  (lexc/xfst); the main alternative paradigm to HC's rule engine.
- **Koskenniemi, Kimmo (1983). *Two-Level Morphology.*** University of Helsinki. KIMMO; the two-level
  model (contrast HC's single-underlying-form + ordered rules).
- **Roark, Brian & Richard Sproat (2007). *Computational Approaches to Morphology and Syntax.*** Oxford UP.

## 7. Glossing & description standards

- **Comrie, Bernard, Martin Haspelmath & Balthasar Bickel (2008/2015). *The Leipzig Glossing Rules.***
  <https://www.eva.mpg.de/lingua/resources/glossing-rules.php> — the interlinear gloss standard our
  gloss output should conform to.
- **Comrie, Bernard & Norval Smith (1977). "Lingua Descriptive Studies Questionnaire." *Lingua* 42.**
- **GOLD — General Ontology for Linguistic Description.** <https://linguistics-ontology.org/> —
  interoperable linguistic categories (gram. features, parts of speech).

## 8. Typology / reference

- **Whaley, Lindsay (1997). *Introduction to Typology.*** SAGE. Cross-linguistic morphological types.
- **WALS — World Atlas of Language Structures.** <https://wals.info/> — typological feature values
  useful as priors when proposing analyses for an under-documented language.
- **Ethnologue.** SIL. <https://www.ethnologue.com/> — language identification / sociolinguistic context.

## 9. Pedagogy & heuristics — "how real linguists work"

How field linguists are *trained*; the skills layer mimics these procedures.

- **Nida, Eugene A. (1949). *Morphology: The Descriptive Analysis of Words* (2nd ed.).** Univ. of
  Michigan Press. The canonical morpheme-discovery procedure: recurring partials → complementary
  distribution → phonological conditioning test → allomorph vs morpheme.
- **Pike, Kenneth L. (1947). *Phonemics: A Technique for Reducing Languages to Writing.*** Univ. of
  Michigan Press. Field phonemic analysis; the **monolingual demonstration** method
  (<https://www.sil.org/about/klp>). The "introspect a language fast from zero" model.
- **Zwicky, Arnold M. (1985). "Rules of allomorphy and phonology–syntax interactions." *J. Linguistics*
  21.** The decision: phonologically-conditioned alternation → **rule**; morphologically-conditioned →
  **listed allomorph**; arbitrary → **suppletion**. Core to [[../primitives/allomorph]] vs
  [[../primitives/phonological-rule]].
- **The "capture the generalization" / evaluation-metric principle** — SPE (Chomsky & Halle 1968,
  §2 above) and Martinet, *Économie des changements phonétiques* (1955): prefer one rule over a
  natural class to enumerating allomorphs. The formal name for "teach it to **generalize**."
- **Vaux, Bert & Justin Cooper (1999). *Introduction to Linguistic Field Methods.*** LINCOM. Course-
  proven sequencing: phonetics → phonology → morphology → syntax → semantics → lexicography.
- **Bartholomew, Doris & Louise Schoenhals (1983). *Bilingual Dictionaries for Indigenous Languages.***
  SIL. Citation-form choice, entry structure for morphologically rich languages.
- **Coward, David & Charles Grimes (1995/2003). *Making Dictionaries: A Guide to Lexicography and the
  Multi-Dictionary Formatter.*** SIL. The "column-based" (one field across all entries) workflow.
- **Kilgarriff, Adam (1997). "I don't believe in word senses." *Computers and the Humanities* 31.**
  Senses as task-relative clusters of corpus citations — the lumping/splitting heuristic.
- **Brewster, E. Thomas & Elizabeth S. Brewster (1976). *Language Acquisition Made Practical (LAMP).***
  Lingua House. Self-directed monolingual language learning; the "interesting features first" instinct.
- **SIL field-linguistics training.** <https://www.sil.org/training/linguistics> — the institutional
  curriculum (phonology → morphology → syntax; FLEx) that defines standard practice.

## 10. Bootstrap data — wordlists, corpora & typological databases

Inputs a cold-start analysis draws on.

- **Swadesh list (100 / 207).** Core-vocabulary list for lexicostatistics; a minimal lexicon seed.
- **Leipzig–Jakarta list (100).** Borrowing-resistant core vocabulary.
  <https://en.wikipedia.org/wiki/Leipzig–Jakarta_list>
- **ASJP list (40).** Minimal wordlist for automated comparison. <https://asjp.clld.org/>
- **SILCAWL — SIL Comparative African Word List (~1,700).** Snider & Roberts (2006), SILEWP 2006-005.
  <https://www.sil.org/resources/publications/entry/7882> — the standard regional comparative wordlist
  (a.k.a. CAWL); strong bootstrap seed for African languages.
- **WALS** <https://wals.info/> · **Grambank** <https://grambank.clld.org/> · **PHOIBLE**
  <https://phoible.org/> — typological priors: expected morphology type (WALS/Grambank) and phoneme
  inventory norms (PHOIBLE) for "what should I look for in this family?"
- **eBible corpus.** <https://ebible.org/> — open, verse-aligned Bible translations across 800+
  languages; the parallel-text substrate for direct parsing and [[../workflows/parallel-translation-qa]].
- **OPUS.** <https://opus.nlpl.eu/> — open parallel corpora (incl. bible-uedin).
