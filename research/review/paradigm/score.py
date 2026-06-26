"""Score a generated report against the GOLDEN report — the system's optimization metric.

Deliberately split into two numbers so every gain attributes to a specific fix (plan §4):

  * evidence_completeness — of the golden's cells (+ conditioning + residue), what fraction is PRESENT
    IN THE PACKET at all? Bounds the ceiling: you cannot report a case-cell the detector never surfaced.
    Moving this means improving the DETECTOR / packet.
  * faithfulness — of the facts that WERE in the packet, what fraction did the generator reproduce
    correctly, with no hallucinated cells? Moving this means improving GEMMA / the prompt.

overall = evidence_completeness × faithfulness. All three returned, plus a per-component breakdown so a
human can see exactly which golden cell went missing (detector) vs got mangled (generator).
"""

from __future__ import annotations

import re

from review.paradigm.schema import ParadigmReport


# Generic schema words that appear in labels but are NOT morpheme evidence — must never count as markers.
_STOP = {"class", "pattern", "voice", "case", "gender", "number", "residue", "concord",
         "verbal", "noun", "locative", "the", "of", "and", "sg", "pl"}


def _norm(m: str) -> str:
    """Normalise a marker for comparison: lowercase, drop hyphens/spaces/dots/parens."""
    return re.sub(r"[-\s.·()]", "", str(m).lower())


def _markers(cell) -> set[str]:
    out = {_norm(m) for m in getattr(cell, "markers", []) if _norm(m)}
    for p in re.split(r"[\s/]+", getattr(cell, "label", "")):
        n = _norm(p)
        if n and len(n) <= 6 and p.lower().strip("-()") not in _STOP:
            out.add(n)
    out.discard("")
    return out


def packet_markers(packet: dict) -> set[str]:
    """Every surface marker the packet surfaces anywhere — the universe of 'evidence present'."""
    ms: set[str] = set()
    for h in packet.get("hypotheses", {}).get("hypotheses", []):
        ms |= {_norm(p) for p in h.get("prefixes", [])}
        ms |= {_norm(p) for p in re.split(r"[\s/]+", h.get("label", ""))
               if 0 < len(_norm(p)) <= 6 and p.lower().strip("-()") not in _STOP}
    for r in packet.get("agreement", {}).get("rows", []):
        ms.add(_norm(r.get("noun_prefix", "")))
        for c in r.get("candidates", []):
            ms.add(_norm(c.get("marker", "")))
    for p in packet.get("residue", {}).get("patterns", []):
        ms.add(_norm(p.get("pattern", "")))
    for c in packet.get("cells", []):  # case/voice packets carry cells directly
        ms |= {_norm(m) for m in (c.get("markers", []) if isinstance(c, dict) else [])}
    ms.discard("")
    return ms


def _cell_in_markers(cell, universe: set[str]) -> bool:
    return bool(_markers(cell) & universe)


def _role_ok(packet_role: str, gold_roles: set[str]) -> bool:
    """Role compatibility, tolerant of UD subtypes (obl ~ obl:loc, nmod ~ nmod:poss, obj ~ dobj)."""
    pr = str(packet_role).lower()
    pr_base = pr.split(":")[0]
    return any(pr == gr or pr_base == gr or pr.startswith(gr + ":") or gr.startswith(pr_base + ":")
               or (gr == "obj" and pr_base == "dobj") for gr in gold_roles)


def _cell_present(gcell, packet: dict, pm: set[str]) -> bool:
    """Is the golden cell's evidence in the packet? Role-aware when the golden cell declares `match_roles`
    AND the packet carries role-bearing families (case): require an overlapping marker on a family whose
    role matches. Otherwise marker-only (noun-class/agreement)."""
    gm = _markers(gcell)
    gold_roles = {str(r).lower() for r in getattr(gcell, "match_roles", []) or []}
    role_cells = [c for c in packet.get("cells", []) if isinstance(c, dict) and c.get("role")]
    if gold_roles and role_cells:
        for c in role_cells:
            if (gm & {_norm(m) for m in c.get("markers", [])}) and _role_ok(c.get("role", ""), gold_roles):
                return True
        return False
    return bool(gm & pm)


def score(generated: ParadigmReport, golden: ParadigmReport, packet: dict) -> dict:
    pm = packet_markers(packet)
    gold_cells = golden.cells
    gen_cells = generated.cells

    # ---- evidence_completeness: golden CELLS whose markers are present in the packet -------------------
    # Headline on cell coverage only — the robust signal. Conditioning/residue presence is reported in the
    # breakdown (builder-agnostic, informational) but NOT folded in, so the score can't move on packet
    # field-name plumbing — only on whether the detector actually surfaced the golden's cells.
    cells_present = [c for c in gold_cells if _cell_present(c, packet, pm)]
    cell_completeness = len(cells_present) / len(gold_cells) if gold_cells else 1.0
    evidence_completeness = round(cell_completeness, 3)
    _COND = ("conditioning", "conditioning_evidence", "agreement", "residue", "case")
    conditioning_in_packet = any(packet.get(k) for k in _COND)
    residue_in_packet = bool(packet.get("residue") or packet.get("fit_none")
                             or packet.get("hypotheses", {}).get("fit_none")
                             or any(packet.get(k, {}).get("fit_none") for k in ("case",) if isinstance(packet.get(k), dict)))

    # ---- faithfulness: of packet-available golden cells, did the generator report them? -----------
    def gen_match(cell) -> bool:
        cms = _markers(cell)
        return any(cms & _markers(gc) for gc in gen_cells)

    reported = [c for c in cells_present if gen_match(c)]
    cell_faithfulness = len(reported) / len(cells_present) if cells_present else (1.0 if not gold_cells else 0.0)
    # hallucination: generated cells whose markers are NOT in the packet at all
    hallucinated = [c for c in gen_cells if not _cell_in_markers(c, pm)]
    hallucination_rate = len(hallucinated) / len(gen_cells) if gen_cells else 0.0
    detected_ok = (generated.detected == golden.detected)
    faithfulness = round(cell_faithfulness * (1 - hallucination_rate) * (1.0 if detected_ok else 0.5), 3)

    overall = round(evidence_completeness * faithfulness, 3)
    return {
        "overall": overall,
        "evidence_completeness": evidence_completeness,
        "faithfulness": faithfulness,
        "breakdown": {
            "golden_cells": len(gold_cells),
            "cells_present_in_packet": len(cells_present),
            "cells_reported_by_generator": len(reported),
            "missing_from_packet": [c.label for c in gold_cells if c not in cells_present],
            "in_packet_but_not_reported": [c.label for c in cells_present if not gen_match(c)],
            "hallucinated_cells": [c.label for c in hallucinated],
            "detected_match": detected_ok,
            "cell_completeness": round(cell_completeness, 3),
            "cell_faithfulness": round(cell_faithfulness, 3),
            "hallucination_rate": round(hallucination_rate, 3),
            "conditioning_in_packet": conditioning_in_packet,
            "residue_in_packet": residue_in_packet,
        },
    }
