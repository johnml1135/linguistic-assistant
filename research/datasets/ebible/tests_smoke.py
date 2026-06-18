"""Offline smoke tests for the eBible read pipeline. Run: `python research/datasets/ebible/tests_smoke.py`
(pytest-discoverable). No network — uses inline fake vref/text lines.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from align import align  # noqa: E402
from datasets.ebible.read import parallel_rows_from_lines  # noqa: E402

# GEN line is OT (filtered); blank + <range> lines are skipped; MAT lines kept.
VREF = ["GEN 1:1", "MAT 1:1", "MAT 1:2", "MAT 1:3", "MAT 1:4", "MAT 1:5"]
SRC = ["In the beginning", "God love", "God world", "love world", "", "alpha <range>"]
TGT = ["alussa", "Tanrı sevgi", "Tanrı dünya", "sevgi dünya", "bos", "<range>"]


def test_filters_ot_blanks_and_ranges_and_tokenizes():
    rows = parallel_rows_from_lines(VREF, SRC, TGT, nt_only=True)
    refs = [r.ref for r in rows]
    assert refs == ["MAT 1:1", "MAT 1:2", "MAT 1:3"]  # OT dropped; blank + <range> dropped
    assert rows[0].src == ["god", "love"] and rows[0].tgt == ["tanrı", "sevgi"]  # lowercased, tokenized


def test_read_then_align_recovers_glosses():
    rows = parallel_rows_from_lines(VREF, SRC, TGT)
    table, used = align([(r.src, r.tgt) for r in rows], backend="cooccur")
    assert used == "cooccur"
    assert table.best("sevgi").source_word == "love"
    assert table.best("tanrı").source_word == "god"
    assert table.best("dünya").source_word == "world"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
