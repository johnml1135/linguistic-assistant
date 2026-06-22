"""The HC counterfactual-parse engine — the shared, deterministic evidence behind every ticket.

A hypothesis is a typed grammar edit (`deferrals.edits`). To show its consequence we clone the gold
grammar, apply the edit, and re-parse the focus form's verse plus a few related verses with the real
`hc` CLI (`golden.hc.run_parse`), recording per verse the parse **now** vs the parse **if the hypothesis
held**. No LLM is involved; HC is the source of truth.

Bounded + honest: parsing is chunked with a per-chunk timeout (inherited from `run_parse`); if HC is not
installed, or a hypothesis grammar times out, the counterfactual is flagged `unverified` rather than
presented as confirmed.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from golden.grammar import LangModel
from golden.hc import gloss_seq, run_parse
from golden.reference.compile import EBIBLE, PAIR_DIR
from golden.reference.hc_coverage import build_reference_model, hc_available
from golden.reference.phonology_gold import phon_feats

from .edits import apply_edits
from .schema import Counterfactual, Hypothesis

# parse knobs: small + bounded so a ticket builds in seconds, not minutes
N_RELATED = 4          # related verses beyond the focus verse (spec: 3–5 total)
MAX_WORDS = 60         # cap distinct words parsed per ticket (HC search is the cost)
CHUNK_TIMEOUT = 20     # per-chunk seconds; a timeout marks the hypothesis unverified


def _tokens(verse_tgt: list[str]) -> list[str]:
    return [t.lower() for t in verse_tgt if t.isalpha() and len(t) >= 2]


@lru_cache(maxsize=8)
def _verses(pair: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """All (ref, tgt-tokens) verses for the pair, in corpus order (cached)."""
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    out: list[tuple[str, tuple[str, ...]]] = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                out.append((d.get("ref", ""), tuple(_tokens(d.get("tgt", [])))))
    return tuple(out)


@lru_cache(maxsize=8)
def _freqs(pair: str) -> Counter:
    c: Counter = Counter()
    for _, toks in _verses(pair):
        c.update(toks)
    return c


def _shares_stem(a: str, b: str, k: int = 4) -> bool:
    """Cheap deterministic relatedness: a shared ≥k-char prefix (root) either direction."""
    if a == b:
        return True
    n = min(len(a), len(b), max(k, 1))
    return n >= k and a[:n] == b[:n]


def related_verses(pair: str, focus: str, n: int = N_RELATED) -> list[tuple[str, str]]:
    """Deterministically pick the focus verse + `n` related verses (shared root/affix/stem, then
    frequency). Returns [(ref, text), …]; same inputs → same output (spec: deterministic evidence set)."""
    focus = focus.lower()
    verses = _verses(pair)
    containing = [(ref, toks) for ref, toks in verses if focus in toks]
    # related = verses that share a stem with the focus (not already chosen), ranked by how much
    # corpus frequency their tokens carry so the reviewer sees consequential, common contexts first.
    freqs = _freqs(pair)
    seen_refs = {ref for ref, _ in containing[:1]}
    related: list[tuple[float, str, tuple[str, ...]]] = []
    for ref, toks in verses:
        if ref in seen_refs or focus not in {t for t in toks} and not any(_shares_stem(focus, t) for t in toks):
            continue
        if ref in {r for r, _ in containing[:1]}:
            continue
        score = sum(freqs.get(t, 0) for t in toks if _shares_stem(focus, t))
        related.append((score, ref, toks))
    related.sort(key=lambda r: (-r[0], r[1]))
    chosen = containing[:1] + [(ref, toks) for _, ref, toks in related[:n]]
    # de-dup by ref, preserve order
    out, seen = [], set()
    for ref, toks in chosen:
        if ref not in seen:
            seen.add(ref)
            out.append((ref, " ".join(toks)))
    return out


def load_base(pair: str) -> tuple[LangModel, dict]:
    """The gold grammar as a `LangModel` + its phonological feature substrate (for HC parsing)."""
    model = build_reference_model(pair)
    return model, phon_feats(pair, model.charset)


def _analyses(parses: dict, word: str) -> list:
    return [list(gloss_seq(a)) for a in parses.get(word, [])]


def attach_counterfactuals(pair: str, hypotheses: list[Hypothesis], focus: str, *,
                           base: LangModel | None = None, pf: dict | None = None,
                           n_related: int = N_RELATED, max_words: int = MAX_WORDS) -> list[Hypothesis]:
    """For each hypothesis, attach per-verse {now, if_hyp} diffs over the focus + related verses.

    The base ('now') parse is computed once and shared across hypotheses; each hypothesis is parsed once
    over the same bounded word set. Marks a hypothesis `unverified` when HC is unavailable."""
    focus = focus.lower()
    if base is None or pf is None:
        base, pf = load_base(pair)
    verses = related_verses(pair, focus, n_related)            # [(ref, text)]
    if not verses:                                             # focus not attested → synthetic verse
        verses = [("(focus)", focus)]
    # bounded, deterministic word set: focus first, then distinct verse tokens in order
    words: list[str] = []
    for _, text in verses:
        for w in [focus, *text.split()]:
            if w not in words:
                words.append(w)
    words = words[:max_words]
    if focus not in words:
        words.insert(0, focus)

    available = hc_available()
    now = run_parse(base, words, templated=False, phon_feats=pf, chunk_timeout=CHUNK_TIMEOUT) if available else {}

    for hyp in hypotheses:
        model2, phon = apply_edits(base, hyp.edits)
        try:
            ifp = run_parse(model2, words, templated=False, phon_feats=pf, chunk_timeout=CHUNK_TIMEOUT,
                            phon_rules=phon or None) if available else {}
        except Exception:
            ifp = {}
        cfs: list[Counterfactual] = []
        any_words_parsed = False
        for ref, text in verses:
            vtoks = [w for w in text.split() if w in words] or [focus]
            now_v = {w: _analyses(now, w) for w in vtoks}
            if_v = {w: _analyses(ifp, w) for w in vtoks}
            any_words_parsed = any_words_parsed or any(if_v.values())
            cfs.append(Counterfactual(
                ref=ref, text=text, focus=focus if focus in vtoks else "",
                now={w: a for w, a in now_v.items() if a or w == focus},
                if_hyp={w: a for w, a in if_v.items() if a or w == focus},
                focus_parsed_now=bool(now.get(focus)),
                focus_parsed_if=bool(ifp.get(focus)),
                unverified=not available,
            ))
        # unverified if HC is absent, or the edit produced no parse anywhere (likely a search timeout
        # rather than a genuine empty result — we cannot confirm it, so we don't claim it).
        hyp.unverified = (not available) or (bool(hyp.edits) and not any_words_parsed and not now)
        hyp.counterfactuals = cfs
    return hypotheses
