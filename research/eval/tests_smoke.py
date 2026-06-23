"""Offline smoke tests for the eval/proposal loop. Run: `python research/eval/tests_smoke.py`
(also pytest-discoverable). No model, no network, no golden data required.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.fixtures import MockProposer, fixture_instances  # noqa: E402
from eval.runner import run_instances  # noqa: E402
from eval.stub_scorer import StubScorer  # noqa: E402
from propose.change_set import validate_change_set  # noqa: E402
from propose.context import assemble_context  # noqa: E402
from propose.contract import ChangeSet, ValidationFailure  # noqa: E402
from propose.propose import ProposeConfig, propose  # noqa: E402


def test_invalid_output_rejected():
    assert isinstance(validate_change_set("not json"), ValidationFailure)
    assert isinstance(validate_change_set('{"ops":[{"op":"nope"}]}'), ValidationFailure)
    assert isinstance(
        validate_change_set('{"ops":[{"op":"lexical.entry.create","morph_type":"stem"}]}'),
        ValidationFailure,
    )  # missing lexeme_form
    ok = validate_change_set('{"ops":[{"op":"lexical.sense.create","entry":"x","gloss":"y"}]}')
    assert isinstance(ok, ChangeSet) and len(ok.ops) == 1


def test_context_byte_identical():
    case = fixture_instances()[0].case
    a = "".join(m.content for m in assemble_context(case))
    b = "".join(m.content for m in assemble_context(case))
    assert a == b


def test_propose_reproducible_and_valid():
    case = fixture_instances()[0].case
    cfg = ProposeConfig(backend_kind="mock")
    r1 = propose(case, MockProposer(), cfg)
    r2 = propose(case, MockProposer(), cfg)
    assert isinstance(r1, ChangeSet) and r1.ops == r2.ops


def test_fixture_loop_scores():
    insts = fixture_instances()
    records = run_instances(insts, MockProposer(), StubScorer(), ProposeConfig(backend_kind="mock"))
    assert len(records) == 1
    assert records[0]["parsed_ok"] is True
    assert records[0]["reward"] == 1.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
