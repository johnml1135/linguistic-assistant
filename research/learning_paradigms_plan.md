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

Three goldens across two anchors; live Gemma runs; the tur case detector built. Measured scores
(completeness × faithfulness = overall):

| anchor | generator | overall | completeness | faithfulness | reads as |
|--------|-----------|--------:|-------------:|-------------:|----------|
| swh noun-class | heuristic | 1.00 | 1.00 | 1.00 | plumbing smoke test (heuristic hand-fit to this golden) — not a measurement |
| swh noun-class | **live Gemma (local)** | **0.63–0.75** | 1.00 | 0.63–0.75 | honest: untuned model recovers 5–6/8 cells from the packet; run-to-run variance |
| swh concord | heuristic | 0.90 | 0.90 | 1.00 | not hand-fit; concord evidence is strong |
| **tur case** | heuristic | **0.50** | **0.50 (3/6)** | 1.00 | **detector is the bottleneck** — recovers nom/dat/loc, misses acc/abl/gen |
| tur case | live Gemma (local) | 0.63 | 0.63 (≈4/6) | 1.00 | generator faithfully reports every packet cell; the gap is upstream |

What this establishes:
- **The metric works and is separable.** tur case completeness 0.5 with faithfulness 1.0 says plainly:
  fix the DETECTOR, not the prompt. swh faithfulness 0.63–0.75 with completeness 1.0 says the opposite for
  swh — the evidence is all there, the generator is what to improve.
- **The Anthropic client is fixed** (structured output via forced tool use; SDK 0.71 has no
  `output_config`). A live `opus` run additionally needs `ANTHROPIC_API_KEY` (unset here); the `local`
  llama.cpp endpoint works once server-side thinking is disabled (`enable_thinking:false`) so the model
  emits the structured answer instead of thinking to the token cap.
- **The tur case detector is real and wired** (`case_detect.py`): role-covarying noun-suffix families
  (the suffixal mirror of Bantu concord) flip the `case` switch to *present* (conf 0.85, agreeing with
  WALS) and **unlock `tur.case`** in the progressive graph. It honestly recovers ~half the 6-case system;
  the English pivot lumps dative/locative/ablative as "oblique", so the oblique cases under-separate —
  the next detector improvement (better suffix segmentation + finer oblique roles) is what the metric now
  measures.

### Case detector — 8-language spot-check (honest)
Wiring the real `detect_case` globally, the data-only verdict vs WALS:

| | swh | ind | tgl | spa | vie | tur | hin | rus |
|--|--|--|--|--|--|--|--|--|
| detector | absent | absent | absent | absent | **present** | present | **absent** | present |
| WALS | absent | absent | absent | absent | absent | present | present | present |

**6/8 correct.** The two misses are upstream, not the detector's logic:
- **vie false-positive**: the morphology inducer *over-segments isolating Vietnamese* (finds 63 "affixes"),
  which also fools the synthesis detector (it reports "fusional", so the isolating-guard can't fire). The
  WALS cross-check flags it as a low-confidence conflict. Root fix = stop over-segmenting isolating langs.
- **hin miss**: Hindi case is **postpositional/analytic** (separate words ne/ko/se), not noun suffixes, so
  a *suffixal* case detector correctly finds none. Hindi needs an analytic/adposition detector instead.

The detector is data-driven and correct wherever its inputs are sound; guards are principled (suffixing +
not-isolating + ≥2 high-purity role-covarying families, no role-diversity requirement because the English
pivot lumps the oblique cases).

### Metric integrity
`evidence_completeness` is now pure **cell coverage** (golden cells whose markers appear in the packet) —
the earlier version blended in two field-name-dependent aux booleans, which docked concord to 0.9 for
plumbing. Conditioning/residue presence is still reported in `breakdown` (builder-agnostic) but not folded
into the score, so the number moves only on real detector coverage. (Re-scored: swh concord = 1.0, tur
case = 0.5 unchanged — the tur gap is genuine 3/6, not plumbing.)

Still open (honest): n=1 golden per (lang,paradigm) still overfits — widen to ≥3 EACH; swh noun-class
completeness 1.0 was authored after seeing the packet, so it is a ceiling, not an independent check; LLM
scores are run-variable (sample ≥3 and average); fix vie over-segmentation + add an analytic-case detector
for hin. Full suite green: **205 passed** (review/ induce/ align/), 15 of them paradigm tests.

## Sources (confirmed 2026-06)
- Turkish case + vowel harmony: [Turkish grammar (Wikipedia)](https://en.wikipedia.org/wiki/Turkish_grammar), [easyturkishgrammar](https://www.easyturkishgrammar.com/post/turkish-case-suffixes)
- Russian declension/cases/gender: [Russian declension (Wikipedia)](https://en.wikipedia.org/wiki/Russian_declension)
- Tagalog symmetrical voice + ang/ng/sa: [Tagalog grammar (Wikipedia)](https://en.wikipedia.org/wiki/Tagalog_grammar), [Foley 2008](https://www.researchgate.net/publication/236902787)
- Swahili noun classes + concord: [Swahili grammar (Wikipedia)](https://en.wikipedia.org/wiki/Swahili_grammar)
- Hindi gender/case/ergative: [Hindustani grammar (Grokipedia)](https://grokipedia.com/page/Hindustani_grammar), [Hindustani declension (Wikipedia)](https://en.wikipedia.org/wiki/Hindustani_declension)
- Indonesian voice/affixes: [Indonesian affixes (Wiktionary)](https://en.wiktionary.org/wiki/Appendix:Indonesian_affixes), [Indonesian language (Wikipedia)](https://en.wikipedia.org/wiki/Indonesian_language)
- Vietnamese isolating/classifiers/tone: [Vietnamese language (Wikipedia)](https://en.wikipedia.org/wiki/Vietnamese_language)
- Spanish gender/number/conjugation: [Spanish gender & number agreement](https://www.donquijote.org/blog/spanish-adjectives-gender-and-number-agreement/)
