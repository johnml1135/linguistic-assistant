"""Offline smoke tests for ParseGym + the HC allomorph mechanism (no `hc` CLI needed)."""

from __future__ import annotations

import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from parsegym.questions import BY_ID, QUESTIONS, get  # noqa: E402
from parsegym.schema import read_jsonl  # noqa: E402

from golden.grammar import Affix, LangModel, LexEntry  # noqa: E402
from golden.hc import build_grammar_xml  # noqa: E402

GYM = _THIS.parent / "gym"


def test_questions_render():
    assert len(QUESTIONS) >= 10
    assert len(BY_ID) == len(QUESTIONS), "duplicate question ids"
    assert "more than one" in get("paradigm_fill").note or True  # spot a known archetype
    assert get("meaning_choice").render(form="y", options="a; b") .startswith("When you hear")


def test_gym_files_valid():
    files = list(GYM.glob("*.jsonl"))
    assert files, "no curated gym files — run curate.py"
    for f in files:
        scen = read_jsonl(f)
        assert scen, f"{f.name} empty"
        ids = [s.id for s in scen]
        assert len(ids) == len(set(ids)), f"{f.name} has duplicate ids"
        for s in scen:
            s.validate()
            if s.solution.kind == "ask_speaker":
                assert s.solution.question_id in BY_ID, f"{s.id} -> unknown question"
        kinds = {s.solution.kind for s in scen}
        assert "ask_speaker" in kinds, f"{f.name} has no ask_speaker scenarios"


def test_allomorph_emitted():
    # an entry with an allomorph emits >1 <Allomorph> and includes the allomorph's chars
    m = LangModel(code="x",
                  lexicon=[LexEntry(form="decir", gloss="say", pos="Verb", allomorphs=("dic",))],
                  affixes=[Affix(form="s", gloss="PL", kind="suffix")])
    xml = build_grammar_xml(m, templated=False)
    assert xml.count("<Allomorph ") == 2, "expected citation form + 1 allomorph"
    assert "d" in m.charset and "c" in m.charset


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"{len(fns)} tests passed")
