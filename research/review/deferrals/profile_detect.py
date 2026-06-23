"""Detect a language's "master switches" (typological parameters) FROM THE CORPUS — then cross-check the
internet (WALS/Grambank seed) and present each as a falsifiable, evidence-backed claim to a human.

Each switch is detected from pieces we already have (the cycle's induced affixes, corpus statistics,
`phonology_induce`, orthography, and the cached morpheme alignment), producing
`{value, confidence, evidence}` with `provenance="detected"`. We then compare to the internet seed
(`profile._seed`) and flag **agree** (boost) vs **conflict** (ask the human) — the internet becomes a
cross-check, not the source. The output reframes the workflow: confirm ~12 switches FIRST (cheap,
high-leverage), and they constrain + accelerate induction, gold-raise, and the deferral hypotheses.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from gold.compile import EBIBLE, PAIR_DIR  # noqa: E402

# English grammatical words used to read alignment-based switches
_PRONOUN = {"i", "you", "we", "he", "she", "they", "it"}
_TENSE = {"will", "shall", "was", "were", "had", "has", "have", "did"}
_ARTICLE = {"the", "a", "an"}


@dataclass
class Switch:
    name: str
    value: object
    confidence: float
    evidence: str
    internet: object = None          # the WALS/Grambank seed value, if any
    agrees: bool | None = None       # detected vs internet


def _freqs(pair: str) -> Counter:
    c: Counter = Counter()
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c.update(t.lower() for t in json.loads(line)["tgt"] if t.isalpha())
    return c


def _cycle_affixes(pair: str) -> list[dict]:
    p = _RESEARCH / "induce" / "out" / f"{pair}_model.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("affixes", [])
    return []


def _morph_markers(pair: str) -> list[dict]:
    from gold.goldio import FROZEN
    p = FROZEN / pair / "morph_alignments.jsonl"
    if p.exists():
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l]
    return []


# --------------------------------------------------------------------------- the detectors
def detect_synthesis(freqs: Counter, affixes: list[dict]) -> Switch:
    uniq, tot = len(freqs), sum(freqs.values())
    ttr = uniq / tot if tot else 0.0
    n_aff = len(affixes)
    if ttr >= 0.09 and n_aff >= 40:
        val = "agglutinative"
    elif n_aff >= 20:
        val = "fusional/agglutinative"
    else:
        val = "isolating-leaning"
    conf = 0.5 + min(0.3, abs(ttr - 0.06) * 3)
    return Switch("synthesis", val, round(conf, 2),
                  f"type:token {ttr:.3f} ({uniq} forms / {tot} tokens), {n_aff} induced affixes")


def detect_affix_polarity(affixes: list[dict]) -> Switch:
    pre = sum(a.get("count", 0) or 1 for a in affixes if a.get("kind") == "prefix")
    suf = sum(a.get("count", 0) or 1 for a in affixes if a.get("kind") == "suffix")
    npre = sum(a.get("kind") == "prefix" for a in affixes)
    nsuf = sum(a.get("kind") == "suffix" for a in affixes)
    tot = npre + nsuf or 1
    val = "prefixing" if npre > nsuf * 1.3 else "suffixing" if nsuf > npre * 1.3 else "both"
    return Switch("affix_polarity", val, round(0.5 + min(0.4, abs(npre - nsuf) / tot), 2),
                  f"{npre} prefix vs {nsuf} suffix morphemes induced")


def detect_reduplication(freqs: Counter) -> Switch:
    content = [w for w, c in freqs.items() if len(w) >= 4 and c >= 2]
    def dup(w: str) -> bool:
        return "-" in w or any(w[:k] == w[k:2 * k] for k in range(2, len(w) // 2 + 1))
    hits = [w for w in content if dup(w)]
    present = len(hits) >= 5
    return Switch("reduplication", present, round(0.5 + min(0.45, len(hits) / 200), 2),
                  f"{len(hits)} word types with a repeated chunk (e.g. {', '.join(hits[:4])})")


def detect_infixation(freqs: Counter) -> Switch:
    """Internal-insertion minimal pairs: a word whose 2-char chunk at position 1 can be removed to leave
    an attested base (sulat → s‹um›ulat). A recurring chunk (um/in) = infixation."""
    chunks: Counter = Counter()
    ex: dict[str, str] = {}
    base = {w for w, c in freqs.items() if 3 <= len(w) <= 9 and c >= 2}
    for w in freqs:
        if len(w) >= 5:
            cand = w[0] + w[3:]
            if cand in base:
                chunks[w[1:3]] += 1
                ex.setdefault(w[1:3], f"{cand}→{w}")
    top = chunks.most_common(1)
    present = bool(top) and top[0][1] >= 5
    note = f"top internal insert -{top[0][0]}- ×{top[0][1]} ({ex.get(top[0][0],'')})" if top else "none found"
    return Switch("infixation", present, round(0.5 + (min(0.4, top[0][1] / 50) if top else 0), 2), note)


def detect_tone(pair: str) -> Switch:
    from gold.orthography import writing_system
    ws = writing_system(pair)
    # tone is orthographically marked with combining tone diacritics; the four NT scripts don't use them
    tone_marks = re.compile(r"[̀́̂̌̄]")  # grave/acute/circumflex/caron/macron
    has = bool(tone_marks.search("".join(ws.get("alphabet", "")) if isinstance(ws.get("alphabet"), str) else ""))
    return Switch("tone", has, 0.6, "no tone diacritics in the orthography (Latin, NT)" if not has
                  else "tone diacritics present in orthography")


def detect_phonology(pair: str) -> list[Switch]:
    from gold.phonology_induce import nasal_assimilation, vowel_harmony
    out = []
    try:
        vh = vowel_harmony(pair)
        out.append(Switch("vowel_harmony", bool(vh), round(0.5 + min(0.4, len(vh) / 10), 2),
                          f"{len(vh)} stem-conditioned suffix-vowel alternations" if vh else "no harmony signal"))
    except Exception as e:
        out.append(Switch("vowel_harmony", None, 0.0, f"detector error: {e}"))
    try:
        na = nasal_assimilation(pair)
        out.append(Switch("nasal_assimilation", bool(na), round(0.5 + min(0.4, len(na) / 10), 2),
                          f"{len(na)} place-conditioned prefix-nasal alternations" if na else "no assimilation signal"))
    except Exception as e:
        out.append(Switch("nasal_assimilation", None, 0.0, f"detector error: {e}"))
    return out


def detect_alignment_switches(pair: str) -> list[Switch]:
    """TAM locus, head-marking agreement, and articles — read from the cached morpheme alignment
    (`morph_alignments.jsonl`). Skipped (low-confidence 'unknown') if no alignment has been run."""
    markers = _morph_markers(pair)
    if not markers:
        return [Switch(n, None, 0.0, "no morpheme alignment cached — run align/morph_align_hc.py")
                for n in ("agreement_head_marking", "tam_locus", "articles")]
    pre = [m for m in markers if m.get("type") == "prefix" and m.get("source_tokens")]
    def aligns_to(ms, vocab):
        return [m for m in ms if (m["source_tokens"][0][0] or "").lower() in vocab]
    agr = aligns_to(pre, _PRONOUN)
    tam = aligns_to(pre, _TENSE)
    art = [m for m in markers if (m.get("source_tokens") or [["", 0]])[0][0].lower() in _ARTICLE]
    return [
        Switch("agreement_head_marking", bool(agr), round(0.5 + min(0.4, len(agr) / 30), 2),
               f"{len(agr)} verb-prefix morphemes align to subject pronouns "
               f"(e.g. {', '.join(sorted({m['form'] for m in agr})[:4])})"),
        Switch("tam_locus", "verb-prefix" if tam else "unclear", round(0.5 + min(0.4, len(tam) / 30), 2),
               f"{len(tam)} prefix morphemes align to tense/aspect words"),
        Switch("articles", bool(art), round(0.5 + min(0.4, len(art) / 30), 2),
               f"{len(art)} morphemes align to the/a" if art else "nothing aligns to the/a → likely no articles"),
    ]


# --------------------------------------------------------------------------- run + cross-check
def _internet_seed(pair: str) -> dict:
    """Flatten the WALS/Grambank-seeded profile into name→value for cross-checking the detectors."""
    from . import profile as P
    prof = P._seed(pair)
    seed = {"affix_polarity": "prefixing" if prof.affix_processes.get("prefix") and
            prof.morph_type == "agglutinative" else None,
            "synthesis": prof.morph_type,
            "reduplication": bool(prof.affix_processes.get("reduplication") and prof.affix_processes["reduplication"].value),
            "infixation": bool(prof.affix_processes.get("infix") and prof.affix_processes["infix"].value),
            "vowel_harmony": bool(prof.phon_processes.get("vowel_harmony") and prof.phon_processes["vowel_harmony"].value),
            "nasal_assimilation": bool(prof.phon_processes.get("nasal_assimilation") and prof.phon_processes["nasal_assimilation"].value),
            "tone": bool(prof.phon_processes.get("tone") and prof.phon_processes["tone"].value)}
    return seed


def detect(pair: str) -> list[Switch]:
    freqs = _freqs(pair)
    affixes = _cycle_affixes(pair)
    switches = [detect_synthesis(freqs, affixes), detect_affix_polarity(affixes),
                detect_reduplication(freqs), detect_infixation(freqs), detect_tone(pair)]
    switches += detect_phonology(pair)
    switches += detect_alignment_switches(pair)
    seed = _internet_seed(pair)
    for s in switches:
        if s.name in seed and seed[s.name] is not None:
            s.internet = seed[s.name]
            s.agrees = _compatible(s.value, s.internet)
    return switches


def _compatible(detected, internet) -> bool:
    if isinstance(internet, bool):
        return bool(detected) == internet
    return str(detected).split("/")[0] in str(internet) or str(internet) in str(detected)


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=["spa", "ind", "tgl", "swh"])
    args = ap.parse_args(argv)
    print(f"\n=== Master switches for {args.pair} — detected from the corpus (am I right?) ===")
    for s in detect(args.pair):
        x = {True: "✓agrees", False: "⚠CONFLICT", None: ""}.get(s.agrees, "")
        net = f"  [internet: {s.internet}]" if s.internet is not None else ""
        print(f"  {s.name:24} = {str(s.value):22} (conf {s.confidence})  — {s.evidence}{net} {x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
