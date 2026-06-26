"""Analytic ("np-case") marker detector — case/role marked by a SEPARATE adjacent function word, not a
suffix. Tagalog marks the noun phrase with a preceding particle (ang trigger, ng genitive, sa oblique);
Hindi marks it with a following postposition (ne, ko, se, mein). The signature: an adjacent short function
word whose presence CO-VARIES with the noun's projected dep-role (ang→nsubj, ng→nmod, sa→obl).

This is the 5th detector family. It is distinct from the gender-determiner detector by REQUIRING role
covariation: Spanish el/la precede nouns of every role (flat role distribution → not case), whereas
Tagalog ang is role-specific. Auto-picks the side (preceding vs following) with the stronger signal.
Cached for reproducibility.
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


def _cache_path(pair: str, sample: int) -> Path:
    return CACHE_DIR / f"npmark_votes_{pair}_{sample}.json"


def adjacent_marker_votes(pair: str, *, sample: int = 300, max_len: int = 4, refresh: bool = False):
    """For each noun, the adjacent (prev AND next) short function word → Counter(role). Cached.
    Returns {'prev': {marker: Counter(role)}, 'next': {...}}, n_noun."""
    cpath = _cache_path(pair, sample)
    if cpath.exists() and not refresh:
        d = json.loads(cpath.read_text(encoding="utf-8"))
        return ({s: {m: Counter(r) for m, r in d[s].items()} for s in ("prev", "next")}, d["n_noun"])

    from review.project import _word_alignment, project_verse, get_parser
    verses, table = _word_alignment(pair, sample=sample)
    par = get_parser("en")
    sides = {"prev": defaultdict(Counter), "next": defaultdict(Counter)}
    n_noun = 0
    for _ref, src, tgt in verses:
        proj = project_verse(par(" ".join(src)), src, tgt, table)
        for i, p in enumerate(proj):
            if p.get("pos") != "NOUN":
                continue
            n_noun += 1
            role = p.get("role", "") or "?"
            for side, j in (("prev", i - 1), ("next", i + 1)):
                if 0 <= j < len(proj):
                    adj = (proj[j].get("vern") or "").lower()
                    if adj and len(adj) <= max_len and proj[j].get("pos") not in ("NOUN", "PROPN"):
                        sides[side][adj][role] += 1
    CACHE_DIR.mkdir(exist_ok=True)
    cpath.write_text(json.dumps({"prev": {m: dict(r) for m, r in sides["prev"].items()},
                                 "next": {m: dict(r) for m, r in sides["next"].items()},
                                 "n_noun": n_noun}, ensure_ascii=False), encoding="utf-8")
    return sides, n_noun


def _rows_for_side(side_votes: dict, *, min_n: int, purity: float, top: int) -> list[dict]:
    rows = []
    for m, roles in side_votes.items():
        total = roles.total()
        if total < min_n:
            continue
        ranked = roles.most_common()
        dom_role, dom_n = ranked[0]
        share = round(dom_n / total, 3)
        if share < purity:
            continue
        rows.append({"markers": [m], "marker": m, "dominant_role": dom_role, "share": share, "n": total,
                     "candidates": [{"role": r, "n": n, "share": round(n / total, 3)} for r, n in ranked[:3]]})
    rows.sort(key=lambda r: -(r["share"] * r["n"]))
    return rows[:top]


def npcase_hypotheses(pair: str, *, sample: int = 300, min_n: int = 8, purity: float = 0.4, top: int = 6) -> dict:
    """Best side's role-covarying adjacent markers as the A/B/C np-case cells."""
    sides, n_noun = adjacent_marker_votes(pair, sample=sample)
    prev_rows = _rows_for_side(sides["prev"], min_n=min_n, purity=purity, top=top)
    next_rows = _rows_for_side(sides["next"], min_n=min_n, purity=purity, top=top)
    # pick the side with more distinct dominant roles (the real case system marks several roles distinctly)
    prev_d = len({r["dominant_role"] for r in prev_rows})
    next_d = len({r["dominant_role"] for r in next_rows})
    side, rows = ("prev", prev_rows) if prev_d >= next_d else ("next", next_rows)
    return {"pair": pair, "question": "analytic case: adjacent particle co-varying with role",
            "side": side, "rows": rows, "n_markers": len(rows), "n_nouns": n_noun}


@lru_cache(maxsize=16)
def detect_np_case(pair: str, *, sample: int = 200) -> tuple[bool, float, str, dict]:
    """Present when >= 2 adjacent markers concentrate on DISTINCT roles (an analytic case/marker system).
    Gated to languages WITHOUT suffixal case (analytic vs synthetic are alternatives)."""
    try:
        from review.paradigm.case_detect import detect_case_real
        if detect_case_real(pair)[0] == "present":
            return False, 0.6, "suffixal case already present — analytic markers are the alternative", {}
    except Exception:
        pass
    try:
        h = npcase_hypotheses(pair, sample=sample)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"np-case detector could not run ({type(e).__name__}: {e})", {}
    rows = h["rows"]
    roles = {r["dominant_role"] for r in rows}
    # a true case SYSTEM marks a CORE argument (subject/object) with its own particle (tgl ang→nsubj),
    # not just genitive/oblique adpositions (spa de→nmod, swh associative wa→nmod) which most langs have.
    core = [r for r in rows if r["dominant_role"] in ("nsubj", "obj", "nsubj:pass")]
    if len(rows) >= 2 and len(roles) >= 2 and core:
        ex = ", ".join(f"{r['marker']}→{r['dominant_role']}({r['share']})" for r in rows[:4])
        return True, round(min(0.85, 0.5 + 0.08 * len(rows)), 2), \
            f"{len(rows)} adjacent markers over {len(roles)} roles incl. core ({h['side']}-side): {ex}", h
    return False, 0.45, f"{len(rows)} markers / {len(roles)} roles, {len(core)} core — no analytic case system", h
