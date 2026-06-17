"""Approach B: the Minimum Description Length objective (`assess-grammar-mdl` spec).

Two-part code  DL(G, D) = L(G) + L(D | G)  in bits; a lower-DL grammar is better. This is the principled
form of Approach A's size + ambiguity proxies, and the engine for the "better? / split-or-combine?"
decisions. Foundations: Rissanen 1978 (MDL); Goldsmith 2001 (Linguistica — two-part code for
morphology); Creutz & Lagus 2007 (Morfessor — MDL as MAP `−log p(G) − log p(D|G)`); de Marcken 1996.

ENCODING SCHEME (versioned — `ENCODING_VERSION`; `DL` is comparable only within one version, per spec):
- `L(G)`: each morpheme's form is coded over the alphabet plus a stop symbol, `(len+1)·log2(|Σ|+1)` bits
  (subsumes length, after Goldsmith 2001 §2 / de Marcken 1996), plus a small structural cost (affix:
  side + slot; lexeme: POS).
- `L(D|G)`: unigram morph model. `p(m)` = relative frequency of morpheme `m` (identified by its gloss —
  HC's reliable signal) across the corpus's chosen analyses. Per token: `Σ_{m∈analysis} −log2 p(m)` plus
  `log2|hc(w)|` to disambiguate among the analyses `G` permits (so spurious ambiguity is charged). A word
  `G` cannot parse falls back to a verbatim surface code `len(w)·log2|Σ|` (no compression) — which makes
  removing a *needed* morpheme raise `DL`.

Glosses are the morpheme identity here (HC corrupts morph forms but not gloss lines — see golden/hc.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .worst_part import _remove  # reuse the golden leave-one-out model surgery

ENCODING_VERSION = "mdl-v1-concat"

GlossLine = tuple[str, ...]
Parses = dict[str, list[GlossLine]]
GlossParseFn = Callable[[object, list[str]], dict[str, list[GlossLine]]]


@dataclass
class EncodingScheme:
    version: str = ENCODING_VERSION
    affix_side_bits: float = 1.0  # prefix vs suffix


def _sigma(model) -> int:
    return max(2, len(model.charset))


# ------------------------------------------------------------------------------------------------ L(G)

def l_grammar(model, scheme: EncodingScheme | None = None) -> dict:
    scheme = scheme or EncodingScheme()
    sigma = _sigma(model)
    form_bit = math.log2(sigma + 1)  # alphabet + stop symbol
    n_pos = max(1, len({e.pos for e in model.lexicon}))
    n_slots = max(1, len({f"{sd}{o}" for a in model.affixes for sd, o in a.filled_slots()}))
    pos_bits = math.log2(n_pos)
    slot_bits = math.log2(n_slots)

    lex = sum((len(e.form) + 1) * form_bit + pos_bits for e in model.lexicon)
    aff = sum((len(a.form) + 1) * form_bit + scheme.affix_side_bits + slot_bits for a in model.affixes)
    return {
        "bits": round(lex + aff, 4),
        "lexicon_bits": round(lex, 4),
        "affix_bits": round(aff, 4),
        "alphabet_size": sigma,
        "version": scheme.version,
    }


# --------------------------------------------------------------------------------------------- L(D|G)

def _choose(parses: Parses, gold: dict[str, GlossLine] | None) -> dict[str, GlossLine | None]:
    """The analysis used to encode each word: the gold line if `G` still produces it, else the 1st parse."""
    gold = gold or {}
    chosen: dict[str, GlossLine | None] = {}
    for w, got in parses.items():
        if w in gold and gold[w] in got:
            chosen[w] = gold[w]
        elif got:
            chosen[w] = got[0]
        else:
            chosen[w] = None
    return chosen


def _morph_probs(chosen: dict[str, GlossLine | None], tc: dict[str, int]) -> dict[str, float]:
    counts: dict[str, float] = {}
    total = 0.0
    for w, a in chosen.items():
        if not a:
            continue
        mult = tc.get(w, 1)
        for m in a:
            counts[m] = counts.get(m, 0.0) + mult
            total += mult
    return {m: c / total for m, c in counts.items()} if total else {}


def l_data_given_grammar(
    model, parses: Parses, gold: dict[str, GlossLine] | None, token_counts: dict[str, int] | None
) -> dict:
    tc = token_counts or {w: 1 for w in parses}
    sigma = _sigma(model)
    chosen = _choose(parses, gold)
    probs = _morph_probs(chosen, tc)
    verbatim_bit = math.log2(sigma)

    bits = 0.0
    n_unparsed = 0
    for w, a in chosen.items():
        mult = tc.get(w, 1)
        if a is None:
            bits += mult * len(w) * verbatim_bit  # no compression — encode the surface
            n_unparsed += 1
        else:
            nll = sum(-math.log2(probs[m]) for m in a)
            ambiguity = math.log2(max(1, len(parses.get(w, []))))
            bits += mult * (nll + ambiguity)
    return {"bits": round(bits, 4), "n_unparsed": n_unparsed, "n_morph_types": len(probs)}


# -------------------------------------------------------------------------------------- DL + decisions

def description_length(
    model, parses: Parses, gold: dict[str, GlossLine] | None = None,
    token_counts: dict[str, int] | None = None, scheme: EncodingScheme | None = None,
) -> dict:
    lg = l_grammar(model, scheme)
    ld = l_data_given_grammar(model, parses, gold, token_counts)
    return {
        "L_G": lg["bits"],
        "L_D_given_G": ld["bits"],
        "DL": round(lg["bits"] + ld["bits"], 4),
        "version": lg["version"],
        "l_grammar": lg,
        "l_data": ld,
    }


def better_grammar(candidates: dict[str, float]) -> dict:
    """`candidates` maps a label to its `DL`. Lower wins. Returns the winner + ΔDL vs each other."""
    if not candidates:
        return {"winner": None, "deltas": {}}
    winner = min(candidates, key=lambda k: candidates[k])
    deltas = {k: round(candidates[k] - candidates[winner], 4) for k in candidates}
    return {"winner": winner, "winner_DL": candidates[winner], "deltas": deltas}


def decide_split_or_combine(dl_combined: float, dl_split: float) -> dict:
    """Linguistica's MDL move: pick the variant with lower DL. Positive ΔDL favors *combined*."""
    res = better_grammar({"combined": dl_combined, "split": dl_split})
    return {"recommend": res["winner"], "delta_DL_split_minus_combined": round(dl_split - dl_combined, 4)}


# ------------------------------------------------------------------------------ marginal DL (worst part)

def _default_parse_fn() -> GlossParseFn:
    from golden.hc import gloss_seq, run_parse

    def parse(model, words):
        raw = run_parse(model, words)
        return {w: list(dict.fromkeys(gloss_seq(a) for a in raw.get(w, []))) for w in words}

    return parse


def worstness_mdl_ranking(
    model, gold: dict[str, GlossLine], *, token_counts: dict[str, int] | None = None,
    scheme: EncodingScheme | None = None, parse_fn: GlossParseFn | None = None,
) -> list[dict]:
    """Rank constructs by `worstness_mdl(c) = DL(G) − DL(G\\{c})` (higher = worse: removing it lowers bits)."""
    parse_fn = parse_fn or _default_parse_fn()
    words = list(gold)
    base_dl = description_length(model, parse_fn(model, words), gold, token_counts, scheme)["DL"]

    rows: list[dict] = []
    constructs = [("lex", e.form, e.gloss) for e in model.lexicon] + \
                 [("affix", a.form, a.gloss) for a in model.affixes]
    for kind, form, gloss in constructs:
        m_c = _remove(model, kind, form, gloss)
        dl_c = description_length(m_c, parse_fn(m_c, words), gold, token_counts, scheme)["DL"]
        rows.append({
            "kind": kind, "form": form, "gloss": gloss,
            "worstness_mdl": round(base_dl - dl_c, 4),
            "DL_without": dl_c,
        })
    rows.sort(key=lambda r: (-r["worstness_mdl"], r["kind"], r["gloss"], r["form"]))
    return rows


def spearman(a: list[float], b: list[float]) -> float:
    """Spearman rank correlation — the 'agree in direction' check (assess-grammar-mdl, task 6.3)."""
    n = len(a)
    if n < 2:
        return 0.0

    def ranks(xs: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: xs[i])
        r = [0.0] * n
        i = 0
        while i < n:  # average ranks for ties
            j = i
            while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    mra, mrb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - mra) * (rb[i] - mrb) for i in range(n))
    den = math.sqrt(sum((ra[i] - mra) ** 2 for i in range(n)) * sum((rb[i] - mrb) ** 2 for i in range(n)))
    return round(num / den, 4) if den else 0.0
