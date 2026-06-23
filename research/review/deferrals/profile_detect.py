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
    """Greenberg (1960) two-index typology: the **synthetic index M/W** (mean morphemes per word) places a
    language on isolating→synthetic→polysynthetic, and the **agglutination index** (how cleanly morphemes
    separate at boundaries) separates *agglutinative* (clean) from *fusional* (fused). We estimate M/W by
    greedily stripping the induced affixes off frequent words, and agglutination by the fraction that strip
    cleanly to an ATTESTED stem (fusion obscures the stem; agglutination leaves it whole)."""
    pre = sorted({a["form"] for a in affixes if a.get("kind") == "prefix" and a.get("form")}, key=len, reverse=True)
    suf = sorted({a["form"] for a in affixes if a.get("kind") == "suffix" and a.get("form")}, key=len, reverse=True)
    attested = {w for w, c in freqs.items() if c >= 2 and len(w) >= 2}
    total_m = clean = n = 0
    for w, c in freqs.most_common(3000):
        if not w.isalpha() or len(w) < 2:
            continue
        n += c
        morphs, residual, changed = 1, w, True
        while changed and len(residual) > 2:
            changed = False
            for p in pre:
                if residual.startswith(p) and len(residual) > len(p) + 1:
                    residual, morphs, changed = residual[len(p):], morphs + 1, True
                    break
            if changed:
                continue
            for s in suf:
                if residual.endswith(s) and len(residual) > len(s) + 1:
                    residual, morphs, changed = residual[: -len(s)], morphs + 1, True
                    break
        total_m += morphs * c
        if morphs >= 2 and residual in attested:        # decomposed cleanly to an attested stem
            clean += c
    mw = total_m / n if n else 1.0                       # synthetic index (reliable)
    agglut = clean / n if n else 0.0                     # agglutination proxy (reported as evidence only)
    # The M/W axis is reliable (isolating ↔ synthetic ↔ polysynthetic). The agglutinative-vs-fusional split
    # is properly the agglutination index, which is NOT reliably measurable from raw text + a noisy induced
    # affix list — so we estimate it from M/W (more morphemes/word leans agglutinative) at moderate
    # confidence and let the cross-check + human settle the fine call.
    if mw < 1.5:
        val = "isolating"
    elif mw >= 3.5:
        val = "polysynthetic"
    elif mw >= 2.3:
        val = "agglutinative"
    else:
        val = "fusional"
    conf = round(min(0.7, 0.5 + abs(mw - 2.3) / 4), 2)   # near the agglutinative/fusional boundary → less sure
    return Switch("synthesis", val, conf,
                  f"Greenberg synthetic index M/W≈{mw:.2f} (agglutination proxy {agglut:.0%}); "
                  f"the agglutinative↔fusional call is M/W-approximate — confirm")


def detect_affix_polarity(affixes: list[dict]) -> Switch:
    pre = sum(a.get("count", 0) or 1 for a in affixes if a.get("kind") == "prefix")
    suf = sum(a.get("count", 0) or 1 for a in affixes if a.get("kind") == "suffix")
    npre = sum(a.get("kind") == "prefix" for a in affixes)
    nsuf = sum(a.get("kind") == "suffix" for a in affixes)
    tot = npre + nsuf or 1
    val = "prefixing" if npre > nsuf * 1.3 else "suffixing" if nsuf > npre * 1.3 else "both"
    return Switch("affix_polarity", val, round(0.5 + min(0.4, abs(npre - nsuf) / tot), 2),
                  f"{npre} prefix vs {nsuf} suffix morphemes induced")


# A morphological process counts as PRESENT only if it is PRODUCTIVE — it recurs across at least this many
# DISTINCT stems (the operational Tolerance Principle, cf. assess.metrics.tolerance_productive). This is
# what rejects coincidental-substring false positives (swh `lakini`→"-ak-", spa `beber`→reduplication).
MIN_STEMS = 8


def detect_reduplication(freqs: Counter) -> Switch:
    """Reduplication is real only when the DE-DOUBLED base is itself an attested word (buku-buku ⇐ buku),
    and the pattern recurs across ≥ MIN_STEMS distinct stems — a coincidental CV repeat (spa beber) has no
    attested base, so it is rejected."""
    attested = set(freqs)
    def base_of(w: str):
        if "-" in w:                                  # hyphenated doubling: araw-araw ⇐ araw
            a, _, b = w.partition("-")
            return a if a and a == b and a in attested else None
        for k in range(2, len(w) // 2 + 1):           # full leading doubling: bukubuku ⇐ buku
            if w[:k] == w[k:2 * k] and (w[k:] in attested or w[:k] in attested):
                return w[:k]
        return None
    real = [w for w in freqs if len(w) >= 4 and freqs[w] >= 2 and base_of(w)]
    present = len(real) >= MIN_STEMS
    return Switch("reduplication", present, round(0.5 + min(0.4, len(real) / 30), 2),
                  f"{len(real)} reduplications with an attested base "
                  f"(e.g. {', '.join(real[:4])}); productive={'yes' if present else 'no'}")


def detect_infixation(freqs: Counter) -> Switch:
    """Internal-insertion minimal pairs: a word whose 2-char chunk at position 1 can be removed to leave
    an attested base (sulat → s‹um›ulat). Present only if a chunk recurs across ≥ MIN_STEMS DISTINCT
    attested stems (productivity gate — kills swh `lakini`→"-ak-")."""
    from collections import defaultdict
    chunk_bases: dict[str, set] = defaultdict(set)
    ex: dict[str, str] = {}
    base = {w for w, c in freqs.items() if 3 <= len(w) <= 9 and c >= 2}
    for w in freqs:
        if len(w) >= 5:
            cand = w[0] + w[3:]
            if cand in base:
                chunk_bases[w[1:3]].add(cand)
                ex.setdefault(w[1:3], f"{cand}→{w}")
    if not chunk_bases:
        return Switch("infixation", False, 0.55, "no internal-insertion minimal pairs found")
    counts = sorted((len(s) for s in chunk_bases.values()), reverse=True)
    chunk = max(chunk_bases, key=lambda c: len(chunk_bases[c]))
    n = counts[0]
    # dominance: a real infix TOWERS over the noise floor (tgl -in-=154); a coincidence sits at it
    # (swh -ak-=43 among many ~40s). Require the top chunk to be ≥ DOMINANCE× the median chunk.
    median = counts[len(counts) // 2] if counts else 0
    # dominance only applies when there's a noise floor to stand out from (≥3 competing chunks);
    # a single clean infix has no floor and passes on its stem count alone.
    dominant = len(counts) < 3 or n >= 3 * max(median, 1)
    present = n >= MIN_STEMS and dominant
    why = "yes" if present else ("no — too few stems" if n < MIN_STEMS
                                 else f"no — not dominant (top {n} vs median {median}, likely coincidental)")
    return Switch("infixation", present, round(0.5 + min(0.4, n / 40), 2),
                  f"top internal insert -{chunk}- across {n} distinct stems (e.g. {ex.get(chunk)}); "
                  f"productive={why}")


def detect_gender_noun_class(freqs: Counter, affixes: list[dict]) -> Switch:
    """Corbett (1991): both gender and noun-class are AGREEMENT-class systems; they differ in size + basis.
    Two corpus signatures: (a) GENDER — a productive Romance-style `-o/-a` suffix alternation on the same
    stem (gato/gata); (b) NOUN-CLASS — a small set of short prefixes that EACH recur across many stems and
    pair up sg/pl (Bantu m-/wa-, ki-/vi-, the alliterative-concord hallmark). Noun-class requires SEVERAL
    such recurring prefixes (so coincidental verbal/derivational prefixes in Philippine-type languages don't
    masquerade as classes); gender requires a productive -o/-a set. Strength-compared; else none."""
    from collections import defaultdict
    attested = {w for w, c in freqs.items() if c >= 2}
    gender_pairs = [w for w in attested if len(w) > 2 and w.endswith("o") and w[:-1] + "a" in attested]
    pre = sorted({a["form"] for a in affixes if a.get("kind") == "prefix" and 1 <= len(a["form"]) <= 3})
    stem_prefixes: dict[str, set] = defaultdict(set)
    for w in attested:
        for p in pre:
            if w.startswith(p) and len(w) > len(p) + 2 and w[len(p):] in attested:
                stem_prefixes[w[len(p):]].add(p)
    multi = [s for s, ps in stem_prefixes.items() if len(ps) >= 2]
    prefix_load = Counter(p for s in multi for p in stem_prefixes[s])
    strong = [p for p, c in prefix_load.items() if c >= MIN_STEMS]   # prefixes that recur across many stems
    # a real noun-class system: SEVERAL recurring class prefixes over many stems (not 1–2 coincidences)
    nc = len(multi) >= 3 * MIN_STEMS and len(strong) >= 4
    gender = len(gender_pairs) >= MIN_STEMS
    if nc and len(multi) >= len(gender_pairs):
        return Switch("gender_or_noun_class", "noun-class", 0.7,
                      f"{len(multi)} stems take ≥2 of {len(strong)} recurring class prefixes "
                      f"(e.g. {sorted(strong)[:6]})")
    if gender:
        return Switch("gender_or_noun_class", "gender", 0.65,
                      f"{len(gender_pairs)} productive -o/-a gender alternations (e.g. {gender_pairs[:3]})")
    return Switch("gender_or_noun_class", "none", 0.55,
                  "no productive -o/-a gender alternation and no recurring class-prefix system")


def detect_case(freqs: Counter) -> Switch:
    """Case is hard to confirm from text without role annotation; we report the conservative default
    (absent) with low confidence — the internet cross-check / human is the real arbiter here."""
    return Switch("case", "absent", 0.45,
                  "no role-correlated noun inflection detectable from text alone (low confidence)")


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
    # Nichols (1986): head-marking agreement (and Bybee's TAM) may sit on EITHER edge of the verb — check
    # both prefix and suffix affixes, and report the locus.
    aff = [m for m in markers if m.get("type") in ("prefix", "suffix") and m.get("source_tokens")]
    def aligns_to(vocab, side=None):
        return [m for m in aff if (side is None or m["type"] == side)
                and (m["source_tokens"][0][0] or "").lower() in vocab]
    agr_pre, agr_suf = aligns_to(_PRONOUN, "prefix"), aligns_to(_PRONOUN, "suffix")
    agr = agr_pre + agr_suf
    agr_val = ("subject" if agr else "none")
    agr_locus = "prefix" if len(agr_pre) >= len(agr_suf) else "suffix"
    tam_pre, tam_suf = aligns_to(_TENSE, "prefix"), aligns_to(_TENSE, "suffix")
    tam_val = ("verb-prefix" if len(tam_pre) > len(tam_suf) else "verb-suffix") if (tam_pre or tam_suf) else "unclear"
    # Articles are a CLOSED, high-frequency class: require a DOMINANT single morpheme aligning to the/a,
    # not diffuse alignment (swh's demonstratives/agreement spread thinly over 'the' → not articles).
    from collections import Counter as _C
    art_load = _C(m["form"] for m in markers
                  if (m.get("source_tokens") or [["", 0]])[0][0].lower() in _ARTICLE)
    art_top = art_load.most_common(1)[0] if art_load else None
    diffuse = len(art_load) > 8 and (art_top[1] < 0.25 * sum(art_load.values()))   # spread thin → no article
    art_present = bool(art_top) and not diffuse
    return [
        Switch("agreement_head_marking", agr_val, round(0.5 + min(0.4, len(agr) / 30), 2),
               f"{len(agr_pre)} prefix + {len(agr_suf)} suffix verb morphemes align to subject pronouns "
               f"(locus: {agr_locus}; e.g. {', '.join(sorted({m['form'] for m in agr})[:4])})"),
        Switch("tam_locus", tam_val, round(0.5 + min(0.4, (len(tam_pre) + len(tam_suf)) / 30), 2),
               f"{len(tam_pre)} prefix + {len(tam_suf)} suffix morphemes align to tense/aspect words"),
        Switch("articles", "both" if art_present else "none",
               round(0.5 + min(0.4, (art_top[1] if art_top else 0) / 30), 2),
               (f"dominant morpheme '{art_top[0]}' aligns to the/a ({art_top[1]}×)" if art_present
                else "no dominant article morpheme (alignment to the/a is diffuse → likely no articles)")),
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
    nc = prof.feature_space.get("noun_class"); g = prof.feature_space.get("gender")
    c = prof.feature_space.get("case")
    seed["gender_or_noun_class"] = ("noun-class" if (nc and nc.value) else
                                    "gender" if (g and g.value) else "none")
    seed["case"] = "present" if (c and c.value) else "absent"
    agr = prof.feature_space.get("agreement"); defi = prof.feature_space.get("definiteness")
    seed["agreement_head_marking"] = "subject" if (agr and agr.value) else "none"
    seed["articles"] = "both" if (defi and defi.value) else "none"
    return seed


def detect(pair: str) -> list[Switch]:
    freqs = _freqs(pair)
    affixes = _cycle_affixes(pair)
    switches = [detect_synthesis(freqs, affixes), detect_affix_polarity(affixes),
                detect_reduplication(freqs), detect_infixation(freqs), detect_tone(pair),
                detect_gender_noun_class(freqs, affixes), detect_case(freqs)]
    switches += detect_phonology(pair)
    switches += detect_alignment_switches(pair)
    seed = _internet_seed(pair)
    for s in switches:
        if s.name in seed and seed[s.name] is not None and s.value not in (None, "unknown"):
            s.internet = seed[s.name]
            s.agrees = _compatible(s.value, s.internet)
            # the internet seed is reliable typology — agreement boosts confidence; a CONFLICT means the
            # detector's heuristic is uncertain, so drop to low confidence and let the human adjudicate
            # (a noisy orthographic guess like swh `-ak-` should never stand at 0.9 against WALS).
            if s.agrees:
                s.confidence = round(min(0.99, s.confidence + 0.1), 2)
            else:
                s.confidence = round(min(s.confidence, 0.4), 2)
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
