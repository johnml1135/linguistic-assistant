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
    # Irregular-stem allomorphy the HC way: extra stem shapes for the SAME entry (LibLCM
    # MoStemAllomorph). HC tries each, so `decir` with allomorphs ('dic','dij') parses `diciendo`,
    # `dijo`. Unconditioned here (HC's easy path); PhoneEnv conditioning is the later refinement.
    allomorphs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Affix:
    form: str
    gloss: str
    kind: str  # 'suffix' | 'prefix' | 'infix'
    count: int = 0
    slot_ord: int = 1  # modal position class: 1 = adjacent to the root, 2 = next out, ...
    slots: tuple[tuple[str, int], ...] = ()  # ALL attested slots (MoInflAffMsa.Slots is a sequence)
    req_pos: str = ""  # MSA: the part of speech this affix attaches to ("" = any/unrestricted)

    @property
    def slot(self) -> tuple[str, int]:
        """The modal (side, ordinal) position-class slot — used for naming/default."""
        return (self.kind, self.slot_ord)

    def filled_slots(self) -> tuple[tuple[str, int], ...]:
        """Every slot this affix may fill (multi-slot membership); falls back to the modal slot."""
        return self.slots or (self.slot,)


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
            for al in e.allomorphs:
                chars.update(al)
        for a in self.affixes:
            chars.update(a.form)
        return sorted(chars)

    def slot_sizes(self) -> dict[str, int]:
        """#affixes that may fill each position-class slot (affix-template structure)."""
        from collections import Counter
        c: Counter = Counter()
        for a in self.affixes:
            for sd, o in a.filled_slots():
                c[f"{sd}{o}"] += 1
        return dict(sorted(c.items()))

    def summary(self) -> dict:
        return {
            "code": self.code,
            "lex_entries": len(self.lexicon),
            "affixes": len(self.affixes),
            "prefixes": sum(a.kind == "prefix" for a in self.affixes),
            "suffixes": sum(a.kind == "suffix" for a in self.affixes),
            "charset": len(self.charset),
            "slots": self.slot_sizes(),
        }


def build_model(code: str, words: list[MorphWord], min_affix_count: int = 1) -> LangModel:
    lex_count: Counter[tuple[str, str]] = Counter()
    aff_count: Counter[tuple[str, str]] = Counter()
    aff_pos: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])  # [prefix, suffix]
    # position-class evidence: per affix, a Counter of (side, ordinal-from-root) observations.
    aff_slot: dict[tuple[str, str], Counter] = defaultdict(Counter)

    for w in words:
        lex_idx = [i for i, m in enumerate(w.morphs) if not is_grammatical(m.gloss)]
        for i, m in enumerate(w.morphs):
            if not m.form:
                continue
            if is_grammatical(m.gloss):
                key = (m.form, m.gloss)
                aff_count[key] += 1
                if lex_idx and i < lex_idx[0]:
                    aff_pos[key][0] += 1
                    aff_slot[key][("prefix", lex_idx[0] - i)] += 1
                else:
                    aff_pos[key][1] += 1
                    prev_roots = [j for j in lex_idx if j < i]
                    base = prev_roots[-1] if prev_roots else (lex_idx[-1] if lex_idx else i)
                    aff_slot[key][("suffix", max(1, i - base))] += 1
            else:
                lex_count[(m.form, m.gloss)] += 1

    lexicon = [LexEntry(form=f, gloss=g, count=c) for (f, g), c in sorted(lex_count.items())]
    affixes = []
    for (f, g), c in sorted(aff_count.items()):
        if c < min_affix_count:
            continue  # prune rare affixes to keep HC's search tractable on high-affix langs
        pre, suf = aff_pos[(f, g)]
        kind = "prefix" if pre > suf else "suffix"
        # observations on the chosen side; modal ordinal is the primary slot.
        side_obs = [(ordn, n) for (sd, ordn), n in aff_slot[(f, g)].items() if sd == kind]
        slot_ord = max(side_obs, key=lambda t: (t[1], -t[0]))[0] if side_obs else 1
        # multi-slot membership: keep every attested ordinal (>=2 obs, or the modal one) — an affix
        # legitimately fills more than one position class (MoInflAffMsa.Slots is a sequence).
        keep = {ordn for ordn, n in side_obs if n >= 2} | {slot_ord}
        slots = tuple(sorted((kind, o) for o in keep))
        affixes.append(Affix(form=f, gloss=g, kind=kind, count=c, slot_ord=slot_ord, slots=slots))
    return LangModel(code=code, lexicon=lexicon, affixes=affixes)
