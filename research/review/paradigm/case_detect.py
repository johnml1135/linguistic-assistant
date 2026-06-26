"""Turkish-style CASE detector — the suffixal mirror of the Bantu noun-class/concord explorer.

Case leaves a signature the prefix-concord machinery can't see: a set of word-FINAL suffixes that (a)
recur across many stems and (b) co-vary with the noun's grammatical ROLE (subject/object/oblique),
with the allomorphs of one case collapsed by vowel harmony. We recover that signature from data:

  * ROLE  — `review.project.project_verse` projects the English-pivot dep-role onto each vernacular noun
    via THOT alignment (nsubj/obj/obl/nmod/...).
  * SUFFIX — `induce.morph_align.segment_word` over the induced model gives each noun's final suffix.
  * HARMONY — `induce.tdd.harmony_families` collapses vowel-harmony allomorphs (-da/-de) into one cell.

A suffix family is a CASE candidate when it recurs across >= min_stems and concentrates on one role
(role purity). Emits the same A/B/C + doesnt_fit shape as `agreement_hypotheses` so the packet/report
machinery is uniform.

HONEST LIMITATION: the English pivot does not distinguish dative/locative/ablative (all project to
obl/nmod), so role-covariation under-separates the oblique cases. The detector surfaces the suffix
FAMILIES with their dominant projected role; mapping families to named cases is left to the report /
reviewer. This under-separation is exactly the gap the report-vs-golden metric is meant to expose.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


def _harmony_families(forms: list[str]) -> dict[str, list[str]]:
    """{consonant-skeleton: [allomorphs]} — collapses vowel-harmony variants. Falls back to a local
    vowel-strip if induce.tdd.harmony_families is unavailable."""
    try:
        from induce.tdd import harmony_families
        fams = harmony_families(forms)
        if fams:
            return fams
    except Exception:
        pass
    VOW = set("aeıioöuüâîû")
    out: dict[str, list[str]] = defaultdict(list)
    for f in forms:
        skel = "".join(c for c in f if c not in VOW)
        out[skel].append(f)
    return out


def case_votes(pair: str, *, sample: int = 300):
    """Scan a sample of verses → (suffix→Counter(role)), (suffix→set(stem)), bare-subject count, model."""
    from induce.morph_align import load_model, segment_word
    from review.project import _word_alignment, project_verse, get_parser

    m = load_model(pair)
    roots = sorted({e.form for e in m.lexicon}, key=len, reverse=True)
    suff = sorted({a.form for a in m.affixes if a.kind == "suffix"}, key=len, reverse=True)
    verses, table = _word_alignment(pair, sample=sample)
    par = get_parser("en")

    suf_role: dict[str, Counter] = defaultdict(Counter)
    suf_stems: dict[str, set] = defaultdict(set)
    nsubj_bare = 0
    bare_stems: set[str] = set()
    for _ref, src, tgt in verses:
        proj = project_verse(par(" ".join(src)), src, tgt, table)
        for p in proj:
            if p.get("pos") != "NOUN":
                continue
            segs = segment_word(p["vern"], roots, suff, [], [])
            sfx = [s for s, r in segs if r == "suffix"]
            stem = "".join(s for s, r in segs if r == "root") or p["vern"]
            role = p.get("role", "") or "?"
            if sfx:
                suf_role[sfx[-1]][role] += 1
                suf_stems[sfx[-1]].add(stem)
            elif role == "nsubj":
                nsubj_bare += 1
                bare_stems.add(p["vern"])
    return suf_role, suf_stems, nsubj_bare, bare_stems, m


def case_hypotheses(pair: str, *, sample: int = 300, min_stems: int = 4, purity: float = 0.4,
                    top: int = 8) -> dict:
    """Rank role-covarying suffix families as candidate CASES (A/B/C by role purity × recurrence), with
    the residue (families that fit no clear role). Mirrors `agreement_hypotheses`."""
    suf_role, suf_stems, nsubj_bare, bare_stems, _m = case_votes(pair, sample=sample)
    fams = _harmony_families([s for s in suf_role if s])
    rows = []
    residue = []
    for skel, allos in fams.items():
        roles: Counter = Counter()
        stems: set = set()
        for a in allos:
            roles += suf_role[a]
            stems |= suf_stems[a]
        total = sum(roles.values())
        if len(stems) < min_stems or total < min_stems:
            continue
        ranked = roles.most_common()
        dom_role, dom_n = ranked[0]
        share = round(dom_n / total, 3)
        cands = [{"rank": i + 1, "role": r, "support": n, "share": round(n / total, 3)}
                 for i, (r, n) in enumerate(ranked[:3])]
        row = {"markers": sorted(allos), "skeleton": skel, "n_stems": len(stems), "total": total,
               "dominant_role": dom_role, "dominant_share": share, "candidates": cands,
               "doesnt_fit": {"n": total - dom_n, "share": round((total - dom_n) / total, 3),
                              "roles": [r for r, _ in ranked[1:][:4]]}}
        (rows if share >= purity else residue).append(row)
    rows.sort(key=lambda r: -(r["dominant_share"] * r["n_stems"]))
    # nominative cell: bare nouns in subject role (zero-marked nominative)
    nom = None
    if nsubj_bare >= min_stems:
        nom = {"markers": ["Ø"], "skeleton": "", "n_stems": len(bare_stems), "total": nsubj_bare,
               "dominant_role": "nsubj", "dominant_share": 1.0,
               "candidates": [{"rank": 1, "role": "nsubj", "support": nsubj_bare, "share": 1.0}],
               "doesnt_fit": {"n": 0, "share": 0.0, "roles": []}}
    out_rows = ([nom] if nom else []) + rows[:top]
    return {"pair": pair, "question": "case: role-covarying noun suffix families",
            "rows": out_rows, "n_case_families": len(rows),
            "fit_none": {"n": len(residue), "examples": [r["markers"] for r in residue[:10]]}}


def is_suffixing(pair: str, *, min_suffixes: int = 3) -> bool:
    """Cheap pre-check (no corpus scan): is this a SUFFIXING language with enough noun suffixes for a
    suffixal case system to be possible? Case is realised by suffixes, so a prefix-dominant language
    (swh) or one with too few suffixes cannot have it — skip the expensive role scan and say absent."""
    try:
        from induce.morph_align import load_model
        aff = load_model(pair).affixes
        nsuf = len({a.form for a in aff if a.kind == "suffix"})
        npre = len({a.form for a in aff if a.kind == "prefix"})
        return nsuf >= min_suffixes and nsuf >= npre        # suffixing (or balanced), not prefix-dominant
    except Exception:
        return False


@lru_cache(maxsize=32)
def detect_case_real(pair: str, *, sample: int = 200) -> tuple[str, float, str, dict]:
    """Corpus verdict for the `case` switch. 'present' when >= 2 suffix families recur across stems AND
    concentrate on a role (role purity) — that is the case signature. Returns (value, conf, evidence, hyps).
    Cached per (pair, sample) so the always-run switch path scans each language at most once per process.

    Case is asserted only on a data signature stringent enough to reject generic suffixation
    (plural/derivation also covary with role). Two principled guards + a count threshold:
      * SUFFIXING — case is suffixal, so prefix-dominant (swh) / suffix-poor langs are out.
      * NOT ISOLATING — an isolating language (vie) has no inflectional case by definition (a
        layer-0 synthesis switch gating a layer-1 paradigm — the progressive design).
      * >= 2 HIGH-PURITY families (purity >= 0.5, >= 4 stems). One family (spa -s) is just a plural.
    (Role-DIVERSITY is NOT required: the English pivot lumps dative/locative/ablative as one 'obl' role,
     so real case langs show few distinct roles — using diversity would reject tur/rus. Honest limitation.)"""
    if not is_suffixing(pair):
        return "absent", 0.55, "prefixing or suffix-poor language — no suffixal case possible (pre-check)", {}
    try:
        from review.deferrals.profile_detect import _cycle_affixes, _freqs, detect_synthesis
        if detect_synthesis(_freqs(pair), _cycle_affixes(pair)).value == "isolating":
            return "absent", 0.6, "isolating language — no inflectional case (synthesis switch gates case)", {}
    except Exception:
        pass
    try:
        hyps = case_hypotheses(pair, sample=sample, purity=0.5, min_stems=4)
    except Exception as e:  # projection/parser unavailable → fall back to absent (no claim)
        return "absent", 0.3, f"case detector could not run ({type(e).__name__}: {e})", {}
    case_rows = [r for r in hyps["rows"] if r["markers"] != ["Ø"] and r["dominant_share"] >= 0.5]
    roles = {r["dominant_role"] for r in case_rows}
    n = len(case_rows)
    if n >= 2:
        ex = ", ".join("/".join(r["markers"][:2]) + f"→{r['dominant_role']}" for r in case_rows[:4])
        return ("present", round(min(0.85, 0.45 + 0.07 * n + 0.03 * len(roles)), 2),
                f"{n} high-purity role-covarying suffix families ({len(roles)} roles; e.g. {ex})", hyps)
    return ("absent", 0.45, f"only {n} high-purity suffix family — not a case system", hyps)
