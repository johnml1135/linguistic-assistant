"""Pipeline validation set by ABLATION of the verified gold — ground truth for free.

Remove a known item (a frequent LexEntry or affix) from the gold `LangModel`, re-parse a corpus slice,
and the forms that *stop* parsing become a scenario whose answer key is the removed item. This exercises
the pipeline end-to-end against a known answer:

  Stage 3 (generation): do the hypotheses contain the removed item (or an equivalent)?  (recall)
  Stage 4 (assessment): does it accept the true item, reject **decoys** (a broad edit that may fix the
                        focus but over-generates / regresses), and report the right net delta?  (precision)

`ablate` builds one scenario; `decoy_hypothesis` builds an over-broad foil; `true_hypothesis` re-adds the
removed item as the correct edit. Deterministic: selection is by frequency rank, no RNG.
"""

from __future__ import annotations

from dataclasses import replace

from golden.grammar import Affix, LangModel, LexEntry
from golden.hc import run_parse

from . import counterfactual as CF
from .schema import GrammarEdit, Hypothesis


def _remove_lex(model: LangModel, e: LexEntry) -> LangModel:
    return LangModel(code=model.code, affixes=list(model.affixes),
                     lexicon=[x for x in model.lexicon if not (x.form == e.form and x.gloss == e.gloss)])


def _remove_affix(model: LangModel, a: Affix) -> LangModel:
    return LangModel(code=model.code, lexicon=list(model.lexicon),
                     affixes=[x for x in model.affixes if not (x.form == a.form and x.gloss == a.gloss)])


def ablate(pair: str, kind: str, rank: int = 0, *, base: LangModel | None = None, pf: dict | None = None,
           n_slice: int = 80) -> dict:
    """Remove the `rank`-th most frequent construct of `kind` ('lex'|'affix'); return the scenario.

    The scenario records the crippled model, the forms it breaks (the targets), the ground-truth removed
    item, and an impact tag — exactly what the pipeline must recover."""
    if base is None or pf is None:
        base, pf = CF.load_base(pair)
    freqs = CF._freqs(pair)
    pool = base.lexicon if kind == "lex" else base.affixes
    if not pool:                                          # nothing of this kind to ablate (e.g. no gold affixes)
        return {"pair": pair, "kind": kind, "ground_truth": None, "broken": [], "focus": "",
                "n_broken": 0, "crippled": base, "pf": pf, "words": [], "impact": "low",
                "skipped": f"no {kind} constructs in the reference model"}
    if kind == "lex":
        ranked = sorted(base.lexicon, key=lambda e: (-e.count, e.form, e.gloss))
        removed = ranked[rank % len(ranked)]
        crippled = _remove_lex(base, removed)
        gt = {"kind": "lex", "form": removed.form, "gloss": removed.gloss, "pos": removed.pos}
    else:
        ranked = sorted(base.affixes, key=lambda a: (-a.count, a.form, a.gloss))
        removed = ranked[rank % len(ranked)]
        crippled = _remove_affix(base, removed)
        gt = {"kind": "affix", "form": removed.form, "gloss": removed.gloss, "affix_kind": removed.kind}

    words = _slice(pair, removed.form, n_slice)
    now = run_parse(base, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
    crip = run_parse(crippled, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
    broken = [w for w in words if now.get(w) and not crip.get(w)]
    return {"pair": pair, "kind": kind, "ground_truth": gt, "broken": broken,
            "focus": broken[0] if broken else removed.form, "n_broken": len(broken),
            "crippled": crippled, "pf": pf, "words": words,
            "impact": "high" if len(broken) >= 10 else "medium" if len(broken) >= 3 else "low"}


def _slice(pair: str, focus: str, n: int) -> list[str]:
    freqs = CF._freqs(pair)
    out = [focus]
    for w, _ in freqs.most_common():
        if w.isalpha() and len(w) >= 2 and w not in out:
            out.append(w)
        if len(out) >= n:
            break
    return out


def true_hypothesis(scenario: dict) -> Hypothesis:
    """The correct edit: re-add the removed item."""
    gt = scenario["ground_truth"]
    if gt["kind"] == "lex":
        edit = GrammarEdit("add_lexentry", {"form": gt["form"], "gloss": gt["gloss"], "pos": gt.get("pos", "root")})
    else:
        edit = GrammarEdit("add_affix", {"form": gt["form"], "gloss": gt["gloss"],
                                         "kind": gt.get("affix_kind", "suffix")})
    return Hypothesis(id="true", mechanism=edit.kind, description="re-add the removed item", edits=[edit])


def defer_scenario(pair: str, word: str) -> dict:
    """A scenario whose CORRECT outcome is to defer (no confident resolution) — the complement of the
    ablation scenarios (task 11.3). Mirrors ParseGym `ask_speaker`/`unknown`: an isolated form with no
    near lemma and no strippable known affix should NOT be auto-resolved; the pipeline must defer it."""
    from golden.reference.goldio import load_gold
    from .taxonomy import _known_affix_split, _nearest_lemma
    gold = load_gold(pair)
    near = _nearest_lemma(word.lower(), gold.get("lemmas", []))
    split = _known_affix_split(word.lower(), gold.get("affixes", []))
    return {"pair": pair, "kind": "defer", "focus": word.lower(),
            "expected": "defer", "has_near_lemma": bool(near), "has_known_affix": bool(split),
            "resolvable": bool(near) or bool(split)}


def decoy_hypothesis(scenario: dict) -> Hypothesis:
    """An over-broad foil: a short, unrestricted affix that licenses too much (should lose on ΔMDL /
    over-generation, or regress), even if it happens to let the focus parse."""
    gt = scenario["ground_truth"]
    # a 1-char vowel suffix with no conditioning — the canonical over-generator
    edit = GrammarEdit("add_affix", {"form": "a", "gloss": "DECOY", "kind": "suffix"})
    return Hypothesis(id="decoy", mechanism="add_affix", description="broad over-generating affix", edits=[edit])
