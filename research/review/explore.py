"""Explore + ranked-hypothesis tools for HIGHER-LEVEL questions (noun classes, typological switches) — the
A/B/C + things-that-don't-fit treatment generalised above the rule level, plus browse-everything tools so a
reviewer (Gemma/Opus/human) can ask "is there ANOTHER pattern here?" the system didn't hypothesise.

Three things:
1. browse — `noun_entries(pair, regex)` lists EVERY noun with its class signals (prefix, assigned class,
   source, confidence, freq); `switch_entries(pair)` lists every typological switch's evidence. The reviewer
   scans the raw entries to spot a pattern the ranked hypotheses missed.
2. ranked hypotheses + residue — `class_hypotheses(pair)` ranks the candidate noun-class groupings (A/B/C…)
   by how many nouns each explains, with the residue (nouns fitting NONE); `switch_hypotheses(pair)` ranks
   each switch's candidate values (detected first, then the other typological contours) with the evidence
   and what disagrees.
3. residue pattern-finder — `residue_patterns(pair)` clusters the UNEXPLAINED nouns by recurring
   initial/final substrings → candidate new patterns + the words that fit none, the "another pattern?" probe.

All offline (gold POS + freqs + persisted classes + emergent groups + switch detection); no parser needed.

CLI: python -m review.explore --pair swh --nouns [REGEX] | --classes | --residue | --switches
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


def _nouns(pair: str) -> set:
    from gold.goldio import load_gold
    from review.project import load_pos
    pos = load_gold(pair).get("pos", {}) or load_pos(pair)
    return {w for w, p in pos.items() if str(p).lower() == "noun"}


def _freqs(pair: str) -> Counter:
    try:
        from induce.tdd import load_freqs
        return load_freqs(pair)
    except Exception:
        return Counter()


def _prefix_of(pair: str):
    from review import langknow
    prefs = langknow.class_prefix_set(pair)

    def pfx(n: str) -> str:
        for p in prefs:
            if n.startswith(p) and len(n) > len(p) + 1:
                return p
        return ""
    return pfx


# ── 1. BROWSE: every noun + its class signals ───────────────────────────────────────────────────────────
def noun_entries(pair: str, pattern: str = "", *, limit: int = 80) -> dict:
    """Every noun (optionally filtered by regex) with prefix / assigned class / source / confidence / freq —
    so the reviewer can read the raw entries and look for a pattern the hypotheses didn't surface."""
    from review.classes import persisted_noun_classes
    nouns, freqs, cls, pfx = _nouns(pair), _freqs(pair), persisted_noun_classes(pair), _prefix_of(pair)
    rx = re.compile(pattern) if pattern else None
    rows = []
    for n in sorted(nouns, key=lambda w: -freqs.get(w, 0)):
        if rx and not rx.search(n):
            continue
        c = cls.get(n, {})
        rows.append({"noun": n, "freq": freqs.get(n, 0), "prefix": pfx(n),
                     "class": c.get("class", ""), "source": c.get("source", ""),
                     "confidence": c.get("confidence", "")})
        if len(rows) >= limit:
            break
    n_classified = sum(1 for n in nouns if n in cls)
    return {"pair": pair, "n_nouns": len(nouns), "n_classified": n_classified,
            "n_matched": sum(1 for n in nouns if not rx or rx.search(n)), "shown": len(rows), "rows": rows}


# ── 2a. RANKED HYPOTHESES (classes): candidate class groups + residue ────────────────────────────────────
def class_hypotheses(pair: str, *, top: int = 8) -> dict:
    """Rank the candidate noun-class groupings (emergent sg/pl pairings) by how many nouns each explains —
    A (best), B, C, … — with the residue: nouns that fit NONE of them (where the next class hides)."""
    from review.recover import emergent_class_groups
    nouns, freqs = _nouns(pair), _freqs(pair)
    groups = emergent_class_groups(pair, top=top)
    explained: set = set()
    hyps = []
    for g in groups:
        prefs = g["prefixes"]
        members = [n for n in nouns if any(n.startswith(p) and len(n) > len(p) + 1 for p in prefs)]
        explained |= set(members)
        hyps.append({"label": "/".join(prefs) + "- class", "prefixes": prefs, "n_explained": len(members),
                     "examples": sorted(members, key=lambda w: -freqs.get(w, 0))[:6]})
    hyps.sort(key=lambda h: -h["n_explained"])
    for i, h in enumerate(hyps, 1):
        h["rank"] = i
    residue = sorted(nouns - explained, key=lambda w: -freqs.get(w, 0))
    return {"pair": pair, "question": "noun-class grouping", "n_nouns": len(nouns),
            "hypotheses": hyps, "fit_none": {"n": len(residue), "examples": residue[:15]}}


# ── 2b. RESIDUE pattern-finder: "is there ANOTHER pattern here?" ─────────────────────────────────────────
def residue_patterns(pair: str, *, min_cluster: int = 4, top: int = 6) -> dict:
    """Cluster the UNEXPLAINED nouns (no definite class) by recurring initial and final substrings → ranked
    candidate patterns the current class system misses, plus the words that fit none. The literal
    'is there another pattern here?' tool."""
    from review.classes import persisted_noun_classes
    nouns, freqs, cls = _nouns(pair), _freqs(pair), persisted_noun_classes(pair)
    # residue = nouns with no definite class, or only the cl9/10 default-residue bucket
    residue = [n for n in nouns if cls.get(n, {}).get("class", "") in ("", "9/10")]

    def cluster(keyfn, label):
        buckets: dict[str, list] = {}
        for n in residue:
            k = keyfn(n)
            if k:
                buckets.setdefault(k, []).append(n)
        ranked = sorted(((k, v) for k, v in buckets.items() if len(v) >= min_cluster), key=lambda kv: -len(kv[1]))
        return [{"lens": label, "pattern": k, "n": len(v),
                 "examples": sorted(v, key=lambda w: -freqs.get(w, 0))[:6]} for k, v in ranked[:top]]

    init2 = cluster(lambda n: n[:2] if len(n) > 3 else "", "initial 2 chars")
    fin2 = cluster(lambda n: n[-2:] if len(n) > 3 else "", "final 2 chars")
    patterns = sorted(init2 + fin2, key=lambda p: -p["n"])[:top]
    # morpheme test per pattern: of its nouns, how many leave an ATTESTED stem (the real-affix count)?
    for p in patterns:
        side = "suffix" if p["lens"].startswith("final") else "prefix"
        members = [n for n in residue if (n[-2:] == p["pattern"] if side == "suffix" else n[:2] == p["pattern"])]
        p["n_real"] = sum(1 for n in members if _stem_recurs(_stem_of(n, p["pattern"], side), freqs, set(nouns)))
        p["side"] = side
    covered = {n for p in patterns for n in
               ([x for x in residue if (x[:2] == p["pattern"] or x[-2:] == p["pattern"])])}
    fit_none = sorted(set(residue) - covered, key=lambda w: -freqs.get(w, 0))
    return {"pair": pair, "n_residue": len(residue), "patterns": patterns,
            "fit_none": {"n": len(fit_none), "examples": fit_none[:15]}}


# ── 3. SWITCHES: per-switch ranked candidate values + what disagrees ─────────────────────────────────────
def switch_hypotheses(pair: str) -> dict:
    """Each typological switch as ranked candidate values: A = the detected value, then the other contours;
    with the detector evidence and what DOESN'T fit (an internet/WALS seed that disagrees, or low
    confidence). The A/B/C + doesn't-fit treatment for the typological frame."""
    try:
        from review.deferrals.profile_detect import detect
        from review.deferrals.switches import BY_ID
    except Exception as e:
        return {"pair": pair, "error": f"switch detection unavailable: {e}", "switches": []}
    out = []
    for sw in detect(pair):
        cdef = BY_ID.get(sw.name)
        contours = list(cdef.contours) if cdef else []
        cands = [{"rank": 1, "value": sw.value, "detected": True, "confidence": round(sw.confidence, 2)}]
        for v in contours:
            if v != sw.value:
                cands.append({"rank": len(cands) + 1, "value": v, "detected": False})
        doesnt_fit = ""
        if sw.agrees is False:
            doesnt_fit = f"WALS/seed says {sw.internet!r} — disagrees with detected {sw.value!r}"
        elif sw.confidence < 0.5:
            doesnt_fit = f"low confidence ({sw.confidence:.2f}) — evidence thin"
        out.append({"switch": sw.name, "presentation": getattr(cdef, "presentation", ""),
                    "candidates": cands, "evidence": sw.evidence, "doesnt_fit": doesnt_fit})
    return {"pair": pair, "switches": out}


def _residue_class(d: dict) -> bool:
    return d.get("class", "") in ("", "9/10")          # unexplained: no class, or the cl9/10 default bucket


def _stem_recurs(stem: str, freqs: Counter, nounset: set, *, min_freq: int = 3) -> bool:
    """Is `stem` an attested morpheme — does it stand alone as a word/noun, or recur in the corpus? This is
    the morpheme test that separates a real affixed form (nyumba-ni: nyumba recurs) from a coincidental
    substring ending (ami-ni: 'ami' does not). Offline."""
    return len(stem) >= 2 and (stem in nounset or freqs.get(stem, 0) >= min_freq)


def _stem_of(noun: str, pattern: str, side: str) -> str:
    return noun[:-len(pattern)] if side == "suffix" else noun[len(pattern):]


def affix_function_gate(pair: str, candidate_nouns: list, *, sample: int = 400, pivot: str = "en"):
    """Parser-based gate: keep only candidate nouns whose PROJECTED English POS is nominal. A coincidental
    ending like `amini` is gold-tagged a noun but ALIGNS to an English verb ('believe') — its projected POS
    conflicts, so it's dropped where stem-recurrence (ami marginally attested) let it through. Returns
    (kept, skipped, posinfo) or None if no pivot parser is available (caller falls back to the stem gate)."""
    try:
        from review.project import get_parser, _word_alignment, project_verse
    except Exception:
        return None
    parser = get_parser(pivot)
    if parser is None:
        return None
    cand = set(candidate_nouns)
    verses, table = _word_alignment(pair, sample)
    votes: dict[str, Counter] = {}
    for _ref, src, tgt in verses:
        if not src or not tgt:
            continue
        for p in project_verse(parser(" ".join(src)), src, tgt, table):
            if p["vern"] in cand and p.get("pos"):
                votes.setdefault(p["vern"], Counter())[p["pos"]] += 1
    kept, skipped, info = [], [], {}
    for n in candidate_nouns:
        c = votes.get(n)
        top = c.most_common(1)[0][0] if c else ""
        info[n] = top
        # keep if no projection evidence (can't disconfirm) or the projected POS is nominal
        if (not c) or top in ("NOUN", "PROPN"):
            kept.append(n)
        else:
            skipped.append(n)
    return kept, skipped, info


def apply_residue_pattern(pair: str, pattern: str, *, side: str = "suffix", label: str | None = None,
                          min_residue: int = 2, gate: str = "stem", min_stem_freq: int = 3,
                          emit_delta: bool = True) -> dict:
    """CLOSE THE LOOP: the reviewer ACCEPTS a residue pattern (e.g. final -ni). Assign every residue noun
    that GENUINELY bears it to a new class `label`, persist (write_noun_classes), add the affix to the model,
    and emit a confidence-routed delta — then report the residue SHRINK.
    `gate='stem'` (default) applies the morpheme test: only assign a noun if stripping the pattern leaves an
    ATTESTED stem (stands alone / recurs) — so `nyumba-ni` is kept but coincidental endings like `amini`,
    `dalasini` are SKIPPED (no `ami`/`dalasi` stem). `gate='none'` is the old raw-substring behaviour.
    Provenance 'reviewer-explore'. Reversible (gold/model files)."""
    from review.classes import persisted_noun_classes, write_noun_classes
    nouns = _nouns(pair)
    freqs = _freqs(pair)
    cls = dict(persisted_noun_classes(pair))
    label = label or f"via-{side[:3]}:{pattern}"

    def bears(n: str) -> bool:
        ok = n.endswith(pattern) if side == "suffix" else n.startswith(pattern)
        return ok and len(n) > len(pattern) + min_residue

    residue_before = [n for n in nouns if _residue_class(cls.get(n, {}))]
    candidates = [n for n in residue_before if bears(n)]
    gate_used = gate
    if gate in ("stem", "both"):
        assigned = [n for n in candidates if _stem_recurs(_stem_of(n, pattern, side), freqs, nouns,
                                                          min_freq=min_stem_freq)]
    else:
        assigned = list(candidates)
    if gate in ("function", "both"):                   # parser gate: drop nouns that align to a non-noun
        fg = affix_function_gate(pair, assigned if gate == "both" else candidates)
        if fg is not None:
            assigned = fg[0]
        else:
            gate_used = "stem (function gate unavailable: no pivot parser)"
            if gate == "function":                     # asked for function-only but no parser → fall back to stem
                assigned = [n for n in candidates if _stem_recurs(_stem_of(n, pattern, side), freqs, nouns,
                                                                  min_freq=min_stem_freq)]
    skipped = [n for n in candidates if n not in set(assigned)]   # over-applications the gate caught
    for n in assigned:
        cls[n] = {"class": label, "source": "reviewer-explore", "confidence": 0.7, "via": f"{side}:{pattern}"}
    write_noun_classes(pair, cls)                       # persist the enriched classification (the gold byproduct)
    affix_added = _add_affix_to_model(pair, pattern, side, label)
    n_delta = _emit_pattern_delta(pair, pattern, side, label, assigned) if emit_delta else 0
    residue_after = [n for n in nouns if _residue_class(cls.get(n, {}))]
    return {"pair": pair, "pattern": pattern, "side": side, "label": label, "decision": "accept", "gate": gate_used,
            "n_candidates": len(candidates), "n_assigned": len(assigned), "examples": sorted(assigned)[:10],
            "n_skipped_by_gate": len(skipped), "skipped_examples": sorted(skipped)[:10],
            "residue_before": len(residue_before), "residue_after": len(residue_after),
            "affix_added": affix_added, "deltas": n_delta}


def _add_affix_to_model(pair: str, form: str, side: str, gloss: str) -> bool:
    """Add the accepted pattern as an affix to the induced model so the segmenter knows it next cycle."""
    try:
        from induce.tdd import _load_prior_model
        from induce.cotrain import save_model
        from engine.grammar import Affix
    except Exception:
        return False
    m = _load_prior_model(pair)
    if m is None:
        return False
    if any(a.form == form and a.kind == side for a in m.affixes):
        return False
    m.affixes.append(Affix(form=form, gloss=gloss, kind=side, count=0))
    save_model(pair, m)
    return True


def _emit_pattern_delta(pair: str, pattern: str, side: str, label: str, nouns: list[str]) -> int:
    try:
        from review.deltas.store import DeltaStore, store_path
    except Exception:
        return 0
    store = DeltaStore.load(store_path(pair))
    op = {"op": "class.assign.by_pattern", "entry": f"class:{pair}:{label}",
          "pattern": f"{side}:{pattern}", "members": sorted(nouns)[:50], "n_members": len(nouns),
          "confidence": 0.7, "provenance": {"source": "reviewer-explore", "pair": pair}}
    n = store.add([op])
    store.save()
    return n


def switch_entries(pair: str) -> dict:
    """Raw browse of every switch's detected value + confidence + evidence + internet seed (the 'look at all
    entries' view for the typological frame)."""
    r = switch_hypotheses(pair)
    return r


def apply_switch(pair: str, switch: str, value, *, lock: bool = True, emit_delta: bool = True) -> dict:
    """CLOSE THE LOOP for switches: the reviewer ACCEPTS a typological switch value → write it into the
    language profile (profile.switches[switch] + projected onto feature_space/affix/phon processes via
    write_switches), locked, provenance reviewer-accepted; and emit a delta. The one higher-level question
    that could present A/B/C but not yet apply — now it can."""
    profile_written = False
    try:
        from review.deferrals.profile import load, save, write_switches
        from review.deferrals.profile_detect import Switch
        prof = load(pair)
        sw = Switch(name=switch, value=value, confidence=1.0, evidence="reviewer-accepted")
        # confirmations maps switch-id → the CHOSEN value (its presence also locks it); not a bool flag
        prof = write_switches(prof, [sw], confirmations={switch: value} if lock else None)
        save(prof)
        profile_written = True
    except Exception as e:
        profile_written = f"error: {e}"
    n_delta = _emit_switch_delta(pair, switch, value) if emit_delta else 0
    return {"pair": pair, "switch": switch, "value": value, "locked": lock,
            "profile_written": profile_written, "deltas": n_delta}


def _emit_switch_delta(pair: str, switch: str, value) -> int:
    try:
        from review.deltas.store import DeltaStore, store_path
    except Exception:
        return 0
    store = DeltaStore.load(store_path(pair))
    op = {"op": "switch.set", "entry": f"switch:{pair}:{switch}", "switch": switch, "value": value,
          "confidence": 1.0, "provenance": {"source": "reviewer-explore", "pair": pair}}
    n = store.add([op])
    store.save()
    return n


# ── AGREEMENT / CONCORD: per-class A/B/C concord markers + the instances that don't fit ──────────────────
def agreement_hypotheses(pair: str, *, sample: int = 0, min_support: int = 8, top: int = 3) -> dict:
    """For each noun-class (by its prefix), rank the CONCORD markers its modifiers carry (the associative
    agreement it triggers) — A = the dominant marker, B/C the alternatives — with `doesnt_fit`: the
    instances that take a NON-dominant marker (concord exceptions / mis-assigned nouns). The A/B/C +
    don't-fit treatment for agreement, on the same associative-vote signal `agreement.induce` uses."""
    from review.agreement import associative_votes
    from review import langknow
    by_pfx, _zero = associative_votes(pair, sample=sample)
    pfx2class = langknow.noun_class_prefixes(pair)
    rows = []
    for pfx, counter in by_pfx.items():
        total = counter.total()
        if pfx == "Ø" or total < min_support:
            continue
        ranked = counter.most_common()
        cands = [{"rank": i + 1, "marker": m, "support": n, "share": round(n / total, 3)}
                 for i, (m, n) in enumerate(ranked[:top])]
        nonfit = sum(n for _, n in ranked[1:])
        rows.append({"noun_prefix": pfx, "class": pfx2class.get(pfx, "?"), "total": total,
                     "candidates": cands,
                     "doesnt_fit": {"n": nonfit, "share": round(nonfit / total, 3),
                                    "markers": [m for m, _ in ranked[1:][:5]]}})
    rows.sort(key=lambda r: -r["total"])
    return {"pair": pair, "question": "noun-class concord (associative agreement)", "rows": rows}


def apply_concord(pair: str, noun_prefix: str, marker: str, *, emit_delta: bool = True) -> dict:
    """CLOSE THE LOOP for agreement: the reviewer ACCEPTS 'class governed by `noun_prefix` takes concord
    marker `marker`'. Fill the declared schema's concord cell (if a schema is declared) and emit a
    confidence-routed delta. Reversible. Provenance 'reviewer-explore'."""
    from review import langknow
    cls = langknow.noun_class_prefixes(pair).get(noun_prefix, noun_prefix)
    schema_updated = _set_schema_concord(pair, cls, marker)
    n_delta = _emit_concord_delta(pair, noun_prefix, cls, marker) if emit_delta else 0
    return {"pair": pair, "noun_prefix": noun_prefix, "class": cls, "marker": marker,
            "schema_updated": schema_updated, "deltas": n_delta}


def _set_schema_concord(pair: str, class_id: str, marker: str) -> bool:
    try:
        from review.classes import declared_schema, declare
    except Exception:
        return False
    schema = declared_schema(pair)
    if not schema:
        return False
    for c in schema.get("classes", []):
        if c.get("id") == class_id:
            c.setdefault("concord", {})["associative"] = marker
            declare(pair, schema, by="reviewer-explore")
            return True
    return False


def _emit_concord_delta(pair: str, noun_prefix: str, class_id: str, marker: str) -> int:
    try:
        from review.deltas.store import DeltaStore, store_path
    except Exception:
        return 0
    store = DeltaStore.load(store_path(pair))
    op = {"op": "concord.set", "entry": f"concord:{pair}:{class_id}",
          "class": class_id, "noun_prefix": noun_prefix, "associative": marker, "confidence": 0.7,
          "provenance": {"source": "reviewer-explore", "pair": pair}}
    n = store.add([op])
    store.save()
    return n


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Explore higher-level decisions: browse + A/B/C + residue.")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--nouns", nargs="?", const="", default=None, help="browse all nouns (optional regex)")
    ap.add_argument("--classes", action="store_true", help="ranked candidate class groups + fit-none")
    ap.add_argument("--residue", action="store_true", help="patterns among unexplained nouns (another pattern?)")
    ap.add_argument("--switches", action="store_true", help="per-switch ranked candidate values + doesn't-fit")
    ap.add_argument("--agreement", action="store_true", help="per-class ranked concord markers + doesn't-fit")
    ap.add_argument("--apply-concord", default="", help="ACCEPT a concord: 'PREFIX:MARKER' (e.g. ki:cha)")
    ap.add_argument("--apply-residue", default="", help="ACCEPT a residue pattern (substring) → assign + add affix")
    ap.add_argument("--side", default="suffix", choices=["suffix", "prefix"], help="which edge the pattern is on")
    ap.add_argument("--gate", default="stem", choices=["stem", "function", "both", "none"],
                    help="morpheme gate for --apply-residue: stem-recurrence | parser POS | both | none")
    ap.add_argument("--label", default="", help="class label for the accepted pattern (e.g. LOC)")
    ap.add_argument("--apply-switch", default="", help="ACCEPT a switch value: 'name=value' (writes the profile)")
    ap.add_argument("--limit", type=int, default=80)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if a.nouns is not None:
        r = noun_entries(a.pair, a.nouns, limit=a.limit)
        print(f"\n{a.pair}: {r['n_nouns']} nouns, {r['n_classified']} classified; "
              f"{r['n_matched']} match /{a.nouns}/ (showing {r['shown']})")
        print(f"  {'noun':16}{'freq':>6}  {'pfx':5}{'class':7}{'source':14}conf")
        for row in r["rows"]:
            print(f"  {row['noun']:16}{row['freq']:6}  {row['prefix']:5}{str(row['class']):7}"
                  f"{str(row['source']):14}{row['confidence']}")
    if a.classes:
        r = class_hypotheses(a.pair)
        print(f"\n{a.pair}: noun-class hypotheses ({r['n_nouns']} nouns) — ranked A/B/C…:")
        for h in r["hypotheses"]:
            tag = chr(64 + h["rank"]) if h["rank"] <= 26 else str(h["rank"])
            print(f"  {tag} [{h['label']:14}] explains {h['n_explained']:4} nouns  e.g. {h['examples']}")
        print(f"  FIT NONE (where the next class hides): {r['fit_none']['n']} {r['fit_none']['examples']}")
    if a.residue:
        r = residue_patterns(a.pair)
        print(f"\n{a.pair}: residue patterns over {r['n_residue']} unexplained nouns — another pattern?")
        for i, p in enumerate(r["patterns"], 1):
            tag = chr(64 + i) if i <= 26 else str(i)
            print(f"  {tag} [{p['lens']}: '{p['pattern']}'] {p['n']} nouns ({p.get('n_real', '?')} real-affix) "
                  f"e.g. {p['examples']}")
        print(f"  FIT NONE: {r['fit_none']['n']} {r['fit_none']['examples']}")
    if a.switches:
        r = switch_hypotheses(a.pair)
        if r.get("error"):
            print(r["error"]); return 1
        print(f"\n{a.pair}: typological switches — ranked candidate values + doesn't-fit:")
        for s in r["switches"]:
            vals = " | ".join(f"{chr(64 + c['rank'])}={c['value']}" + ("*" if c["detected"] else "")
                              for c in s["candidates"])
            print(f"  [{s['switch']:20}] {vals}")
            if s["doesnt_fit"]:
                print(f"        ⚑ doesn't fit: {s['doesnt_fit']}")
            if s["evidence"]:
                print(f"        evidence: {s['evidence'][:90]}")
    if a.agreement:
        r = agreement_hypotheses(a.pair)
        print(f"\n{a.pair}: {r['question']} — ranked concord per noun-class + doesn't-fit:")
        for row in r["rows"][:12]:
            vals = " | ".join(f"{chr(64 + c['rank'])}={c['marker']}({c['support']},{c['share']:.0%})"
                              for c in row["candidates"])
            print(f"  [{row['noun_prefix']:3}→cl{str(row['class']):5}] {vals}")
            df = row["doesnt_fit"]
            if df["n"]:
                print(f"        ⚑ doesn't fit ({df['n']}, {df['share']:.0%}): markers {df['markers']}")
    if a.apply_concord and ":" in a.apply_concord:
        pfx, mk = a.apply_concord.split(":", 1)
        r = apply_concord(a.pair, pfx, mk)
        print(f"\n{a.pair}: ACCEPTED concord — cl{r['class']} ({pfx}-) governs '{mk}' "
              f"(schema_updated={r['schema_updated']}, deltas={r['deltas']})")
    if a.apply_switch and "=" in a.apply_switch:
        name, val = a.apply_switch.split("=", 1)
        r = apply_switch(a.pair, name, val)
        print(f"\n{a.pair}: ACCEPTED switch {name} = {val} "
              f"(locked={r['locked']}, profile_written={r['profile_written']}, deltas={r['deltas']})")
    if a.apply_residue:
        r = apply_residue_pattern(a.pair, a.apply_residue, side=a.side, label=a.label or None, gate=a.gate)
        print(f"\n{a.pair}: ACCEPTED {a.side} pattern '{a.apply_residue}' as class '{r['label']}' (gate={r['gate']})")
        print(f"  {r['n_candidates']} bear it → {r['n_assigned']} assigned (stem attested)  e.g. {r['examples']}")
        print(f"  SKIPPED by gate (coincidental ending, no stem): {r['n_skipped_by_gate']} {r['skipped_examples']}")
        print(f"  residue: {r['residue_before']} -> {r['residue_after']} (−{r['residue_before'] - r['residue_after']})")
        print(f"  affix added to model: {r['affix_added']} · deltas emitted: {r['deltas']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
