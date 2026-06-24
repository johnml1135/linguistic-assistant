"""Class-system lifecycle — suggest → define → utilize (docs/workflow.md §2).

The noun/verb class system is the COMPILE ROOT: the machine SUGGESTS a candidate system (with evidence +
the subjective cut-points laid out), the HUMAN DEFINES it (declares it into the language profile), then the
machine UTILIZES it — assigns words to the DECLARED classes and FLAGS misfits (exceptions / amendment
proposals). It never re-clusters a committed system.

Foundational commits stay human; leaf decisions (a noun's assignment, an exception) auto-push when
VERIFIED-confident, stamped "good enough — AI generated" and reversible (`route`).

Strategy-dispatched: Spanish gender (gender-by-article) is implemented; Bantu noun-class co-clustering
slots in behind the same propose→declare→assign interface. Pure functions (build/flag/assign/route) are
unit-tested; the corpus scan is the only slow/gated part.

CLI:  uv run python -m review.classes --pair spa suggest | declare [--accept] | utilize | status
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

MASC_ARTICLES = {"el", "los", "un", "unos"}
FEM_ARTICLES = {"la", "las", "una", "unas"}
FOUNDATIONAL_KINDS = {"class_system", "class_boundary", "class_rename"}   # never auto-commit


# ── confidence tier ─────────────────────────────────────────────────────────────────────────────────────
def route(kind: str, verified_confidence: float, *, bar: float = 0.9) -> dict:
    """Where a decision goes. Foundational (the compile root) → always human review. Leaf + VERIFIED-confident
    → auto-push, stamped + reversible. Else → review. `verified_confidence` must be a verification signal
    (round-trip / corroboration), not a self-reported one."""
    if kind in FOUNDATIONAL_KINDS:
        return {"lane": "review", "reason": "foundational — everything compiles from it; human ratifies"}
    if verified_confidence >= bar:
        return {"lane": "auto", "stamp": "good enough — AI generated", "reversible": True,
                "confidence": round(verified_confidence, 3)}
    return {"lane": "review", "reason": f"confidence {verified_confidence:.2f} < bar {bar}"}


# ── SUGGEST (pure builder + corpus scan) ────────────────────────────────────────────────────────────────
def _ending_gender(noun: str) -> str | None:
    """Spanish noun-ending heuristic (a SECONDARY signal, used mainly to flag article/ending conflicts)."""
    if noun.endswith("o"):
        return "m"
    if noun.endswith(("a", "ión", "dad", "tad", "umbre")):
        return "f"
    return None


def build_gender_classes(votes: dict[str, Counter]) -> dict:
    """Pure: turn {noun -> Counter({'M','F'})} into a proposed 2-gender schema + evidence + the subjective
    cut laid out as alternatives. `votes` come from article→noun agreement (the target agreeing with the
    controller — Corbett), which is the real class signal."""
    masc = [n for n, c in votes.items() if c["M"] >= c["F"] and c["M"] > 0]
    fem = [n for n, c in votes.items() if c["F"] > c["M"]]

    def cls(cid, name, examples, concord):
        return {"id": cid, "name": name, "semantics": "grammatical gender", "concord": concord,
                "criteria": {"signal": "definite/indefinite article agreement"},
                "evidence": {"n_nouns": len(examples), "examples": sorted(examples, key=lambda n: -votes[n].total())[:8]},
                "provenance": "propose.gender-by-article", "confidence": 0.9}

    classes = [
        cls("m", "masculine", masc,
            {"def_art_sg": "el", "def_art_pl": "los", "indef_art_sg": "un", "adjective_suffix": "o"}),
        cls("f", "feminine", fem,
            {"def_art_sg": "la", "def_art_pl": "las", "indef_art_sg": "una", "adjective_suffix": "a"}),
    ]
    return {
        "strategy": "gender-by-article", "status": "proposed", "version": 0,
        "classes": classes,
        "alternatives": [
            {"option": "gender only (2 classes)", "note": "number handled as a separate cross-cutting feature (recommended)"},
            {"option": "gender × number (4 classes)", "note": "if singular/plural concord differs enough to be its own break"},
        ],
        "provenance": {"source": "review.classes.propose", "controllers": len(votes)},
    }


def _article_noun_votes(pair: str, *, sample: int = 0) -> dict[str, Counter]:
    """Corpus scan (slow): article→following-noun gender votes — the article agrees with the noun's gender."""
    from align.morph_align_hc import _verses
    votes: dict[str, Counter] = {}
    for _ref, _src, tgt in _verses(pair, sample):
        toks = [w for w in tgt if w.isalpha()]
        for i, w in enumerate(toks[:-1]):
            g = "M" if w in MASC_ARTICLES else "F" if w in FEM_ARTICLES else None
            if g:
                nxt = toks[i + 1]
                if nxt not in MASC_ARTICLES and nxt not in FEM_ARTICLES and len(nxt) > 2:
                    votes.setdefault(nxt, Counter())[g] += 1
    return votes


def _noun_pos(pair: str) -> set:
    """The gold's common-noun lexicon — the member filter that drops verbs/function words (e.g. the spa
    *alimenta*=verb noise) and makes the exception list real."""
    try:
        from gold.goldio import load_gold
        return {w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "noun"}
    except Exception:
        return set()


# ── strategy dispatch (which kind of class system this language has) ─────────────────────────────────────
def _strategy(pair: str) -> str | None:
    from review.deferrals import profile as P
    fs = P.load(pair).feature_space
    if getattr(fs.get("gender"), "value", False):
        return "gender-by-article"          # spa: articles agree with gender
    if getattr(fs.get("noun_class"), "value", False):
        return "bantu-prefix"               # swh: noun-class prefixes
    return None                             # ind/tgl: no gender/noun-class system


# Standard Bantu (Meinhof) class prefixes → a SUGGESTED numbering/name. m/mw is shared by classes 1 & 3 —
# the genuinely subjective split (persons vs things), surfaced as an alternative for the human to ratify.
BANTU_CLASSES = [
    ("1/3", "m-/mw- (cl1 persons · cl3 things, sg)", ["mw", "m"]),
    ("2", "wa- (cl2 persons, pl)", ["wa"]),
    ("4", "mi- (cl4 things, pl)", ["mi"]),
    ("5", "ji-/Ø (cl5)", ["ji"]),
    ("6", "ma- (cl6, pl)", ["ma"]),
    ("7", "ki-/ch- (cl7, sg)", ["ki", "ch"]),
    ("8", "vi-/vy- (cl8, pl)", ["vi", "vy"]),
    ("9/10", "n- (cl9/10 animals)", ["n"]),
    ("11/14", "u- (cl11/14 abstracts)", ["u"]),
    ("15", "ku- (cl15 infinitives)", ["ku"]),
    ("16-18", "pa-/ku-/mu- (locatives)", ["pa"]),
]
_BANTU_PREFIXES = sorted({p for _, _, ps in BANTU_CLASSES for p in ps}, key=len, reverse=True)


def _bantu_prefix_clusters(pair: str) -> dict[str, list]:
    """Cluster the gold's nouns by their longest-matching Bantu class prefix."""
    nouns = _noun_pos(pair)
    clusters: dict[str, list] = {}
    for n in nouns:
        for p in _BANTU_PREFIXES:
            if n.startswith(p) and len(n) > len(p) + 1:
                clusters.setdefault(p, []).append(n)
                break
    return clusters


def build_bantu_classes(clusters: dict[str, list]) -> dict:
    """Pure: turn noun-prefix clusters into a proposed Bantu class inventory + the subjective cuts. Concord
    (how each class marks adjectives/verbs) is left empty — it needs agreement detection (the next phase)."""
    classes = []
    for cid, name, prefixes in BANTU_CLASSES:
        members = [n for p in prefixes for n in clusters.get(p, [])]
        if not members:
            continue
        classes.append({"id": cid, "name": name, "semantics": "noun class", "prefixes": prefixes,
                        "concord": {}, "criteria": {"signal": "noun class prefix"},
                        "evidence": {"n_nouns": len(members), "examples": sorted(members)[:8]},
                        "provenance": "propose.bantu-prefix", "confidence": 0.7})
    return {
        "strategy": "bantu-prefix", "status": "proposed", "version": 0, "classes": classes,
        "alternatives": [
            {"option": "split cl1 (persons) vs cl3 (things) — both m-/mw-", "note": "needs agreement: they take different verb concord (a- vs u-). The key subjective cut."},
            {"option": "merge or split 9/10 (n-)", "note": "sg/pl often syncretic; decide if they're one class or two."},
            {"option": "treat locatives 16/17/18 as classes or as a separate system", "note": "your call."},
        ],
        "provenance": {"source": "review.classes.propose", "concord": "deferred — needs agreement detection"},
    }


def propose(pair: str, *, sample: int = 0) -> dict:
    """SUGGEST: a candidate class system, dispatched by the language's typology."""
    strat = _strategy(pair)
    if strat == "gender-by-article":
        nouns = _noun_pos(pair)
        votes = {n: c for n, c in _article_noun_votes(pair, sample=sample).items() if not nouns or n in nouns}
        schema = build_gender_classes(votes)
    elif strat == "bantu-prefix":
        schema = build_bantu_classes(_bantu_prefix_clusters(pair))
    else:
        schema = {"strategy": None, "status": "none", "version": 0, "classes": [],
                  "reason": "profile declares no gender/noun-class system — none expected for this language"}
    schema["pair"] = pair
    return schema


# ── DEFINE (the human commit-gate) ──────────────────────────────────────────────────────────────────────
def declare(pair: str, schema: dict, *, by: str = "human") -> dict:
    """DEFINE: commit a class system into the profile as the compile root. The proposal becomes authoritative
    only here. Bumps the version + records who declared it. `by='ai-accepted'` records a one-click ratify."""
    from review.deferrals import profile as P
    prof = P.load(pair)
    prev = prof.class_schema or {}
    committed = dict(schema)
    committed.update({"pair": pair, "status": "declared", "version": int(prev.get("version", 0)) + 1,
                      "declared_by": by})
    prof.class_schema = committed
    P.save(prof)
    return committed


def declared_schema(pair: str) -> dict | None:
    from review.deferrals import profile as P
    s = P.load(pair).class_schema
    return s if s and s.get("status") == "declared" else None


def persisted_noun_classes(pair: str) -> dict:
    """The combined noun→class assignment written by `write_noun_classes` (prefix + agreement + projection),
    if present — so the frontier/lifecycle uses the golden-set byproduct without re-running projection."""
    import json
    from gold.goldio import FROZEN
    p = FROZEN / pair / "noun_classes.jsonl"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["noun"]] = d
    return out


# ── UTILIZE (fit-and-flag against the declared schema) ──────────────────────────────────────────────────
def assign_from_votes(votes: dict[str, Counter], schema: dict) -> dict:
    """Pure: assign each noun to a declared class by its dominant article, with a verified confidence
    (vote agreement × support). Does NOT re-cluster — the classes are fixed by `schema`."""
    ids = {c["id"] for c in schema.get("classes", [])}
    assigned = {}
    for noun, c in votes.items():
        total = c.total()
        if not total:
            continue
        gid = "m" if c["M"] >= c["F"] else "f"
        if gid not in ids:
            continue
        agree = max(c["M"], c["F"]) / total
        support = min(1.0, total / 5)                 # ≥5 article tokens → full support
        assigned[noun] = {"class": gid, "confidence": round(agree * support, 3), "support": total}
    return assigned


def flag_exceptions(votes: dict[str, Counter], assigned: dict) -> list[dict]:
    """Pure: a noun whose ARTICLE-gender conflicts with its ENDING-gender is a misfit (the *el agua* class —
    feminine noun taking the masculine article). Raised as an exception, never an auto re-class."""
    out = []
    for noun, a in assigned.items():
        eg = _ending_gender(noun)
        if eg and eg != a["class"]:
            out.append({"noun": noun, "assigned_by_article": a["class"], "ending_suggests": eg,
                        "count": a["support"],
                        "reason": f"takes {a['class']}-gender article but ends like {eg} — exception "
                                  f"(e.g. 'el agua': feminine noun, masculine article before stressed a-)"})
    return out


def assign(pair: str, *, sample: int = 0) -> dict:
    """UTILIZE: requires a DECLARED schema. Assign nouns to the declared classes, flag misfits, surface
    coverage-gap candidates (the long tail — article/prefix-takers not yet in the gold), and route each
    assignment through the confidence tier."""
    schema = declared_schema(pair)
    if not schema:
        return {"error": "no declared class schema — run suggest then declare first", "pair": pair}
    nouns = _noun_pos(pair)
    bar = _auto_bar(pair)
    if schema.get("strategy") == "gender-by-article":
        raw = _article_noun_votes(pair, sample=sample)
        votes = {n: c for n, c in raw.items() if not nouns or n in nouns}     # member filter
        assigned = assign_from_votes(votes, schema)
        exceptions = flag_exceptions(votes, assigned)
        gaps = sorted([n for n, c in raw.items() if nouns and n not in nouns and c.total() >= 3 and len(n) > 3],
                      key=lambda n: -raw[n].total())[:30]                     # article-takers absent from gold
        routed = Counter(route("class_assignment", a["confidence"], bar=bar)["lane"] for a in assigned.values())
        from review.exceptions import carve              # layer the exceptions: rule → classes → individuals
        layered = carve([e["noun"] for e in exceptions])
        return {"pair": pair, "schema_version": schema.get("version"), "strategy": "gender-by-article",
                "n_assigned": len(assigned), "auto_pushed": routed["auto"], "to_review": routed["review"],
                "exceptions": exceptions, "n_exceptions": len(exceptions), "exception_layers": layered,
                "by_class": dict(Counter(a["class"] for a in assigned.values())),
                "coverage_gap_candidates": gaps, "n_coverage_gaps": len(gaps)}
    if schema.get("strategy") == "bantu-prefix":
        clusters = _bantu_prefix_clusters(pair)
        pref_to_class = {p: c["id"] for c in schema["classes"] for p in c.get("prefixes", [])}
        by_class = Counter()
        for p, members in clusters.items():
            if p in pref_to_class:
                by_class[pref_to_class[p]] += len(members)
        unassigned = [n for n in nouns if not any(n.startswith(p) and len(n) > len(p) + 1 for p in _BANTU_PREFIXES)]
        return {"pair": pair, "schema_version": schema.get("version"), "strategy": "bantu-prefix",
                "n_assigned": sum(by_class.values()), "by_class": dict(by_class),
                "n_unassigned_nouns": len(unassigned), "unassigned_examples": sorted(unassigned)[:20],
                "note": "concord (adjective/verb agreement per class) not yet populated — needs the agreement phase",
                "exceptions": [], "n_exceptions": 0}
    return {"error": f"no utilize path for strategy {schema.get('strategy')!r}", "pair": pair}


def combined_classification(pair: str, *, with_projection: bool = True, sample: int = 0) -> dict:
    """The authoritative per-noun class assignment, merging all signals by reliability:
       subject-marking (projection — splits m- into cl1/cl3) > associative concord > unambiguous prefix.
    Returns {noun: {class, source, confidence}}. The golden-set byproduct (persist with `write_noun_classes`)."""
    from gold.goldio import load_gold
    nouns = {w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "noun"}
    UNAMBIG = {"wa": "2", "mi": "4", "ji": "5", "ki": "7", "ch": "7", "vi": "8", "vy": "8", "ma": "6"}

    def npfx(n: str) -> str:
        for p in _BANTU_PREFIXES:
            if n.startswith(p) and len(n) > len(p) + 1:
                return p
        return "Ø"

    out: dict[str, dict] = {}
    for n in nouns:                                  # weakest signal first; stronger ones overwrite
        p = npfx(n)
        if p in UNAMBIG:
            out[n] = {"class": UNAMBIG[p], "source": "prefix", "confidence": 0.7}
    try:                                             # associative concord (zero-prefix → cl9/10, cl5…)
        from review.agreement import associative_votes, classify_zero_prefix
        _by, zero = associative_votes(pair, sample=sample)
        for n, d in classify_zero_prefix(zero).items():
            if n in nouns:
                out[n] = {"class": d["class"], "source": "associative", "confidence": d["confidence"]}
    except Exception:
        pass
    if with_projection:                              # subject marking (splits m- cl1/cl3) — strongest
        try:
            from review.project import classify_by_subject_marking
            for n, d in classify_by_subject_marking(pair, sample=sample).items():
                if n in nouns:
                    out[n] = {"class": d["class"], "source": "subject-marking", "confidence": d["confidence"]}
        except Exception:
            pass
    return out


def write_noun_classes(pair: str, assignments: dict) -> str:
    """Persist the combined noun→class assignment to the gold (the byproduct)."""
    import json
    from gold.goldio import FROZEN
    p = FROZEN / pair / "noun_classes.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for noun, d in sorted(assignments.items()):
            f.write(json.dumps({"noun": noun, **d}, ensure_ascii=False) + "\n")
    return str(p)


def _auto_bar(pair: str) -> float:
    try:
        from review.deferrals import profile as P
        return min(0.95, P.load(pair).auto_accept_bar())   # cap so leaf assignments can actually auto-push
    except Exception:
        return 0.9


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Class-system lifecycle (suggest → declare → utilize).")
    ap.add_argument("--pair", required=True)
    ap.add_argument("cmd", choices=["suggest", "declare", "utilize", "status"])
    ap.add_argument("--accept", action="store_true", help="declare: one-click ratify the AI proposal (by=ai-accepted)")
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if a.cmd == "suggest":
        s = propose(a.pair, sample=a.sample)
        if s.get("status") == "none":
            print(f"\n{a.pair}: no gender/noun-class system to propose — {s['reason']}."); return 0
        print(f"\nPROPOSED class system for {a.pair} (strategy: {s['strategy']}) — NOT yet committed:")
        for c in s["classes"]:
            mark = f"concord={c['concord']}" if c.get("concord") else f"prefixes={c.get('prefixes')}"
            print(f"  [{c['id']}] {c['name']}: {c['evidence']['n_nouns']} nouns, {mark}")
            print(f"       e.g. {c['evidence']['examples']}")
        print("  alternatives (your call):")
        for alt in s["alternatives"]:
            print(f"    - {alt['option']}: {alt['note']}")
        print("\n  → review, then: python -m review.classes --pair %s declare [--accept]" % a.pair)
    elif a.cmd == "declare":
        s = propose(a.pair, sample=a.sample)
        if s.get("status") == "none":
            print(f"{a.pair}: nothing to declare — {s['reason']}."); return 0
        committed = declare(a.pair, s, by="ai-accepted" if a.accept else "human")
        print(f"DECLARED class schema v{committed['version']} for {a.pair} (by {committed['declared_by']}) — "
              f"now the compile root.")
    elif a.cmd == "utilize":
        r = assign(a.pair, sample=a.sample)
        if r.get("error"):
            print(r["error"]); return 1
        print(f"\nUTILIZE {a.pair} (schema v{r['schema_version']}, {r['strategy']}): "
              f"{r['n_assigned']} nouns assigned {r['by_class']}")
        if r["strategy"] == "gender-by-article":
            print(f"  auto-pushed (verified-confident): {r['auto_pushed']} · to review: {r['to_review']}")
            print(f"  exceptions flagged: {r['n_exceptions']} · coverage-gap candidates (long tail): {r['n_coverage_gaps']}")
            for e in r["exceptions"][:10]:
                print(f"    ⚑ {e['noun']} — {e['reason']}")
            if r["coverage_gap_candidates"]:
                print(f"    long tail (article-takers not in gold): {r['coverage_gap_candidates'][:12]}")
        else:
            print(f"  unassigned nouns (no clear prefix — the tail): {r['n_unassigned_nouns']} "
                  f"e.g. {r['unassigned_examples'][:10]}")
            print(f"  note: {r['note']}")
    elif a.cmd == "status":
        s = declared_schema(a.pair)
        print(f"{a.pair}: " + (f"declared schema v{s['version']} ({len(s['classes'])} classes, by {s.get('declared_by')})"
                               if s else "no declared class schema yet"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
