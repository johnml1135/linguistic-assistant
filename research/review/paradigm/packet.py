"""Packet assembler — gather the FULL PICTURE for one candidate paradigm into a single evidence dict that
Gemma reads (and only that). The packet braids three sources:

  * the A/B/C + fit-none EXPLORER  (review/explore.py) — ranked hypotheses + the residue,
  * THOT alignment evidence        — concord/role votes derived from the morpheme alignment,
  * HC parse evidence              — how much of the data the current grammar segments / classifies.

AUDIT INVARIANT (the firewall/golden tension, see learning_paradigms_plan.md §4): a packet may contain
ONLY facts derived from THOT/HC/explorer over the corpus. It must NEVER contain the answer-key (the true
case inventory, the real class semantics). The golden report is allowed recalled knowledge; the packet is
not. `audit()` checks the structural invariant; keep new builders honest.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import explore as EX  # noqa: E402

PROVENANCE = ("explorer(class/agreement/residue) over HC parse + THOT alignment — derived from corpus "
              "only, no external/recalled knowledge")


def build_noun_class_packet(pair: str) -> dict:
    """Full picture for the prefixal noun-class question. All evidence already exists end-to-end (this is
    the swh slice that needs no new detection code)."""
    classes = EX.class_hypotheses(pair)
    agreement = EX.agreement_hypotheses(pair)
    residue = EX.residue_patterns(pair)
    browse = EX.noun_entries(pair, limit=0)  # just the counts
    n_nouns = browse["n_nouns"]
    n_classified = browse["n_classified"]
    # worked examples: top class group's members + the concord marker they trigger
    concord_rows = agreement.get("rows", [])
    examples = []
    for r in concord_rows[:6]:
        if r["candidates"]:
            top = r["candidates"][0]
            examples.append({"noun_prefix": r["noun_prefix"], "class": r["class"],
                             "concord_marker": top["marker"], "share": top["share"],
                             "support": top["support"]})
    return {
        "language": pair,
        "paradigm_type": "noun-class",
        "question": "Is there a prefixal noun-class system, and what are its classes + concord?",
        "hypotheses": classes,        # A/B/C class groups + fit_none  (HC/recover-derived grouping)
        "agreement": agreement,       # concord A/B/C + doesnt_fit      (THOT associative votes)
        "residue": residue,           # the 'another pattern?' probe    (e.g. locative -ni)
        "hc": {
            "n_nouns": n_nouns,
            "n_classified": n_classified,
            "frac_classified": round(n_classified / n_nouns, 3) if n_nouns else 0.0,
            "n_class_groups": len(classes.get("hypotheses", [])),
        },
        "thot": {
            "signal": "associative concord votes from THOT morpheme alignment",
            "n_classes_with_concord": sum(1 for r in concord_rows
                                          if r["candidates"] and r["candidates"][0]["share"] >= 0.5),
            "n_classes_voting": len(concord_rows),
        },
        "examples": examples,
        "provenance": PROVENANCE,
    }


def build_case_packet(pair: str) -> dict:
    """Full picture for the suffixal CASE question (the tur anchor). Uses the role-covariation detector
    (case_detect) — the suffixal mirror of the Bantu concord explorer."""
    from review.paradigm.case_detect import detect_case_real
    from induce.morph_align import load_model
    value, conf, evidence, hyps = detect_case_real(pair, sample=300)
    rows = hyps.get("rows", [])
    cells = [{"markers": r["markers"], "role": r["dominant_role"], "share": r["dominant_share"],
              "n_stems": r["n_stems"]} for r in rows]
    m = load_model(pair)
    n_suffix = len({a.form for a in m.affixes if a.kind == "suffix"})
    return {
        "language": pair,
        "paradigm_type": "case",
        "question": "Is there a case system (role-covarying noun suffixes)? What are the cases?",
        "detected": value == "present",
        "confidence": conf,
        # mirror the A/B/C+fit_none shape so the scorer's packet_markers + the heuristic both read it
        "hypotheses": {"hypotheses": [{"label": "/".join(r["markers"][:3]), "prefixes": r["markers"],
                                       "n_explained": r["n_stems"], "examples": []} for r in rows],
                       "fit_none": hyps.get("fit_none", {"n": 0, "examples": []})},
        "case": hyps,
        "cells": cells,
        "hc": {"n_suffixes": n_suffix, "n_case_families": hyps.get("n_case_families", 0)},
        "thot": {"signal": "projected dep-role covariation over THOT alignment",
                 "n_case_families": hyps.get("n_case_families", 0)},
        "conditioning": "vowel-harmony",
        "examples": [{"markers": r["markers"], "role": r["dominant_role"], "share": r["dominant_share"]}
                     for r in rows[:6]],
        "provenance": PROVENANCE,
    }


def build_agreement_packet(pair: str) -> dict:
    """Full picture for CONCORD/agreement (the swh second anchor) — wraps the agreement explorer."""
    agreement = EX.agreement_hypotheses(pair)
    rows = agreement.get("rows", [])
    cells = [{"markers": [r["noun_prefix"], r["candidates"][0]["marker"]] if r["candidates"] else [r["noun_prefix"]],
              "function": f"{r['noun_prefix']}->{r['candidates'][0]['marker']}" if r["candidates"] else "",
              "share": r["candidates"][0]["share"] if r["candidates"] else 0.0}
             for r in rows]
    return {
        "language": pair,
        "paradigm_type": "agreement",
        "question": "What concord marker does each noun class govern on its modifiers?",
        "detected": len([r for r in rows if r["candidates"] and r["candidates"][0]["share"] >= 0.5]) >= 2,
        "agreement": agreement,
        "cells": cells,
        "hc": {"n_classes_voting": len(rows)},
        "thot": {"signal": "associative concord votes from THOT alignment",
                 "n_clean": len([r for r in rows if r["candidates"] and r["candidates"][0]["share"] >= 0.5])},
        "conditioning": "noun-class",
        "examples": [{"prefix": r["noun_prefix"], "marker": r["candidates"][0]["marker"],
                      "share": r["candidates"][0]["share"]} for r in rows[:6] if r["candidates"]],
        "provenance": PROVENANCE,
    }


def build_gender_number_packet(pair: str) -> dict:
    """Full picture for the GENDER-NUMBER question (the spa anchor): gender = final-vowel classes that take
    distinct determiners; number = the -s suffix's projected Number covariation."""
    from review.paradigm.gender_number_detect import detect_gender_number
    detected, conf, evidence, h = detect_gender_number(pair, sample=300)
    gender_cells = [{"markers": g["markers"], "ending": g["ending"], "determiner": g["determiner"],
                     "share": g["det_share"], "n": g["n"]} for g in h.get("gender_classes", [])]
    num = h.get("number")
    cells = list(gender_cells)
    if num:
        cells.append({"markers": num["markers"], "function": f"number={num['dominant_number']}",
                      "share": num["share"], "n": num["n"]})
    return {
        "language": pair,
        "paradigm_type": "gender-number",
        "question": "Is there a gender system (determiner agreement on noun endings) + a number marker?",
        "detected": detected,
        "confidence": conf,
        "hypotheses": {"hypotheses": [{"label": "/".join(g["markers"][:2]), "prefixes": g["markers"],
                                       "n_explained": g["n"], "examples": []}
                                      for g in h.get("gender_classes", [])],
                       "fit_none": {"n": 0, "examples": []}},
        "gender_number": h,
        "cells": cells,
        "hc": {"n_gender_classes": h.get("n_gender_classes", 0)},
        "thot": {"signal": "preceding-determiner agreement on noun endings + projected Number feat",
                 "evidence": evidence},
        "conditioning": "gender",
        "examples": cells[:6],
        "provenance": PROVENANCE,
    }


def build_voice_packet(pair: str) -> dict:
    """Full picture for VOICE/focus (ind anchor): affixes the feature-predictor labels Voice=* (the
    markable passive, e.g. di-). The active is unmarked in English so it is reported as inferred, not a cell."""
    from review.paradigm.voice_detect import detect_voice
    detected, conf, evidence, h = detect_voice(pair, sample=300)
    voice_aff = h.get("voice_affixes", [])
    cells = [{"markers": c["markers"], "voice": c["voice"], "function": f"Voice={c['voice']}",
              "lift": c.get("lift"), "heldout": c.get("heldout")} for c in voice_aff]
    return {
        "language": pair,
        "paradigm_type": "voice-focus",
        "question": "Is there a voice system? Which affix marks the passive?",
        "detected": detected,
        "confidence": conf,
        "hypotheses": {"hypotheses": [{"label": f"{c['markers'][0]}- ({c['voice']})", "prefixes": c["markers"],
                                       "n_explained": 0, "examples": []} for c in voice_aff],
                       "fit_none": {"n": 0, "examples": []}},
        "voice": h,
        "cells": cells,
        "hc": {"n_voice_affixes": h.get("n_voice", 0)},
        "thot": {"signal": "held-out English-feature prediction labels Voice on affixes", "evidence": evidence},
        "conditioning": "voice",
        "examples": cells[:6],
        "provenance": PROVENANCE,
    }


def build_np_case_packet(pair: str) -> dict:
    """Full picture for ANALYTIC case (tgl ang/ng/sa, hin postpositions): adjacent particles whose presence
    co-varies with the noun's role. Role-bearing cells → role-aware scoring applies."""
    from review.paradigm.markers_detect import detect_np_case
    detected, conf, evidence, h = detect_np_case(pair, sample=300)
    rows = h.get("rows", [])
    cells = [{"markers": r["markers"], "role": r["dominant_role"], "share": r["share"], "n": r["n"]}
             for r in rows]
    return {
        "language": pair,
        "paradigm_type": "np-case",
        "question": "Is case marked analytically — an adjacent particle co-varying with the noun's role?",
        "detected": detected,
        "confidence": conf,
        "hypotheses": {"hypotheses": [{"label": f"{r['marker']}→{r['dominant_role']}", "prefixes": r["markers"],
                                       "n_explained": r["n"], "examples": []} for r in rows],
                       "fit_none": {"n": 0, "examples": []}},
        "np_case": h,
        "cells": cells,
        "hc": {"n_markers": h.get("n_markers", 0), "side": h.get("side")},
        "thot": {"signal": "adjacent-particle role covariation over THOT alignment", "evidence": evidence},
        "conditioning": "analytic (separate-word marking)",
        "examples": cells[:6],
        "provenance": PROVENANCE,
    }


def build_tam_packet(pair: str) -> dict:
    """Full picture for TAM (swh na-/li-/ta-/me-): verb affixes carrying a projected tense label."""
    from review.paradigm.tam_detect import detect_tam
    detected, conf, evidence, h = detect_tam(pair, sample=300)
    tam = h.get("tam", [])
    cells = [{"markers": c["markers"], "function": f"Tense={c['tense']}", "tense": c["tense"], "n": c.get("n")}
             for c in tam]
    return {
        "language": pair,
        "paradigm_type": "tam",
        "question": "Is there a tense/aspect paradigm on the verb? Which affixes mark it?",
        "detected": detected,
        "confidence": conf,
        "hypotheses": {"hypotheses": [{"label": f"{c['markers'][0]}→{c['tense']}", "prefixes": c["markers"],
                                       "n_explained": c.get("n", 0), "examples": []} for c in tam],
                       "fit_none": {"n": 0, "examples": []}},
        "tam": h,
        "cells": cells,
        "hc": {"n_tam": h.get("n_tam", 0)},
        "thot": {"signal": "projected English Tense on verb affixes (label_tam)", "evidence": evidence},
        "conditioning": "tense/aspect",
        "examples": cells[:6],
        "provenance": PROVENANCE,
    }


def build_possessive_packet(pair: str) -> dict:
    """Full picture for POSSESSIVE/NUMBER suffixes (tur -lAr plural, -(s)I/-Im/-In possessive). The plural
    (Number) projects cleanly; possessor agreement is largely unmarked in English (only partly recoverable)."""
    from review.paradigm.feature_affix_detect import detect_feature_paradigm
    detected, conf, evidence, h = detect_feature_paradigm(pair, ("Person", "Number", "Poss"), sample=300)
    cells = [{"markers": c["markers"], "function": c["function"]} for c in h.get("cells", [])]
    return {
        "language": pair,
        "paradigm_type": "possessive",
        "question": "Are there possessive/number suffixes on the noun?",
        "detected": detected,
        "confidence": conf,
        "hypotheses": {"hypotheses": [{"label": c["function"], "prefixes": c["markers"], "n_explained": 0,
                                       "examples": []} for c in h.get("cells", [])],
                       "fit_none": {"n": 0, "examples": []}},
        "possessive": h,
        "cells": cells,
        "hc": {"n_cells": h.get("n", 0)},
        "thot": {"signal": "held-out Person/Number/Poss feature prediction on suffixes", "evidence": evidence},
        "conditioning": "vowel-harmony",
        "examples": cells[:6],
        "provenance": PROVENANCE,
    }


_BUILDERS = {
    "noun-class": build_noun_class_packet,
    "case": build_case_packet,
    "np-case": build_np_case_packet,
    "agreement": build_agreement_packet,
    "gender-number": build_gender_number_packet,
    "voice-focus": build_voice_packet,
    "tam": build_tam_packet,
    "possessive": build_possessive_packet,
}


def assemble(pair: str, paradigm_type: str) -> dict:
    """Build the evidence packet for (language, paradigm_type)."""
    if paradigm_type not in _BUILDERS:
        raise ValueError(f"no packet builder for paradigm_type={paradigm_type!r}; have {list(_BUILDERS)}")
    return _BUILDERS[paradigm_type](pair)


def register_builder(paradigm_type: str, fn) -> None:
    """Register a new per-paradigm packet builder (e.g. the suffixal/case detector for tur)."""
    _BUILDERS[paradigm_type] = fn


def has_builder(paradigm_type: str) -> bool:
    return paradigm_type in _BUILDERS


def builders() -> list[str]:
    return sorted(_BUILDERS)


# Keys that, if present in a packet, would mean recalled answer-key leaked in. The audit is structural:
# packets carry stats + examples + hypotheses, never a `truth`/`answer`/`gold` field.
_FORBIDDEN_KEYS = {"truth", "answer", "answer_key", "gold", "golden", "expected", "correct_cells"}


def audit(packet: dict) -> list[str]:
    """Return a list of audit violations (empty == clean). Enforces the no-answer-leak invariant."""
    problems = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).lower() in _FORBIDDEN_KEYS:
                    problems.append(f"forbidden key {k!r} at {path}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(packet, "packet")
    if "provenance" not in packet:
        problems.append("missing provenance note")
    return problems
