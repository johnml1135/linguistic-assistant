"""The "worst part of the grammar" ranking — leave-one-out over constructs.

For each construct `c`, remove it, re-parse the gold words, and compute
`worstness_metrics(c) = lam·cost(c) − benefit(c)` (higher = worse), per the `assess-grammar-metrics`
spec. Constructs are ranked descending. Reuses the golden grammar/ablation model.

`parse_fn(model, words) -> {word: [gloss_line, ...]}` is injectable so the ranking is testable without
the `hc` CLI (the default wraps `golden.hc.run_parse`).
"""

from __future__ import annotations

from typing import Callable

from . import metrics

GlossLine = tuple[str, ...]
GlossParseFn = Callable[[object, list[str]], dict[str, list[GlossLine]]]


def _default_parse_fn() -> GlossParseFn:
    from engine.hc import gloss_seq, run_parse

    def parse(model, words):
        raw = run_parse(model, words)
        return {w: list(dict.fromkeys(gloss_seq(a) for a in raw.get(w, []))) for w in words}

    return parse


def _remove(model, kind: str, form: str, gloss: str):
    """Return a copy of the LangModel with one construct removed (mirrors golden.ablate)."""
    from engine.grammar import LangModel

    lex = [e for e in model.lexicon if not (kind == "lex" and e.form == form and e.gloss == gloss)]
    aff = [a for a in model.affixes if not (kind == "affix" and a.form == form and a.gloss == gloss)]
    return LangModel(code=model.code, lexicon=lex, affixes=aff)


def _snapshot(parses: dict[str, list[GlossLine]], gold: dict[str, GlossLine]) -> tuple[float, float, float]:
    cov = metrics.coverage(parses)["coverage_type"]
    rec = metrics.gold_roundtrip(parses, gold)["exact_analysis_recall"]
    amb = metrics.spurious_ambiguity(parses)["mean_analyses"]
    return cov, rec, amb


def worst_part_ranking(
    model,
    gold: dict[str, GlossLine],
    *,
    lam: float = 1.0,
    parse_fn: GlossParseFn | None = None,
) -> list[dict]:
    """Rank constructs by `worstness_metrics(c)` (descending = worst first)."""
    parse_fn = parse_fn or _default_parse_fn()
    words = list(gold)
    base_cov, base_rec, base_amb = _snapshot(parse_fn(model, words), gold)

    rows: list[dict] = []
    constructs = [("lex", e.form, e.gloss) for e in model.lexicon] + \
                 [("affix", a.form, a.gloss) for a in model.affixes]
    for kind, form, gloss in constructs:
        cov, rec, amb = _snapshot(parse_fn(_remove(model, kind, form, gloss), words), gold)
        benefit = (base_cov - cov) + (base_rec - rec)          # what removing c loses
        cost = 1.0 + max(0.0, base_amb - amb)                  # size unit + ambiguity it contributes
        rows.append({
            "kind": kind, "form": form, "gloss": gloss,
            "worstness": round(lam * cost - benefit, 6),
            "benefit": round(benefit, 6), "cost": round(cost, 6),
        })
    rows.sort(key=lambda r: (-r["worstness"], r["kind"], r["gloss"], r["form"]))
    return rows
