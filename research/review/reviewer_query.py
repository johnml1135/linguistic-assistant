"""Reviewer query + what-if — let a reviewer (human, Opus, or Gemma) INTERROGATE the data behind a
proposed rule instead of judging a static dossier. Two capabilities:

1. QUERY: `query_words(pair, regex)` — every corpus word matching a pattern, with its frequency, HC gloss,
   and POS. ("Give me all words matching ^vy.* and the glosses found.")

2. WHAT-IF: `compare_options(pair, options)` — evaluate competing grammar edits (prune affixes, add a live
   glide rule with a conditioned environment) against the corpus and report, for the SAME test set:
     • before applying anything (baseline coverage + parsed set)
     • after option A / after option B (coverage, words gained, words lost vs baseline)
     • the cases that fit NEITHER (parsed at baseline but broken by every option) — the residue that tells
       the reviewer the rule is mis-scoped (e.g. cl4 mi- breaking under a global glide rule).

The point is accurate, on-demand evidence so the reviewer can say "this is a possible rule" — or see why
it isn't — from the data, not from recalled knowledge.

CLI:  python -m review.reviewer_query --pair swh --query "^vy"        # words + glosses
      python -m review.reviewer_query --pair swh --whatif-glide       # before / A / B / fit-neither
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


def _word_freq(pair: str, sample: int = 0) -> Counter:
    from align.morph_align_hc import _verses
    c: Counter = Counter()
    for _ref, _src, tgt in _verses(pair, sample):
        for w in tgt:
            c[w] += 1
    return c


def _pos_map(pair: str) -> dict:
    from gold.goldio import load_gold
    from review.project import load_pos
    return load_gold(pair).get("pos", {}) or load_pos(pair)


def query_words(pair: str, pattern: str, *, limit: int = 40, sample: int = 0) -> dict:
    """Corpus words matching `pattern` (regex), with frequency + HC gloss + POS — ranked by frequency."""
    from induce.tdd import _load_prior_model
    from engine.hc import run_parse, gloss_seq
    from gold.phonology_gold import phon_feats
    rx = re.compile(pattern)
    freq = _word_freq(pair, sample)
    pos = _pos_map(pair)
    matches = sorted((w for w in freq if rx.search(w)), key=lambda w: -freq[w])[:limit]
    model = _load_prior_model(pair)
    glosses = {}
    if model and matches:
        pf = phon_feats(pair, model.charset)
        res = run_parse(model, matches, chunk_timeout=20, phon_feats=pf)
        for w in matches:
            a = res.get(w) or []
            glosses[w] = "-".join(gloss_seq(a[0])) if a else ""
    rows = [{"word": w, "freq": freq[w], "gloss": glosses.get(w, ""), "pos": pos.get(w, "")}
            for w in matches]
    return {"pair": pair, "pattern": pattern, "n_matched": sum(1 for w in freq if rx.search(w)),
            "shown": len(rows), "rows": rows}


@dataclass
class Option:
    name: str
    prune_prefixes: frozenset = field(default_factory=frozenset)
    prune_suffixes: frozenset = field(default_factory=frozenset)
    glide_rule: bool = False
    glide_block_vowels: frozenset = field(default_factory=frozenset)


def _model_with(pair, opt: Option):
    import copy
    from induce.tdd import _load_prior_model
    m = copy.deepcopy(_load_prior_model(pair))
    m.affixes = [a for a in m.affixes
                 if not (a.kind == "prefix" and a.form in opt.prune_prefixes)
                 and not (a.kind == "suffix" and a.form in opt.prune_suffixes)]
    return m


def _parsed(pair, opt: Option, words, pf):
    from engine.hc import run_parse
    res = run_parse(_model_with(pair, opt), words, chunk_size=25, chunk_timeout=30,
                    phon_feats=pf, glide_rule=opt.glide_rule, glide_block_vowels=opt.glide_block_vowels)
    parsed = {w for w in words if res.get(w)}
    amb = sum(len(res[w]) for w in parsed) / len(parsed) if parsed else 0.0
    return parsed, round(amb, 2)


def context(pair: str, *, sample: int = 500, test_words=None):
    """Shared what-if context computed ONCE (model phon-feats, test words, baseline parsed set) so many
    candidates can be evaluated without re-parsing the baseline each time."""
    from induce.tdd import _load_prior_model, load_freqs
    from gold.phonology_gold import phon_feats
    model = _load_prior_model(pair)
    pf = phon_feats(pair, model.charset)
    if test_words is None:
        test_words = [w for w, _ in load_freqs(pair).most_common() if len(w) >= 2][:sample]
    base_parsed, base_amb = _parsed(pair, Option("baseline"), test_words, pf)
    return {"pf": pf, "test_words": test_words, "base_parsed": base_parsed, "base_amb": base_amb}


def summarize(pair: str, options: list[Option], ctx: dict) -> dict:
    """Before / after-each-option / fit-neither over a precomputed `context`. Pure set logic on parsed sets."""
    tw, pf, base_parsed = ctx["test_words"], ctx["pf"], ctx["base_parsed"]
    n = len(tw) or 1
    out = {"n_test": len(tw), "baseline": {"coverage": round(len(base_parsed) / n, 4),
                                           "amb": ctx["base_amb"], "n_parsed": len(base_parsed)}, "options": []}
    opt_parsed = []
    for opt in options:
        ps, amb = _parsed(pair, opt, tw, pf)
        opt_parsed.append(ps)
        out["options"].append({
            "name": opt.name, "coverage": round(len(ps) / n, 4),
            "delta": round((len(ps) - len(base_parsed)) / n, 4), "amb": amb,
            "n_gained": len(ps - base_parsed), "n_lost": len(base_parsed - ps),
            "gained_examples": sorted(ps - base_parsed)[:8], "lost_examples": sorted(base_parsed - ps)[:8]})
    if opt_parsed:
        broken_by_all = base_parsed.intersection(*[base_parsed - ps for ps in opt_parsed])
        out["fit_neither"] = {"n": len(broken_by_all), "examples": sorted(broken_by_all)[:12]}
    return out


def compare_options(pair: str, options: list[Option], *, sample: int = 500, test_words=None) -> dict:
    """Before / after-each-option / fit-neither, on a shared test set (computes its own context)."""
    ctx = context(pair, sample=sample, test_words=test_words)
    out = {"pair": pair, **summarize(pair, options, ctx)}
    return out


def option_from_spec(spec: dict) -> Option:
    """Build an Option from a free-form reviewer dict — the open-ended 'what happens if this?' input.
    Fields: name, prune_prefixes, prune_suffixes, glide_rule, glide_block_vowels (lists ok)."""
    return Option(
        name=spec.get("name", "option"),
        prune_prefixes=frozenset(spec.get("prune_prefixes", [])),
        prune_suffixes=frozenset(spec.get("prune_suffixes", [])),
        glide_rule=bool(spec.get("glide_rule", False)),
        glide_block_vowels=frozenset(spec.get("glide_block_vowels", [])),
    )


def whatif(pair: str, specs: list[dict], *, scope: str = "", sample: int = 500) -> dict:
    """Free-form follow-up: run the reviewer's own options, optionally on a SCOPE (regex of words to test —
    'test it on the words matching ^vy'). Returns before / after-each / fit-neither."""
    options = [option_from_spec(s) for s in specs]
    test_words = None
    if scope:
        rx = re.compile(scope)
        freq = _word_freq(pair)
        test_words = sorted((w for w in freq if rx.search(w)), key=lambda w: -freq[w])[:1000]
    out = compare_options(pair, options, sample=sample, test_words=test_words)
    out["scope"] = scope or f"top-{sample} frequent"
    out["n_scope"] = len(test_words) if test_words is not None else None
    return out


def print_compare(r: dict) -> None:
    b = r["baseline"]
    print(f"\n=== {r['pair']}: what-if over {r['n_test']} words ===")
    print(f"  BEFORE (baseline)      coverage={b['coverage']:.4f}  amb={b['amb']}  parsed={b['n_parsed']}")
    for o in r["options"]:
        print(f"  AFTER [{o['name']:24}] coverage={o['coverage']:.4f} (d{o['delta']:+.4f}) amb={o['amb']} "
              f"gained={o['n_gained']} lost={o['n_lost']}")
        if o["gained_examples"]:
            print(f"        + gained: {o['gained_examples']}")
        if o["lost_examples"]:
            print(f"        - lost  : {o['lost_examples']}")
    if r.get("fit_neither"):
        print(f"  FIT NEITHER (broken by every option): {r['fit_neither']['n']} — {r['fit_neither']['examples']}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Reviewer query + what-if over the corpus.")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--query", default="", help="regex: show matching words + freq + gloss + POS")
    ap.add_argument("--whatif-glide", action="store_true", help="compare glide-rule options (before/A/B/residue)")
    ap.add_argument("--whatif-spec", default="", help="JSON list of free-form option dicts ('what happens if this?')")
    ap.add_argument("--scope", default="", help="regex: restrict the what-if test set to matching words")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if a.query:
        r = query_words(a.pair, a.query, limit=a.limit, sample=a.sample)
        print(f"\n{a.pair}: {r['n_matched']} words match /{a.query}/ (showing {r['shown']}):")
        print(f"  {'word':16}{'freq':>6}  {'pos':8} gloss")
        for row in r["rows"]:
            print(f"  {row['word']:16}{row['freq']:6}  {row['pos']:8} {row['gloss']}")
    if a.whatif_glide:
        opts = [
            Option("prune vy/mw/my, no rule", prune_prefixes=frozenset({"vy", "mw", "my"})),
            Option("global glide, block u", prune_prefixes=frozenset({"vy", "mw", "my"}),
                   glide_rule=True, glide_block_vowels=frozenset({"u"})),
            Option("global glide, block u,i", prune_prefixes=frozenset({"vy", "mw", "my"}),
                   glide_rule=True, glide_block_vowels=frozenset({"u", "i"})),
        ]
        print_compare(compare_options(a.pair, opts, sample=a.sample or 500))
    if a.whatif_spec:
        import json
        r = whatif(a.pair, json.loads(a.whatif_spec), scope=a.scope, sample=a.sample or 500)
        print(f"\n[follow-up] scope={r['scope']}" + (f" ({r['n_scope']} words)" if r.get("n_scope") else ""))
        print_compare(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
