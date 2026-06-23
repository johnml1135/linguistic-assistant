"""Offline tests for the constraint-induction spine: the distribution information-gain judge, environment
compilation, the decision logic, and the realign PLUMBING (mock aligner — proves split tokens form and IG
goes positive on a real split, so a live "defer" is honest, not a silent bug). No THOT/HC/LLM."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align.contract import CandidateGloss, GlossTable   # noqa: E402
from review import constraints as C                      # noqa: E402
from review import dossier as D                          # noqa: E402
from review import judge as J                            # noqa: E402


# ── judge: entropy + distribution information gain ──────────────────────────────────────────────────────
def test_entropy_pure_vs_mixed():
    assert J.entropy({"a": 10}) == 0.0
    assert abs(J.entropy({"a": 5, "b": 5}) - 1.0) < 1e-9
    assert abs(J.entropy({"a": 1, "b": 1, "c": 1, "d": 1}) - 2.0) < 1e-9


def test_ig_dist_sharp_split_is_one_bit():
    # in→'you', out→'to', equal counts: mixture is 50/50 (1 bit), each bucket pure (0) → IG = 1.0
    assert J.information_gain_dist({"you": 1.0}, {"to": 1.0}, 10, 10) == 1.0


def test_ig_dist_identical_distributions_zero():
    assert J.information_gain_dist({"you": 0.5, "to": 0.5}, {"you": 0.5, "to": 0.5}, 10, 10) == 0.0


def test_ig_dist_partial_divergence_positive_but_below_one():
    ig = J.information_gain_dist({"you": 1.0}, {"you": 0.5, "to": 0.5}, 10, 10)
    assert 0.0 < ig < 1.0


def test_ig_dist_empty_is_zero():
    assert J.information_gain_dist({}, {}, 0, 0) == 0.0


# ── judge: artifact guard + decision ────────────────────────────────────────────────────────────────────
def _diverse(label, ig, cov, **kw):
    return {"label": label, "info_gain": ig, "coverage": cov, "spec": {"l": label},
            "n_in": 100, "n_out": 100, "n_hosts_in": 40, "n_hosts_out": 40,
            "top_host_share_in": 0.1, "top_host_share_out": 0.1, **kw}


def test_is_artifact_flags_single_stem_bucket():
    # carved-out (smaller) in-bucket dominated by one host word → artifact (kuwa pattern)
    r = _diverse("before w", 0.73, 0.21, n_in=90, n_out=339, n_hosts_in=2, top_host_share_in=0.85)
    assert J.is_artifact(r) is True


def test_is_artifact_passes_diverse_split():
    assert J.is_artifact(_diverse("word-initial", 0.95, 0.64)) is False


def test_decide_picks_highest_ig_genuine_not_artifact():
    results = [
        _diverse("before w", 0.73, 0.21, n_in=90, n_out=339, n_hosts_in=2, top_host_share_in=0.85),  # artifact
        _diverse("word-initial", 0.63, 0.64),                                                          # genuine
    ]
    out = J.decide_dist(results, min_gain=0.15)
    assert out["decision"] == "accept"
    assert out["best"] == "word-initial"     # genuine split wins, not the higher-IG artifact
    assert out["n_artifacts"] == 1 and out["n_genuine"] == 1


def test_decide_defers_when_only_artifacts():
    results = [_diverse("before w", 0.73, 0.21, n_in=90, n_out=339, n_hosts_in=1, top_host_share_in=0.95)]
    assert J.decide_dist(results, min_gain=0.15)["decision"] == "defer"


def test_decide_defers_when_below_min_gain():
    assert J.decide_dist([_diverse("x", 0.04, 0.5)], min_gain=0.15)["decision"] == "defer"


# ── dossier: environment compilation ────────────────────────────────────────────────────────────────────
def test_compile_env_right_in():
    label, fn = D.compile_env({"kind": "right_in", "set": ["p", "b", "m"], "label": "before labial"})
    assert label == "before labial"
    assert fn({"right": "p"}) is True and fn({"right": "t"}) is False


def test_compile_env_class_and_position():
    _, fc = D.compile_env({"kind": "right_class", "value": "vowel"})
    assert fc({"right_class": "vowel"}) is True
    _, fp = D.compile_env({"kind": "position", "value": "medial"})
    assert fp({"position": "medial"}) is True and fp({"position": "initial"}) is False


def test_compile_env_unknown_raises():
    try:
        D.compile_env({"kind": "bogus"}); assert False
    except ValueError:
        pass


def test_seed_environments_has_class_position_and_frequent_segs():
    occ = [{"right": "p", "right_class": "consonant"} for _ in range(5)] + \
          [{"right": "a", "right_class": "vowel"} for _ in range(5)]
    specs = D.seed_environments("swh", occ)
    kinds = {s["kind"] for s in specs}
    assert {"right_class", "position"} <= kinds
    assert any(s.get("set") == ["p"] for s in specs)


# ── PLUMBING: realign_distributions actually splits the token & emits positive IG on a real split ───────
def _mock_ctx():
    """A tiny hand-built ctx: 3 verses with word-MEDIAL `ku` (aligns to 'you') and 3 with word-INITIAL
    `ku` (aligns to 'to'). A perfect homograph split on the `position` environment."""
    streams, english_by_ref = [], {}
    for i in range(3):
        ref = f"M{i}"
        morphs = [{"form": "a", "_word": "anakupenda"}, {"form": "na", "_word": "anakupenda"},
                  {"form": "ku", "_word": "anakupenda"}, {"form": "penda", "_word": "anakupenda"}]
        streams.append((ref, 0, morphs)); english_by_ref[ref] = ["you"]
    for i in range(3):
        ref = f"I{i}"
        morphs = [{"form": "ku", "_word": "kusoma"}, {"form": "soma", "_word": "kusoma"}]
        streams.append((ref, 0, morphs)); english_by_ref[ref] = ["to"]
    return {"pair": "swh", "morpheme": "ku", "kind": "prefix", "streams": streams,
            "english_by_ref": english_by_ref, "pos_of": {}}


def _mock_aligner(rows):
    """Stands in for THOT: asserts the bare token was split, then maps each split token to its sense."""
    tokens = {t for _src, forms in rows for t in forms}
    assert "ku" not in tokens, "bare morpheme should have been split into ku␁in / ku␁out"
    tbl = GlossTable()
    if "ku␁in" in tokens:
        tbl.table["ku␁in"] = [CandidateGloss("ku␁in", "you", 1.0, 1)]
    if "ku␁out" in tokens:
        tbl.table["ku␁out"] = [CandidateGloss("ku␁out", "to", 1.0, 1)]
    return tbl


def test_realign_plumbing_splits_and_goes_positive():
    ctx = _mock_ctx()
    r = D.realign_distributions(ctx, {"kind": "position", "value": "medial"}, align_fn=_mock_aligner)
    assert r["n_in"] == 3 and r["n_out"] == 3          # medial ku (3) vs initial ku (3)
    assert r["dist_in"] == {"you": 1.0} and r["dist_out"] == {"to": 1.0}
    ig = J.information_gain_dist(r["dist_in"], r["dist_out"], r["n_in"], r["n_out"])
    assert ig == 1.0                                    # a clean split → maximal gain (plumbing proven)


def test_realign_no_gain_when_sense_independent_of_env():
    """Same ctx but the (mock) aligner maps BOTH split tokens to 'you' — env doesn't predict the sense."""
    ctx = _mock_ctx()

    def flat(rows):
        tbl = GlossTable()
        for t in {t for _s, fs in rows for t in fs if t.startswith("ku␁")}:
            tbl.table[t] = [CandidateGloss(t, "you", 1.0, 1)]
        return tbl

    r = D.realign_distributions(ctx, {"kind": "position", "value": "medial"}, align_fn=flat)
    assert J.information_gain_dist(r["dist_in"], r["dist_out"], r["n_in"], r["n_out"]) == 0.0


def test_llm_environments_degrades_to_empty_offline():
    assert C.llm_environments({"morpheme": "u", "seed_environments": []}) == []


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); passed += 1; print(f"  ok  {fn.__name__}")
        except Exception:
            print(f"FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
