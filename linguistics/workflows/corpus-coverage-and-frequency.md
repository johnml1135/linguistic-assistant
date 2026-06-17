# Corpus coverage and frequency

> Measure how much of the corpus the lexicon/parser actually covers, rank what's missing by
> frequency, and find incomplete analyses — the report that prioritizes everything else.

**Primary tool(s):** Hermit Crab (parse over corpus); FLEx; FlexTools *Lexeme Usage in Corpus*,
*Incomplete Analyses*, *Check Count of Lexemes in Corpus*  ·  **Mode:** investigate  ·  **Stage in
our loop:** scan  ·  **Parallel-aware:** partial

## Goal & when it runs

A read-only measurement pass that answers "how good is coverage, and what should we fix first?" It
runs at the start of every loop and produces the **prioritized backlog** that
[[interlinearization]], [[lexeme-and-lexicon-building]], and [[morphological-parser-setup]] draw
from. Pure **investigate**: it changes nothing (except, optionally, writing frequency annotations).

## The human process (in FLEx today)

- Run the parser over the corpus; read parse statistics (parsed vs unparsed wordforms).
- *Lexeme Usage in Corpus* counts [[lexical-entry]]/[[sense]] occurrences (and can write
  "Entry Frequency"/"Sense Frequency" custom fields — its optional **change** side, the "mixed" bit).
- *Incomplete Analyses* lists corpus segments missing a morph or sense.
- *Check Count of Lexemes in Corpus* cross-checks two counting methods to catch data corruption.

## How the assistant supports it

- Run Hermit Crab over the corpus, compute **coverage** (parsed token/type %), and **rank unparsed
  forms by frequency** so impact is real, not guessed.
- Surface incomplete interlinear analyses and zero-frequency ("ghost") entries as flags.
- Emit a prioritized backlog with an **impact** field every downstream op inherits. (Optionally
  annotate frequency back as a `lexical/*` op — the only change this workflow makes, and only when asked.)

## Inputs

The corpus (interlinear texts), the lexicon, and the current Hermit Crab grammar. Parallel alignment
optionally adds source-frequency context.

## Primitives involved

[[lexical-entry]], [[sense]], [[allomorph]], [[morph-type]], [[morphosyntactic-analysis]].

## Oracle / gold / metrics

Deterministic counts from the Hermit Crab parse (coverage %, unparsed ranking) — this report *is* the
"scan" that feeds the golden-set loop; its own correctness is just count-consistency
(*Check Count of Lexemes* style).

## Outputs

A coverage/frequency report and the **prioritized backlog**. No grammar/lexicon change (frequency
annotation optional).

## Pitfalls

- **Coverage can be gamed** by over-generating allomorphs/rules that parse anything — always read it
  next to the golden-set regression gate, never alone (see [[morphological-parser-setup]]).
- **Type vs token** coverage tell different stories; report both.
- Frequency from a small/biased corpus mis-ranks impact; note corpus size/coverage caveats.

## References

FlexTools Reports & Integrity Checks modules; Maxwell (1994/2003) on HC parsing; FLEx interlinear
docs. See [../References.md](../References.md).
