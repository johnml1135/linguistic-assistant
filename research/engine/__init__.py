"""HermitCrab grammar model + the ablate -> propose -> score virtuous-cycle harness.

Origin-agnostic: given a set of segmented, glossed words (:class:`golden.igt.MorphWord`)
from any ingester, ``grammar.build_model`` derives a candidate lexicon + affix-template
model, ``hc`` emits a HermitCrab grammar and drives the ``hc`` CLI to parse/score it, and
``ablate``/``score`` run the golden-set improvement loop (remove a morpheme -> propose a
fix -> gate on HC re-parse with zero regression). ``scorer.build_scorer`` /
``instances.make_instances`` expose this to ``research/eval``; ``assess`` reuses the
``LangModel`` + ``hc`` for its metric/MDL scorecards.

The data origin is eBible parallel text + statistical word glosses + FieldWorks data — NOT
a pre-annotated IGT corpus. See ``README.md``.
"""
