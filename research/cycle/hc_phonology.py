"""Emit a feature-bearing Hermit Crab grammar with archiphonemes + vowel-harmony rules, and verify it.

Phase 1 task 1.1 of the phonology-induction loop. Where `cycle/phonology.py` *proposes* a collapse
(an archiphoneme like `lAr`/`nIn` over a conditioning class), this module turns that into an actual HC
grammar and checks the collapse **round-trips through `hc`**: one archiphoneme affix + a harmony rule
must parse every surface allomorph back to the same morpheme + gloss.

The representation is the one verified against `hc.exe` (answering the design's open question): each
vowel carries real distinctive features (`hi`, `rnd`, `back`); an **archiphoneme** is a vowel left
*underspecified* for the harmonizing feature(s); harmony is HC's native **alpha-variable** rule
(`VariableFeature` + `AlphaVariable`) that copies the feature from the nearest left vowel. Consonants
get a unique identity feature (`cid`) so HC renders distinct morph forms.

Representations are ASCII (HC corrupts non-ASCII output rendering). Vowel ASCII bundles:
``a=[lo,unr,bk] e=[lo,unr,fr] i=[hi,unr,fr] y=[hi,unr,bk] u=[hi,rnd,bk] w=[hi,rnd,fr]``;
archiphonemes ``A=[lo,unr,back?]`` and ``I=[hi,back?,round?]``.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

HC_EXE = os.path.expanduser(os.path.join("~", ".dotnet", "tools", "hc.exe"))
_ENV = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}

Analysis = list[tuple[str, str]]  # [(morph_form, gloss), ...]

# Verified ASCII demo inventory. segment -> (voc, hi, rnd, back); None = underspecified archiphoneme.
DEFAULT_VOWELS: dict[str, tuple[str, str | None, str | None, str | None]] = {
    "a": ("vow", "lo", "unr", "bk"),
    "e": ("vow", "lo", "unr", "fr"),
    "i": ("vow", "hi", "unr", "fr"),
    "y": ("vow", "hi", "unr", "bk"),
    "u": ("vow", "hi", "rnd", "bk"),
    "w": ("vow", "hi", "rnd", "fr"),
    "A": ("vow", "lo", "unr", None),   # low archiphoneme: backness varies
    "I": ("vow", "hi", None, None),    # high archiphoneme: backness + rounding vary
}
DEFAULT_CONSONANTS: tuple[str, ...] = ("l", "r", "t", "v", "n", "g", "z")

# Spanish phoneme→feature inventory (the per-language table that closes the "#1 gap" for spa). Spanish
# is a transparent five-vowel system, so the table is read straight off the orthography — no audio
# needed. Each vowel is uniquely identified by (hi, rnd, back) in the existing binary feature system;
# mid e/o map to `lo` (non-high) and are kept distinct from `a` by backness/rounding. Accented vowels
# (á é í ó ú) are stress marks over the same qualities → fold to their base vowel before lookup.
# Representations stay ASCII (HC corrupts non-ASCII output); ñ is therefore out of the HC-round-trip set.
SPANISH_VOWELS: dict[str, tuple[str, str | None, str | None, str | None]] = {
    "a": ("vow", "lo", "unr", "bk"),
    "e": ("vow", "lo", "unr", "fr"),
    "i": ("vow", "hi", "unr", "fr"),
    "o": ("vow", "lo", "rnd", "bk"),
    "u": ("vow", "hi", "rnd", "bk"),
}
SPANISH_CONSONANTS: tuple[str, ...] = tuple("bcdfghjklmnpqrstvwxyz")
SPANISH_ACCENTS = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}


def fold_spanish_accents(word: str) -> str:
    """Strip Spanish stress accents to base vowels (for HC-safe, ASCII segment lookup)."""
    return "".join(SPANISH_ACCENTS.get(c, c) for c in word)


def spanish_phon_feats(charset: set[str] | str) -> dict[str, dict[str, str]]:
    """Per-grapheme phonological-feature map for the live cycle (golden.hc.build_grammar_xml `phon_feats`).

    Only vowels (incl. accented vowels, which fold to their base quality) get features here; every other
    grapheme is left out and the grammar builder treats it as a consonant identity. This is the Spanish
    inventory wired into the live loop — real voc/hi/rnd/back features instead of one fake feature per
    character, so natural classes (vowel/front/high) exist for future rules.
    """
    feats: dict[str, dict[str, str]] = {}
    for ch in set(charset):
        base = SPANISH_ACCENTS.get(ch, ch)
        bundle = SPANISH_VOWELS.get(base)
        if bundle is None:
            continue
        voc, hi, rnd, bk = bundle
        d = {"voc": voc}
        if hi:
            d["hi"] = hi
        if rnd:
            d["rnd"] = rnd
        if bk:
            d["back"] = bk
        feats[ch] = d
    return feats


@dataclass(frozen=True)
class Affix:
    """A suffix whose phonetic shape may contain archiphoneme symbols (e.g. ``lAr``, ``In``)."""

    id: str
    form: str
    gloss: str


def hc_available() -> bool:
    """True if the Hermit Crab CLI is installed (so callers can skip gracefully when it is not)."""
    return Path(HC_EXE).exists()


def build_harmony_grammar(
    roots: list[tuple[str, str]],
    affixes: list[Affix],
    *,
    vowels: dict[str, tuple[str, str | None, str | None, str | None]] | None = None,
    consonants: tuple[str, ...] = DEFAULT_CONSONANTS,
    include_harmony_rules: bool = True,
    extra_phon_rules: list[tuple[str, str]] | None = None,
) -> str:
    """Build a HC grammar string: feature system + segments + natural classes + lexicon + affixes.

    With ``include_harmony_rules`` (default) it also emits the alpha-variable backness/rounding harmony
    rules. Set it False for a language with **no** vowel harmony (e.g. Spanish): you still get the real
    feature-bearing segment inventory and natural classes, but no rule that would wrongly harmonize
    vowels — a clean concatenative grammar that future, language-specific rules can build on.

    ``extra_phon_rules`` injects additional phonological rules as ``(rule_id, rule_xml)`` pairs (e.g. the
    Spanish ``-s/-es`` epenthesis rule) — appended to the rule defs and the stratum's ordered rule list.
    """
    vowels = vowels or DEFAULT_VOWELS
    cid_syms = "".join(f'<Symbol id="c_{c}">{escape(c)}</Symbol>' for c in consonants)

    seg_defs: list[str] = []
    for ch, (voc, hi, rnd, bk) in vowels.items():
        fvs = [f'<FeatureValue feature="voc" symbolValues="{voc}"/>']
        if hi is not None:
            fvs.append(f'<FeatureValue feature="hi" symbolValues="{hi}"/>')
        if rnd is not None:
            fvs.append(f'<FeatureValue feature="rnd" symbolValues="{rnd}"/>')
        if bk is not None:
            fvs.append(f'<FeatureValue feature="back" symbolValues="{bk}"/>')
        seg_defs.append(
            f'<SegmentDefinition id="s_{ch}"><Representations><Representation>{escape(ch)}</Representation>'
            f'</Representations>{"".join(fvs)}</SegmentDefinition>'
        )
    for ch in consonants:
        seg_defs.append(
            f'<SegmentDefinition id="s_{ch}"><Representations><Representation>{escape(ch)}</Representation>'
            f'</Representations><FeatureValue feature="voc" symbolValues="cons"/>'
            f'<FeatureValue feature="cid" symbolValues="c_{ch}"/></SegmentDefinition>'
        )
    any_segs = "".join(f'<Segment segment="s_{s}"/>' for s in (list(vowels) + list(consonants)))

    morph_rules: list[str] = []
    for a in affixes:
        morph_rules.append(
            f'<MorphologicalRule id="{a.id}" requiredPartsOfSpeech="root" outputPartOfSpeech="root">'
            f"<Name>{escape(a.gloss)}</Name><MorphologicalSubrules>"
            f'<MorphologicalSubrule id="{a.id}_s"><MorphologicalInput>'
            f'<PhoneticSequence id="{a.id}_st"><OptionalSegmentSequence min="1" max="-1">'
            f'<SimpleContext naturalClass="any"/></OptionalSegmentSequence></PhoneticSequence>'
            f'</MorphologicalInput><MorphologicalOutput><CopyFromInput index="{a.id}_st"/>'
            f"<InsertSegments><PhoneticShape>{escape(a.form)}</PhoneticShape></InsertSegments>"
            f"</MorphologicalOutput></MorphologicalSubrule></MorphologicalSubrules>"
            f"<Gloss>{escape(a.gloss)}</Gloss></MorphologicalRule>"
        )
    lex = "".join(
        f'<LexicalEntry id="e_{i}" partOfSpeech="root"><Allomorphs>'
        f'<Allomorph id="e_{i}_a"><PhoneticShape>{escape(form)}</PhoneticShape></Allomorph>'
        f"</Allomorphs><Gloss>{escape(gloss)}</Gloss></LexicalEntry>"
        for i, (form, gloss) in enumerate(roots)
    )
    rule_ids = " ".join(a.id for a in affixes)

    harmony_rule_defs = """
      <PhonologicalRule id="r_back" multipleApplicationOrder="leftToRightIterative">
        <Name>backness harmony</Name>
        <VariableFeatures><VariableFeature id="va" name="a" phonologicalFeature="back"/></VariableFeatures>
        <PhoneticInput><PhoneticSequence><SimpleContext naturalClass="nc_vow"/></PhoneticSequence></PhoneticInput>
        <PhonologicalSubrules><PhonologicalSubrule>
          <PhoneticOutput><PhoneticSequence>
            <SimpleContext naturalClass="nc_vow"><AlphaVariables><AlphaVariable variableFeature="va"/></AlphaVariables></SimpleContext>
          </PhoneticSequence></PhoneticOutput>
          <Environment><LeftEnvironment><PhoneticTemplate><PhoneticSequence>
            <SimpleContext naturalClass="nc_vow"><AlphaVariables><AlphaVariable variableFeature="va"/></AlphaVariables></SimpleContext>
            <OptionalSegmentSequence min="0" max="-1"><SimpleContext naturalClass="nc_cons"/></OptionalSegmentSequence>
          </PhoneticSequence></PhoneticTemplate></LeftEnvironment></Environment>
        </PhonologicalSubrule></PhonologicalSubrules>
      </PhonologicalRule>
      <PhonologicalRule id="r_round" multipleApplicationOrder="leftToRightIterative">
        <Name>rounding harmony</Name>
        <VariableFeatures><VariableFeature id="vb" name="b" phonologicalFeature="rnd"/></VariableFeatures>
        <PhoneticInput><PhoneticSequence><SimpleContext naturalClass="nc_high"/></PhoneticSequence></PhoneticInput>
        <PhonologicalSubrules><PhonologicalSubrule>
          <PhoneticOutput><PhoneticSequence>
            <SimpleContext naturalClass="nc_high"><AlphaVariables><AlphaVariable variableFeature="vb"/></AlphaVariables></SimpleContext>
          </PhoneticSequence></PhoneticOutput>
          <Environment><LeftEnvironment><PhoneticTemplate><PhoneticSequence>
            <SimpleContext naturalClass="nc_vow"><AlphaVariables><AlphaVariable variableFeature="vb"/></AlphaVariables></SimpleContext>
            <OptionalSegmentSequence min="0" max="-1"><SimpleContext naturalClass="nc_cons"/></OptionalSegmentSequence>
          </PhoneticSequence></PhoneticTemplate></LeftEnvironment></Environment>
        </PhonologicalSubrule></PhonologicalSubrules>
      </PhonologicalRule>""" if include_harmony_rules else ""
    phon_rule_ids = "r_back r_round" if include_harmony_rules else ""
    if extra_phon_rules:
        harmony_rule_defs += "".join(xml for _, xml in extra_phon_rules)
        phon_rule_ids = (phon_rule_ids + " " + " ".join(rid for rid, _ in extra_phon_rules)).strip()

    return f"""<?xml version="1.0" encoding="utf-8"?>
<HermitCrabInput>
  <Language>
    <Name>harmony</Name>
    <PartsOfSpeech><PartOfSpeech id="root"><Name>root</Name></PartOfSpeech></PartsOfSpeech>
    <PhonologicalFeatureSystem>
      <SymbolicFeature id="voc" defaultSymbol="cons"><Name>voc</Name>
        <Symbols><Symbol id="vow">vowel</Symbol><Symbol id="cons">consonant</Symbol></Symbols></SymbolicFeature>
      <SymbolicFeature id="hi"><Name>hi</Name>
        <Symbols><Symbol id="hi">high</Symbol><Symbol id="lo">low</Symbol></Symbols></SymbolicFeature>
      <SymbolicFeature id="rnd"><Name>rnd</Name>
        <Symbols><Symbol id="rnd">round</Symbol><Symbol id="unr">unround</Symbol></Symbols></SymbolicFeature>
      <SymbolicFeature id="back"><Name>back</Name>
        <Symbols><Symbol id="bk">back</Symbol><Symbol id="fr">front</Symbol></Symbols></SymbolicFeature>
      <SymbolicFeature id="cid"><Name>cid</Name><Symbols>{cid_syms}</Symbols></SymbolicFeature>
    </PhonologicalFeatureSystem>
    <CharacterDefinitionTable id="t1"><Name>main</Name>
      <SegmentDefinitions>{"".join(seg_defs)}</SegmentDefinitions></CharacterDefinitionTable>
    <NaturalClasses>
      <FeatureNaturalClass id="nc_vow"><Name>vowel</Name><FeatureValue feature="voc" symbolValues="vow"/></FeatureNaturalClass>
      <FeatureNaturalClass id="nc_cons"><Name>cons</Name><FeatureValue feature="voc" symbolValues="cons"/></FeatureNaturalClass>
      <FeatureNaturalClass id="nc_high"><Name>high</Name><FeatureValue feature="voc" symbolValues="vow"/><FeatureValue feature="hi" symbolValues="hi"/></FeatureNaturalClass>
      <SegmentNaturalClass id="any"><Name>any</Name>{any_segs}</SegmentNaturalClass>
    </NaturalClasses>
    <PhonologicalRuleDefinitions>{harmony_rule_defs}
    </PhonologicalRuleDefinitions>
    <Strata>
      <Stratum characterDefinitionTable="t1" morphologicalRuleOrder="unordered"
               phonologicalRules="{phon_rule_ids}" morphologicalRules="{rule_ids}">
        <Name>main</Name>
        <MorphologicalRuleDefinitions>{"".join(morph_rules)}</MorphologicalRuleDefinitions>
        <LexicalEntries>{lex}</LexicalEntries>
      </Stratum>
    </Strata>
  </Language>
</HermitCrabInput>
"""


_PARSING = re.compile(r'^Parsing "(.*)"$')


def _parse_output(text: str) -> dict[str, list[Analysis]]:
    results: dict[str, list[Analysis]] = {}
    cur: str | None = None
    morphs: list[str] | None = None
    for line in text.splitlines():
        m = _PARSING.match(line.strip())
        if m:
            cur = m.group(1)
            results.setdefault(cur, [])
            morphs = None
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("Morphs:"):
            morphs = s[len("Morphs:"):].split()
        elif s.startswith("Gloss:") and morphs is not None:
            glosses = s[len("Gloss:"):].split()
            n = min(len(morphs), len(glosses))
            results[cur].append(list(zip(morphs[:n], glosses[:n])))
            morphs = None
    return results


def run_parse(xml: str, words: list[str], *, timeout: int = 60) -> dict[str, list[Analysis]]:
    """Parse ``words`` with the given grammar via the `hc` CLI. Requires :func:`hc_available`."""
    uniq = list(dict.fromkeys(words))
    with tempfile.TemporaryDirectory() as d:
        cfg, scr, out = Path(d) / "g.xml", Path(d) / "s.txt", Path(d) / "o.txt"
        cfg.write_text(xml, encoding="utf-8")
        scr.write_text("\n".join(f"parse {w}" for w in uniq) + "\n", encoding="utf-8")
        out.write_text("", encoding="utf-8")
        subprocess.run(
            [HC_EXE, "-i", str(cfg), "-s", str(scr), "-o", str(out), "-c"],
            env=_ENV, capture_output=True, timeout=timeout,
        )
        return _parse_output(out.read_text(encoding="utf-8"))


def collapse_round_trips(
    roots: list[tuple[str, str]],
    affix: Affix,
    surface_to_gloss: dict[str, str],
    *,
    timeout: int = 60,
) -> bool:
    """True iff one archiphoneme ``affix`` + the harmony rules parse every surface to the expected gloss.

    This is the HC-gated form of the collapse gate: a family of surface allomorphs is replaced by a
    single archiphoneme morpheme, and the grammar must still analyze each surface (coverage holds with
    one morpheme instead of many).
    """
    xml = build_harmony_grammar(roots, [affix])
    parsed = run_parse(xml, list(surface_to_gloss), timeout=timeout)
    for surface, expected_gloss in surface_to_gloss.items():
        analyses = parsed.get(surface, [])
        if not analyses:
            return False
        glosses = {" ".join(g for _, g in a) for a in analyses}
        if expected_gloss not in glosses:
            return False
    return True
