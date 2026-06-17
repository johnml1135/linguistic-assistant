"""Candidate lexicon + affix model derived from aligned IGT by the Leipzig casing split.

A morpheme whose gloss is all-caps (ignoring digits, dots, whitespace) is *grammatical*
(an affix); otherwise it is *lexical* (a root → lexical entry). Affix direction
(prefix/suffix) is decided by majority position relative to the word's lexical morphs.
This is the heuristic the spec's certification layer later checks and repairs.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .igt import MorphWord

_GRAM_STRIP = re.compile(r"[0-9.\s/()]")


def is_grammatical(gloss: str) -> bool:
    core = _GRAM_STRIP.sub("", gloss)
    return core != "" and core.isupper()


@dataclass(frozen=True)
class LexEntry:
    form: str
    gloss: str
    pos: str = "root"
    count: int = 0


@dataclass(frozen=True)
class Affix:
    form: str
    gloss: str
    kind: str  # 'suffix' | 'prefix'
    count: int = 0


@dataclass
class LangModel:
    code: str
    lexicon: list[LexEntry] = field(default_factory=list)
    affixes: list[Affix] = field(default_factory=list)

    @property
    def charset(self) -> list[str]:
        chars: set[str] = set()
        for e in self.lexicon:
            chars.update(e.form)
        for a in self.affixes:
            chars.update(a.form)
        return sorted(chars)

    def summary(self) -> dict:
        return {
            "code": self.code,
            "lex_entries": len(self.lexicon),
            "affixes": len(self.affixes),
            "prefixes": sum(a.kind == "prefix" for a in self.affixes),
            "suffixes": sum(a.kind == "suffix" for a in self.affixes),
            "charset": len(self.charset),
        }


def build_model(code: str, words: list[MorphWord], min_affix_count: int = 1) -> LangModel:
    lex_count: Counter[tuple[str, str]] = Counter()
    aff_count: Counter[tuple[str, str]] = Counter()
    aff_pos: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])  # [prefix, suffix]

    for w in words:
        lex_idx = [i for i, m in enumerate(w.morphs) if not is_grammatical(m.gloss)]
        for i, m in enumerate(w.morphs):
            if not m.form:
                continue
            if is_grammatical(m.gloss):
                aff_count[(m.form, m.gloss)] += 1
                if lex_idx and i < lex_idx[0]:
                    aff_pos[(m.form, m.gloss)][0] += 1
                else:
                    aff_pos[(m.form, m.gloss)][1] += 1
            else:
                lex_count[(m.form, m.gloss)] += 1

    lexicon = [
        LexEntry(form=f, gloss=g, count=c) for (f, g), c in sorted(lex_count.items())
    ]
    affixes = []
    for (f, g), c in sorted(aff_count.items()):
        if c < min_affix_count:
            continue  # prune rare affixes to keep HC's unordered search tractable on high-affix langs
        pre, suf = aff_pos[(f, g)]
        affixes.append(Affix(form=f, gloss=g, kind="prefix" if pre > suf else "suffix", count=c))
    return LangModel(code=code, lexicon=lexicon, affixes=affixes)
