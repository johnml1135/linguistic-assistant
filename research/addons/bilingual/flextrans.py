"""FLExTrans direct import/export — bidix + sense links only (NOT the .t*x transfer rules).

A FLExTrans `bilingual.dix` is an Apertium bidix, so import/export reuse the `.dix` reader/writer. The
exact on-disk layout + tag direction must be reconciled against a real FLExTrans sample (open question
6.3 in the openspec change); until then this is the Apertium-bidix format with our `<l>`=reference /
`<r>`=vernacular convention. Stdlib-only.
"""

from __future__ import annotations

from pathlib import Path

from .bidix import Bidix, parse_bidix, serialize_bidix


def import_flextrans_bidix(path_or_text: str | Path) -> Bidix:
    """Read a FLExTrans/Apertium `bilingual.dix`. Accepts a path or raw XML text."""
    text = path_or_text
    p = Path(str(path_or_text))
    if p.exists():
        text = p.read_text(encoding="utf-8")
    return parse_bidix(str(text))


def export_flextrans_bidix(bidix: Bidix, path: str | Path | None = None) -> str:
    """Serialize a bidix to FLExTrans/Apertium `.dix`. Writes to ``path`` if given; returns the XML."""
    xml = serialize_bidix(bidix)
    if path is not None:
        Path(path).write_text(xml, encoding="utf-8")
    return xml


# NOTE: transfer rules (.t1x/.t2x/.t3x) are intentionally NOT handled here — that is FLExTrans's MT
# layer and out of scope (see the qa-not-mt-parallel-core decision).
