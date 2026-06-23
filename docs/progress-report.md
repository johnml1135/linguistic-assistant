# Linguistic Assistant — progress report (2026-06-23)

_Per the four eBible NTs. Switch marks: ✓ agrees with reference typology · ⚠ conflicts (low-confidence, flagged for review) · · no reference._

## Corpus (the denominator)

| pair | verses | tokens | unique forms | hapax% |
|---|--:|--:|--:|--:|
| spa | 7948 | 164,072 | 11,004 | 47% |
| ind | 7936 | 166,020 | 6,957 | 39% |
| tgl | 7948 | 192,532 | 8,831 | 44% |
| swh | 7948 | 141,406 | 17,541 | 63% |

## Parsing — words parsed well vs the number needing parsing

| pair | sample tested | parsed | coverage | ex-names | real morphology gap | likely names |
|---|--:|--:|--:|--:|--:|--:|
| spa | 250 | 236 | 94% | 94% | 14 | 0 |
| ind | 250 | 248 | 99% | 99% | 2 | 0 |
| tgl | 250 | 0 | 0% | 0% | 2 | 248 |
| swh | 250 | 171 | 68% | 85% | 30 | 49 |

_Coverage = parsed / tested on a held-out frequent-form sample; the real morphology gap (not names) is what's left to close._

## Lexicon · morphology · phonology

| pair | lemmas | glossed | affixes | infl-classes | wordforms | phon rules |
|---|--:|--:|--:|--:|--:|--:|
| spa | 5,431 | 92% | 1597 | 27 | 10,543 | 3 |
| ind | 3,655 | 95% | 44 | 5 | 6,261 | 3 |
| tgl | 4,183 | 68% | 0 | 0 | 4,029 | 1 |
| swh | 6,615 | 49% | 182 | 2 | 5,054 | 1 |

## The 12 master switches (chosen value · alignment with the data)

| switch | spa | ind | tgl | swh |
|---|---|---|---|---|
| synthesis | fusional ✓ | agglutinative ✓ | fusional ⚠ | agglutinative ✓ |
| affix_polarity | suffixing · | both ⚠ | prefixing ✓ | prefixing ✓ |
| infixation | True ⚠ | True ✓ | True ✓ | True ⚠ |
| reduplication | True ⚠ | True ✓ | True ✓ | True ✓ |
| vowel_harmony | False ✓ | False ✓ | False ✓ | True ✓ |
| nasal_assimilation | True ⚠ | True ✓ | True ✓ | False ⚠ |
| tone | False ✓ | False ✓ | False ✓ | False ✓ |
| gender_or_noun_class | gender ✓ | noun-class ⚠ | noun-class ⚠ | noun-class ✓ |
| case | absent ✓ | absent ✓ | absent ✓ | absent ✓ |
| tam_locus | verb-suffix · | — · | — · | verb-prefix · |
| agreement_head_marking | none ⚠ | — · | — · | subject ✓ |
| articles | both ✓ | — · | — · | both ⚠ |

**Switch alignment with the data** (of switches with a reference):
- **spa**: 6/10 agree with reference · 4/12 high-confidence · 4 flagged conflict
- **ind**: 7/9 agree with reference · 4/12 high-confidence · 2 flagged conflict
- **tgl**: 7/9 agree with reference · 5/12 high-confidence · 2 flagged conflict
- **swh**: 8/11 agree with reference · 8/12 high-confidence · 3 flagged conflict

## Headline indicators

| pair | scripture parse-cov | gloss% | real gap | switches agree | switches hi-conf |
|---|--:|--:|--:|--:|--:|
| spa | 94% | 92% | 14 | 6/10 | 4/12 |
| ind | 99% | 95% | 2 | 7/9 | 4/12 |
| tgl | 0% | 68% | 2 | 7/9 | 5/12 |
| swh | 68% | 49% | 30 | 8/11 | 8/12 |
