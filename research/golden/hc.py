"""Emit a HermitCrab.NET grammar from a :class:`~golden.grammar.LangModel` and drive the
``hc`` CLI to parse wordforms — the deterministic verifier at the core of the gold.

The emitted grammar does pure concatenative segmentation (one unique phonological feature
per orthographic character, so HC never merges distinct letters). Roots are
``<LexicalEntry>``; affixes are ``<MorphologicalRule>`` with an
``OptionalSegmentSequence(min=1,max=-1)`` stem matcher (proven recipe — see PLAN.md).
Phonological rules / allomorphy are deliberately out of v1.
"""

from __future__ import annotations

import os
import re
import string
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from .grammar import LangModel

HC_EXE = os.path.expanduser(os.path.join("~", ".dotnet", "tools", "hc.exe"))
_ENV = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}

Analysis = list[tuple[str, str]]  # [(morph_form, gloss), ...]

# HermitCrab.NET corrupts both its *output* rendering of non-ASCII-alnum characters AND its
# *internal* handling of multi-char representations built from LETTERS (verified: a letter
# token like "BD" gets silently substituted to "AB" — a phoneme merge). DIGIT-only
# fixed-width tokens round-trip exactly (verified). So we transliterate each source grapheme
# into a unique zero-padded decimal token over [0-9], then invert on output. HC only ever
# sees digits, where it is correct; we recover the real graphemes ourselves.
_SAFE = string.digits  # 10, all HC-safe; fixed-width tokens stay uniquely decodable


def _tok_len(n: int) -> int:
    width = 2
    while 10 ** width < n:
        width += 1
    return width


class Translit:
    """Bijective grapheme<->digit-token map keeping HC I/O in characters it renders correctly."""

    def __init__(self, chars: list[str]):
        uniq = sorted(set(chars))
        self.width = _tok_len(len(uniq))
        self.fwd = {c: str(i).zfill(self.width) for i, c in enumerate(uniq)}
        self.bwd = {v: k for k, v in self.fwd.items()}

    def enc(self, s: str) -> str:
        return "".join(self.fwd[c] for c in s if c in self.fwd)

    def dec(self, s: str) -> str:
        pairs = [s[i : i + self.width] for i in range(0, len(s), self.width)]
        return "".join(self.bwd.get(p, p) for p in pairs)


def _xid(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def build_grammar_xml(model: LangModel, tl: Translit | None = None, templated: bool = True) -> str:
    tl = tl or Translit(model.charset)
    src_chars = sorted(set(model.charset))

    # One symbolic feature value + segment per source grapheme; representation is its token.
    symbols = "".join(f'<Symbol id="seg_{i}">v{i}</Symbol>' for i in range(len(src_chars)))
    segdefs = "".join(
        f'<SegmentDefinition id="cd_{i}"><Representations><Representation>{escape(tl.fwd[c])}'
        f'</Representation></Representations><FeatureValue feature="seg" '
        f'symbolValues="seg_{i}" /></SegmentDefinition>'
        for i, c in enumerate(src_chars)
    )
    anyseg = "".join(f'<Segment segment="cd_{i}" />' for i in range(len(src_chars)))
    default_sym = "seg_0"

    entries = []
    for i, e in enumerate(model.lexicon):
        eid = _xid("e", i)
        entries.append(
            f'<LexicalEntry id="{eid}" partOfSpeech="root"><Allomorphs>'
            f'<Allomorph id="{eid}a"><PhoneticShape>{escape(tl.enc(e.form))}</PhoneticShape></Allomorph>'
            f'</Allomorphs><Gloss>{escape(e.gloss)}</Gloss></LexicalEntry>'
        )

    rules = []
    rule_ids = []
    for i, a in enumerate(model.affixes):
        rid = _xid("r", i)
        rule_ids.append(rid)
        stem = (
            '<PhoneticSequence id="st"><OptionalSegmentSequence min="1" max="-1">'
            '<SimpleContext naturalClass="any" /></OptionalSegmentSequence></PhoneticSequence>'
        )
        ins = f"<InsertSegments><PhoneticShape>{escape(tl.enc(a.form))}</PhoneticShape></InsertSegments>"
        copy = '<CopyFromInput index="st" />'
        out = (ins + copy) if a.kind == "prefix" else (copy + ins)
        rules.append(
            f'<MorphologicalRule id="{rid}" requiredPartsOfSpeech="root" outputPartOfSpeech="root">'
            f"<Name>{escape(a.gloss)}</Name><MorphologicalSubrules>"
            f'<MorphologicalSubrule id="{rid}s"><MorphologicalInput>{stem}</MorphologicalInput>'
            f"<MorphologicalOutput>{out}</MorphologicalOutput></MorphologicalSubrule>"
            f"</MorphologicalSubrules><Gloss>{escape(a.gloss)}</Gloss></MorphologicalRule>"
        )

    # Best-practice morphotactics: group affix rules into ordered position-class slots
    # (an HC AffixTemplate), one filler per slot, slots in inner->outer order — instead of the
    # flat, unordered, arbitrarily-stacking rule list of v1. This is the affix-template/slot model
    # (MoInflAffixTemplate/MoInflAffixSlot) and is what collapses the over-generation.
    if templated and model.affixes:
        # Known slots come from affixes carrying explicit (gold) slot evidence; an affix with no
        # evidence (e.g. an agent-proposed one) is placed leniently in every known slot on its side.
        known: dict[str, set[int]] = {"suffix": set(), "prefix": set()}
        for a in model.affixes:
            for sd, o in a.slots:
                known[sd].add(o)
        slot_rules: dict[tuple[str, int], list[str]] = {}
        for i, a in enumerate(model.affixes):
            targets = a.slots or tuple((a.kind, o) for o in sorted(known.get(a.kind, {a.slot_ord})) or [a.slot_ord])
            for slot in (targets or (a.slot,)):
                slot_rules.setdefault(slot, []).append(rule_ids[i])
        suffix_ords = sorted(o for (s, o) in slot_rules if s == "suffix")
        prefix_ords = sorted(o for (s, o) in slot_rules if s == "prefix")
        slots_xml = ""
        for side, ords in (("suffix", suffix_ords), ("prefix", prefix_ords)):
            for o in ords:
                rids = " ".join(slot_rules[(side, o)])
                slots_xml += (f'<Slot optional="true" morphologicalRules="{rids}">'
                              f'<Name>{side}{o}</Name></Slot>')
        template_xml = ('<AffixTemplates><AffixTemplate final="true" requiredPartsOfSpeech="root">'
                        f'<Name>main</Name>{slots_xml}</AffixTemplate></AffixTemplates>')
        stratum_open = '<Stratum characterDefinitionTable="t1" morphologicalRuleOrder="linear"><Name>main</Name>'
    else:
        template_xml = ""
        stratum_open = ('<Stratum characterDefinitionTable="t1" morphologicalRuleOrder="unordered" '
                        f'morphologicalRules="{" ".join(rule_ids)}"><Name>main</Name>')

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<HermitCrabInput><Language><Name>" + escape(model.code) + "</Name>"
        '<PartsOfSpeech><PartOfSpeech id="root"><Name>root</Name></PartOfSpeech></PartsOfSpeech>'
        f'<PhonologicalFeatureSystem><SymbolicFeature id="seg" defaultSymbol="{default_sym}">'
        f"<Name>seg</Name><Symbols>{symbols}</Symbols></SymbolicFeature></PhonologicalFeatureSystem>"
        f'<CharacterDefinitionTable id="t1"><Name>main</Name><SegmentDefinitions>{segdefs}'
        "</SegmentDefinitions></CharacterDefinitionTable>"
        f'<NaturalClasses><SegmentNaturalClass id="any"><Name>any</Name>{anyseg}'
        "</SegmentNaturalClass></NaturalClasses>"
        f"<Strata>{stratum_open}"
        f"<MorphologicalRuleDefinitions>{''.join(rules)}</MorphologicalRuleDefinitions>"
        f"{template_xml}"
        f"<LexicalEntries>{''.join(entries)}</LexicalEntries>"
        "</Stratum></Strata></Language></HermitCrabInput>"
    )


_PARSING = re.compile(r'^Parsing "(.*)"$')


def _parse_output(text: str, tl: Translit) -> dict[str, list[Analysis]]:
    """Parse the ``hc`` output file into {word: [analysis, ...]}, decoding transliteration."""
    results: dict[str, list[Analysis]] = {}
    cur: str | None = None
    morphs: list[str] | None = None
    for line in text.splitlines():
        m = _PARSING.match(line.strip())
        if m:
            cur = tl.dec(m.group(1))
            results.setdefault(cur, [])
            morphs = None
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("Morphs:"):
            morphs = [tl.dec(t) for t in s[len("Morphs:"):].split()]
        elif s.startswith("Gloss:") and morphs is not None:
            glosses = s[len("Gloss:"):].split()
            if len(morphs) == len(glosses):
                results[cur].append(list(zip(morphs, glosses)))
            morphs = None
    return results


def run_parse(
    model: LangModel,
    words: list[str],
    timeout: int = 600,
    chunk_size: int = 25,
    chunk_timeout: int = 45,
    templated: bool = True,
) -> dict[str, list[Analysis]]:
    """Parse ``words`` (underlying forms) with the emitted grammar; return analyses.

    Parsing is chunked with a per-chunk timeout. High-affix grammars (e.g. Tsez, Uspanteko)
    make HC's unconstrained search explode on some words; chunking bounds time AND memory
    (the timed-out ``hc`` process is killed) and localizes the loss — words in a timed-out
    chunk are simply returned with no analyses (counted as unparsed). This is the scaling
    signal that motivates the affix-template/ordering enrichment.
    """
    tl = Translit(model.charset)
    xml = build_grammar_xml(model, tl, templated=templated)
    uniq = list(dict.fromkeys(words))
    results: dict[str, list[Analysis]] = {w: [] for w in uniq}
    with tempfile.TemporaryDirectory() as d:
        cfg = Path(d) / "g.xml"
        cfg.write_text(xml, encoding="utf-8")
        for start in range(0, len(uniq), chunk_size):
            chunk = uniq[start : start + chunk_size]
            scr = Path(d) / "s.txt"
            out = Path(d) / "o.txt"
            out.write_text("", encoding="utf-8")
            scr.write_text("\n".join(f"parse {tl.enc(w)}" for w in chunk) + "\n", encoding="utf-8")
            try:
                subprocess.run(
                    [HC_EXE, "-i", str(cfg), "-s", str(scr), "-o", str(out), "-c"],
                    env=_ENV, capture_output=True, timeout=min(chunk_timeout, timeout),
                )
            except subprocess.TimeoutExpired:
                continue  # chunk's words stay unparsed
            results.update(_parse_output(out.read_text(encoding="utf-8"), tl))
    return results


@dataclass
class RoundTrip:
    n: int
    recall: float           # gold analysis present among parses
    parsed: float           # produced at least one parse
    mean_ambiguity: float   # mean #parses over words that parsed
    unparsed: list[str]

    def as_dict(self) -> dict:
        return {
            "n": self.n, "recall": round(self.recall, 4), "parsed": round(self.parsed, 4),
            "mean_ambiguity": round(self.mean_ambiguity, 2), "n_unparsed": len(self.unparsed),
        }


def gloss_seq(analysis: Analysis) -> tuple[str, ...]:
    """The gloss line of an analysis — the reliable, linguistically-meaningful target.

    (HermitCrab.NET's echoed morph *forms* are corrupted by a segment-reindexing bug, but
    its Gloss line is exact; reconstructing the gloss line is also precisely the
    agent-proposal reward — 'do the proposed lexemes make HC gloss the held-out forms right'.)
    """
    return tuple(g for _, g in analysis)


def round_trip(model: LangModel, gold: list[tuple[str, Analysis]], timeout: int = 600,
               templated: bool = True) -> RoundTrip:
    """Score the grammar: does each gold (underlying form -> gloss line) round-trip?"""
    words = [w for w, _ in gold]
    parses = run_parse(model, words, timeout=timeout, templated=templated)
    hits = produced = amb_total = 0
    unparsed: list[str] = []
    for w, analysis in gold:
        got = parses.get(w, [])
        if got:
            produced += 1
            amb_total += len(got)
        else:
            unparsed.append(w)
        if gloss_seq(analysis) in {gloss_seq(a) for a in got}:
            hits += 1
    n = len(gold)
    return RoundTrip(
        n=n,
        recall=hits / n if n else 0.0,
        parsed=produced / n if n else 0.0,
        mean_ambiguity=amb_total / produced if produced else 0.0,
        unparsed=unparsed,
    )
