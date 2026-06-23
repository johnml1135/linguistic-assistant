"""Offline smoke tests for word-gloss alignment. Run: `python research/align/tests_smoke.py`
(also pytest-discoverable). No machine.py / network needed — uses the co-occurrence backend.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from align.aligner import align  # noqa: E402
from align.fixtures import FIXTURE_ROWS  # noqa: E402
from align.to_bilingual import gloss_table_to_sense_link_ops  # noqa: E402
from propose.change_set import validate_change_set  # noqa: E402
from propose.contract import ChangeSet  # noqa: E402


def test_cooccur_recovers_glosses():
    table, used = align(FIXTURE_ROWS, backend="cooccur")
    assert used == "cooccur"
    assert table.best("sevgi").source_word == "love"
    assert table.best("tanri").source_word == "god"
    assert table.best("dunya").source_word == "world"


def test_alignment_is_deterministic():
    a, _ = align(FIXTURE_ROWS, backend="cooccur")
    b, _ = align(FIXTURE_ROWS, backend="cooccur")
    assert {k: [c.source_word for c in v] for k, v in a} == {k: [c.source_word for c in v] for k, v in b}


def test_auto_falls_back_to_cooccur_offline():
    # No THOT installed in CI → auto must fall back, not crash.
    _table, used = align(FIXTURE_ROWS, backend="auto")
    assert used in {"hmm", "cooccur"}


def test_gloss_ops_validate_as_bilingual_change_set():
    table, _ = align(FIXTURE_ROWS, backend="cooccur")
    ops = gloss_table_to_sense_link_ops(table, min_count=2)
    assert ops, "expected at least one confident gloss op"
    cs = validate_change_set('{"ops": %s}' % _json(ops))
    assert isinstance(cs, ChangeSet) and len(cs.ops) == len(ops)
    assert all(o["op"] == "bilingual.sense_link.add" and o["confidence"] <= 0.6 for o in ops)


def _json(ops):
    import json

    return json.dumps(ops)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
