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
