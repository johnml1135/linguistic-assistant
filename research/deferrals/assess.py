"""Stage 4 — regression-aware hypothesis assessment (deterministic; the gold-corrupting failure guard).

A hypothesis is NOT judged by "does the focus parse now". We apply its edit, re-parse a representative
corpus slice, and compute:

  net parse delta = gains − regressions
      gains       = forms that did NOT parse before and DO under the hypothesis
      regressions = forms that parsed before and no longer do (or lost their analysis)

and the principled "which is better" signal, **ΔMDL** (`research/assess/mdl.py`, `L(G)+L(D|G)` in bits;
lower is better), so a broad rule that over-generates is penalised even when its net delta is positive.

A hypothesis is acceptable only if it (a) parses the focus, (b) has non-negative net delta, and (c)
causes no high-impact regression. These deterministic gates run before any LLM verdict; the LLM (group 6)
may rank among gate-passers but can never override a regression rejection.
"""

from __future__ import annotations

from golden.grammar import LangModel
from golden.hc import gloss_seq, run_parse

from assess.mdl import description_length

from . import counterfactual as CF
from .edits import apply_edits
from .schema import DeferralTicket, Hypothesis

HIGH_IMPACT_FREQ = 50      # a regressed form at/above this corpus frequency blocks acceptance
SLICE = 150                # corpus words assessed per hypothesis (bounds HC cost)


def corpus_slice(pair: str, focus: str, n: int = SLICE) -> list[str]:
    """A deterministic, representative word set: the focus, forms sharing its stem, then the most
    frequent corpus words (the part of the grammar most worth not breaking)."""
    freqs = CF._freqs(pair)
    focus = focus.lower()
    related = sorted((w for w in freqs if CF._shares_stem(focus, w) and w != focus),
                     key=lambda w: -freqs.get(w, 0))
    frequent = [w for w, _ in freqs.most_common() if w.isalpha() and len(w) >= 2]
    out: list[str] = []
    for w in [focus, *related, *frequent]:
        if w not in out:
            out.append(w)
        if len(out) >= n:
            break
    return out


def _glosslines(parses: dict, words: list[str]) -> dict:
    return {w: list(dict.fromkeys(gloss_seq(a) for a in parses.get(w, []))) for w in words}


def assess_hypothesis(pair: str, hyp: Hypothesis, focus: str, *, base: LangModel, pf: dict,
                      words: list[str], base_parses: dict | None = None,
                      base_dl: float | None = None) -> dict:
    """Assess one hypothesis over a corpus slice; sets `hyp.metrics` + `hyp.verdict` and returns metrics."""
    focus = focus.lower()
    now = base_parses if base_parses is not None else \
        run_parse(base, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
    model2, phon = apply_edits(base, hyp.edits)
    try:
        ifp = run_parse(model2, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT,
                        phon_rules=phon or None)
    except Exception:
        ifp = {}
        hyp.unverified = True

    freqs = CF._freqs(pair)
    gains, regressions, hi_regr = [], [], []
    for w in words:
        had, has = bool(now.get(w)), bool(ifp.get(w))
        if has and not had:
            gains.append(w)
        elif had and not has:
            regressions.append(w)
            if freqs.get(w, 0) >= HIGH_IMPACT_FREQ:
                hi_regr.append(w)
    net = len(gains) - len(regressions)

    # ΔMDL (bits): lower DL is better, so a negative delta = the hypothesis improves the grammar.
    base_dl = base_dl if base_dl is not None else \
        description_length(base, _glosslines(now, words), token_counts=freqs)["DL"]
    if_dl = description_length(model2, _glosslines(ifp, words), token_counts=freqs)["DL"]
    delta_mdl = round(if_dl - base_dl, 2)

    parsed_now = sum(1 for w in words if now.get(w))
    parsed_if = sum(1 for w in words if ifp.get(w))
    amb_if = [len(ifp[w]) for w in words if ifp.get(w)]
    metrics = {
        "delta_mdl": delta_mdl,                         # <0 is better
        "net_delta": net, "gains": len(gains), "regressions": len(regressions),
        "coverage_now": round(parsed_now / len(words), 4) if words else 0.0,
        "coverage_if": round(parsed_if / len(words), 4) if words else 0.0,
        "coverage_gain": parsed_if - parsed_now,
        "over_generation": round(sum(amb_if) / len(amb_if), 2) if amb_if else 0.0,
        "high_impact_regressions": len(hi_regr),
        "slice": len(words),
    }
    focus_if = bool(ifp.get(focus))
    acceptable = focus_if and net >= 0 and not hi_regr and not hyp.unverified
    hyp.metrics = metrics
    hyp.verdict = {"acceptable": acceptable, "gains": len(gains), "regressions": len(regressions),
                   "net": net, "focus_parses": focus_if,
                   "high_impact_regressions": hi_regr[:5]}
    return metrics


def assess_ticket(ticket: DeferralTicket, *, base: LangModel | None = None, pf: dict | None = None,
                  n_slice: int = SLICE) -> dict:
    """Assess every hypothesis on a ticket, rank them, and return the ranking + best acceptable id.

    Ranking: acceptable first, then by ΔMDL (most negative = best), then higher net delta. This is the
    'which hypothesis is better' decision, grounded in MDL with regression as a hard gate."""
    pair, focus = ticket.pair, ticket.target.get("form", "")
    if base is None or pf is None:
        base, pf = CF.load_base(pair)
    words = corpus_slice(pair, focus, n_slice)
    freqs = CF._freqs(pair)
    base_parses = run_parse(base, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
    base_dl = description_length(base, _glosslines(base_parses, words), token_counts=freqs)["DL"]

    for h in ticket.hypotheses:
        assess_hypothesis(pair, h, focus, base=base, pf=pf, words=words,
                          base_parses=base_parses, base_dl=base_dl)

    # rank: acceptable first, then by ΔMDL (lower=better), then RESTRICTIVENESS (lower over-generation —
    # the subset principle / D11), then higher net delta.
    ranked = sorted(ticket.hypotheses,
                    key=lambda h: (0 if h.verdict.get("acceptable") else 1,
                                   h.metrics.get("delta_mdl", 0.0),
                                   h.metrics.get("over_generation", 0.0),
                                   -h.metrics.get("net_delta", 0)))
    best = next((h.id for h in ranked if h.verdict.get("acceptable")), None)
    # narrow-vs-broad: when ≥2 hypotheses are acceptable but differ in over-generation, surface the
    # trade-off explicitly (coverage vs over-generation) rather than silently picking by bits.
    acc = [h for h in ranked if h.verdict.get("acceptable")]
    tradeoff = None
    if len(acc) >= 2:
        og = sorted(acc, key=lambda h: h.metrics.get("over_generation", 0.0))
        if og[-1].metrics.get("over_generation", 0) - og[0].metrics.get("over_generation", 0) >= 0.5:
            tradeoff = {"narrower": og[0].id, "broader": og[-1].id,
                        "note": "both fix the focus; the narrower over-generates less (subset principle)."}
            ticket.tags["restrictiveness_tradeoff"] = tradeoff
    return {"ticket": ticket.id, "ranking": [h.id for h in ranked], "best": best,
            "best_delta_mdl": next((h.metrics.get("delta_mdl") for h in ranked if h.id == best), None),
            "tradeoff": tradeoff}
