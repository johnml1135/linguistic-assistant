"""Spanish-style GENDER-NUMBER detector — the third detector family (after Bantu prefixal concord and
suffixal case). Two emergent signals, both recovered from data, no recalled "masculine/feminine":

  * GENDER as a 2-class agreement: cluster nouns by final vowel (-o, -a, …); the DETERMINER that precedes
    each cluster differs (-o → el/del/al, -a → la). Distinct determiners on distinct endings = a gender
    agreement system. (The concord half — like Bantu, but the controller is the noun's suffix.)
  * NUMBER from projected feature covariation: the -s suffix co-varies with the English-pivot Number
    feature (Plur). (The covariation half — like case, but keyed on the Number feat, not the dep-role.)

Cached per (lang, sample) like the case detector, so the metric is reproducible (THOT is stochastic).
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
_VOWELS = set("aeiouáéíóúü")


def _cache_path(pair: str, sample: int) -> Path:
    return CACHE_DIR / f"gn_votes_{pair}_{sample}.json"


def gn_votes(pair: str, *, sample: int = 300, refresh: bool = False):
    """Scan → (final-vowel → Counter(preceding determiner)), (suffix → Counter(Number feat)), counts.
    Disk-cached for reproducibility + speed."""
    cpath = _cache_path(pair, sample)
    if cpath.exists() and not refresh:
        d = json.loads(cpath.read_text(encoding="utf-8"))
        return ({k: Counter(v) for k, v in d["fv_det"].items()},
                {k: Counter(v) for k, v in d["suf_num"].items()}, d["n_noun"])

    from review.project import _word_alignment, project_verse, get_parser
    verses, table = _word_alignment(pair, sample=sample)
    par = get_parser("en")
    fv_det: dict[str, Counter] = defaultdict(Counter)
    suf_num: dict[str, Counter] = defaultdict(Counter)
    n_noun = 0
    for _ref, src, tgt in verses:
        proj = project_verse(par(" ".join(src)), src, tgt, table)
        for i, p in enumerate(proj):
            if p.get("pos") != "NOUN" or not p.get("vern"):
                continue
            n_noun += 1
            w = p["vern"].lower()
            fv = w[-1]
            num = p.get("feats", {}).get("Number", "") or "?"
            suf = "s" if w.endswith("s") else (fv if fv in _VOWELS else "C")
            suf_num[suf][num] += 1
            if fv in _VOWELS:
                prev = proj[i - 1]["vern"].lower() if i > 0 and proj[i - 1].get("vern") else "<s>"
                fv_det[fv][prev] += 1
    CACHE_DIR.mkdir(exist_ok=True)
    cpath.write_text(json.dumps({"fv_det": {k: dict(v) for k, v in fv_det.items()},
                                 "suf_num": {k: dict(v) for k, v in suf_num.items()},
                                 "n_noun": n_noun}, ensure_ascii=False), encoding="utf-8")
    return fv_det, suf_num, n_noun


def gender_number_hypotheses(pair: str, *, sample: int = 300, min_n: int = 8, top: int = 4) -> dict:
    """A/B/C gender classes (final-vowel cluster + its dominant determiner) + the number marker."""
    fv_det, suf_num, n_noun = gn_votes(pair, sample=sample)
    gender_rows = []
    for fv, det in sorted(fv_det.items(), key=lambda kv: -kv[1].total()):
        total = det.total()
        if total < min_n:
            continue
        ranked = det.most_common()
        top_det, top_c = ranked[0]
        gender_rows.append({"ending": fv, "n": total, "markers": [fv, top_det],
                            "determiner": top_det, "det_share": round(top_c / total, 3),
                            "candidates": [{"determiner": d, "n": c, "share": round(c / total, 3)}
                                           for d, c in ranked[:3]]})
    gender_rows = gender_rows[:top]
    # number: the -s suffix's dominant projected Number feature
    s_num = suf_num.get("s", Counter())
    num_total = s_num.total()
    number_row = None
    if num_total >= min_n:
        ranked = s_num.most_common()
        number_row = {"suffix": "s", "n": num_total, "markers": ["s"],
                      "dominant_number": ranked[0][0], "share": round(ranked[0][1] / num_total, 3)}
    return {"pair": pair, "question": "gender (determiner agreement) + number (-s covariation)",
            "n_nouns": n_noun, "gender_classes": gender_rows, "number": number_row,
            "n_gender_classes": len(gender_rows)}


@lru_cache(maxsize=16)
def detect_gender_number(pair: str, *, sample: int = 200) -> tuple[bool, float, str, dict]:
    """Present when >= 2 final-vowel classes take DISTINCT dominant determiners (the gender-agreement
    signature). Returns (detected, conf, evidence, hyps)."""
    # Layer-0 gate: only a gender language has gender agreement. The "ending → distinct preceding marker"
    # signal alone can't tell true gender (spa el/la) from phrase case-markers (tgl ang/ng) or isolating
    # noise (vie) — so require the gender_or_noun_class switch to read "gender" (consistent with the
    # progressive design: a switch gates a paradigm).
    try:
        from review.deferrals.profile_detect import _cycle_affixes, _freqs, detect_gender_noun_class
        if detect_gender_noun_class(_freqs(pair), _cycle_affixes(pair)).value != "gender":
            return False, 0.6, "gender_or_noun_class switch is not 'gender' — no gender agreement to find", {}
    except Exception:
        pass
    try:
        h = gender_number_hypotheses(pair, sample=sample)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"gender-number detector could not run ({type(e).__name__}: {e})", {}
    # Gender = distinct endings select DISTINCT dominant determiners. Absolute shares are inherently low
    # (a noun takes many preceding words), so the signature is the CONTRAST (el vs la), not a high share —
    # require only a modest preference (>=0.15) so the dominant determiner is real, not a tie.
    classes = [g for g in h["gender_classes"] if g["det_share"] >= 0.15 and g["n"] >= 12]
    distinct_dets = {g["determiner"] for g in classes[:3]}
    detected = len(classes) >= 2 and len(distinct_dets) >= 2
    if detected:
        ex = ", ".join(f"-{g['ending']}→{g['determiner']}({g['det_share']})" for g in classes[:3])
        return True, round(min(0.85, 0.5 + 0.1 * len(classes)), 2), \
            f"{len(distinct_dets)} ending-classes take distinct determiners ({ex})", h
    return False, 0.45, f"{len(classes)} ending-classes, {len(distinct_dets)} distinct determiners — no gender agreement", h
