"""Turn a cycle run's output into change-set ops with a composed confidence — the store's input.

Maps the induced grammar + LLM scenarios + alignment glosses onto the `proposal.change_set` vocabulary:
  root      -> lexical.entry.create (+ lexical.sense.create for its gloss, lexical.entry.set_pos for POS)
  affix     -> morphophonology.affix.add  (gram = the proposed grammatical label/gloss)
  phon rule -> morphophonology.rule.add   (the meN-/epenthesis proposals — low confidence, review)

Confidence is composed from the signals we actually have, so the store can route: frequent roots and
high-alignment-prob glosses score high (auto-accept); coarse gloss-derived POS and weak affix analyses
score medium (human/LLM review); everything else low (deferred). Every op carries provenance.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RESEARCH))

import liblcm  # noqa: E402

EBIBLE = _RESEARCH / "_sources" / "ebible"
OUT = _RESEARCH / "induce" / "out"
PAIR_DIR = {
    "swh": "eng-engwebp__swh-swhulb", "ind": "eng-engwebp__ind-indags",
    "tgl": "eng-engwebp__tgl-tglulb", "spa": "eng-engwebp__spa-spaRV1909",
}
_MORPH_KIND = {"prefix": "prefix", "suffix": "suffix", "infix": "infix"}


def _freq_conf(count: int) -> float:
    """A frequent form is more trustworthy as a real lexeme. Log-scaled, capped."""
    return round(min(0.9, 0.3 + 0.12 * math.log10(max(count, 1) + 1)), 3)


def _load_word_prob(pair: str) -> dict[str, float]:
    """target word -> alignment prob, from glosses.tsv (sense-gloss confidence)."""
    p = EBIBLE / PAIR_DIR[pair] / "glosses.tsv"
    out: dict[str, float] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    out[parts[0]] = float(parts[2])
                except ValueError:
                    pass
    return out


def _load_scenarios(pair: str) -> dict[str, dict]:
    """affix form -> proposed analysis ({label, confidence, ...}) from llm_propose output."""
    p = OUT / f"{pair}_scenarios.jsonl"
    out: dict[str, dict] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                s = json.loads(line)
                form = s.get("evidence", {}).get("affix")
                if form and s.get("proposed"):
                    out[form] = s["proposed"]
    return out


def emit_ops(pair: str, *, round_no: int = 1) -> list[dict]:
    """Build change-set ops (with confidence + provenance) from `out/<pair>_model.json` + sidecars."""
    model = json.loads((OUT / f"{pair}_model.json").read_text(encoding="utf-8"))
    word_prob = _load_word_prob(pair)
    scen = _load_scenarios(pair)
    prov = {"source": "cycle", "pair": pair, "round": round_no}
    ops: list[dict] = []

    for r in model["roots"]:
        form, gloss, pos = r["form"], r.get("gloss", "?"), r.get("pos", "noun")
        entry = f"entry:{pair}:{form}"
        ops.append({"op": "lexical.entry.create", "lexeme_form": {pair: form}, "morph_type": "stem",
                    "entry": entry, "confidence": _freq_conf(r.get("count", 0)), "provenance": prov})
        if gloss and gloss != "?":
            # gloss confidence = the alignment prob for the surface form (sense reliability)
            ops.append({"op": "lexical.sense.create", "entry": entry, "gloss": {"en": gloss},
                        "confidence": round(word_prob.get(form, 0.4), 3), "provenance": prov})
        if pos:
            # gloss-derived POS is coarse → medium confidence, lands in review by design.
            # Convert the cycle's internal id to the LibLCM/FieldWorks PartOfSpeech name (destination).
            ops.append({"op": "lexical.entry.set_pos", "entry": entry, "pos": liblcm.pos_from_cycle(pos),
                        "confidence": 0.5, "provenance": prov})

    for a in model["affixes"]:
        analysis = scen.get(a["form"], {})
        gram = analysis.get("label") if analysis.get("label") not in (None, "?") else a.get("gloss", a["form"])
        # affix confidence: the LLM/heuristic analysis confidence if we have one, else frequency-based
        conf = analysis.get("confidence")
        conf = float(conf) if conf is not None else _freq_conf(a.get("count", 0)) * 0.7
        ops.append({"op": "morphophonology.affix.add", "form": a["form"], "gram": gram,
                    "kind": _MORPH_KIND.get(a.get("kind", ""), "suffix"), "slot": a.get("slot_ord", 1),
                    "req_pos": a.get("req_pos", ""), "confidence": round(conf, 3),
                    "rationale": analysis.get("rationale", ""), "provenance": prov})

    res_path = OUT / f"{pair}_result.json"
    if res_path.exists():
        for rule in json.loads(res_path.read_text(encoding="utf-8")).get("phonology", {}).get("rules_proposed", []):
            ops.append({"op": "morphophonology.rule.add", "name": rule["rule"],
                        "rule": rule["archiphoneme"], "members": rule["members"],
                        "confidence": 0.45, "rationale": rule["conditioning"], "provenance": prov})
    return ops
