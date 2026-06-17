"""Emit LIFT (Lexicon Interchange FormaT) from a candidate lexicon.

LIFT is the XML lexicon format FLEx imports/exports, so the gold lexicon stays
FLEx-importable and text-diffable (per the spec's canonical-format decision). GUIDs are
derived deterministically (uuid5) so a rebuild produces byte-identical output — no
``Date.now``/random, which keeps the gold reproducible.
"""

from __future__ import annotations

import uuid
from xml.sax.saxutils import escape

from .grammar import LangModel

_NS = uuid.UUID("6f1b5e00-0000-4000-8000-000000000001")  # fixed namespace for this project


def _guid(*parts: str) -> str:
    return str(uuid.uuid5(_NS, "|".join(parts)))


def build_lift(model: LangModel, vern: str = "vern", analysis: str = "en") -> str:
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<lift version="0.13" producer="linguistic-assistant/golden">']
    for e in model.lexicon:
        eg = _guid("entry", model.code, e.form, e.gloss)
        sg = _guid("sense", model.code, e.form, e.gloss)
        out.append(f'  <entry id="{escape(e.form)}_{eg[:8]}" guid="{eg}">')
        out.append(f'    <lexical-unit><form lang="{vern}"><text>{escape(e.form)}</text></form></lexical-unit>')
        out.append(f'    <sense id="{sg}"><grammatical-info value="{escape(e.pos)}"/>'
                   f'<gloss lang="{analysis}"><text>{escape(e.gloss)}</text></gloss></sense>')
        out.append('  </entry>')
    out.append('</lift>')
    return "\n".join(out)
