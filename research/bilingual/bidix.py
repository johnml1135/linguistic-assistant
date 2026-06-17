"""Apertium bilingual dictionary (bidix): in-memory model + `.dix` XML read/write + lookup.

Convention here: `<l>` = **reference** (source/major language) lemma+tags, `<r>` = **vernacular**
(target) lemma+tags. The bidix is a *derived* artifact built from the `bilingual/*` sense links — never
the primary store. Stdlib-only (xml.etree), deterministic.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

LemmaTags = tuple[str, tuple[str, ...]]  # (lemma, tags)


@dataclass(frozen=True)
class BidixEntry:
    reference: LemmaTags  # <l>
    vernacular: LemmaTags  # <r>


@dataclass
class Bidix:
    entries: list[BidixEntry] = field(default_factory=list)

    def lookup_by_reference(self, lemma: str) -> list[LemmaTags]:
        """Vernacular candidates for a reference lemma (the direction the reference-finder uses)."""
        return [e.vernacular for e in self.entries if e.reference[0] == lemma]

    def lookup_by_vernacular(self, lemma: str) -> list[LemmaTags]:
        return [e.reference for e in self.entries if e.vernacular[0] == lemma]


def _read_side(p_child: ET.Element) -> LemmaTags:
    # <l>lemma<s n="n"/><s n="pl"/></l>  -> ("lemma", ("n","pl"))
    lemma = (p_child.text or "").strip()
    tags = tuple((s.get("n") or "") for s in p_child.findall("s"))
    return (lemma, tags)


def _write_side(parent: ET.Element, tag: str, lt: LemmaTags) -> None:
    el = ET.SubElement(parent, tag)
    el.text = lt[0]
    for t in lt[1]:
        ET.SubElement(el, "s", {"n": t})


def serialize_bidix(bidix: Bidix) -> str:
    """Emit Apertium bidix `.dix` XML. Entries are sorted for byte-stable output."""
    root = ET.Element("dictionary")
    section = ET.SubElement(root, "section", {"id": "main", "type": "standard"})
    for e in sorted(bidix.entries, key=lambda e: (e.reference, e.vernacular)):
        p = ET.SubElement(ET.SubElement(section, "e"), "p")
        _write_side(p, "l", e.reference)
        _write_side(p, "r", e.vernacular)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


def parse_bidix(xml: str) -> Bidix:
    root = ET.fromstring(xml)
    entries: list[BidixEntry] = []
    for e in root.iter("e"):
        p = e.find("p")
        if p is None:
            continue
        l, r = p.find("l"), p.find("r")
        if l is None or r is None:
            continue
        entries.append(BidixEntry(reference=_read_side(l), vernacular=_read_side(r)))
    return Bidix(entries=entries)
