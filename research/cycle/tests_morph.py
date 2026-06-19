"""Offline smoke tests for morpheme alignment + the LLM propose step (no network / no model / no hc)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from golden.grammar import Affix, LangModel, LexEntry  # noqa: E402

from cycle.llm_propose import ANALYSIS_SCHEMA, LABELS, MorphemeAnalysis, heuristic_analysis  # noqa: E402
from cycle.morph_align import morpheme_gloss_table, segment_word  # noqa: E402


def _model():
    return LangModel(
        code="t",
        lexicon=[LexEntry(form="mungu", gloss="god"), LexEntry(form="sulat", gloss="write")],
        affixes=[Affix(form="ni", gloss="-ni", kind="suffix"), Affix(form="wa", gloss="wa-", kind="prefix"),
                 Affix(form="um", gloss="<um>", kind="infix")],
    )


def test_segment_word_prefix_root_suffix():
    roots = ["mungu", "sulat"]
    seg = segment_word("wamunguni", roots, ["ni"], ["wa"], ["um"])
    assert seg == [("wa", "prefix"), ("mungu", "root"), ("ni", "suffix")]


def test_segment_word_infix():
    seg = segment_word("sumulat", ["sulat"], [], [], ["um"])
    assert ("sulat", "root") in seg and ("um", "infix") in seg


def test_segment_word_unknown_is_one_root():
    assert segment_word("xyz", ["mungu"], ["ni"], ["wa"], []) == [("xyz", "root")]


def test_morpheme_gloss_table_runs_and_keys_by_morpheme():
    rows = [(["god", "in"], ["munguni"]), (["god"], ["mungu"]), (["write"], ["sulat"])]
    table, used = morpheme_gloss_table(rows, _model(), backend="cooccur")
    assert used == "cooccur"
    # morphemes (root + the stripped suffix) are the keys, not the whole word
    assert "mungu" in table and "ni" in table
    assert all(set(v) >= {"gloss", "prob", "count", "role"} for v in table.values())


def test_heuristic_analysis_maps_function_words_and_keeps_uppercase():
    a = heuristic_analysis({"affix": "de", "current_gloss": "-de", "morpheme_alignment_gloss": "of"})
    assert a.label == "GEN" and a.category in ("inflectional", "clitic")
    b = heuristic_analysis({"affix": "s", "current_gloss": "PL", "morpheme_alignment_gloss": "the"})
    assert b.label == "PL"  # an already-inferred uppercase gloss is trusted over the noisy alignment
    c = heuristic_analysis({"affix": "zz", "current_gloss": "-zz", "morpheme_alignment_gloss": "xyzzy"})
    assert c.label == "?" and c.confidence < 0.2


def test_analysis_schema_labels_are_consistent():
    assert ANALYSIS_SCHEMA["properties"]["label"]["enum"] == LABELS
    a = heuristic_analysis({"affix": "no", "current_gloss": "-no", "morpheme_alignment_gloss": "not"})
    assert a.label in LABELS and isinstance(a, MorphemeAnalysis)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
