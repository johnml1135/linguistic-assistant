# Learning Paradigms Plan

How the system auto-learns each language's core grammatical paradigms, presents the *full picture*
(THOT + HC + the A/B/C+fit explorer) to **Gemma**, who writes a **report** for **Opus-as-Reviewer** —
and how we make **report quality vs a golden report** the metric the whole system optimizes.

---

## 1. What must be auto-learned, per language (top 3–10, confirmed online)

Each row is a *paradigm* the system should surface on its own (a "hey, this looks like X"), with the
data signature it leaves. Sources confirmed 2026-06 (links at bottom). The system must *recover these
from data*, never from this table — this table is the answer key (the ceiling), not an input.

### swh — Swahili (Bantu) — **prefixal concord; no case, no gender**
1. **Noun-class system** — ~15–18 classes in sg/pl pairs, each a noun prefix (m-/wa-, ki-/vi-, ji-/ma-, u-, ku-).
2. **Subject concord** on the verb (cl1 a-, cl2 wa-, cl7 ki-, …) agreeing with the subject's class.
3. **Object concord** on the verb.
4. **Adjectival / possessive / associative (-a "of") concord** agreeing with the head noun's class.
5. **Locative classes** (16 pa-, 17 ku-, 18 mu-) + the locative suffix **-ni**.
6. **Verb TAM prefixes** (na- pres, li- past, ta- fut, me- perf, hu- habitual).
7. **Verb derivational extensions** (applicative, passive -w-, causative -sh-/-z-).

### ind — Indonesian (Austronesian) — **voice + derivation; no case, no gender, no agreement**
1. **Voice**: active **meN-**, passive **di-**.
2. **Reduplication** for plurality (buku-buku).
3. **Circumfixes** ke-…-an, pe(r)-…-an (abstraction / nominalization).
4. **peN-** agentive/instrument nominalizer.
5. **-kan / -i** applicative & causative suffixes.

### tgl — Tagalog (Austronesian) — **symmetrical voice/focus + NP case-markers; no gender**
1. **Symmetrical voice/focus**: actor -um-/mag-, patient -in, locative -an, instrument/benefactive i-.
2. **NP case-markers**: **ang** (trigger/nominative), **ng** (genitive), **sa** (oblique/dative).
3. **Aspect** via reduplication + infix (-um-/-in-: perfective/imperfective/contemplated).
4. **Plural** marker mga.

### spa — Spanish (Romance) — **gender/number agreement + rich verb conjugation; no nominal case**
1. **Gender** (m/f), nouns -o/-a.
2. **Number** -s.
3. **Gender+number agreement** across article–noun–adjective.
4. **Verb conjugation**: 3 classes (-ar/-er/-ir) × person/number × TAM.
5. **Clitic object pronouns** (me/te/lo/la/se).

### tur — Turkish (Turkic) — **agglutinative case under vowel harmony; no gender** ← biggest current gap
1. **Case (6)**: nom-Ø, acc **-(y)I**, dat **-(y)A**, loc **-DA**, abl **-DAn**, gen **-(n)In**.
2. **Vowel harmony** (front/back + rounding) — conditions the shape of *every* suffix.
3. **Plural** -lAr.
4. **Possessive suffixes** (-Im, -In, -(s)I, …).
5. **Verb TAM + person agreement**; evidentiality -mIş.

### vie — Vietnamese (isolating) — **the auto-learn target is the NEGATIVE: confirm no inflection**
1. **Isolating**: no case/gender/number/tense morphology — the system must *correctly find nothing* and say so.
2. **Classifiers** (cái, con, …) — a closed function class before nouns.
3. **Tone** (6, orthographically marked).
4. **Reduplication / compounding** for word formation.

### hin — Hindi (Indo-Aryan) — **gender + case + split ergativity**
1. **Gender** (m/f).
2. **Number** (sg/pl).
3. **Case**: direct/oblique/vocative (nouns) + postpositional case (ne, ko, se, mein, par, ke).
4. **Split ergativity**: **ne** on the perfective transitive subject.
5. **Verb agreement** (gender+number; agrees with the *object* when subject is ne-marked).

### rus — Russian (Slavic) — **fusional case × gender × declension class**
1. **Case (6)**: nom, gen, dat, acc, instr, prep.
2. **Gender** (m/f/n).
3. **Number** (sg/pl).
4. **Declension classes** (multiple, gender-linked).
5. **Animacy** (acc = gen for animate masc).
6. **Adjective agreement** (gender+number+case).
7. **Verb aspect** (perfective/imperfective).

**Cross-cutting:** the only paradigm the current discovery layer truly handles is swh's *prefixal
concord*. Case (tur/rus/hin), symmetrical voice (tgl), and gender agreement (spa) have **no detector** —
`detect_case` is a hard-coded `"absent"` stub. Closing that is the iteration this plan drives.

---

## 2. The pipeline: data → full picture → report → review

```
corpus ─┬─► HC parse (coverage, segmentation, gloss line, ambiguity)
        └─► THOT align (morpheme ↔ English pivot, role projection)
                         │
                         ▼
        A/B/C + fit-none EXPLORER  (review/explore.py + a new suffixal/case detector)
          "candidate paradigm: rank-A hypothesis, rank-B, rank-C, + the residue that fits none"
                         │
                         ▼
        PACKET ASSEMBLER  (review/paradigm/packet.py)
          one "full picture" per candidate: hypotheses + THOT stats + HC stats + worked examples
                         │
                         ▼
        GEMMA  (review/paradigm/report.py via swappable LLMClient)
          reads the packet ONLY → writes a structured ParadigmReport (slots + prose)
                         │
                         ▼
        OPUS-AS-REVIEWER  (firewall: packet evidence + universal method, never recalled knowledge)
          promote / defer / reject
```

The report is the product. Everything upstream exists to make the report good.

---

## 2.5 Progressive / layered learning (the core principle)

**Paradigms are NOT all generated in the first pass. They fall out progressively, one layer at a time, as
each prerequisite is learned.** You cannot meaningfully ask "what are the concord markers?" before you
know the noun classes; you cannot ask "what conditions the case allomorphy?" before you know there is
case. So the system learns in strict layers, each gated by what the layer below already established.

### The four layers (strict order)
| layer | what it learns | gated by |
|-------|----------------|----------|
| 0 **switches** | typological profile: synthesis, affix polarity, vowel harmony, gender-or-noun-class, **case presence**, voice | nothing — learned first; it is the gate-source for everything |
| 1 **inventory** | the CELLS: noun classes / cases / voices / gender-number / classifiers | switch values |
| 2 **agreement** | concord / agreement over the inventory | the inventory being learned |
| 3 **exceptions** | allomorphy, conditioning, splits (glide formation, vowel harmony, ergative split) | the relevant inventory (± agreement) |

### Status lifecycle (per paradigm)
`locked` → (gate satisfied) → `candidate` → (report generated) → `learned` → (Opus promotes) → `confirmed`.
A detector that runs and finds nothing real marks the paradigm `absent` (the *correct* answer for case in
vie/swh — "we looked and there is no case" is a learned fact, not a gap).

### The dependency graph IS the registry
Every paradigm carries a **gate** in a tiny language: `switch:NAME == VALUE`, `switch:NAME != VALUE`,
`switch:NAME ~ TOKEN` ("has this"; `affix_polarity ~ suffix` matches *suffixing* and *both*), and
`paradigm:ID in {learned,confirmed}`, joined by `and`/`or`. `next_unlocked(lang, switch_values, statuses)`
returns exactly the paradigms whose gate is now satisfied but which aren't yet learned — the ones that
"fall out next." Examples:
- `swh.concord` gate = `paradigm:swh.noun-class in {learned,confirmed}` → stays locked until classes are learned.
- `tur.case` gate = `switch:affix_polarity ~ suffix and switch:case != absent` → **stays locked while the
  broken `detect_case` stub reports `absent`**. Fixing the detector is what unlocks it. The biggest gap is
  encoded as a dependency, not a TODO.

This means the worklist is emergent and self-pruning: at any moment the system is only ever working on the
handful of paradigms the data has earned the right to ask about. (Same spine as the frontier-finder and
the switches→classes→exceptions workflow.)

### Per-language profile JSON — the queryable registry + state of record
`review/paradigm/profiles/<lang>.json` (emitted from the single source of truth in `profiles.py`). One
solid, queryable file per language, with metadata:

```
language, name, family, macro_profile, sources[], confirmed, schema_version, layers[]
paradigms: [
  { id, paradigm_type, layer, priority, gate,
    status,                 # locked | candidate | learned | confirmed | absent
    summary,
    golden?, expected_cells?,
    metric? }               # the report-vs-golden score, written back by the loop
]
```

The **report metric is recorded back onto this profile** (`run.py` → `profiles.record_result`), so the
per-language file is the live, queryable answer to "what has this language learned, how well, and what's
unlocked next." Query it with `profiles.load / get_paradigm / by_layer / next_unlocked / status_summary`.

## 3. The report schema (shared contract — golden and generated are the same shape)

`review/paradigm/schema.py :: ParadigmReport`

```
language            str
paradigm_type       str        # noun-class | case | voice-focus | gender-number | isolating | tam | ...
detected            bool       # does this paradigm exist here? (vie: false is the right answer)
confidence          float
cells               [ {label, markers[], function, support:int, examples[]} ]   # classes/cases/voices
conditioning        str|null   # allomorphy trigger: vowel-harmony | gender | phonology | none
fit_none            {n:int, examples[], note}                                   # the residue
evidence_citations  [ {claim, source: thot|hc|explorer, stat} ]                 # every claim is backed
prose               str        # the human-readable report Opus reads
```

A **golden report** is this schema, filled by me with full linguistic + online knowledge — the ceiling.
A **generated report** is this schema, filled by Gemma from the packet alone.

---

## 4. The metric: report quality vs golden (separable, so it's an optimization target)

Closeness-to-golden is split into two scores so each gain attributes to a specific fix:

- **evidence_completeness** ∈ [0,1] — of the golden's cells + conditioning + fit_none, what fraction is
  *present in the packet at all*? Measures **detector / packet** quality (upstream). A missing case-cell
  here means the explorer never surfaced it.
- **faithfulness** ∈ [0,1] — of the facts that *were* in the packet, what fraction did Gemma report
  correctly, with no hallucinated cells? Measures **Gemma / prompt** quality (downstream).

`overall = evidence_completeness × faithfulness`. We report all three. A detector fix moves
completeness; a prompt fix moves faithfulness; the product is "how close to golden."

### The firewall/golden tension (must not be violated)
The golden encodes the *true* grammar (recalled + online). The pipeline must recover it from the
**packet alone**. So the gap is *expected* to be < 1.0 — it measures "how much of the real grammar did
we recover from data." **The one forbidden way to close the gap is leaking the answer into the packet.**
We close it only by (a) a better detector → more real evidence in the packet, and (b) better Gemma
synthesis. The packet assembler is audited to contain only THOT/HC/explorer-derived facts.

### Smoke-test discipline
- Generator must be a *weaker* model than the golden author, or the score sits near ceiling and means
  nothing. Use Gemma/heuristic as generator; Opus/me as golden.
- n=2 golden reports overfit instantly. The per-language "3–10 things" above **is the golden-report
  backlog** — widen to several per anchor as the loop stabilizes.

---

## 5. Build order (vertical slices)

1. **swh noun-class slice (no new detection code)** — evidence already exists (`class_hypotheses`,
   `agreement_hypotheses`: concord 13/14 clean). Build packet → report → golden → score here. This
   proves the metric machinery where the data is good.
2. **tur case detector** — the suffixal mirror of the Bantu explorer (real `detect_case` via
   role-covarying final-syllable sets; paradigm-cell hypotheses conditioned by vowel harmony). This is
   the *first improvement the loop measures*: completeness on tur-case should jump from ~0 once it lands.
3. **Widen**: tgl voice-focus, spa gender-number, rus case — each adds a golden + a detector pass.
4. **vie negative case** — confirm the system reports `detected:false` and scores well for *not*
   inventing a paradigm.

---

## 6. Results so far (honest)

The machinery is built and exercised end-to-end on the **swh noun-class** anchor; the per-language
profiles + progressive gating are live for all 8. What the numbers do and don't mean:

| run | overall | completeness | faithfulness | what it shows |
|-----|--------:|-------------:|-------------:|---------------|
| heuristic generator | 1.00 | 1.00 | 1.00 | **plumbing smoke test, NOT a measurement.** The deterministic generator was hand-fit to this one golden (saw the 3 missing cells, added the paths that recover them). Proves the pipeline runs; says nothing about accuracy. |
| mock-as-generator (JSON, untuned) | **0.50** | 1.00 | 0.50 | **the honest number.** A generator decoupled from the golden recovers 4/8 cells from the evidence-only packet — partial, no hallucination. This is "how close an untuned generator gets." |

- **completeness 1.0 on swh is expected** (it's the one success case — the detector genuinely surfaces all
  8 classes' evidence), but with n=1 golden authored after seeing the packet it is not yet independently
  verified; widening to ≥3 goldens per anchor is required before trusting it.
- **Live Gemma/opus has not produced a scored report yet.** The endpoint is reachable, but the existing
  `propose/harness/anthropic_client.py` passes an `output_config` kwarg the installed SDK rejects — a
  pre-existing harness/SDK mismatch. The full LLM path is validated with a messy-JSON mock; a live run is
  a follow-up (fix the vendor client's structured-output call).

**Bottom line:** the architecture + metric + progressive layering are in place and tested (12 tests). The
real "how close to golden" story needs (a) a live weaker-than-golden generator and (b) ≥3 goldens per
anchor; the swh 1.0 is plumbing, the untuned 0.5 is the first honest data point.

## Sources (confirmed 2026-06)
- Turkish case + vowel harmony: [Turkish grammar (Wikipedia)](https://en.wikipedia.org/wiki/Turkish_grammar), [easyturkishgrammar](https://www.easyturkishgrammar.com/post/turkish-case-suffixes)
- Russian declension/cases/gender: [Russian declension (Wikipedia)](https://en.wikipedia.org/wiki/Russian_declension)
- Tagalog symmetrical voice + ang/ng/sa: [Tagalog grammar (Wikipedia)](https://en.wikipedia.org/wiki/Tagalog_grammar), [Foley 2008](https://www.researchgate.net/publication/236902787)
- Swahili noun classes + concord: [Swahili grammar (Wikipedia)](https://en.wikipedia.org/wiki/Swahili_grammar)
- Hindi gender/case/ergative: [Hindustani grammar (Grokipedia)](https://grokipedia.com/page/Hindustani_grammar), [Hindustani declension (Wikipedia)](https://en.wikipedia.org/wiki/Hindustani_declension)
- Indonesian voice/affixes: [Indonesian affixes (Wiktionary)](https://en.wiktionary.org/wiki/Appendix:Indonesian_affixes), [Indonesian language (Wikipedia)](https://en.wikipedia.org/wiki/Indonesian_language)
- Vietnamese isolating/classifiers/tone: [Vietnamese language (Wikipedia)](https://en.wikipedia.org/wiki/Vietnamese_language)
- Spanish gender/number/conjugation: [Spanish gender & number agreement](https://www.donquijote.org/blog/spanish-adjectives-gender-and-number-agreement/)
