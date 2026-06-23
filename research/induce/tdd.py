"""TDD-for-grammar cycle over the eBible-derived wordforms (Swahili, Indonesian, Tagalog, Spanish).

Red   = held-out frequent target wordforms that do NOT parse against the current grammar.
Green = induce the affix (or stem) that makes failing forms parse — accepted ONLY if HC coverage rises.
Refactor = (assess) keep the grammar minimal; HC search explosion on bloated affix sets shows up as
           chunk timeouts → coverage drops → the gate reverts the change (an emergent Occam pressure).

Reuses the sibling golden harness: `golden.grammar.LangModel` + `golden.hc.run_parse` (the `hc` CLI).
Deterministic induction (no model needed to demonstrate the loop); the propose step is swappable for
the LLM `propose-from-evidence` skill later.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RESEARCH))

from induce.glossing import infer_affix_glosses  # noqa: E402
from induce.gold import load_gold, score_gold  # noqa: E402
from induce.hc_phonology import spanish_phon_feats  # noqa: E402
from induce.phonology import HARMONY_CLASSES, collapse_families, propose_morphophon_rules  # noqa: E402
from induce.pos import pos_of  # noqa: E402
from engine.grammar import Affix, LangModel, LexEntry  # noqa: E402
from engine.hc import run_parse  # noqa: E402

EBIBLE = _RESEARCH / "_sources" / "ebible"
PAIR_DIR = {
    "swh": "eng-engwebp__swh-swhulb",
    "ind": "eng-engwebp__ind-indags",
    "tgl": "eng-engwebp__tgl-tglulb",
    "spa": "eng-engwebp__spa-spaRV1909",
}


def load_freqs(pair: str) -> Counter:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    c: Counter = Counter()
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c.update(json.loads(line)["tgt"])
    return c


def load_glosses(pair: str) -> dict[str, str]:
    p = EBIBLE / PAIR_DIR[pair] / "glosses.tsv"
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


# Vowels stripped to form an affix's consonant skeleton when grouping suspected harmony allomorphs.
# Latin five vowels + Spanish accented vowels (the current targets are Latin-script).
_HARMONY_VOWELS = set("aeiouáéíóú")


def harmony_families(affix_forms: list[str]) -> dict[str, list[str]]:
    """Group affixes by their consonant skeleton (harmony vowels stripped) to surface suspected
    vowel-harmony allomorph sets — e.g. {lr: [lar, ler], dn: [dan, den], nn: [nın, nin, nun, nün]}.

    This is the *enumerate -> generalize* hand-off worklist: each family with >1 member is one
    morpheme the next stage should collapse into a single archiphoneme + a harmony phonological rule,
    rather than N separate affixes. The TDD cycle stops at enumeration on purpose; this names the debt.
    See linguistics/skills/generalize-not-enumerate.md.
    """
    fams: dict[str, list[str]] = {}
    for f in affix_forms:
        skel = "".join(c for c in f if c not in _HARMONY_VOWELS)
        if skel:  # ignore bare-vowel affixes (no consonant anchor)
            fams.setdefault(skel, []).append(f)
    return {k: sorted(set(v)) for k, v in fams.items() if len(set(v)) > 1}


def seed(pair: str, n_roots: int) -> tuple[LangModel, list[str], Counter]:
    freqs = load_freqs(pair)
    glosses = load_glosses(pair)
    ranked = [w for w, _ in freqs.most_common() if len(w) >= 2]
    roots = ranked[:n_roots]
    rootset = set(roots)
    model = LangModel(
        code=pair,
        lexicon=[LexEntry(form=w, gloss=glosses.get(w, "?"), pos=pos_of(glosses.get(w, "?")), count=freqs[w]) for w in roots],
        affixes=[],
    )
    # held-out test set = next frequent forms not used as roots (the Red tests)
    test = [w for w in ranked[n_roots:] if w not in rootset][:120]
    return model, test, freqs


def _affix_label(side: str, form: str) -> str:
    """Human/gloss label for an affix by side: prefix `na-`, suffix `-ka`, infix `<um>`."""
    return {"prefix": f"{form}-", "suffix": f"-{form}", "infix": f"<{form}>"}.get(side, form)


def affix_candidates(model: LangModel, freqs: Counter, *, max_len: int = 4, min_root: int = 3) -> Counter:
    """Frequent residues around the longest known root = candidate affixes, BOTH sides.

    A root that is a *prefix* of the word leaves a SUFFIX residue (suffixing langs: Spanish);
    a root that is a *suffix* of the word leaves a PREFIX residue (prefixing/agglutinating langs:
    Swahili `a-na-soma`, Indonesian `meN-`, Tagalog). An **infix** splits the root after its onset
    consonant (Tagalog `s-um-ulat`, `s-in-ulat` from root `sulat`): word = root[0] + INFIX + root[1:].
    Inducing all three is the coverage unlock for the non-suffixing targets. Returns a Counter keyed by
    ``(side, form)`` where side ∈ {suffix, prefix, infix}.
    """
    roots = sorted({e.form for e in model.lexicon}, key=len, reverse=True)
    known = {(a.kind, a.form) for a in model.affixes}
    cand: Counter = Counter()
    for w, f in freqs.items():
        for r in roots:
            if len(r) < min_root or len(w) <= len(r):
                continue
            if w.startswith(r):
                res = w[len(r):]
                if 1 <= len(res) <= max_len and ("suffix", res) not in known:
                    cand[("suffix", res)] += f
                break  # longest matching root only
            if w.endswith(r):
                res = w[: len(w) - len(r)]
                if 1 <= len(res) <= max_len and ("prefix", res) not in known:
                    cand[("prefix", res)] += f
                break
            # infix: root split after its ONSET CONSONANT — word = r[0] + INFIX + r[1:] (Tagalog
            # -um-/-in-). Tight (root ≥4, consonant onset, 2–3-char infix) so a loose pattern doesn't
            # manufacture spurious infixes in non-infixing languages (e.g. Spanish).
            if len(r) >= 4 and w[0] == r[0] and w[0] not in _HARMONY_VOWELS and w.endswith(r[1:]):
                inf = w[1: len(w) - (len(r) - 1)]
                if 2 <= len(inf) <= 3 and ("infix", inf) not in known:
                    cand[("infix", inf)] += f
                break
    return cand


def grow_roots(model: LangModel, freqs: Counter, *, max_new: int = 20, min_stem: int = 3,
               glosses: dict[str, str] | None = None) -> list[LexEntry]:
    """Refactor/Green: strip a known affix (suffix OR prefix) off frequent forms → propose the stem.

    Held-out forms can't parse if their stem isn't a root, however many affixes exist. Discovering
    stems from the morphology is the lever that pushes coverage up — and for prefixing languages the
    stem is found by stripping a known *prefix*, not a suffix.

    When ``glosses`` is given, a grown stem that ALSO aligned as a bare word inherits that gloss instead
    of ``?`` — backfilling the lexicon so HC's analyses carry a real meaning, not a placeholder.
    """
    glosses = glosses or {}
    rootset = {e.form for e in model.lexicon}
    suffixes = sorted({a.form for a in model.affixes if a.kind == "suffix"}, key=len, reverse=True)
    prefixes = sorted({a.form for a in model.affixes if a.kind == "prefix"}, key=len, reverse=True)
    infixes = sorted({a.form for a in model.affixes if a.kind == "infix"}, key=len, reverse=True)
    stems: Counter = Counter()
    for w, f in freqs.items():
        if len(w) < min_stem + 1:
            continue
        stem: str | None = None
        for s in suffixes:
            if w.endswith(s) and len(w) - len(s) >= min_stem:
                stem = w[: -len(s)]
                break
        if stem is None:
            for p in prefixes:
                if w.startswith(p) and len(w) - len(p) >= min_stem:
                    stem = w[len(p):]
                    break
        if stem is None:
            for inf in infixes:  # infix after the onset segment → stem = w[0] + rest
                if w[1:1 + len(inf)] == inf and len(w) - len(inf) >= min_stem:
                    stem = w[0] + w[1 + len(inf):]
                    break
        if stem is not None and stem not in rootset:
            stems[stem] += f
    return [LexEntry(form=st, gloss=glosses.get(st, "?"), pos=pos_of(glosses.get(st, "?")), count=c)
            for st, c in stems.most_common(max_new)]


def assign_slots(model: LangModel, freqs: Counter, *, max_ord: int = 4, min_obs: int = 2,
                 pos_share: float = 0.6) -> list[Affix]:
    """Learn each affix's position-class **slot** ordinal AND its **MSA** (the POS it attaches to) from
    its co-occurrence with roots, in one segmentation pass.

    Slot order is structural (slot 1 = root-adjacent, 2 = next out, …), learned by greedily segmenting
    frequent words with the induced roots + affixes and recording each affix's distance from the root —
    the Refactor move that controls over-generation. In the same pass, each affix accumulates the POS of
    the roots it attaches to; a clear majority (≥ ``pos_share``) becomes its ``req_pos`` (otherwise it
    stays unrestricted). Mirrors `golden.build_model`'s slot/MSA evidence, which the cycle lacks because
    it has no gold morpheme breaks. See order-the-morphotactics + assign-pos-and-msa skills.
    """
    rootpos = {e.form: e.pos for e in model.lexicon}
    roots = sorted({e.form for e in model.lexicon if len(e.form) >= 3}, key=len, reverse=True)
    suff = sorted({a.form for a in model.affixes if a.kind == "suffix"}, key=len, reverse=True)
    pref = sorted({a.form for a in model.affixes if a.kind == "prefix"}, key=len, reverse=True)
    obs: dict[tuple[str, str], Counter] = defaultdict(Counter)      # ordinal evidence
    pobs: dict[tuple[str, str], Counter] = defaultdict(Counter)     # attached-root POS evidence (MSA)
    for w, f in freqs.items():
        ridx = rlen = -1
        for r in roots:
            i = w.find(r)
            if i >= 0:
                ridx, rlen = i, len(r)
                break  # longest root that occurs (roots are length-sorted)
        if ridx < 0:
            continue
        rp = rootpos.get(w[ridx:ridx + rlen], "")
        pre, suf = w[:ridx], w[ridx + rlen:]
        pos, ordn = 0, 1  # suffixes: inner (root-adjacent) first
        while pos < len(suf) and ordn <= max_ord:
            m = next((s for s in suff if suf.startswith(s, pos)), None)
            if not m:
                break
            obs[("suffix", m)][ordn] += f
            if rp:
                pobs[("suffix", m)][rp] += f
            pos += len(m); ordn += 1
        end, ordn = len(pre), 1  # prefixes: inner (root-adjacent) first → scan pre backward
        while end > 0 and ordn <= max_ord:
            m = next((p for p in pref if pre.endswith(p, 0, end)), None)
            if not m:
                break
            obs[("prefix", m)][ordn] += f
            if rp:
                pobs[("prefix", m)][rp] += f
            end -= len(m); ordn += 1

    out: list[Affix] = []
    for a in model.affixes:
        c = obs.get((a.kind, a.form))
        # MSA: a clear-majority attached POS becomes req_pos; otherwise leave unrestricted.
        pc = pobs.get((a.kind, a.form))
        req_pos = ""
        if pc:
            top, n = pc.most_common(1)[0]
            if n >= pos_share * sum(pc.values()):
                req_pos = top
        if not c:
            out.append(replace(a, req_pos=req_pos))  # no slot evidence → keep default slot, set MSA
            continue
        modal = max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0]
        keep = {o for o, n in c.items() if n >= min_obs} | {modal}
        slots = tuple(sorted((a.kind, o) for o in keep if o <= max_ord))
        out.append(replace(a, slot_ord=modal, slots=slots, req_pos=req_pos))
    return out


def coverage(model: LangModel, words: list[str], phon_feats: dict[str, dict[str, str]] | None = None,
             templated: bool = False, pos_aware: bool = False) -> tuple[float, float]:
    res = run_parse(model, words, chunk_size=25, chunk_timeout=20, templated=templated,
                    phon_feats=phon_feats, pos_aware=pos_aware)
    parsed = [w for w in words if res.get(w)]
    amb = sum(len(res[w]) for w in parsed) / len(parsed) if parsed else 0.0
    return (len(parsed) / len(words) if words else 0.0), amb


def _load_prior_model(pair: str) -> LangModel | None:
    """Reconstruct the accumulated grammar from a prior run's `out/<pair>_model.json` (for --resume)."""
    p = Path(__file__).resolve().parent / "out" / f"{pair}_model.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    lex = [LexEntry(form=r["form"], gloss=r.get("gloss", "?"), pos=r.get("pos", "noun"), count=r.get("count", 0))
           for r in d["roots"]]
    aff = [Affix(form=a["form"], gloss=a.get("gloss", a["form"]), kind=a["kind"], count=a.get("count", 0),
                 slot_ord=a.get("slot_ord", 1), req_pos=a.get("req_pos", "")) for a in d["affixes"]]
    return LangModel(code=pair, lexicon=lex, affixes=aff)


def run(pair: str, seconds: float, n_roots: int = 300, batch: int = 4,
        test_size: int = 120, expand: int = 120, amb_cap: float = 5.0, resume: bool = False) -> dict:
    """Moving-window curriculum: promote frequent forms to roots, test the next tranche, induce affixes
    to parse it (HC-gated), and when that window converges, slide to the next — real work, no spin.

    `amb_cap` bounds mean parse ambiguity: a change is kept only if coverage rises AND ambiguity stays
    under the cap. Without it, two-sided induction over an unordered grammar over-generates (ambiguity
    12–15) and HC search-explosion timeouts then drop coverage — so the cap is what keeps the metric
    healthy while coverage climbs. The deeper fix is ordered morphotactics (affix templates).

    `resume` loads the accumulated grammar from the prior run and continues into the next frequency
    tranche — the basis of the accumulating driver (`accumulate.py`): roots/affixes/glosses/POS grow
    round over round until coverage plateaus and the frequent vocabulary is exhausted."""
    freqs = load_freqs(pair)
    glosses = load_glosses(pair)
    ranked = [w for w, _ in freqs.most_common() if len(w) >= 2]

    # Live feature inventory: Spanish gets real voc/hi/rnd/back features + natural classes in the
    # emitted HC grammar (the feature-bearing substrate); other targets keep the identity-only grammar.
    pf = spanish_phon_feats(set("".join(ranked))) if pair == "spa" else None

    prior = _load_prior_model(pair) if resume else None
    if prior is not None and prior.lexicon:
        model = prior
        rootset = {e.form for e in model.lexicon}
        # carry on from where the accumulated roots reach into the frequency list
        roots_end = max(n_roots, sum(1 for w in ranked if w in rootset))
        for w in ranked[:roots_end]:  # ensure the frequent prefix is covered as roots
            if w not in rootset:
                model.lexicon.append(LexEntry(form=w, gloss=glosses.get(w, "?"),
                                              pos=pos_of(glosses.get(w, "?")), count=freqs[w]))
                rootset.add(w)
        print(f"[{pair}] resume: {len(model.lexicon)} roots, {len(model.affixes)} affixes carried over")
    else:
        roots_end = n_roots
        model = LangModel(code=pair, affixes=[],
                          lexicon=[LexEntry(form=w, gloss=glosses.get(w, "?"), pos=pos_of(glosses.get(w, "?")), count=freqs[w]) for w in ranked[:roots_end]])
    test = ranked[roots_end:roots_end + test_size]
    trend: list[dict] = []
    rejected: set[str] = set()

    cov, base_amb = coverage(model, test, pf)
    base_cov0 = cov
    trend.append({"iter": 0, "window": 0, "affixes": 0, "roots": len(model.lexicon),
                  "coverage": round(cov, 4), "ambiguity": round(base_amb, 2), "action": "seed", "kept": True})
    print(f"[{pair}] seed: roots={len(model.lexicon)} test={len(test)} cov={cov:.3f}")

    pool = [c for c, _ in affix_candidates(model, freqs).most_common(80)]
    t0 = time.monotonic()
    it = window = stall = 0
    while time.monotonic() - t0 < seconds:
        it += 1
        if it % 3 == 0:  # root growth (morphology-derived stems)
            new_roots = grow_roots(model, freqs, max_new=25, glosses=glosses)
            model.lexicon.extend(new_roots)
            new_cov, new_amb = coverage(model, test, pf)
            kept = new_cov > cov + 1e-9 and new_amb <= amb_cap
            if not kept and new_roots:
                del model.lexicon[-len(new_roots):]
            else:
                cov = max(cov, new_cov)
            action, label = f"roots+{len(new_roots)}", f"+{len(new_roots)} roots"
        else:  # affix induction
            pool = [c for c in pool if c not in rejected]
            if not pool:
                known_affixes = {(a.kind, a.form) for a in model.affixes}
                pool = [c for c, _ in affix_candidates(model, freqs).most_common(120)
                        if c not in rejected and c not in known_affixes]
            if not pool:
                stall += 1
                if stall >= 2:  # window converged → slide to the next tranche (productive, no spin)
                    if roots_end + test_size >= len(ranked):
                        break  # walked the whole frequent vocabulary
                    window += 1
                    model.lexicon.extend(
                        LexEntry(form=w, gloss=glosses.get(w, "?"), pos=pos_of(glosses.get(w, "?")), count=freqs[w]) for w in test)  # promote tested forms to roots
                    roots_end += test_size
                    test = ranked[roots_end:roots_end + test_size]
                    cov, _ = coverage(model, test, pf)
                    pool = [c for c, _ in affix_candidates(model, freqs).most_common(120)
                            if c not in {(a.kind, a.form) for a in model.affixes}]
                    rejected.clear()
                    stall = 0
                    trend.append({"iter": it, "window": window, "affixes": len(model.affixes),
                                  "roots": len(model.lexicon), "coverage": round(cov, 4),
                                  "ambiguity": 0.0, "action": f"slide->window{window}", "kept": True})
                    print(f"[{pair}] it{it}: slide to window {window} "
                          f"(roots={len(model.lexicon)} test={len(test)} cov={cov:.3f})")
                continue
            take, pool = pool[:batch], pool[batch:]
            model.affixes.extend(
                Affix(form=form, gloss=_affix_label(side, form), kind=side, count=freqs.get(form, 0))
                for side, form in take
            )
            new_cov, new_amb = coverage(model, test, pf)
            kept = new_cov > cov + 1e-9 and new_amb <= amb_cap
            if not kept:
                del model.affixes[-len(take):]
                rejected.update(take)
            else:
                cov = new_cov
                stall = 0
            shown = [_affix_label(side, form) for side, form in take]
            action, label = "add:" + ",".join(shown), "+[" + " ".join(shown) + "]"
        trend.append({"iter": it, "window": window, "affixes": len(model.affixes), "roots": len(model.lexicon),
                      "coverage": round(new_cov, 4), "ambiguity": round(new_amb, 2), "action": action, "kept": kept})
        print(f"[{pair}] it{it} w{window}: {label} -> cov={new_cov:.3f} amb={new_amb:.1f} "
              f"{'KEEP' if kept else 'revert'}  ({len(model.affixes)} aff / {len(model.lexicon)} roots)")
    base_cov = base_cov0

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{pair}_trend.jsonl").write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in trend), encoding="utf-8"
    )
    kept_affixes = [a.form for a in model.affixes]
    fams = harmony_families(kept_affixes)
    # Phase 1 phonology induction: collapse harmony families into archiphoneme affixes + rules,
    # gated offline by the harmony-rule expander (every observed allomorph must regenerate).
    collapse = collapse_families(fams, HARMONY_CLASSES.get(pair, {}))
    _, final_amb = coverage(model, test, pf)  # unordered-grammar ambiguity (metric)

    # Refactor — ORDERED MORPHOTACTICS + POS/MSA: assign_slots learns each affix's position-class slot
    # (from co-occurrence order) AND its MSA (the POS it attaches to); roots already carry a POS from
    # their gloss. Then pick the best grammar among {unordered, ordered template, ordered+POS-aware} by
    # lowest ambiguity subject to coverage held (assess-grammar style; the golden/coverage gate binds).
    # Real morpheme glosses: relabel affixes (e.g. -s -> PL) from the English inflection diff where the
    # alignment gives a clear majority; surface-form gloss kept otherwise.
    model.affixes, n_relabelled = infer_affix_glosses(model, freqs, glosses)

    # Enrich affixes with slots + MSA (kept regardless of which grammar wins — the emission flags below
    # decide whether slots/POS are *used*, so the MSA stays recorded on the lexicon even for unordered).
    model.affixes = assign_slots(model, freqs)
    tol = 0.02
    t_cov, t_amb = coverage(model, test, pf, templated=True)
    tp_cov, tp_amb = coverage(model, test, pf, templated=True, pos_aware=True)
    variants = {  # name -> (coverage, ambiguity, templated, pos_aware)
        "unordered": (cov, final_amb, False, False),
        "templated": (t_cov, t_amb, True, False),
        "templated+pos": (tp_cov, tp_amb, True, True),
    }
    chosen_name, (chosen_cov, chosen_amb, use_templated, use_pos) = "unordered", variants["unordered"]
    for name, (c, amb, tt, pp) in variants.items():
        if c >= cov - tol and amb < chosen_amb - 1e-9:
            chosen_name, (chosen_cov, chosen_amb, use_templated, use_pos) = name, (c, amb, tt, pp)
    morphotactics = {
        "chosen": chosen_name, "templated": use_templated, "pos_aware": use_pos,
        "variants": {n: {"coverage": round(c, 4), "ambiguity": round(a, 2)} for n, (c, a, _t, _p) in variants.items()},
        "slots": model.slot_sizes() if use_templated else {},
    }

    # POS/MSA report (the lexicon carries POS regardless of which grammar variant won).
    pos_counts = dict(sorted(Counter(e.pos for e in model.lexicon).items(), key=lambda kv: -kv[1]))
    msa = sorted((a.req_pos for a in model.affixes if a.req_pos))
    pos_block = {"applied": use_pos, "roots_by_pos": pos_counts,
                 "affixes_with_msa": len(msa), "affixes_total": len(model.affixes)}

    glossed = sum(1 for e in model.lexicon if e.gloss and e.gloss != "?")  # lexicon quality (non-? roots)
    result = {"pair": pair, "iterations": it, "base_coverage": round(base_cov, 4),
              "final_coverage": round(chosen_cov, 4), "delta": round(chosen_cov - base_cov, 4),
              "final_ambiguity": round(chosen_amb, 2), "amb_cap": amb_cap,
              "morphotactics": morphotactics,
              "pos": pos_block,
              "lexicon": {"roots": len(model.lexicon), "glossed": glossed,
                          "glossed_frac": round(glossed / len(model.lexicon), 4) if model.lexicon else 0.0,
                          "affix_glosses_inferred": n_relabelled},
              "affixes_kept": kept_affixes,
              # generalize-not-enumerate worklist: harmony allomorph sets to collapse next (see helper).
              "harmony_families": fams,
              "enumeration_debt": sum(len(v) - 1 for v in fams.values()),
              # phonology induction outcome (text-only, hc-gated when the scaffold gains classes):
              "phonology": {
                  "enumeration_debt_before": collapse.debt_before,
                  "enumeration_debt_after": collapse.debt_after,
                  "affixes_removed": collapse.affixes_removed,
                  "collapsed": [
                      {"archiphoneme": p.archiphoneme, "members": p.members,
                       "conditioning_class": p.conditioning_symbol}
                      for p in collapse.collapsed
                  ],
                  "needs_review": [
                      {"members": p.members, "reason": p.reason} for p in collapse.retained
                  ],
                  # non-harmony morphophonology rule candidates (meN- nasal assimilation, -s/-es epenthesis)
                  "rules_proposed": propose_morphophon_rules(
                      {a.form for a in model.affixes if a.kind == "prefix"},
                      {a.form for a in model.affixes if a.kind == "suffix"}),
              }}
    # Correctness gate (stronger than coverage): score the induced grammar against a hand-verified
    # word->gloss gold, if one exists for this pair. Coverage says "parsed"; this says "parsed RIGHT".
    gold = load_gold(pair)
    if gold:
        result["gold"] = score_gold(model, gold, phon_feats=pf, templated=use_templated, pos_aware=use_pos)

    (out_dir / f"{pair}_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    # Dump the final grammar (roots + affixes with kind/slot/MSA) so morph_align.py and the LLM propose
    # step can reconstruct the model and close the loop without re-running the cycle.
    (out_dir / f"{pair}_model.json").write_text(json.dumps({
        "pair": pair,
        "roots": [{"form": e.form, "gloss": e.gloss, "pos": e.pos, "count": e.count} for e in model.lexicon],
        "affixes": [{"form": a.form, "gloss": a.gloss, "kind": a.kind, "slot_ord": a.slot_ord,
                     "req_pos": a.req_pos, "count": a.count} for a in model.affixes],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{pair}] DONE: coverage {base_cov:.3f} -> {chosen_cov:.3f} (+{chosen_cov-base_cov:.3f}); "
          f"final ambiguity {chosen_amb:.2f} (cap {amb_cap}); "
          f"affixes: {' '.join(kept_affixes) or '(none)'}")
    m = morphotactics
    print(f"[{pair}] grammar: chose '{m['chosen']}' (templated={m['templated']}, pos_aware={m['pos_aware']}) — "
          + ", ".join(f"{n} cov {v['coverage']:.3f}/amb {v['ambiguity']:.2f}" for n, v in m["variants"].items())
          + (f"; slots {m['slots']}" if m['templated'] else ""))
    print(f"[{pair}] pos/msa: roots {pos_block['roots_by_pos']}; "
          f"{pos_block['affixes_with_msa']}/{pos_block['affixes_total']} affixes carry an MSA "
          f"(POS-aware grammar {'applied' if use_pos else 'not kept'})")
    glossed_affixes = sorted({a.gloss for a in model.affixes if a.gloss.isupper()})
    print(f"[{pair}] morpheme glosses: {n_relabelled} affixes relabelled from English inflection diffs"
          + (f" — {', '.join(glossed_affixes)}" if glossed_affixes else ""))
    if gold:
        g = result["gold"]
        print(f"[{pair}] gold gate: recall {g['gold_recall']:.3f} (correct gloss), "
              f"parsed {g['gold_parsed']:.3f} on {g['n']} hand-verified words"
              + (f"; missed e.g. {', '.join(g['missed'][:6])}" if g["missed"] else ""))
    if fams:
        top = sorted(fams.items(), key=lambda kv: -len(kv[1]))[:8]
        print(f"[{pair}] harmony families to collapse (generalize step): "
              + "; ".join(f"{k}={'/'.join(v)}" for k, v in top)
              + f"  [enumeration debt: {result['enumeration_debt']} affixes]")
    if collapse.collapsed:
        print(f"[{pair}] phonology: collapsed {len(collapse.collapsed)} families "
              f"(-{collapse.affixes_removed} affixes); debt {collapse.debt_before} -> {collapse.debt_after}: "
              + "; ".join(f"{p.archiphoneme}={'/'.join(p.members)}" for p in collapse.collapsed[:8]))
    rp = result["phonology"]["rules_proposed"]
    if rp:
        print(f"[{pair}] phonology rules proposed: "
              + "; ".join(f"{r['rule']} {r['archiphoneme']} ({'/'.join(r['members'])})" for r in rp))
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--seconds", type=float, default=480.0)
    ap.add_argument("--roots", type=int, default=300)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--amb-cap", type=float, default=5.0, help="reject changes whose mean ambiguity exceeds this")
    ap.add_argument("--resume", action="store_true", help="continue from the prior out/<pair>_model.json")
    args = ap.parse_args(argv)
    run(args.pair, args.seconds, n_roots=args.roots, batch=args.batch, amb_cap=args.amb_cap, resume=args.resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
