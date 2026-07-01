# THOT Eflomal vs. THOT HMM — measured comparison

`align/` switched its THOT backend from `hmm` to `eflomal` (`sil-machine[thot]>=1.9`, native to
`sil-thot>=3.5`; not the standalone POSIX-only `eflomal` PyPI package — see `README.md`). This is the
measured before/after on `align.morph_align_hc`'s own reported quality signal: the **THOT ∩ HC
accept rate** (of all morpheme markers, how many have a THOT alignment that *agrees* with the
independently-parsed Hermit Crab gloss — the fraction the pipeline can confidently raise into the
gold data via `deltas/`, vs. defer). Higher is better — it is the size of the deployable
high-confidence tier, not word-alignment accuracy against a gold alignment (no gold alignment exists
for these pairs).

Method: `python -m align.morph_align_hc --pair <p> --backend <hmm|eflomal> --sample <n>`. `hmm` was
removed from the shipped CLI as part of this transition; the HMM numbers below were reproduced with a
throwaway benchmark shim that calls `word_align_corpus(aligner="hmm")` directly, for comparison only.

## First pass was misleading — a metric bug, not an aligner difference

The first measurement round showed HMM ahead by up to 7 points on swh. Manually diffing the two
backends' markers (per-marker accept/defer disagreement) traced almost the entire gap to a
pre-existing bug in `_agrees()`: its substring-overlap fallback let 1–2 letter source tokens
spuriously "agree" with grammatical gloss tags via coincidental substring containment — e.g. the
English word `"a"` is a literal substring of the gloss tag `"ADJ"`, and `"in"` is a substring of
`"IND"`. HMM happened to guess these short function words for two very common Swahili noun-class /
verb-agreement prefixes; the bug then credited that as "agreement" even though `"a"`/`"in"` have no
real relationship to noun class or verb agreement marking. **All 764 of the 904 "HMM accept, eflomal
defer" disagreements on swh/400 collapsed into exactly 2 repeated (form, gloss, guess) triples**, both
this exact artifact — zero genuine affix-level HMM wins. On the *genuine* (non-artifact) root-level
(content-word) disagreements, eflomal actually won more of them than HMM (182 vs. 121), and a manual
read of a sample confirmed eflomal's picks were correct where HMM's were wrong (e.g. `musa`→`moses`
vs. HMM's `priest`; `petro`→`peter` vs. HMM's `lying`; `nzige`→`locusts` vs. HMM's `was`).

Fixed `_agrees()` to require the source token be >2 characters before applying the substring
fallback (exact/set-membership matches, which is how real short-word agreement like `"you"`↔`"you
(2SG.OBJ)"` is detected, are unaffected). Existing tests (`tests_morph_align_hc.py`) still pass.

## Corrected results (post-fix, same runs, 400 verses)

| Pair | HMM accept rate | Eflomal accept rate | Δ |
|---|---|---|---|
| swh | 21.7% (1962/9033) | 22.5% (2041/9074) | +0.8pp (eflomal) |
| spa | 22.8% (2706/11884) | 23.2% (2752/11883) | +0.4pp (eflomal) |
| tgl | 33.9% (3233/9539) | 34.0% (3245/9539) | +0.1pp (eflomal) |

## Verdict

Once the `_agrees()` bug is fixed, eflomal is consistently at or slightly ahead of HMM on all three
pairs — not the clear regression the first (buggy) pass suggested. The two are close enough that this
reads as "roughly equivalent quality, eflomal very slightly ahead" rather than a decisive win either
way; the earlier "HMM is better" conclusion was an artifact of the metric, not the aligner. Combined
with eflomal's native Windows support (`sil-thot>=3.5` wheels) and the intent of this transition, this
supports keeping eflomal as the default.

Not investigated (follow-up, if it matters enough to chase): tuning `eflomal_lex_alpha` /
`eflomal_jump_alpha` / iteration counts (currently `sil-machine` defaults, tuned for larger MT
corpora) for these short low-resource verse corpora; behavior at full-NT scale (7k+ verses/pair)
rather than the 400-verse samples used here.

## Follow-up (batch 1): three more data-quality bugs found sampling swh output

Prompted by the metric-bug discovery above, sampled `align.morph_align_hc`'s swh/400 output more
broadly to check for other correctness issues in the pipeline (independent of which THOT backend is
used — these affect both). Checked five areas; three had real bugs, now fixed:

1. **`_agrees()` compound-gloss tokenization (fixed).** Wiktionary-derived glosses like
   `"Applicative_form_of_-amba:_to_tell"` or `"contraction_of_mke_+_wako:_your_wife"` weren't split on
   `_`/`:`, so they stayed one glued string and only matched via lucky substring containment. No
   observed false positives yet, but grammatical scaffolding words (`"form"`, `"of"`, `"class"`,
   `"passive"`, …) that appear in the description — never the actual meaning — were one coincidental
   alignment away from a spurious accept (e.g. `"[[Appendix:Swahili_noun_classes#Ji-ma_class|ji_class_"`
   contains the literal token `"class"`). Now: appendix/citation glosses (`"[["`-prefixed) never agree;
   compound glosses are split on `_`/`:`/`|`/`;`/`=`, take only the text after the last `:` (the real
   meaning, not the grammatical description), and filter a curated scaffold-word list.
2. **`assemble_markers()` accepting ambiguous parses (fixed, real impact: 346 markers on swh/400).**
   The accept gate checked `unparsed` and `unmapped` but not `ambiguous` — so a word HC parsed multiple
   ways, with none matching a known gold line (meaning the segmentation itself is an arbitrary pick,
   not a verified one), could still have its arbitrarily-chosen morphemes raised into gold data via
   `deltas/` if THOT's alignment happened to look confident. This directly contradicted the module's
   own stated design ("precision over recall — never a silent wrong marker"). Fixed: `ambiguous` now
   blocks `accept` like `unparsed`/`unmapped` do.
3. **`gloss_index()` collapsing the placeholder gloss `"?"` (fixed, serious — was corrupting
   segmentation).** `"?"` is the model's own sentinel for "no real gloss yet," and **1,548 distinct
   lexicon entries** in the swh reference model share it. `gloss_index()` indexed it like any other
   gloss, so it collapsed all 1,548 into one arbitrary highest-count entry. Any word whose HC parse
   contained an unknown-gloss morpheme (`"?"` in the gloss line) then got peeled/labeled using that one
   unrelated root's surface form and POS — not a display bug, a real segmentation corruption. Confirmed
   in the data: e.g. `hukumu` (a real Swahili word) was being torn down to a bogus 1-letter root `'u'`
   with `pos: "Verb"` borrowed from an unrelated lexicon entry. Fixed by excluding `"?"` from the index
   entirely, so these words now correctly fall through to the existing `unmapped` path (kept whole,
   flagged) instead. Before the fix, 39 markers on swh/400 had a suspicious ≤1-character "root" form;
   after, zero.

Checked and found clean (no fix needed): `table.best()` form lookup (only 30/9063 markers — 0.3% — had
no alignment at all, and none of those forms were *ever* aligned elsewhere in the run, i.e. genuinely
rare words, not a systematic key-mismatch); `gloss_index()`'s root-vs-affix tie-break rule (roots
unconditionally win ties over affixes on a shared gloss — deliberate, no counter-evidence found).

These three fixes reduce raw accept counts on both backends (fewer, more trustworthy accepts — e.g.
swh/400 eflomal accept rate moved from 22.5% to 19.8% after the ambiguous-gate fix, then marker count
dropped from 9078 to 8933 after the `"?"`-collision fix, accept rate ~19.7%), but the *relative*
eflomal-vs-HMM comparison is unaffected: eflomal remained slightly ahead of HMM (19.8% vs. 19.0% on
swh/400) under the corrected metric. Full test suite (232 tests) passes after all fixes.

## Follow-up (batch 2): a severe delta-store dedup bug, plus a dead feature flag

Second sampling pass, five more areas:

1. **Affix-peeling boundary condition in `morphemes_of()` — checked, clean.** Worried the strict
   `len(residual) > len(form)` guard (vs. `>=`) could leave a prefix/suffix unpeeled when it exactly
   consumes the residual. Instrumented the real peel loop over all 2,073 swh/400 word types: zero
   exact-consume cases occurred. A "residual still starts with its own prefix" check flagged 10 words,
   but all were false positives from my own diagnostic — real Swahili roots that happen to start with
   the same two letters as their prefix (e.g. `kukubali` → prefix `ku-` + root `kubali`, where `kubali`
   coincidentally also starts with `ku`). No bug.
2. **`word_morphemes()`'s `gold_line` parameter — dead code (documented, not fixed).** The function is
   written to prefer a gold-matching analysis when a word has multiple parses (`"gold-matching if
   present, else first"`), but grepping every call site confirms `gold_line` is **never supplied
   anywhere in the codebase** — `build_streams()` always calls it with 3 args, so the gold-preferring
   branch is unreachable and every ambiguous word silently gets `analyses[0]` (whatever order Hermit
   Crab returns, not verified against anything). Not touched: correctly wiring this would need new
   logic to map a gold wordform's features to the matching `gloss_line` tuple, which doesn't exist yet
   and is too large a change to improvise safely here. The batch-1 `ambiguous` accept-gate fix already
   prevents this from silently corrupting gold data — this is a missed-recall gap, not a correctness
   bug, now that it's understood.
3. **`_verses()`'s `t.isalpha()` filter (source vs. target asymmetry) — checked, clean.** Target tokens
   are filtered to alphabetic-only; source tokens aren't filtered at all. Worried this could inject
   noise into alignment training (punctuation "words" on the source side with nothing to align to).
   Checked real data: source tokens (from the eBible build pipeline) are already 100% alphabetic before
   reaching `_verses()` — the asymmetry exists in the code but never manifests, since upstream already
   cleans the source side by construction.
4. **`ACCEPT_PROB = 0.5` threshold — checked, looks correctly conservative.** 139 markers on swh/400
   agree with HC (`agrees_with_hc=True`) but fall under the 0.5 confidence cutoff and get deferred
   anyway. That's the intended "precision over recall" tradeoff, not a bug — spot-checking the
   borderline accepts just above 0.5 (e.g. `fikiri`→`think`, `dhambi`→`sins`, `eneo`→`region`) shows
   the threshold is picking up genuinely correct matches, not noise. No retuning without a real gold
   alignment to validate against.
5. **`DeltaStore` dedup key for `lexical.sense.create` ops (fixed — the serious one).**
   `propose/change_set.py`'s `_KEY_FIELD` mapped `"lexical.sense.create"` → `"gloss"`, not `"entry"`.
   Since `op_signature()` is what `DeltaStore.add()` uses to decide "is this a repeat of something
   already queued," this meant **two different lexical entries that happen to share an English gloss
   collide into one delta record** — the second one is silently merged away instead of recorded.
   Confirmed with real data: on swh/400 alone, 19 distinct English glosses among accepted root markers
   already map to multiple different Swahili forms (e.g. `"father"` ← both `baba` and `babu`, which are
   different words — grandfather vs. father; `"wife"` ← `mkeo`/`mkewe`, different possessive forms).
   Had `--apply` been run, proposing `babu`'s sense after `baba`'s would have been silently dropped as
   a "duplicate," never reaching a human reviewer. Fixed by keying `lexical.sense.create` on `"entry"`
   instead — verified `engine/scorer.py` (the only other real consumer of sense-gloss data) already
   does its own entry-keyed lookup independent of this mapping, so nothing relies on the old gloss key.
   Test suite (254 tests, now including `propose/`/`engine/`/`eval/`) passes.
