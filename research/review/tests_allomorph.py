"""Offline tests for the allomorph detector: phon-neighbor generation, the meaning/complementary checks,
conditioning, and the detect() conjunction logic (via a monkeypatched survey — no THOT/vectors needed)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import allomorph as A   # noqa: E402


# ── C: phonological neighbors ───────────────────────────────────────────────────────────────────────────
def test_levenshtein():
    assert A.levenshtein("mu", "mw") == 1
    assert A.levenshtein("u", "w") == 1
    assert A.levenshtein("men", "mem") == 1
    assert A.levenshtein("mu", "soma") >= 3


def test_phon_neighbors_pairs_close_only():
    pairs = A.phon_neighbors(["mu", "mw", "ku", "kw", "soma"])
    assert ("mu", "mw") in pairs and ("ku", "kw") in pairs
    assert not any("soma" in p for p in pairs)          # too far from everything


def test_alternating_segment_vocalic():
    alt = A.alternating_segment("mu", "mw", vowels={"a", "e", "i", "o", "u"})
    assert "u" in alt["changed"] and "w" in alt["changed"] and alt["vocalic"] is True
    seg = A.alternating_segment("men", "mem", vowels={"a", "e", "i", "o", "u"})
    assert seg["vocalic"] is False                      # m/n are consonants


# ── A: meaning (features for grammatical morphemes; vectors/string for content) ─────────────────────────
def test_feature_jaccard():
    assert A.feature_jaccard("ADJ;PL;LGSPEC9", "ADJ;PL;LGSPEC9") == 1.0      # mu ≡ mw
    assert A.feature_jaccard("ADJ;PL;LGSPEC9", "V;FIN;IND;HAB;SG") == 0.0    # mu vs hu → rejected
    assert 0.0 < A.feature_jaccard("ADJ;PL;LGSPEC9", "ADJ;PL;LGSPEC6") < 1.0  # mu vs ku → partial


def test_meaning_score_features_for_grammatical():
    s, method = A.meaning_score({"features": "ADJ;PL;LGSPEC9"}, {"features": "ADJ;PL;LGSPEC9"})
    assert method == "features" and s == 1.0
    s2, _ = A.meaning_score({"features": "ADJ;PL;LGSPEC9"}, {"features": "V;FIN;IND;HAB;SG"})
    assert s2 == 0.0                                  # hu/mu correctly NOT same-meaning


def test_meaning_score_string_overlap_without_vectors():
    s, method = A.meaning_score({"english": {"the": 0.6, "a": 0.3}, "features": ""},
                                {"english": {"the": 0.6, "a": 0.3}, "features": ""}, vectors=None)
    assert method == "string-overlap" and s > 0.8


class _FakeVectors:
    available = True

    def meaning_vector(self, dist):
        m = {"big": np.array([1.0, 0.0]), "large": np.array([0.95, 0.05]), "cat": np.array([0.0, 1.0])}
        acc = None
        for w, p in dist.items():
            v = m.get(w)
            if v is not None:
                acc = v * p if acc is None else acc + v * p
        return acc


def test_meaning_score_vectors_catch_synonyms():
    s, method = A.meaning_score({"english": {"big": 1.0}, "features": ""},
                                {"english": {"large": 1.0}, "features": ""}, vectors=_FakeVectors())
    assert method == "vector" and s > 0.9              # big~large recognised as same meaning


# ── A/B: complementary distribution + conditioning ──────────────────────────────────────────────────────
def test_complementary_score_high_when_disjoint():
    a = {"right_class": {"consonant": 80, "vowel": 2}, "left_class": {"#": 82}}
    b = {"right_class": {"vowel": 28, "consonant": 1}, "left_class": {"#": 29}}
    score, dim = A.complementary_score(a, b)
    assert dim == "right_class" and score > 0.9        # one before C, one before V → complementary


def test_complementary_score_low_when_overlapping():
    a = {"right_class": {"consonant": 50, "vowel": 50}}
    b = {"right_class": {"consonant": 50, "vowel": 50}}
    score, _ = A.complementary_score(a, b)
    assert score < 0.1


def test_conditioning_reports_dominant_buckets():
    a = {"right_class": {"consonant": 80, "vowel": 2}}
    b = {"right_class": {"vowel": 28, "consonant": 1}}
    cond = A.conditioning(a, b, "right_class", "mu", "mw")
    assert cond["mu"] == "consonant" and cond["mw"] == "vowel" and cond["edge"] == "following"


# ── detect(): the conjunction (monkeypatched survey) ────────────────────────────────────────────────────
def _profiles_mu_mw(meaning_same=True, complementary=True):
    return {
        "mu": {"count": 86, "kind": "prefix", "n_hosts": 40, "english": {}, "features": "ADJ;PL;LGSPEC9",
               "right_class": {"consonant": 80, "vowel": 2}, "left_class": {"#": 82}},
        "mw": {"count": 30, "kind": "prefix", "n_hosts": 20,
               "features": "ADJ;PL;LGSPEC9" if meaning_same else "V;FIN;IND;HAB;SG", "english": {},
               "right_class": ({"vowel": 28, "consonant": 1} if complementary
                               else {"consonant": 27, "vowel": 1}),
               "left_class": {"#": 29}},
    }


def test_detect_emits_candidate(monkeypatch):
    monkeypatch.setattr(A, "survey_raw", lambda pair, **kw: _profiles_mu_mw())
    res = A.detect("swh", source="raw", use_vectors=False)
    assert len(res["candidates"]) == 1
    c = res["candidates"][0]
    assert sorted(c["members"]) == ["mu", "mw"] and c["kind"] == "allomorph-collapse"
    assert c["environment"]["mu"] == "consonant" and c["environment"]["mw"] == "vowel"
    assert c["alternating"]["vocalic"] is True
    assert c["evidence"]["complementary_score"] > 0.9
    assert c["evidence"]["meaning_method"] == "features"      # grammatical meaning via gold features


def test_detect_rejects_when_not_complementary(monkeypatch):
    monkeypatch.setattr(A, "survey_raw", lambda pair, **kw: _profiles_mu_mw(complementary=False))
    assert A.detect("swh", source="raw", use_vectors=False)["candidates"] == []


def test_detect_rejects_when_different_meaning(monkeypatch):
    # mw given hu's features → not same meaning → rejected (the hu/mu false-positive guard)
    monkeypatch.setattr(A, "survey_raw", lambda pair, **kw: _profiles_mu_mw(meaning_same=False))
    assert A.detect("swh", source="raw", use_vectors=False)["candidates"] == []


if __name__ == "__main__":
    import traceback

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn(_MP()) if "monkeypatch" in fn.__code__.co_varnames else fn()
            passed += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
