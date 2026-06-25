"""Glide-collapse emitter + HC round-trip gate.

Turns an `allomorph-collapse` candidate whose alternation is a high-vowel→glide (mu/mw, vi/vy, mi/my) into
a real HC `<PhonologicalRule>` — `[+high,+syllabic] → [−syllabic] / __ V` — and VERIFIES the collapse by
round-trip: ONE underlying form + that single rule must re-parse every attested member, in both the
vowel environment (before a consonant: mu·ngu) and the glide environment (before a vowel: mw·ana). One
general rule covers the whole family (u→w and i→y alike). Verified against hc.exe.

Leaf module (engine): both `gold.phonology_gold.active_phon_rules` (to emit the live rule) and
`review.promote` (to gate candidates) import it, honouring the one-way dependency contract.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

HC_EXE = os.path.expanduser(os.path.join("~", ".dotnet", "tools", "hc.exe"))
_ENV = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}

# A 5-vowel distinctive table (hi, rnd, back) that keeps every vowel unique; glides are the [−syllabic]
# twins of the high vowels (w←u, y←i), so the output of the desyllabification rule lands on exactly one
# segment. ASCII only (HC corrupts non-ASCII output).
VOWELS: dict[str, tuple[str, str, str]] = {   # vowel -> (hi, rnd, back)
    "a": ("lo", "unr", "bk"), "e": ("lo", "unr", "fr"), "i": ("hi", "unr", "fr"),
    "o": ("lo", "rnd", "bk"), "u": ("hi", "rnd", "bk"),
}
GLIDE_OF = {"u": "w", "i": "y"}               # high vowel -> its glide


def hc_available() -> bool:
    return Path(HC_EXE).exists()


# --------------------------------------------------------------------------- the emitter (one rule, whole family)
def glide_rule_xml(rid: str = "r_glide", right_env_class: str = "nc_syl") -> tuple[str, str]:
    """The reusable HC rule: a high syllabic vowel desyllabifies (becomes its glide) before a vowel.
    `[+high,+syl] → [−syl] / __ [+syl]`. Covers u→w and i→y with one rule. `right_env_class` is the
    natural class of the triggering following vowel — pass a restricted class (e.g. all vowels except the
    homorganic `u`) to emit a CONDITIONED rule that doesn't fire before the blocking vowel."""
    xml = (
        f'<PhonologicalRule id="{rid}" multipleApplicationOrder="leftToRightIterative">'
        '<Name>glide formation</Name>'
        '<PhoneticInput><PhoneticSequence><SimpleContext naturalClass="nc_high_syl"/></PhoneticSequence>'
        '</PhoneticInput><PhonologicalSubrules><PhonologicalSubrule>'
        '<PhoneticOutput><PhoneticSequence><SimpleContext naturalClass="nc_glide_out"/></PhoneticSequence>'
        '</PhoneticOutput><Environment><RightEnvironment><PhoneticTemplate><PhoneticSequence>'
        f'<SimpleContext naturalClass="{right_env_class}"/>'
        '</PhoneticSequence></PhoneticTemplate></RightEnvironment></Environment>'
        '</PhonologicalSubrule></PhonologicalSubrules></PhonologicalRule>'
    )
    return rid, xml


# --------------------------------------------------------------------------- the verification grammar
def _segment_defs(chars: set[str]) -> tuple[str, str]:
    """(segment definitions, cid symbol defs) for the chars used by a round-trip — vowels get distinctive
    features + syl=plus, glides their high vowel's features + syl=minus, consonants a unique cid."""
    glides = {g for g in GLIDE_OF.values() if g in chars}
    vowels = {c for c in chars if c in VOWELS}
    consonants = sorted(c for c in chars if c not in VOWELS and c not in glides)
    src_of = {g: v for v, g in GLIDE_OF.items()}
    defs = []
    for v in sorted(vowels):
        hi, rnd, bk = VOWELS[v]
        defs.append(
            f'<SegmentDefinition id="s_{v}"><Representations><Representation>{escape(v)}</Representation>'
            f'</Representations><FeatureValue feature="voc" symbolValues="vow"/>'
            f'<FeatureValue feature="hi" symbolValues="{hi}"/><FeatureValue feature="rnd" symbolValues="{rnd}"/>'
            f'<FeatureValue feature="back" symbolValues="{bk}"/>'
            f'<FeatureValue feature="syl" symbolValues="plus"/></SegmentDefinition>')
    for g in sorted(glides):
        hi, rnd, bk = VOWELS[src_of[g]]
        defs.append(
            f'<SegmentDefinition id="s_{g}"><Representations><Representation>{escape(g)}</Representation>'
            f'</Representations><FeatureValue feature="voc" symbolValues="vow"/>'
            f'<FeatureValue feature="hi" symbolValues="{hi}"/><FeatureValue feature="rnd" symbolValues="{rnd}"/>'
            f'<FeatureValue feature="back" symbolValues="{bk}"/>'
            f'<FeatureValue feature="syl" symbolValues="minus"/></SegmentDefinition>')
    cid_syms = "".join(f'<Symbol id="c_{c}">{escape(c)}</Symbol>' for c in consonants)
    for c in consonants:
        defs.append(
            f'<SegmentDefinition id="s_{c}"><Representations><Representation>{escape(c)}</Representation>'
            f'</Representations><FeatureValue feature="voc" symbolValues="cons"/>'
            f'<FeatureValue feature="cid" symbolValues="c_{c}"/></SegmentDefinition>')
    return "".join(defs), cid_syms


def build_collapse_grammar(ur: str, stems: list[tuple[str, str]], *, ur_gloss: str = "UR",
                           kind: str = "prefix", block_vowels: frozenset = frozenset()) -> str:
    """A focused grammar: the single underlying affix `ur` + the glide rule + the given stems. Parsing a
    surface member with it = un-applying the rule back to ur+stem (the round-trip). `block_vowels` emits a
    CONDITIONED rule whose right environment is every vowel EXCEPT those listed (the homorganic blocker) —
    so e.g. `mu+umini` does not glide and round-trips as `mu`, instead of being a false exception."""
    chars = set(ur) | {ch for form, _ in stems for ch in form}
    chars |= {GLIDE_OF[c] for c in list(chars) if c in GLIDE_OF}   # the glide segment (w←u, y←i) only
    segdefs, cid_syms = _segment_defs(chars)                       # surfaces in members, not in the stems
    all_segs = sorted({f"s_{c}" for c in chars})
    any_segs = "".join(f'<Segment segment="{s}"/>' for s in all_segs)
    trigger_nc, right_env_class = "", "nc_syl"
    if block_vowels:                                               # conditioned rule: trigger = vowels − blockers
        trig = sorted(v for v in chars if v in VOWELS and v not in block_vowels)
        trig_segs = "".join(f'<Segment segment="s_{v}"/>' for v in trig)
        trigger_nc = f'<SegmentNaturalClass id="nc_trigger"><Name>trigger</Name>{trig_segs}</SegmentNaturalClass>'
        right_env_class = "nc_trigger"
    _rid, rule = glide_rule_xml(right_env_class=right_env_class)
    affix_out = (f'<InsertSegments><PhoneticShape>{escape(ur)}</PhoneticShape></InsertSegments><CopyFromInput index="st"/>'
                 if kind == "prefix" else
                 f'<CopyFromInput index="st"/><InsertSegments><PhoneticShape>{escape(ur)}</PhoneticShape></InsertSegments>')
    affix = (
        '<MorphologicalRule id="mr_ur" requiredPartsOfSpeech="root" outputPartOfSpeech="root">'
        f'<Name>{escape(ur_gloss)}</Name><MorphologicalSubrules><MorphologicalSubrule id="mr_ur_s">'
        '<MorphologicalInput><PhoneticSequence id="st"><OptionalSegmentSequence min="1" max="-1">'
        '<SimpleContext naturalClass="any"/></OptionalSegmentSequence></PhoneticSequence></MorphologicalInput>'
        f'<MorphologicalOutput>{affix_out}</MorphologicalOutput></MorphologicalSubrule></MorphologicalSubrules>'
        f'<Gloss>{escape(ur_gloss)}</Gloss></MorphologicalRule>')
    lex = "".join(
        f'<LexicalEntry id="e_{i}" partOfSpeech="root"><Allomorphs>'
        f'<Allomorph id="e_{i}_a"><PhoneticShape>{escape(form)}</PhoneticShape></Allomorph>'
        f'</Allomorphs><Gloss>{escape(gloss)}</Gloss></LexicalEntry>'
        for i, (form, gloss) in enumerate(stems))
    return (
        '<?xml version="1.0" encoding="utf-8"?><HermitCrabInput><Language><Name>collapse</Name>'
        '<PartsOfSpeech><PartOfSpeech id="root"><Name>root</Name></PartOfSpeech></PartsOfSpeech>'
        '<PhonologicalFeatureSystem>'
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
        f'<SymbolicFeature id="cid"><Name>cid</Name><Symbols>{cid_syms}</Symbols></SymbolicFeature>'
        '</PhonologicalFeatureSystem>'
        f'<CharacterDefinitionTable id="t1"><Name>main</Name><SegmentDefinitions>{segdefs}'
        '</SegmentDefinitions></CharacterDefinitionTable><NaturalClasses>'
        '<FeatureNaturalClass id="nc_vow"><Name>vow</Name><FeatureValue feature="voc" symbolValues="vow"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_cons"><Name>cons</Name><FeatureValue feature="voc" symbolValues="cons"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_syl"><Name>syllabic</Name><FeatureValue feature="voc" symbolValues="vow"/>'
        '<FeatureValue feature="syl" symbolValues="plus"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_high_syl"><Name>high syllabic</Name><FeatureValue feature="voc" symbolValues="vow"/>'
        '<FeatureValue feature="hi" symbolValues="hi"/><FeatureValue feature="syl" symbolValues="plus"/></FeatureNaturalClass>'
        '<FeatureNaturalClass id="nc_glide_out"><Name>nonsyllabic</Name><FeatureValue feature="syl" symbolValues="minus"/></FeatureNaturalClass>'
        f'<SegmentNaturalClass id="any"><Name>any</Name>{any_segs}</SegmentNaturalClass>'
        f'{trigger_nc}</NaturalClasses>'
        f'<PhonologicalRuleDefinitions>{rule}</PhonologicalRuleDefinitions><Strata>'
        '<Stratum characterDefinitionTable="t1" morphologicalRuleOrder="unordered" '
        'phonologicalRules="r_glide" morphologicalRules="mr_ur"><Name>main</Name>'
        f'<MorphologicalRuleDefinitions>{affix}</MorphologicalRuleDefinitions>'
        f'<LexicalEntries>{lex}</LexicalEntries></Stratum></Strata></Language></HermitCrabInput>')


_PARSING = re.compile(r'^Parsing "(.*)"$')


def _run_parse_xml(xml: str, words: list[str], *, timeout: int = 60) -> dict[str, list]:
    uniq = list(dict.fromkeys(words))
    with tempfile.TemporaryDirectory() as d:
        cfg, scr, out = Path(d) / "g.xml", Path(d) / "s.txt", Path(d) / "o.txt"
        cfg.write_text(xml, encoding="utf-8")
        scr.write_text("\n".join(f"parse {w}" for w in uniq) + "\n", encoding="utf-8")
        out.write_text("", encoding="utf-8")
        subprocess.run([HC_EXE, "-i", str(cfg), "-s", str(scr), "-o", str(out), "-c"],
                       env=_ENV, capture_output=True, timeout=timeout)
        text = out.read_text(encoding="utf-8")
    results: dict[str, list] = {}
    cur, morphs = None, None
    for line in text.splitlines():
        m = _PARSING.match(line.strip())
        if m:
            cur = m.group(1); results.setdefault(cur, []); morphs = None; continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("Morphs:"):
            morphs = s[len("Morphs:"):].split()
        elif s.startswith("Gloss:") and morphs is not None:
            gl = s[len("Gloss:"):].split()
            n = min(len(morphs), len(gl))
            results[cur].append(list(zip(morphs[:n], gl[:n]))); morphs = None
    return results


def glide_collapse_round_trips(ur: str, vowel: str, glide: str, vowel_env_words: list[str],
                               glide_env_words: list[str], *, timeout: int = 60,
                               block_vowels: frozenset = frozenset()) -> dict:
    """Validate the collapse against its OWN counterexamples. Build the single-UR + glide-rule grammar and
    re-parse the members, separating **in-environment** items (prefix before a vowel — where `vowel→glide`
    MUST apply: every glide-form word + every `ur`+vowel word) from out-of-environment ones. The Tolerance
    Principle is judged on the in-environment set (`n_env`, `n_exceptions` = `ur`+vowel forms that don't
    glide, e.g. *muumini*). `ur` is the vowel form; the glide form is `ur[:-1]+glide`.
    `block_vowels` emits a CONDITIONED rule (no gliding before those vowels) AND removes `ur`+blocker words
    from the in-environment set — so a homorganic blocker (mu+u → muumini) is treated as outside the rule's
    domain, not a false exception. Returns {ran, ok, recall_env, n_env, n_exceptions, n_members, ...}."""
    if not ur.endswith(vowel):
        return {"ran": False, "ok": False, "reason": f"ur {ur!r} does not end in {vowel!r}",
                "recall_env": 0.0, "n_env": 0, "n_exceptions": 0, "n_members": 0, "failures": []}
    glide_prefix = ur[:-1] + glide
    vowels = set(VOWELS)
    stems: dict[str, str] = {}
    classified: list[tuple[str, bool]] = []                # (word, in_environment = prefix before a trigger vowel)
    for w in dict.fromkeys(vowel_env_words):
        if w.startswith(ur) and len(w) > len(ur):
            stem = w[len(ur):]; stems.setdefault(stem, f"ST{len(stems)}")
            in_env = stem[0] in vowels and stem[0] not in block_vowels   # ur+trigger-vowel = in-env
            classified.append((w, in_env))
    for w in dict.fromkeys(glide_env_words):
        if w.startswith(glide_prefix) and len(w) > len(glide_prefix):
            stems.setdefault(w[len(glide_prefix):], f"ST{len(stems)}")
            classified.append((w, True))                   # glide form = in-env by definition
    members = [w for w, _ in classified]
    if not members or not glide_env_words:
        return {"ran": False, "ok": False, "reason": "no usable members (need both environments)",
                "recall_env": 0.0, "n_env": 0, "n_exceptions": 0, "n_members": len(members), "failures": []}
    if not hc_available():
        return {"ran": False, "ok": False, "reason": "hc.exe not available", "recall_env": 0.0,
                "n_env": 0, "n_exceptions": 0, "n_members": len(members), "failures": []}
    xml = build_collapse_grammar(ur, [(f, g) for f, g in stems.items()], block_vowels=block_vowels)
    parsed = _run_parse_xml(xml, members, timeout=timeout)

    def passes(w: str) -> bool:
        return any(any(g == "UR" for _, g in a) for a in parsed.get(w, []))

    env_items = [w for w, ie in classified if ie]
    exceptions = [w for w in env_items if not passes(w)]    # in-env words the rule fails to reproduce
    all_fail = [w for w in members if not passes(w)]
    n_env = len(env_items)
    return {"ran": True, "ok": not exceptions, "n_env": n_env, "n_exceptions": len(exceptions),
            "recall_env": round((n_env - len(exceptions)) / n_env, 3) if n_env else 0.0,
            "n_members": len(members), "n_failures": len(all_fail), "failures": exceptions[:10],
            "ur": ur, "glide_form": glide_prefix,
            "rule": f"{vowel}->{glide} / __V" + (f"[-{''.join(sorted(block_vowels))}]" if block_vowels else ""),
            "stems_collapsed": len(stems)}
