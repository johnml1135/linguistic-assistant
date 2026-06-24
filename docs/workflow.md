# Working through a language — the process

This is the human's guide to documenting a language with the assistant. It describes the **phases you move
through** and, inside each, **who decides what**. The tool does a great deal of analysis, but the decisions
that everything else depends on are yours. The guiding rule:

> **The machine suggests, populates, and flags — with evidence. You own the foundational cuts. Once you
> commit a decision, the system respects it and operates inside it, raising refinements and exceptions for
> your approval rather than quietly changing what you decided.**

There are three foundational phases, in this order, because each constrains the next:

1. **Switches** — the typological frame (what kind of language this is).
2. **Classes** — the noun/verb class system (the schema everything else compiles from).
3. **Exceptions & rules** — the morphophonology and agreement, layered, scoped to your classes.

You don't finish one before touching the next — but you *commit* them in this order, because a class
decision assumes the switches, and a rule assumes the classes.

---

## The lifecycle inside every phase

Each phase runs the same four steps. The middle one is a gate only you pass through.

| step | who | what happens |
|---|---|---|
| **Suggest** | machine | analyses the corpus, proposes an answer **with the evidence**, and — where the choice is genuinely subjective — lays out the *alternatives* (where a break could fall, how many classes, naming options) and their trade-offs. It does not commit anything. |
| **Define / Confirm** | **you** | you make the call: confirm, adjust, or override. This is deliberate. The more foundational the decision, the more this matters. |
| **Utilize** | machine | everything downstream is rebuilt from your committed decision. The machine now *fits to* and *flags against* it — it does not re-derive it. |
| **Refine** | you ↔ machine | as evidence accumulates, the machine raises proposals — a tightened rule, a new exception, a possible re-break — for your approval. Accepting one updates the committed decision and recompiles. Until then, your decision stands and is used as-is. |

Two things hold across all phases:

- **Nothing foundational is auto-committed.** The machine never decides class boundaries or names on its own.
- **Every change flows through review and is recorded.** Decisions are versioned; downstream recompiles when
  you accept a change. The reference data the system measures against is never silently rewritten.

### The auto-push tier (so you aren't asked to confirm everything)

Confirming every trivial item would sink the tool, so high-confidence work is pushed through automatically
and stamped **"good enough — AI generated."** Two guardrails keep that honest:

- **"Confident enough" means *verified*, not self-reported.** The trigger is a verification signal — a rule
  reproduces the attested forms through the parser, productivity holds against the rule's own
  counterexamples, the alignment corroborates — not the model's own say-so. The stamp records what verified it.
- **Auto-push is for leaves, never for the compile root.** Reversible, derived decisions auto-push (an
  individual allomorph, a single exception, a noun's *assignment* to an already-declared class, a concord
  cell). The **class system itself** — the breaks, names, numbers — never auto-commits; the machine proposes
  the whole system and you ratify it (one click is fine), because everything compiles from it.

| phase | auto-push when verified-confident? |
|---|---|
| **Switches** (allowed/not) | yes — stamped, revisable |
| **Classes** — the *system* (compile root) | **no** — you ratify (one-click ok), never silent |
| **Classes** — a noun's *assignment* to a declared class | yes — stamped, reversible |
| **Exceptions/rules** — individual items | yes — stamped, reversible |

Everything auto-pushed is stamped, queued in a "review later" lane, and reversible — so the tier is a
fast path, never a black hole.

---

## Phase 1 — Switches: the typological frame

**What it is.** A small set of master switches that say what kind of language this is — degree of synthesis,
prefixing vs suffixing, whether there's vowel harmony, nasal assimilation, tone, a gender/noun-class system,
case, where tense/aspect lives, head- vs dependent-marking, articles, infixation, reduplication.

**Why first.** They're cheap to detect and they *constrain everything after*. Knowing the language is
agglutinative and prefixing, with a noun-class system, tells the tool where to look and what not to propose.

**How you work through it.** The machine detects each switch from the corpus and cross-checks it against
typological databases (WALS/Grambank), then presents each with its evidence and its confidence. You confirm
or override. Conflicts (corpus says one thing, the database another) are flagged, not hidden. Your answers
are recorded in the language profile and from then on constrain detection.

**Your role:** ratify the frame. It's quick, but it sets the search space for the hard phases.

---

## Phase 2 — Classes: the schema everything compiles from

**What it is.** The noun classes (or genders, or verb classes) — *and* how they show up on the words around
the noun. A class isn't just a prefix on the noun; it **propagates** to adjectives, verbs, demonstratives.
The same adjective "big" appears as `ukulu / ikulu / cikulu`, the prefix tracking the class of the noun it
modifies; Spanish `el / la` is the article tracking gender. The full picture is a **concord table**: for each
class, which prefix appears on each kind of agreeing word.

**Why you must own this.** Where the breaks fall, how many classes there are, what to number and name them —
these are foundational and partly subjective, and **everything else falls out of them**. The class labels
become the vocabulary of every later rule. So this is the one decision the tool will not make for you.

**How you work through it.**

- **Suggest:** the machine groups words by how they *agree* (two nouns are the same class when they trigger
  the same agreements — not merely when they share a prefix), proposes a candidate inventory and concord
  table, and surfaces the judgment calls: where two classes might merge or one might split, alternative
  numbering, the database comparison.
- **Define:** you declare the authoritative class system — numbers, names, boundaries, membership criteria.
  This is recorded in the language profile as the **compile root**: the grammar's class features, the concord
  cells, and the scope of every later rule are generated from it.
- **Utilize:** the machine now *assigns* words to your defined classes, *fills in* the concord table, and
  *flags* what doesn't fit — a noun whose agreement disagrees with its class becomes either an exception
  under that class or, if several misfits form a pattern, a **proposed amendment** (a split, a new subclass)
  with evidence. It never silently re-clusters.

**Your role:** define the system after careful thought; then let the tool work inside it and bring you the
misfits.

---

## Phase 3 — Exceptions & rules: the layered detail

**What it is.** The predictable changes — a prefix reshaping before a vowel (`mu → mw`), a class's concord,
a stem alternation — *and* their exceptions. Real rules are layered, like the spelling rule "*i before e,
except after c, except when sounded as A (neighbor, weigh), except seize/weird*": a **default**, then
**classes of exceptions**, then **individual** exceptions. We model each fact as one **ordered block**:

```
default rule              the general pattern
 ├ exception class 1       a tighter environment that overrides it
 ├ exception class 2       another (e.g. a loanword stratum, a semantic group)
 └ individual exceptions   the handful nothing generalizes
```

Ordered most-specific-first, so the specific cases win where they apply (the Elsewhere principle).

**What conditions a rule** can be any of three things — the tool tests which:

- the **adjacent sound** (phonology — `u → w` before a vowel),
- the **slot** in the word (a prefix vs an infix position),
- the **class of an agreeing word** (agreement — the concord prefix tracks the head noun's class).

Agreement is just a rule whose conditioner lives in another word; it uses the same block structure
(`el / la`, then `el` before a stressed *a*- noun like *el agua*, then lexical exceptions).

**How you work through it.**

- **Suggest:** the machine finds same-meaning form families, works out what conditions the choice, and —
  when a single rule has too many exceptions to be one clean rule — *carves the exceptions into the largest
  regular sub-pattern it can*, recursively, until only individuals remain. It proposes each exception class
  **with a reason** (a sound class, a loan set, a semantic group) and checks the whole block actually
  reproduces every attested form through the parser.
- **Confirm / Refine:** you see the block as a tree — rule, its exceptions, the exceptions that break those
  exceptions — each node with its supporting data. You refine *the block as a whole*: tighten the default,
  promote an individual into a class or demote a thin class to a list, reorder, split or merge. The block
  re-validates after each edit.

**Your role:** judge the layering. The tool does the carving and the verification; you decide what's a real
class of exceptions versus a list, and whether each "why" holds.

---

## How a session tends to flow

```
orient → confirm the switches → define the class system → work the rules & exceptions
                                        │                          │
                                        ▼                          ▼
                                  (compile root)            review queue: misfits,
                                                            exception classes, amendments
                                        └──────── you accept ───────┘  → recompiles, re-validates
```

You move down into detail and back up to revise — but the commit order holds: switches frame the classes,
classes are the vocabulary of the rules, rules and their exceptions are scoped to the classes.

---

## Principles that hold throughout

- **You own the foundational and subjective cuts; the machine owns the tractable, checkable work** — detect,
  populate, verify, flag. It surfaces the choices; it doesn't make the ones that are yours.
- **Everything compiles from your committed decisions.** Change a switch, a class, or a rule and the
  downstream artifacts rebuild from it — there's one source of truth per decision, and it's the one you
  ratified.
- **Claims are verified, not asserted.** A proposed rule must reproduce the attested forms through the parser
  (a round-trip), and a rule's productivity is judged against *its own counterexamples* and a tolerance for a
  bounded number of exceptions — not against a convenient sample. The tool reports what it actually checked.
- **Changes are gated and recorded.** Refinements and exceptions are proposals you approve; accepting one
  versions the decision and recompiles. The independent reference the system grades itself against is never
  rewritten to make results look better.
- **Audio is always optional.** Where recordings exist they can raise confidence or break a tie, but no step
  ever requires them; the whole process runs from text alone.

---

## Where the detail lives

- `docs/phonology-architecture.md` — the rule pipeline (substrate → detect → underlying form → ordered rule
  → verify → promote) and how the layered blocks + class schema compile into Hermit Crab.
- The language profile — your committed switches and class schema (the compile root).
- The review queue — the working surface for misfits, exception classes, and amendments.
