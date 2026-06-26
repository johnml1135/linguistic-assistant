"""Per-language paradigm PROFILES — the queryable registry of what each language must learn, in LAYERS
that fall out progressively as each prerequisite is learned (not all at once).

Layers (strict order; a paradigm is only ever offered to Gemma once its gate is satisfied):
  0 switches    typological profile (synthesis, affix polarity, harmony, gender-or-noun-class, case
                presence, voice). No dependencies — learned first; it is the gate-source for everything.
  1 inventory   the CELLS: noun classes / cases / voices / gender-number / classifiers. Gated by switches.
  2 agreement   concord / agreement patterns over the inventory. Gated by the inventory being learned.
  3 exceptions  allomorphy, conditioning, splits (glide formation, harmony, ergative split). Gated by
                the relevant inventory (and sometimes agreement).

Status lifecycle per paradigm:
  locked     gate not satisfied yet (a prerequisite switch/paradigm is unlearned)
  candidate  gate satisfied → the detector should run / a packet can be built → present to Gemma
  learned    a report was generated with cells
  confirmed  Opus-as-Reviewer promoted it
  absent     the detector ran and correctly found the paradigm is NOT present (e.g. case in vie/swh)

`profiles/<lang>.json` is the emitted, queryable artifact (one per language). This module is the single
source of truth that emits them and the gate engine that computes what unlocks next.

CLI:  python -m review.paradigm.profiles --emit          # (re)write all profiles/<lang>.json
      python -m review.paradigm.profiles --lang swh      # show profile + next-unlocked
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"
LAYERS = ("switches", "inventory", "agreement", "exceptions")

# ── single source of truth ───────────────────────────────────────────────────────────────────────────
# Each paradigm: id, paradigm_type, layer, gate (mini-language, see _gate_ok), priority, summary,
# and optional golden/expected_cells. Gates reference SWITCH values or prior PARADIGM statuses, so the
# registry encodes the progressive dependency graph directly.
SEED: dict[str, dict] = {
    "swh": {
        "name": "Swahili", "family": "Bantu (Atlantic-Congo, Niger-Congo)",
        "macro_profile": "agglutinative; prefixing; noun-class concord; no case; no gender",
        "sources": ["https://en.wikipedia.org/wiki/Swahili_grammar"],
        "paradigms": [
            {"id": "swh.noun-class", "paradigm_type": "noun-class", "layer": "inventory", "priority": 1,
             "gate": "switch:gender_or_noun_class == noun-class",
             "golden": "golden/swh_noun-class.json", "expected_cells": 8,
             "summary": "~15-18 sg/pl class pairs (m-/wa-, ki-/vi-, ji-/ma-, u-, ku-, locative -ni)"},
            {"id": "swh.concord", "paradigm_type": "agreement", "layer": "agreement", "priority": 2,
             "gate": "paradigm:swh.noun-class in {learned,confirmed}",
             "summary": "subject/object/adjectival/associative concord agreeing with the noun's class"},
            {"id": "swh.verb-tam", "paradigm_type": "tam", "layer": "inventory", "priority": 3,
             "gate": "switch:tam_locus ~ verb",
             "summary": "verb TAM prefixes na-/li-/ta-/me-/hu-"},
            {"id": "swh.class-allomorphy", "paradigm_type": "reduplication", "layer": "exceptions",
             "priority": 4, "gate": "paradigm:swh.noun-class in {learned,confirmed}",
             "summary": "prefix glide allomorphy before vowels (m~mw, ki~ch, vi~vy, mi~my)"},
        ],
    },
    "ind": {
        "name": "Indonesian", "family": "Austronesian (Malayo-Polynesian)",
        "macro_profile": "agglutinative; affix voice + derivation; no case, no gender, no agreement",
        "sources": ["https://en.wikipedia.org/wiki/Indonesian_language",
                    "https://en.wiktionary.org/wiki/Appendix:Indonesian_affixes"],
        "paradigms": [
            {"id": "ind.voice", "paradigm_type": "voice-focus", "layer": "inventory", "priority": 1,
             "gate": "switch:affix_polarity ~ prefix and switch:case == absent",
             "summary": "active meN-, passive di-"},
            {"id": "ind.reduplication", "paradigm_type": "reduplication", "layer": "inventory",
             "priority": 2, "gate": "switch:reduplication == true",
             "summary": "reduplication for plurality (buku-buku)"},
            {"id": "ind.derivation", "paradigm_type": "voice-focus", "layer": "exceptions", "priority": 3,
             "gate": "paradigm:ind.voice in {learned,confirmed}",
             "summary": "ke-...-an, pe(r)-...-an circumfixes; peN- agentive; -kan/-i applicative/causative"},
        ],
    },
    "tgl": {
        "name": "Tagalog", "family": "Austronesian (Philippine)",
        "macro_profile": "symmetrical voice/focus + NP case-markers; infix+redup aspect; no gender",
        "sources": ["https://en.wikipedia.org/wiki/Tagalog_grammar"],
        "paradigms": [
            {"id": "tgl.voice-focus", "paradigm_type": "voice-focus", "layer": "inventory", "priority": 1,
             "gate": "switch:infixation == true and switch:case == absent",
             "summary": "actor -um-/mag-, patient -in, locative -an, instrument/benefactive i-"},
            {"id": "tgl.np-markers", "paradigm_type": "case", "layer": "inventory", "priority": 2,
             "gate": "paradigm:tgl.voice-focus in {learned,confirmed}",
             "summary": "NP case-markers ang (trigger), ng (genitive), sa (oblique/dative)"},
            {"id": "tgl.aspect", "paradigm_type": "tam", "layer": "exceptions", "priority": 3,
             "gate": "paradigm:tgl.voice-focus in {learned,confirmed}",
             "summary": "aspect via reduplication + infix (-um-/-in-)"},
        ],
    },
    "spa": {
        "name": "Spanish", "family": "Indo-European (Romance)",
        "macro_profile": "fusional; suffixing; gender/number agreement; rich verb conjugation; no nominal case",
        "sources": ["https://www.donquijote.org/blog/spanish-adjectives-gender-and-number-agreement/"],
        "paradigms": [
            {"id": "spa.gender-number", "paradigm_type": "gender-number", "layer": "inventory",
             "priority": 1, "gate": "switch:gender_or_noun_class == gender",
             "summary": "gender (m/f, -o/-a) and number (-s)"},
            {"id": "spa.agreement", "paradigm_type": "agreement", "layer": "agreement", "priority": 2,
             "gate": "paradigm:spa.gender-number in {learned,confirmed}",
             "summary": "gender+number agreement across article-noun-adjective"},
            {"id": "spa.verb-conj", "paradigm_type": "tam", "layer": "inventory", "priority": 3,
             "gate": "switch:synthesis == fusional and switch:affix_polarity ~ suffix",
             "summary": "3 conjugation classes (-ar/-er/-ir) x person/number x TAM"},
            {"id": "spa.clitics", "paradigm_type": "agreement", "layer": "exceptions", "priority": 4,
             "gate": "paradigm:spa.verb-conj in {learned,confirmed}",
             "summary": "clitic object pronouns (me/te/lo/la/se)"},
        ],
    },
    "tur": {
        "name": "Turkish", "family": "Turkic (Oghuz)",
        "macro_profile": "agglutinative; suffixing; case under vowel harmony; no gender",
        "sources": ["https://en.wikipedia.org/wiki/Turkish_grammar",
                    "https://www.easyturkishgrammar.com/post/turkish-case-suffixes"],
        "paradigms": [
            {"id": "tur.case", "paradigm_type": "case", "layer": "inventory", "priority": 1,
             "gate": "switch:affix_polarity ~ suffix and switch:case != absent",
             "golden": "golden/tur_case.json", "expected_cells": 6,
             "summary": "6 cases: nom-Ø, acc -(y)I, dat -(y)A, loc -DA, abl -DAn, gen -(n)In"},
            {"id": "tur.possessive", "paradigm_type": "possessive", "layer": "inventory", "priority": 2,
             "gate": "switch:affix_polarity ~ suffix",
             "summary": "possessive suffixes -Im/-In/-(s)I/...; plural -lAr"},
            {"id": "tur.harmony-allomorphy", "paradigm_type": "case", "layer": "exceptions", "priority": 3,
             "gate": "paradigm:tur.case in {learned,confirmed} and switch:vowel_harmony == true",
             "summary": "every suffix's vowel harmonises (front/back + rounding) with the stem"},
            {"id": "tur.verb-tam", "paradigm_type": "tam", "layer": "inventory", "priority": 4,
             "gate": "switch:affix_polarity ~ suffix",
             "summary": "verb TAM + person agreement; evidentiality -mIş"},
        ],
    },
    "vie": {
        "name": "Vietnamese", "family": "Austroasiatic (Vietic)",
        "macro_profile": "isolating; tonal; classifiers; NO inflectional morphology",
        "sources": ["https://en.wikipedia.org/wiki/Vietnamese_language"],
        "paradigms": [
            {"id": "vie.isolating-confirm", "paradigm_type": "isolating", "layer": "inventory",
             "priority": 1, "gate": "switch:synthesis == isolating",
             "summary": "CONFIRM no case/gender/number/tense morphology — the right answer is 'absent'"},
            {"id": "vie.classifiers", "paradigm_type": "classifier", "layer": "inventory", "priority": 2,
             "gate": "switch:synthesis == isolating",
             "summary": "classifier system (cái, con, ...) before counted/specified nouns"},
        ],
    },
    "hin": {
        "name": "Hindi", "family": "Indo-European (Indo-Aryan)",
        "macro_profile": "fusional/agglutinative; suffixing+postpositional; gender + case + split ergativity",
        "sources": ["https://en.wikipedia.org/wiki/Hindustani_declension",
                    "https://grokipedia.com/page/Hindustani_grammar"],
        "paradigms": [
            {"id": "hin.gender", "paradigm_type": "gender-number", "layer": "inventory", "priority": 1,
             "gate": "switch:gender_or_noun_class == gender",
             "summary": "gender (m/f) and number (sg/pl)"},
            {"id": "hin.case", "paradigm_type": "case", "layer": "inventory", "priority": 2,
             "gate": "switch:affix_polarity ~ suffix and switch:case != absent",
             "summary": "direct/oblique/vocative + postpositional case (ne, ko, se, mein, par, ke)"},
            {"id": "hin.ergative-split", "paradigm_type": "case", "layer": "exceptions", "priority": 3,
             "gate": "paradigm:hin.case in {learned,confirmed}",
             "summary": "split ergativity: ne on the perfective transitive subject; verb agrees with object"},
            {"id": "hin.agreement", "paradigm_type": "agreement", "layer": "agreement", "priority": 4,
             "gate": "paradigm:hin.gender in {learned,confirmed}",
             "summary": "verb/adjective agreement in gender+number"},
        ],
    },
    "rus": {
        "name": "Russian", "family": "Indo-European (Slavic)",
        "macro_profile": "fusional; suffixing; case x gender x declension class; verb aspect; no articles",
        "sources": ["https://en.wikipedia.org/wiki/Russian_declension"],
        "paradigms": [
            {"id": "rus.case", "paradigm_type": "case", "layer": "inventory", "priority": 1,
             "gate": "switch:affix_polarity ~ suffix and switch:case != absent",
             "golden": "golden/rus_case.json", "expected_cells": 6,
             "summary": "6 cases: nom, gen, dat, acc, instr, prep"},
            {"id": "rus.gender", "paradigm_type": "gender-number", "layer": "inventory", "priority": 2,
             "gate": "switch:gender_or_noun_class == gender or switch:gender_or_noun_class == noun-class",
             "summary": "gender (m/f/n) and number (sg/pl); animacy (acc=gen for animate masc)"},
            {"id": "rus.declension", "paradigm_type": "case", "layer": "exceptions", "priority": 3,
             "gate": "paradigm:rus.case in {learned,confirmed} and paradigm:rus.gender in {learned,confirmed}",
             "summary": "declension classes (gender-linked); case x gender fusion"},
            {"id": "rus.adj-agreement", "paradigm_type": "agreement", "layer": "agreement", "priority": 4,
             "gate": "paradigm:rus.case in {learned,confirmed} and paradigm:rus.gender in {learned,confirmed}",
             "summary": "adjective agreement in gender+number+case"},
            {"id": "rus.aspect", "paradigm_type": "tam", "layer": "inventory", "priority": 5,
             "gate": "switch:affix_polarity ~ suffix",
             "summary": "verb aspect (perfective/imperfective)"},
        ],
    },
}


def _switches_paradigm(lang: str) -> dict:
    """Every language's layer-0 paradigm: learn the typological switches first. No gate."""
    return {"id": f"{lang}.switches", "paradigm_type": "switches", "layer": "switches", "priority": 0,
            "gate": "", "summary": "typological switch profile (synthesis, affix polarity, harmony, "
                                   "gender-or-noun-class, case presence, voice) — gates everything below"}


def build_profile(lang: str) -> dict:
    s = SEED[lang]
    paradigms = [_switches_paradigm(lang)] + [dict(p, status=p.get("status", "locked")) for p in s["paradigms"]]
    paradigms[0]["status"] = paradigms[0].get("status", "candidate")  # switches always start unlocked
    return {
        "language": lang, "name": s["name"], "family": s["family"],
        "macro_profile": s["macro_profile"], "sources": s["sources"],
        "confirmed": "2026-06", "layers": list(LAYERS),
        "schema_version": 1,
        "paradigms": paradigms,
    }


# ── gate engine: the progressive unlock ────────────────────────────────────────────────────────────────
def _atom_ok(atom: str, switches: dict, statuses: dict) -> bool:
    atom = atom.strip()
    m = re.match(r"switch:(\w+)\s*(==|!=|~)\s*(.+)", atom)
    if m:
        name, op, val = m.group(1), m.group(2), m.group(3).strip()
        have = str(switches.get(name, "")).lower()
        val = val.lower()
        if op == "==":
            return have == val
        if op == "!=":
            return have != val
        if op == "~":               # 'has this' — affix_polarity ~ suffix matches 'suffixing' AND 'both';
            if not have:            # tam_locus ~ verb matches 'verb-prefix'/'verb-suffix'
                return False
            return val in have or have in val or have == "both"
    m = re.match(r"paradigm:([\w.-]+)\s+in\s+\{([^}]*)\}", atom)
    if m:
        pid, allowed = m.group(1), {x.strip() for x in m.group(2).split(",")}
        return statuses.get(pid, "locked") in allowed
    return False


def gate_ok(gate: str, switches: dict, statuses: dict) -> bool:
    """Evaluate a gate string. Supports `A and B` / `A or B` conjunctions of atoms; empty gate == open."""
    if not gate.strip():
        return True
    if " or " in gate:
        return any(gate_ok(part, switches, statuses) for part in gate.split(" or "))
    return all(_atom_ok(part, switches, statuses) for part in gate.split(" and "))


def next_unlocked(lang: str, switches: dict, statuses: dict | None = None) -> list[dict]:
    """Given the learned switch values + current per-paradigm statuses, return the paradigms whose gate is
    now satisfied but which are not yet learned/confirmed/absent — i.e. what falls out next, in priority
    order. This is the progressive 'fall out as each one is learned' engine."""
    prof = load(lang)
    statuses = statuses or {p["id"]: p.get("status", "locked") for p in prof["paradigms"]}
    out = []
    for p in sorted(prof["paradigms"], key=lambda x: x.get("priority", 99)):
        st = statuses.get(p["id"], p.get("status", "locked"))
        if st in ("learned", "confirmed", "absent"):
            continue
        if gate_ok(p.get("gate", ""), switches, statuses):
            out.append(p)
    return out


# ── emit + query the per-language JSON artifacts ────────────────────────────────────────────────────────
def emit(lang: str, *, reset: bool = False) -> Path:
    """Write profiles/<lang>.json from the seed. By default PRESERVES runtime state (status/metric) already
    recorded for a paradigm id, so re-emitting to pick up seed changes does not wipe learned progress —
    the file stays a trustworthy state of record. Pass reset=True to force back to seed defaults."""
    PROFILE_DIR.mkdir(exist_ok=True)
    path = PROFILE_DIR / f"{lang}.json"
    fresh = build_profile(lang)
    if not reset and path.exists():
        prev = {p["id"]: p for p in json.loads(path.read_text(encoding="utf-8")).get("paradigms", [])}
        for p in fresh["paradigms"]:
            old = prev.get(p["id"])
            if old and old.get("status", "locked") not in ("locked", "candidate"):
                p["status"] = old["status"]
                if "metric" in old:
                    p["metric"] = old["metric"]
    path.write_text(json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def emit_all(*, reset: bool = False) -> list[Path]:
    return [emit(lang, reset=reset) for lang in SEED]


def load(lang: str) -> dict:
    path = PROFILE_DIR / f"{lang}.json"
    if not path.exists():
        emit(lang)
    return json.loads(path.read_text(encoding="utf-8"))


def get_paradigm(lang: str, pid: str) -> dict | None:
    return next((p for p in load(lang)["paradigms"] if p["id"] == pid), None)


def by_layer(lang: str, layer: str) -> list[dict]:
    return [p for p in load(lang)["paradigms"] if p["layer"] == layer]


def set_status(lang: str, pid: str, status: str) -> dict:
    """Persist a paradigm's learned status (locked|candidate|learned|confirmed|absent) + optional metric."""
    prof = load(lang)
    for p in prof["paradigms"]:
        if p["id"] == pid:
            p["status"] = status
    (PROFILE_DIR / f"{lang}.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
    return prof


def find_by_type(lang: str, paradigm_type: str) -> dict | None:
    """First paradigm of this type (preferring the inventory layer — the cell-defining one)."""
    ps = [p for p in load(lang)["paradigms"] if p["paradigm_type"] == paradigm_type]
    ps.sort(key=lambda p: 0 if p["layer"] == "inventory" else 1)
    return ps[0] if ps else None


def record_result(lang: str, pid: str, *, status: str, metric: dict | None = None) -> dict:
    """Persist a learned/absent result + its report-vs-golden metric onto the queryable profile. This is
    how the report metric becomes the live state of the per-language paradigm registry."""
    prof = load(lang)
    for p in prof["paradigms"]:
        if p["id"] == pid:
            p["status"] = status
            if metric is not None:
                p["metric"] = metric
    (PROFILE_DIR / f"{lang}.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
    return prof


def status_summary(lang: str) -> dict:
    prof = load(lang)
    out: dict[str, int] = {}
    for p in prof["paradigms"]:
        out[p.get("status", "locked")] = out.get(p.get("status", "locked"), 0) + 1
    return {"language": lang, "n_paradigms": len(prof["paradigms"]), "by_status": out}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", action="store_true", help="(re)write all profiles/<lang>.json (preserves runtime state)")
    ap.add_argument("--reset", action="store_true", help="with --emit: force back to seed defaults")
    ap.add_argument("--lang", help="show one language's profile + next-unlocked")
    args = ap.parse_args(argv)
    if args.emit:
        paths = emit_all(reset=args.reset)
        print(f"wrote {len(paths)} profiles: " + ", ".join(p.name for p in paths))
    if args.lang:
        prof = load(args.lang)
        print(json.dumps(prof, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
