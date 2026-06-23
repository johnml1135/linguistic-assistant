"""Offline tests for the grammar-assessment measures. Run: `python research/assess/tests_smoke.py`
(also pytest-discoverable). No `hc`, no network.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assess import inventory, metrics  # noqa: E402
from assess.scorecard import Scorecard  # noqa: E402
from assess.worst_part import worst_part_ranking  # noqa: E402


def test_coverage():
    parses = {"a": [("x",)], "b": [], "c": [("y",), ("z",)]}
    cov = metrics.coverage(parses, {"a": 2, "b": 5, "c": 1})
    assert abs(cov["coverage_type"] - 2 / 3) < 1e-5
    assert abs(cov["coverage_token"] - 3 / 8) < 1e-5


def test_spurious_ambiguity():
    parses = {"a": [("x",)], "b": [], "c": [("y",), ("z",)]}
    amb = metrics.spurious_ambiguity(parses)
    assert abs(amb["mean_analyses"] - 1.5) < 1e-5
    assert abs(amb["ambiguity_rate"] - 0.5) < 1e-5
    assert abs(amb["average_parse_base"] - math.sqrt(2)) < 1e-5  # geo mean of {1,2}


def test_gold_roundtrip_and_overgeneration():
    parses = {"a": [("x",)], "c": [("y",), ("z",)]}
    gold = {"a": ("x",), "c": ("y",)}
    assert metrics.gold_roundtrip(parses, gold)["exact_analysis_recall"] == 1.0
    assert abs(metrics.overgeneration(parses, gold)["overgeneration_rate"] - 1 / 3) < 1e-5


def test_boundary_prf():
    prf = metrics.boundary_prf({"w": [2, 4]}, {"w": [2, 5]})
    assert prf["precision"] == 0.5 and prf["recall"] == 0.5 and prf["f1"] == 0.5


def test_generalization_and_tolerance():
    assert metrics.generalization_ratio(4, 3)["generalization_ratio"] == 0.75
    assert metrics.generalization_ratio(0, 0)["generalization_ratio"] is None
    assert metrics.tolerance_productive(100, 5)["productive"] is True   # 5 <= 100/ln100 ≈ 21.7
    assert metrics.tolerance_productive(10, 8)["productive"] is False    # 8 > 10/ln10 ≈ 4.34
    assert metrics.tolerance_productive(1, 0)["productive"] is None


def test_dead_constructs():
    parses = {"a": [("X",)]}
    dead = metrics.dead_constructs(parses, ["X", "Y", "Z"])
    assert dead["dead"] == ["Y", "Z"]


def test_liblcm_and_lift_inventory():
    fwdata = (
        '<root><LexEntry><MoStemAllomorph/><MoStemMsa/>'
        '<LexSense><Gloss><AUni ws="en">walk</AUni></Gloss></LexSense></LexEntry>'
        '<PhRegularRule/><PhNCFeatures/><MoInflAffMsa/></root>'
    )
    inv = inventory.from_liblcm_xml(fwdata)
    assert inv.counts.get("lexical_entry") == 1
    assert inv.counts.get("phonological_rule") == 1
    assert inv.counts.get("msa") == 2
    assert "walk" in inv.glosses

    lift = ('<lift><entry><sense><gloss lang="en"><text>child</text></gloss></sense>'
            '<variant/></entry></lift>')
    linv = inventory.from_lift_xml(lift)
    assert linv.counts.get("lexical_entry") == 1 and linv.counts.get("sense") == 1
    assert linv.counts.get("allomorph") == 1


def test_scorecard_deterministic():
    sc = Scorecard("g", "c", "hermitcrab", {"coverage": {"coverage_type": 0.5}})
    assert sc.to_json() == sc.to_json()
    assert sc.to_dict()["content_hash"].startswith("sha256:")


def test_worst_part_ranks_useless_first():
    from engine.grammar import Affix, LangModel, LexEntry

    model = LangModel(
        code="t",
        lexicon=[LexEntry("walk", "walk"), LexEntry("ghost", "unused")],
        affixes=[Affix("ni", "1SG", "prefix")],
    )
    gold = {"niwalk": ("1SG", "walk")}
    decomp = {"niwalk": [("ni", "1SG"), ("walk", "walk")]}

    def fake_parse(m, words):
        forms = {e.form for e in m.lexicon} | {a.form for a in m.affixes}
        return {w: ([tuple(g for _, g in decomp[w])] if all(f in forms for f, _ in decomp[w]) else [])
                for w in words}

    ranking = worst_part_ranking(model, gold, parse_fn=fake_parse)
    # 'ghost' is used by no gold word → benefit 0 → highest worstness → ranked first.
    assert ranking[0]["gloss"] == "unused"
    assert ranking[0]["worstness"] > ranking[-1]["worstness"]


def _demo_model_gold():
    from engine.grammar import Affix, LangModel, LexEntry

    model = LangModel(
        code="t",
        lexicon=[LexEntry("walk", "walk"), LexEntry("ghost", "unused")],
        affixes=[Affix("ni", "1SG", "prefix")],
    )
    gold = {"niwalk": ("1SG", "walk")}
    decomp = {"niwalk": [("ni", "1SG"), ("walk", "walk")]}

    def fake_parse(m, words):
        forms = {e.form for e in m.lexicon} | {a.form for a in m.affixes}
        return {w: ([tuple(g for _, g in decomp[w])] if all(f in forms for f, _ in decomp[w]) else [])
                for w in words}

    return model, gold, fake_parse


def test_mdl_grammar_cost_grows_with_redundancy():
    from engine.grammar import LangModel, LexEntry
    from assess import mdl

    base = LangModel(code="t", lexicon=[LexEntry("walk", "walk")], affixes=[])
    bigger = LangModel(code="t", lexicon=[LexEntry("walk", "walk"), LexEntry("walkk", "redundant")], affixes=[])
    assert mdl.l_grammar(bigger)["bits"] > mdl.l_grammar(base)["bits"] > 0


def test_mdl_better_grammar_and_split():
    from assess import mdl

    assert mdl.better_grammar({"A": 100.0, "B": 90.0})["winner"] == "B"
    d = mdl.decide_split_or_combine(dl_combined=90.0, dl_split=100.0)
    assert d["recommend"] == "combined"


def test_mdl_worstness_orientation_and_agreement():
    from assess import mdl
    from assess.worst_part import worst_part_ranking

    model, gold, fake = _demo_model_gold()
    mrows = worst_part_ranking(model, gold, parse_fn=fake)
    drows = mdl.worstness_mdl_ranking(model, gold, parse_fn=fake)

    # 'ghost' (used by no gold word) is worst under both rankings.
    assert mrows[0]["gloss"] == "unused"
    assert drows[0]["gloss"] == "unused"
    assert drows[0]["worstness_mdl"] > 0  # removing it lowers DL

    # The two rankings agree in direction: positive Spearman correlation (spec consistency check).
    key = lambda r: (r["kind"], r["form"], r["gloss"])
    md = {key(r): r["worstness"] for r in mrows}
    dd = {key(r): r["worstness_mdl"] for r in drows}
    ks = sorted(md)
    rho = mdl.spearman([md[k] for k in ks], [dd[k] for k in ks])
    assert rho > 0, f"expected positive rank correlation, got {rho}"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
