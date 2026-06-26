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


def _phon_feature_xml(
    src_chars: list[str], phon_feats: dict[str, dict[str, str]] | None
) -> tuple[str, dict[str, str], str]:
    """Build (feature-system defs, per-grapheme extra FeatureValues, natural-class defs) for a real
    phonological feature inventory. Vowels carry voc/hi/rnd/back (from ``phon_feats``); every other
    grapheme becomes a consonant with a unique ``cid`` identity. Returns empty strings when no
    inventory is given (the original, identity-only behaviour)."""
    if not phon_feats:
        return "", {}, ""
    consonants = [c for c in src_chars if c not in phon_feats]
    cid_syms = "".join(f'<Symbol id="c_{i}">{escape(c)}</Symbol>' for i, c in enumerate(consonants))
    feature_defs = (
        '<SymbolicFeature id="voc" defaultSymbol="cons"><Name>voc</Name><Symbols>'
        '<Symbol id="vow">vowel</Symbol><Symbol id="cons">consonant</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="hi"><Name>hi</Name><Symbols>'
        '<Symbol id="hi">high</Symbol><Symbol id="lo">low</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="rnd"><Name>rnd</Name><Symbols>'
        '<Symbol id="rnd">round</Symbol><Symbol id="unr">unround</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="back"><Name>back</Name><Symbols>'
        '<Symbol id="bk">back</Symbol><Symbol id="fr">front</Symbol></Symbols></SymbolicFeature>'
        f'<SymbolicFeature id="cid"><Name>cid</Name><Symbols>{cid_syms}</Symbols></SymbolicFeature>'
    )
    seg_extra: dict[str, str] = {}
    for c, feats in phon_feats.items():
        seg_extra[c] = "".join(
            f'<FeatureValue feature="{f}" symbolValues="{v}" />' for f, v in feats.items()
        )
    for i, c in enumerate(consonants):
        seg_extra[c] = (
            '<FeatureValue feature="voc" symbolValues="cons" />'
            f'<FeatureValue feature="cid" symbolValues="c_{i}" />'
        )
    nat = (
        '<FeatureNaturalClass id="nc_vow"><Name>vowel</Name>'
        '<FeatureValue feature="voc" symbolValues="vow"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_cons"><Name>cons</Name>'
        '<FeatureValue feature="voc" symbolValues="cons"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_front"><Name>front</Name>'
        '<FeatureValue feature="voc" symbolValues="vow"/><FeatureValue feature="back" symbolValues="fr"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_high"><Name>high</Name>'
        '<FeatureValue feature="voc" symbolValues="vow"/><FeatureValue feature="hi" symbolValues="hi"/></FeatureNaturalClass>'
    )
    return feature_defs, seg_extra, nat


def _glide_substrate(src_chars: list[str], block_vowels: frozenset = frozenset()):
    """Feature substrate that lets the GLIDE RULE live in the main grammar. The rule desyllabifies a high
    vowel before a vowel (u→w, i→y), which requires the high vowel and its glide to be identified by
    PHONOLOGICAL features (hi/rnd/back/syl) — NOT by the per-grapheme `seg` identity (under `seg`, u→[-syl]
    can't become w because they have distinct seg ids). So vowels/glides drop `seg` and carry phon features;
    consonants keep `seg` + voc=cons. Returns (feature_defs, segfv_by_char, cons_voc_by_char, nat_classes)
    or None if the inventory lacks vowels or glides. Only valid when no other phon_feats inventory is set."""
    from engine.hc_collapse import GLIDE_OF, VOWELS
    src_of = {g: v for v, g in GLIDE_OF.items()}
    vowels = [c for c in src_chars if c in VOWELS]
    glides = [c for c in src_chars if c in src_of and src_of[c] in VOWELS]
    if not vowels or not glides:
        return None
    feature_defs = (
        '<SymbolicFeature id="voc" defaultSymbol="cons"><Name>voc</Name><Symbols>'
        '<Symbol id="vow">vowel</Symbol><Symbol id="cons">consonant</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="hi"><Name>hi</Name><Symbols><Symbol id="hi">high</Symbol>'
        '<Symbol id="lo">low</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="rnd"><Name>rnd</Name><Symbols><Symbol id="rnd">round</Symbol>'
        '<Symbol id="unr">unround</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="back"><Name>back</Name><Symbols><Symbol id="bk">back</Symbol>'
        '<Symbol id="fr">front</Symbol></Symbols></SymbolicFeature>'
        '<SymbolicFeature id="syl" defaultSymbol="plus"><Name>syl</Name><Symbols>'
        '<Symbol id="plus">syllabic</Symbol><Symbol id="minus">nonsyllabic</Symbol></Symbols></SymbolicFeature>'
    )

    def vfv(c, syl):
        hi, rnd, bk = VOWELS[c]
        return (f'<FeatureValue feature="voc" symbolValues="vow" /><FeatureValue feature="hi" symbolValues="{hi}" />'
                f'<FeatureValue feature="rnd" symbolValues="{rnd}" /><FeatureValue feature="back" symbolValues="{bk}" />'
                f'<FeatureValue feature="syl" symbolValues="{syl}" />')

    segfv = {v: vfv(v, "plus") for v in vowels}
    segfv.update({g: vfv(src_of[g], "minus") for g in glides})
    cons_voc = {c: '<FeatureValue feature="voc" symbolValues="cons" />'
                for c in src_chars if c not in vowels and c not in glides}
    nat = (
        '<FeatureNaturalClass id="nc_syl"><Name>syllabic</Name><FeatureValue feature="voc" symbolValues="vow"/>'
        '<FeatureValue feature="syl" symbolValues="plus"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_high_syl"><Name>high syllabic</Name><FeatureValue feature="voc" symbolValues="vow"/>'
        '<FeatureValue feature="hi" symbolValues="hi"/><FeatureValue feature="syl" symbolValues="plus"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_glide_out"><Name>nonsyllabic</Name>'
        '<FeatureValue feature="syl" symbolValues="minus"/></FeatureNaturalClass>'
    )
    trigger_idx = ""           # CONDITIONED rule: right env = vowels minus the blocker(s) (e.g. not before u)
    if block_vowels:
        trig = [c for c in vowels if c not in block_vowels]
        cd = {c: i for i, c in enumerate(src_chars)}
        trig_segs = "".join(f'<Segment segment="cd_{cd[v]}" />' for v in trig if v in cd)
        nat += f'<SegmentNaturalClass id="nc_trigger"><Name>trigger</Name>{trig_segs}</SegmentNaturalClass>'
        trigger_idx = "nc_trigger"
    return feature_defs, segfv, cons_voc, nat, trigger_idx


def build_grammar_xml(
    model: LangModel,
    tl: Translit | None = None,
    templated: bool = True,
    phon_feats: dict[str, dict[str, str]] | None = None,
    pos_aware: bool = False,
    phon_rules: list[tuple[str, str]] | None = None,
    glide_rule: bool = False,
    glide_block_vowels: frozenset = frozenset(),
    conditioned_affixes: list[dict] | None = None,
) -> str:
    """Emit the HC grammar. With ``phon_feats`` (grapheme -> {feature: symbolValue}, e.g. a Spanish
    inventory mapping vowels to voc/hi/rnd/back), each segment carries REAL phonological features
    *in addition to* its unique ``seg`` identity, and real natural classes (vowel/cons/front/high)
    are emitted — the feature-bearing substrate future phonological rules need. Default ``None`` keeps
    the original behaviour byte-for-byte (one identity feature per grapheme, single ``any`` class).

    With ``pos_aware``, the grammar emits the real parts of speech (``LexEntry.pos``), tags each root,
    and gives each affix rule an MSA: it attaches to its ``req_pos`` (output = same, an inflectional
    category-preserving rule) or, if unrestricted, to any POS (output left unchanged). Default off keeps
    the single ``root`` POS."""
    # include any chars used only by conditioned-affix shapes, so Translit never silently drops them (a
    # dropped char yields an empty InsertSegments, which crashes hc.exe — see the HC NRE bug report).
    _extra_chars = {ch for ca in (conditioned_affixes or []) for al in ca.get("allomorphs", []) for ch in al.get("shape", "")}
    tl = tl or Translit(sorted(set(model.charset) | _extra_chars))
    src_chars = sorted(set(model.charset) | _extra_chars)
    pos_list = sorted({e.pos for e in model.lexicon if e.pos}) if pos_aware else ["root"]
    if not pos_list:
        pos_list = ["root"]
    all_pos_attr = " ".join(pos_list)

    # One symbolic feature value + segment per source grapheme; representation is its token. The `seg`
    # identity feature guarantees HC never merges distinct graphemes (incl. á vs a, which share
    # phonological features) — so it stays even when real features are layered on.
    symbols = "".join(f'<Symbol id="seg_{i}">v{i}</Symbol>' for i in range(len(src_chars)))
    extra_feature_defs, seg_extra_fvs, extra_nat_classes = _phon_feature_xml(src_chars, phon_feats)

    # GLIDE RULE substrate (live morphophonology): vowels/glides identified by phon features (drop `seg` so
    # u→w can fire); consonants keep `seg`. Only when no other inventory is set (avoids double feature defs).
    glide_sub = _glide_substrate(src_chars, glide_block_vowels) if (glide_rule and not phon_feats) else None
    g_segfv, g_consvoc = ({}, {})
    if glide_sub:
        g_featdefs, g_segfv, g_consvoc, g_nat, g_trigger = glide_sub
        from engine.hc_collapse import glide_rule_xml
        extra_feature_defs += g_featdefs
        extra_nat_classes += g_nat
        phon_rules = list(phon_rules or []) + [glide_rule_xml(right_env_class=g_trigger or "nc_syl")]

    # CONDITIONED-ALLOMORPH substrate (morpheme-scoped collapse): a light voc=vow/cons feature so an affix's
    # subrule can select its allomorph by the stem's first-segment class (vy- before a vowel, vi- elsewhere)
    # — no global rule, so other classes (mi-) are untouched. Only when no other inventory owns voc.
    voc_fv: dict = {}
    if conditioned_affixes and not glide_sub and not phon_feats:
        _VOW = set("aeiou")
        voc_fv = {c: ('<FeatureValue feature="voc" symbolValues="vow" />' if c in _VOW
                      else '<FeatureValue feature="voc" symbolValues="cons" />') for c in src_chars}
        extra_feature_defs += ('<SymbolicFeature id="voc" defaultSymbol="cons"><Name>voc</Name><Symbols>'
                               '<Symbol id="vow">vowel</Symbol><Symbol id="cons">consonant</Symbol>'
                               '</Symbols></SymbolicFeature>')
        extra_nat_classes += ('<FeatureNaturalClass id="nc_vow"><Name>vow</Name>'
                              '<FeatureValue feature="voc" symbolValues="vow"/></FeatureNaturalClass>')

    def _seg_fv(i: int, c: str) -> str:
        if c in g_segfv:                              # vowel/glide → phon features, no seg identity
            return g_segfv[c]
        return (f'<FeatureValue feature="seg" symbolValues="seg_{i}" />'
                + g_consvoc.get(c, "") + voc_fv.get(c, "") + seg_extra_fvs.get(c, ""))

    segdefs = "".join(
        f'<SegmentDefinition id="cd_{i}"><Representations><Representation>{escape(tl.fwd[c])}'
        f'</Representation></Representations>{_seg_fv(i, c)}</SegmentDefinition>'
        for i, c in enumerate(src_chars)
    )
    anyseg = "".join(f'<Segment segment="cd_{i}" />' for i in range(len(src_chars)))
    default_sym = "seg_0"

    entries = []
    for i, e in enumerate(model.lexicon):
        eid = _xid("e", i)
        ep = (e.pos or "root") if pos_aware else "root"
        # One <Allomorph> per stem shape (citation form + any irregular allomorphs) — HC's native
        # multi-allomorph entry (MoStemAllomorph). De-duped, order preserved.
        shapes = list(dict.fromkeys([e.form, *e.allomorphs]))
        allos = "".join(
            f'<Allomorph id="{eid}a{j}"><PhoneticShape>{escape(tl.enc(s))}</PhoneticShape></Allomorph>'
            for j, s in enumerate(shapes)
        )
        entries.append(
            f'<LexicalEntry id="{eid}" partOfSpeech="{ep}"><Allomorphs>{allos}'
            f'</Allomorphs><Gloss>{escape(e.gloss)}</Gloss></LexicalEntry>'
        )

    rules = []
    rule_ids = []
    for i, a in enumerate(model.affixes):
        rid = _xid("r", i)
        rule_ids.append(rid)
        ins = f"<InsertSegments><PhoneticShape>{escape(tl.enc(a.form))}</PhoneticShape></InsertSegments>"
        if a.kind == "infix":
            # infix splits the stem after its first segment: copy(seg1) + insert + copy(rest).
            minput = (
                '<PhoneticSequence id="st1"><SimpleContext naturalClass="any" /></PhoneticSequence>'
                '<PhoneticSequence id="st2"><OptionalSegmentSequence min="0" max="-1">'
                '<SimpleContext naturalClass="any" /></OptionalSegmentSequence></PhoneticSequence>'
            )
            out = '<CopyFromInput index="st1" />' + ins + '<CopyFromInput index="st2" />'
        else:
            minput = (
                '<PhoneticSequence id="st"><OptionalSegmentSequence min="1" max="-1">'
                '<SimpleContext naturalClass="any" /></OptionalSegmentSequence></PhoneticSequence>'
            )
            copy = '<CopyFromInput index="st" />'
            out = (ins + copy) if a.kind == "prefix" else (copy + ins)
        if pos_aware:
            req = a.req_pos or all_pos_attr
            pos_attr = f'requiredPartsOfSpeech="{req}"' + (f' outputPartOfSpeech="{a.req_pos}"' if a.req_pos else "")
        else:
            pos_attr = 'requiredPartsOfSpeech="root" outputPartOfSpeech="root"'
        rules.append(
            f'<MorphologicalRule id="{rid}" {pos_attr}>'
            f"<Name>{escape(a.gloss)}</Name><MorphologicalSubrules>"
            f'<MorphologicalSubrule id="{rid}s"><MorphologicalInput>{minput}</MorphologicalInput>'
            f"<MorphologicalOutput>{out}</MorphologicalOutput></MorphologicalSubrule>"
            f"</MorphologicalSubrules><Gloss>{escape(a.gloss)}</Gloss></MorphologicalRule>"
        )

    # CONDITIONED-allomorph affixes: ONE rule, several env-conditioned subrules (vy- before a vowel-initial
    # stem, vi- elsewhere) — the morpheme-scoped collapse that replaces a pair of enumerated affixes without
    # a global rule. Each allomorph = {"shape", "first": "vow"|None (elsewhere)}.
    # STATUS (2026-06-25): WORKS — vitu->cl8+tu (vi elsewhere) and vyombo->cl8+ombo (vy before a vowel) parse
    # via ONE cl8 affix, no global rule (so mi- is untouched). The earlier crash was OURS: affix-shape chars
    # (v,i,y) missing from the charset made Translit emit an empty InsertSegments, which crashes hc.exe (see
    # the HC NRE bug report). Fixed above by adding shape chars to the charset.
    cd_of = {c: i for i, c in enumerate(src_chars)}
    cond_rule_ids = []
    for k, ca in enumerate(conditioned_affixes or []):
        crid = _xid("cr", k)
        cond_rule_ids.append(crid)
        kind = ca.get("kind", "prefix")
        subs = ""
        for j, allo in enumerate(ca.get("allomorphs", [])):
            shp = f'<InsertSegments><PhoneticShape>{escape(tl.enc(allo["shape"]))}</PhoneticShape></InsertSegments>'
            first = allo.get("first")
            if isinstance(first, (list, tuple, set, frozenset)):   # marked before a SPECIFIC vowel set
                segs = "".join(f'<Segment segment="cd_{cd_of[v]}" />' for v in sorted(first) if v in cd_of)
                tnc = f"nc_trig_{crid}_{j}"
                extra_nat_classes += f'<SegmentNaturalClass id="{tnc}"><Name>{tnc}</Name>{segs}</SegmentNaturalClass>'
                minp = (f'<SimpleContext naturalClass="{tnc}" /><OptionalSegmentSequence min="0" max="-1">'
                        '<SimpleContext naturalClass="any" /></OptionalSegmentSequence>')
            elif first == "vow":                                  # marked before any vowel (needs voc substrate)
                minp = ('<SimpleContext naturalClass="nc_vow" /><OptionalSegmentSequence min="0" max="-1">'
                        '<SimpleContext naturalClass="any" /></OptionalSegmentSequence>')
            else:                                                 # elsewhere (default)
                minp = ('<OptionalSegmentSequence min="1" max="-1"><SimpleContext naturalClass="any" />'
                        '</OptionalSegmentSequence>')
            cp = '<CopyFromInput index="st" />'
            oput = (shp + cp) if kind != "suffix" else (cp + shp)
            subs += (f'<MorphologicalSubrule id="{crid}s{j}"><MorphologicalInput>'
                     f'<PhoneticSequence id="st">{minp}</PhoneticSequence></MorphologicalInput>'
                     f'<MorphologicalOutput>{oput}</MorphologicalOutput></MorphologicalSubrule>')
        g = escape(ca.get("gloss", "AFX"))
        rules.append(f'<MorphologicalRule id="{crid}" requiredPartsOfSpeech="root" outputPartOfSpeech="root">'
                     f'<Name>{g}</Name><MorphologicalSubrules>{subs}</MorphologicalSubrules>'
                     f'<Gloss>{g}</Gloss></MorphologicalRule>')
        rule_ids.append(crid)

    # Best-practice morphotactics: group affix rules into ordered position-class slots
    # (an HC AffixTemplate), one filler per slot, slots in inner->outer order — instead of the
    # flat, unordered, arbitrarily-stacking rule list of v1. This is the affix-template/slot model
    # (MoInflAffixTemplate/MoInflAffixSlot) and is what collapses the over-generation.
    if templated and model.affixes:
        # Known slots come from affixes carrying explicit (gold) slot evidence; an affix with no
        # evidence (e.g. an agent-proposed one) is placed leniently in every known slot on its side.
        known: dict[str, set[int]] = {"suffix": set(), "prefix": set(), "infix": set()}
        for a in model.affixes:
            for sd, o in a.slots:
                known.setdefault(sd, set()).add(o)
        slot_rules: dict[tuple[str, int], list[str]] = {}
        for i, a in enumerate(model.affixes):
            targets = a.slots or tuple((a.kind, o) for o in sorted(known.get(a.kind, {a.slot_ord})) or [a.slot_ord])
            for slot in (targets or (a.slot,)):
                slot_rules.setdefault(slot, []).append(rule_ids[i])
        slots_xml = ""
        for side in ("prefix", "infix", "suffix"):  # template order: prefixes, infixes, suffixes
            for o in sorted(o for (s, o) in slot_rules if s == side):
                rids = " ".join(slot_rules[(side, o)])
                slots_xml += (f'<Slot optional="true" morphologicalRules="{rids}">'
                              f'<Name>{side}{o}</Name></Slot>')
        if cond_rule_ids:                                # conditioned affixes get an outermost prefix slot
            slots_xml = (f'<Slot optional="true" morphologicalRules="{" ".join(cond_rule_ids)}">'
                         f'<Name>conditioned</Name></Slot>') + slots_xml
        template_xml = (f'<AffixTemplates><AffixTemplate final="true" requiredPartsOfSpeech="{all_pos_attr}">'
                        f'<Name>main</Name>{slots_xml}</AffixTemplate></AffixTemplates>')
        stratum_open = f'<Stratum characterDefinitionTable="t1" morphologicalRuleOrder="linear"{{prattr}}><Name>main</Name>'
    else:
        template_xml = ""
        stratum_open = ('<Stratum characterDefinitionTable="t1" morphologicalRuleOrder="unordered" '
                        f'morphologicalRules="{" ".join(rule_ids)}"{{prattr}}><Name>main</Name>')

    # phonological rules (the harder path): emitted at language level, referenced by the stratum.
    prd = ""
    if phon_rules:
        prd = "<PhonologicalRuleDefinitions>" + "".join(x for _, x in phon_rules) + "</PhonologicalRuleDefinitions>"
        stratum_open = stratum_open.replace("{prattr}", f' phonologicalRules="{" ".join(i for i, _ in phon_rules)}"')
    else:
        stratum_open = stratum_open.replace("{prattr}", "")

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<HermitCrabInput><Language><Name>" + escape(model.code) + "</Name>"
        "<PartsOfSpeech>"
        + "".join(f'<PartOfSpeech id="{p}"><Name>{p}</Name></PartOfSpeech>' for p in pos_list)
        + "</PartsOfSpeech>"
        f'<PhonologicalFeatureSystem><SymbolicFeature id="seg" defaultSymbol="{default_sym}">'
        f"<Name>seg</Name><Symbols>{symbols}</Symbols></SymbolicFeature>{extra_feature_defs}"
        "</PhonologicalFeatureSystem>"
        f'<CharacterDefinitionTable id="t1"><Name>main</Name><SegmentDefinitions>{segdefs}'
        "</SegmentDefinitions></CharacterDefinitionTable>"
        f'<NaturalClasses>{extra_nat_classes}<SegmentNaturalClass id="any"><Name>any</Name>{anyseg}'
        "</SegmentNaturalClass></NaturalClasses>"
        f"{prd}"
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
    phon_feats: dict[str, dict[str, str]] | None = None,
    pos_aware: bool = False,
    phon_rules: list[tuple[str, str]] | None = None,
    glide_rule: bool = False,
    glide_block_vowels: frozenset = frozenset(),
    conditioned_affixes: list[dict] | None = None,
) -> dict[str, list[Analysis]]:
    """Parse ``words`` (underlying forms) with the emitted grammar; return analyses.

    Parsing is chunked with a per-chunk timeout. High-affix grammars (e.g. Tsez, Uspanteko)
    make HC's unconstrained search explode on some words; chunking bounds time AND memory
    (the timed-out ``hc`` process is killed) and localizes the loss — words in a timed-out
    chunk are simply returned with no analyses (counted as unparsed). This is the scaling
    signal that motivates the affix-template/ordering enrichment.
    """
    tl = Translit(model.charset)
    xml = build_grammar_xml(model, tl, templated=templated, phon_feats=phon_feats, pos_aware=pos_aware,
                            phon_rules=phon_rules, glide_rule=glide_rule, glide_block_vowels=glide_block_vowels,
                            conditioned_affixes=conditioned_affixes)
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
