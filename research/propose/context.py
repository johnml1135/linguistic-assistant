"""Deterministic context assembly: a compiled language *primer* + harness-orchestrated retrieval.

No model tool-calls, no vector/embedding retrieval — the harness selects what the model sees, in code,
so the rendered context is byte-identical for identical inputs (and reproducible across the future C#
port). Keep stdlib-only.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from propose.harness.base import Message

from .contract import Case
from .grammar import schema_hint

# A distilled, example-led default skill for the local 30B tier (frontier skills are too verbose for
# an 8-16K context at Q4). Override via assemble_context(skill=...).
DEFAULT_SKILL = """\
You are helping document a low-resource language for FieldWorks. You PROPOSE lexicon and \
morphophonology edits as change-set operations; a deterministic parser (Hermit Crab) verifies them.

Method (Nida discovery + capture-the-generalization):
1. Find recurring form-meaning partials across the data.
2. Prefer ONE phonological rule over a natural class to listing many allomorphs (generalize, don't enumerate).
3. If unsure, propose with low confidence rather than inventing — wrong proposals are rejected by the gate.

Lowercase glosses are lexical meanings (lexicon); UPPERCASE glosses are grammatical (morphology).\
"""


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


@dataclass
class _Entry:
    form: str
    pos: str
    gloss: str


def _parse_lift_entries(lift_xml: str) -> list[_Entry]:
    """Best-effort, namespace-tolerant extraction of (form, pos, gloss) from LIFT."""
    if not lift_xml.strip():
        return []
    try:
        root = ET.fromstring(lift_xml)
    except ET.ParseError:
        return []
    entries: list[_Entry] = []
    for entry in root.iter():
        if _localname(entry.tag) != "entry":
            continue
        form = pos = gloss = ""
        for el in entry.iter():
            ln = _localname(el.tag)
            if ln == "lexical-unit":
                t = next((t for t in el.iter() if _localname(t.tag) == "text"), None)
                if t is not None and t.text:
                    form = t.text.strip()
            elif ln == "grammatical-info" and not pos:
                pos = (el.get("value") or "").strip()
            elif ln == "gloss" and not gloss:
                t = next((t for t in el.iter() if _localname(t.tag) == "text"), None)
                if t is not None and t.text:
                    gloss = t.text.strip()
        if form:
            entries.append(_Entry(form=form, pos=pos, gloss=gloss))
    return entries


def _grammar_counts(hcgr_xml: str) -> dict[str, int]:
    """Coarse counts of HC constructs, by local tag name — a stable primer summary."""
    if not hcgr_xml.strip():
        return {}
    try:
        root = ET.fromstring(hcgr_xml)
    except ET.ParseError:
        return {}
    interesting = {
        "PhonologicalRule", "MetathesisRule", "NaturalClass", "AffixProcess",
        "AffixalMorpheme", "Stratum", "CompoundingRule", "Morpheme",
    }
    counts: dict[str, int] = {}
    for el in root.iter():
        ln = _localname(el.tag)
        if ln in interesting:
            counts[ln] = counts.get(ln, 0) + 1
    return dict(sorted(counts.items()))


def compile_primer(case: Case, *, top_n: int = 60) -> str:
    """A small, byte-stable per-language card: inventories + counts + top entries (no timestamps)."""
    entries = _parse_lift_entries(case.lexicon_lift)
    pos_inv = sorted({e.pos for e in entries if e.pos})
    # deterministic top-N by (form) — stable tie-break, no frequency available pre-corpus-parse
    top = sorted(entries, key=lambda e: (e.form, e.gloss))[:top_n]
    g = _grammar_counts(case.grammar_hcgr)

    lines = [
        f"LANGUAGE PRIMER (glottocode: {case.glottocode})",
        f"lexicon entries: {len(entries)} | parts of speech: {', '.join(pos_inv) or '(none)'}",
        "grammar: " + (", ".join(f"{k}={v}" for k, v in g.items()) or "(none yet)"),
        "known entries (form | pos | gloss):",
    ]
    for e in top:
        lines.append(f"  {e.form} | {e.pos or '-'} | {e.gloss or '-'}")
    return "\n".join(lines)


def _render_igt(case: Case) -> str:
    lines = ["DATA TO ANALYZE (interlinear):"]
    for r in case.igt:
        lines.append(f"  [{r.id}] text: {r.text}")
        if r.segmentation:
            lines.append(f"        segmentation: {r.segmentation}")
        if r.translation:
            lines.append(f"        translation: {r.translation}")
        if r.pos:
            lines.append(f"        pos: {r.pos}")
    return "\n".join(lines)


def assemble_context(case: Case, *, skill: str | None = None) -> list[Message]:
    """Build the (system, user) messages. Byte-identical for identical inputs."""
    system = (skill or DEFAULT_SKILL).rstrip() + "\n\n" + schema_hint()
    user = "\n\n".join(
        [
            compile_primer(case),
            _render_igt(case),
            "TASK: Propose the lexicon/morphology change-set operations needed so the data above "
            "parses correctly against the (incomplete) lexicon and grammar shown in the primer. "
            "Only propose what the evidence supports.",
        ]
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]
