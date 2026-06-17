"""Assemble a full :class:`Scorecard` from each data source.

- `assess_hermitcrab` drives the golden `hc` verifier (parse-based + structural measures).
- `assess_liblcm` / `assess_lift` compute the structural measures from a data dump (no parser).
"""

from __future__ import annotations

from typing import Callable

from . import inventory, metrics
from .scorecard import Scorecard

GlossLine = tuple[str, ...]
GlossParseFn = Callable[[object, list[str]], dict[str, list[GlossLine]]]


def _default_parse_fn() -> GlossParseFn:
    """Wrap golden `hc.run_parse` (which returns [(form, gloss)] analyses) into gloss-line parses."""
    from golden.hc import gloss_seq, run_parse

    def parse(model, words):
        raw = run_parse(model, words)
        return {w: list(dict.fromkeys(gloss_seq(a) for a in raw.get(w, []))) for w in words}

    return parse


def assess_hermitcrab(
    model,
    corpus_words: list[str],
    *,
    gold: dict[str, GlossLine] | None = None,
    token_counts: dict[str, int] | None = None,
    weights: dict[str, float] | None = None,
    grammar_id: str = "hc-grammar",
    corpus_id: str = "corpus",
    parse_fn: GlossParseFn | None = None,
) -> Scorecard:
    parse_fn = parse_fn or _default_parse_fn()
    inv = inventory.from_langmodel(model)
    words = list(dict.fromkeys(corpus_words))
    parses = parse_fn(model, words)

    m: dict = {}
    m["coverage"] = metrics.coverage(parses, token_counts)
    m["spurious_ambiguity"] = metrics.spurious_ambiguity(parses)
    m["grammar_size"] = metrics.grammar_size(inv.counts, weights)
    m["dead_constructs"] = metrics.dead_constructs(parses, inv.glosses)
    if inv.n_rule_derived is not None:
        m["generalization"] = metrics.generalization_ratio(inv.n_alternations or 0, inv.n_rule_derived)
    if gold:
        m["gold_roundtrip"] = metrics.gold_roundtrip(parses, gold)
        m["overgeneration"] = metrics.overgeneration(parses, gold)
    m["_notes"] = {
        "boundary_f1": "skipped on the HC path — HermitCrab echoes corrupted morph forms; "
        "gloss-line exact-analysis recall is the reliable correctness (golden/hc.py).",
        "productivity": "n/a for the v1 concatenative grammar (no phonological rules).",
    }
    return Scorecard(grammar_id=grammar_id, corpus_id=corpus_id, source="hermitcrab", measures=m)


def assess_liblcm(xml_text: str, *, grammar_id: str = "liblcm-project", weights: dict[str, float] | None = None) -> Scorecard:
    inv = inventory.from_liblcm_xml(xml_text)
    m: dict = {"grammar_size": metrics.grammar_size(inv.counts, weights)}
    if inv.n_rule_derived is not None:
        m["generalization"] = metrics.generalization_ratio(inv.n_alternations or 0, inv.n_rule_derived)
    else:
        m["generalization"] = {
            "generalization_ratio": None,
            "reason": "rule↔allomorph mapping not derivable from LibLCM counts alone",
            "n_alternations": inv.n_alternations,
        }
    m["_notes"] = {
        "parse_based": "coverage/ambiguity/round-trip/over-generation require a parser; build an HC "
        "grammar from this project (or use the FLEx parser) and run assess_hermitcrab for those."
    }
    return Scorecard(grammar_id=grammar_id, corpus_id="(structural-only)", source="liblcm", measures=m)


def assess_lift(xml_text: str, *, grammar_id: str = "lift-lexicon", weights: dict[str, float] | None = None) -> Scorecard:
    inv = inventory.from_lift_xml(xml_text)
    m = {
        "grammar_size": metrics.grammar_size(inv.counts, weights),
        "_notes": {"scope": "lexicon-only LIFT counts; no morphology/parse measures"},
    }
    return Scorecard(grammar_id=grammar_id, corpus_id="(structural-only)", source="lift", measures=m)
