"""Ablate a certified gold grammar into agent-proposal instances (spec components 3 & 4).

Remove a controlled set of morphemes (lexical entries and/or affixes) from the model; the
held-out wordforms that *used* a removed morpheme become the instance's targets — they can
no longer be glossed until the agent re-proposes the missing pieces. Deterministic given a
seed (no RNG that would break reproducibility): selection is by frequency rank + seed offset.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .grammar import Affix, LangModel, LexEntry
from .igt import MorphWord


@dataclass
class Instance:
    """One ablation: what was removed, what it breaks, and the crippled model to repair."""

    kind: str                              # 'lex' | 'affix'
    removed_lex: list[LexEntry] = field(default_factory=list)
    removed_affix: list[Affix] = field(default_factory=list)
    held_out: list[tuple[str, list]] = field(default_factory=list)   # (underlying, gold analysis)
    control: list[tuple[str, list]] = field(default_factory=list)    # unaffected words (regression guard)
    incomplete: LangModel | None = None

    def answer_key(self) -> dict:
        return {
            "lex": [(e.form, e.gloss) for e in self.removed_lex],
            "affix": [(a.form, a.gloss, a.kind) for a in self.removed_affix],
        }


def _words_using(words: list[MorphWord], forms_glosses: set[tuple[str, str]]) -> list[tuple[str, list]]:
    out, seen = [], set()
    for w in words:
        if w.underlying in seen:
            continue
        if any((m.form, m.gloss) in forms_glosses for m in w.morphs):
            out.append((w.underlying, w.gold_analysis))
            seen.add(w.underlying)
    return out


def ablate_lex(model: LangModel, words: list[MorphWord], rank: int, n_control: int = 50) -> Instance:
    """Remove the ``rank``-th most frequent lexical entry; held-out = words using it."""
    ranked = sorted(model.lexicon, key=lambda e: (-e.count, e.form, e.gloss))
    removed = [ranked[rank % len(ranked)]]
    rm_keys = {(e.form, e.gloss) for e in removed}
    held = _words_using(words, rm_keys)
    incomplete = LangModel(
        code=model.code,
        lexicon=[e for e in model.lexicon if (e.form, e.gloss) not in rm_keys],
        affixes=list(model.affixes),
    )
    held_keys = {w for w, _ in held}
    control = [(w.underlying, w.gold_analysis) for w in words if w.underlying not in held_keys][:n_control]
    return Instance("lex", removed_lex=removed, held_out=held, control=control, incomplete=incomplete)


def ablate_affix(model: LangModel, words: list[MorphWord], rank: int, n_control: int = 50) -> Instance:
    """Remove the ``rank``-th most frequent affix; held-out = words using it."""
    ranked = sorted(model.affixes, key=lambda a: (-a.count, a.form, a.gloss))
    removed = [ranked[rank % len(ranked)]]
    rm_keys = {(a.form, a.gloss) for a in removed}
    held = _words_using(words, rm_keys)
    incomplete = LangModel(
        code=model.code,
        lexicon=list(model.lexicon),
        affixes=[a for a in model.affixes if (a.form, a.gloss) not in rm_keys],
    )
    held_keys = {w for w, _ in held}
    control = [(w.underlying, w.gold_analysis) for w in words if w.underlying not in held_keys][:n_control]
    return Instance("affix", removed_affix=removed, held_out=held, control=control, incomplete=incomplete)
