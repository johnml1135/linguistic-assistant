"""Offline smoke tests for the PolyGloss conversion/gold/scoring pipeline. Run:
`python research/corpus/polygloss/tests_smoke.py` (pytest-discoverable). No network, no `hc` CLI —
exercises only the pure conversion/scoring logic against a hand-built fixture row.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from corpus.polygloss.convert import (  # noqa: E402
    is_english_metalanguage,
    is_grammatical_gloss,
    stem_and_features,
    to_morphwords,
    to_parallel_row,
)
from corpus.polygloss.schema import PolyglossRow  # noqa: E402
from corpus.polygloss.score import score_parses  # noqa: E402
from corpus.polygloss.run_batch import write_report  # noqa: E402
from corpus.polygloss.to_gold import rows_to_wordforms_and_lexicon  # noqa: E402

# A real PolyGloss-shaped row (Vera'a; the exact example surfaced by the paper's research).
ROW = PolyglossRow(
    id="ex1",
    source="polygloss-test",
    transcription="o wōlēn 'ēqēk",
    translation="Oh, over there is my garden",
    glottocode="vera1241",
    language="Vera'a",
    metalanguage="English",
    metalang_glottocode="stan1293",
    segmentation="o wōlē-0=n 'ēqē-k",
    glosses="INTERJ you.know-ZERO=ART garden-1SG",
)

MISALIGNED_ROW = PolyglossRow(
    id="ex2", source="polygloss-test", transcription="x", translation="y",
    glottocode="vera1241", language="Vera'a", metalanguage="English", metalang_glottocode="stan1293",
    segmentation="a-b", glosses="ONLY_ONE_TAG",  # morph-count mismatch within the word
)


def test_to_morphwords_segments_and_glosses_by_boundary():
    words = to_morphwords(ROW)
    assert len(words) == 3
    w0, w1, w2 = words
    assert w0.surface == "o" and w0.gold_analysis == [("o", "INTERJ")]
    assert w1.surface == "wōlē0n"
    assert w1.gold_analysis == [("wōlē", "you.know"), ("0", "ZERO"), ("n", "ART")]
    assert [m.boundary for m in w1.morphs] == ["", "-", "="]
    assert w2.surface == "'ēqēk"
    assert w2.gold_analysis == [("'ēqē", "garden"), ("k", "1SG")]


def test_misaligned_word_is_skipped_not_guessed():
    assert to_morphwords(MISALIGNED_ROW) == []


def test_is_grammatical_gloss_leipzig_convention():
    assert is_grammatical_gloss("ART") and is_grammatical_gloss("1SG") and is_grammatical_gloss("0")
    assert not is_grammatical_gloss("garden") and not is_grammatical_gloss("you.know")


def test_stem_and_features_splits_lexical_from_grammatical():
    words = to_morphwords(ROW)
    stem0, feats0 = stem_and_features(words[0])  # "o"/INTERJ — no lexical stem at all
    assert stem0 is None and feats0 == ["INTERJ"]
    stem1, feats1 = stem_and_features(words[1])
    assert stem1.form == "wōlē" and stem1.gloss == "you.know"
    assert feats1 == ["ZERO", "ART"]
    stem2, feats2 = stem_and_features(words[2])
    assert stem2.form == "'ēqē" and stem2.gloss == "garden" and feats2 == ["1SG"]


def test_is_english_metalanguage_filter():
    assert is_english_metalanguage(ROW)
    spanish_row = PolyglossRow(id="ex3", source="s", transcription="t", translation="tr",
                                glottocode="g", language="L", metalanguage="Spanish",
                                metalang_glottocode="spa1234")
    assert not is_english_metalanguage(spanish_row)


def test_to_parallel_row_tokenizes_both_sides():
    src, tgt = to_parallel_row(ROW)
    assert src == ["oh", "over", "there", "is", "my", "garden"]
    assert tgt == ["o", "wōlēn", "ēqēk"]  # tokenizer drops the leading apostrophe as non-word


def test_rows_to_wordforms_and_lexicon_skips_stemless_words():
    wordforms, lexicon = rows_to_wordforms_and_lexicon([ROW, MISALIGNED_ROW], glottocode="vera1241")
    # "o"/INTERJ has no stem -> skipped; wōlē and 'ēqē each produce one wordform.
    assert len(wordforms) == 2
    surfaces = {w["surface"] for w in wordforms}
    assert surfaces == {"wōlē0n", "'ēqēk"}
    lemmas = {e["word"] for e in lexicon}
    assert lemmas == {"wōlē", "'ēqē"}
    wf_by_surface = {w["surface"]: w for w in wordforms}
    assert wf_by_surface["'ēqēk"]["lemma"] == "'ēqē"
    assert wf_by_surface["'ēqēk"]["features"] == ["1SG"]


def test_score_parses_separates_parse_lemma_and_feature_recall():
    wordforms = [
        {"surface": "wōlē0n", "lemma": "wōlē", "features": ["ZERO", "ART"]},
        {"surface": "'ēqēk", "lemma": "'ēqē", "features": ["1SG"]},
        {"surface": "unseen", "lemma": "'ēqē", "features": ["1SG"]},
    ]
    lemma_gloss = {"wōlē": "you.know", "'ēqē": "garden"}
    parses = {
        # correct lemma + correct features
        "wōlē0n": [[("wōlē", "you.know"), ("0", "ZERO"), ("n", "ART")]],
        # parses, but to the WRONG lemma (a homograph/ambiguity case)
        "'ēqēk": [[("'ēqē", "house"), ("k", "1SG")]],
        # "unseen" has no HC analysis at all
    }
    result = score_parses(wordforms, lemma_gloss, parses)
    assert result["tested"] == 3
    assert result["parse_rate"] == round(2 / 3, 4)     # wōlē0n + 'ēqēk parsed; unseen did not
    assert result["lemma_recall"] == round(1 / 3, 4)   # only wōlē0n got the right lemma
    assert result["feature_recall"] == round(1 / 3, 4)  # only wōlē0n satisfied lemma+features
    assert "unseen" in result["miss_parse"]
    assert any("'ēqēk" in m for m in result["miss_lemma"])


def test_write_report_handles_ok_and_error_rows(tmp_path=None):
    """Regression test: `write_report` once assumed a top-level `r["language"]` key that only exists
    on error rows a batch run constructs itself — successful rows nest it under `r["manifest"]
    ["language"]` (`run_pilot`'s return shape). This bug only surfaced after an hour-long batch run
    because `write_report` was never exercised before that. Covers both row shapes with fake data."""
    import tempfile
    from pathlib import Path

    ok_row = {
        "glottocode": "xx1234", "language": "Xtestlang", "typology_note": "fixture",
        "status": "ok", "secs": 1.0,
        "manifest": {"language": "Xtestlang", "gold_source_split": "test", "rows_train_english_meta": 42},
        "induction": {"base_coverage": 0.0, "final_coverage": 0.5,
                      "lexicon": {"glossed_frac": 0.8}, "enumeration_debt": 2},
        "gold_benchmark": {"parse_rate": 0.5, "lemma_recall": 0.3, "feature_recall": 0.2},
    }
    error_row = {
        "glottocode": "yy9999", "language": "Yfaillang", "typology_note": "fixture",
        "status": "error", "error": "RuntimeError: boom", "secs": 0.5,
    }
    out_dir = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    path = out_dir / "PILOT_REPORT.md"
    write_report([ok_row, error_row], path)
    text = path.read_text(encoding="utf-8")
    assert "Xtestlang" in text and "1 succeeded, 1 failed" in text
    assert "ERROR: RuntimeError: boom" in text


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
