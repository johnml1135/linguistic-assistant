"""The fixed HC-mechanism taxonomy: deferral `type` → the candidate grammar edits that could resolve it.

Deterministic, LLM-free (Phase A). Each deferral predicament maps to a small set of typed `Hypothesis`
objects whose `edits` are real ops over the gold `LangModel`:

  lexeme_gloss / no-parse word
      → add the word as a root (LexEntry + gloss)
      → attach it as a stem allomorph of the nearest existing lemma (MoStemAllomorph)
      → re-segment: a new stem + a known affix (resegment)
  homograph         → split into a second sense/POS entry (split_homograph)
  affix_function    → add the affix→function rule (add_affix); + repair (narrow/retract) if it looks over-broad
  segmentation      → stem + known affix, or stem + new affix

`enumerate_hypotheses` consults an optional `allowed` set of edit kinds (the language-profile filter,
wired in group 15): a locked-off mechanism for the language — e.g. an infix for a non-infixing language —
is never produced. With `allowed=None` every mechanism is permitted.
"""

from __future__ import annotations

from .schema import EDIT_KINDS, GrammarEdit, Hypothesis

# the deferral `type` we infer when a source doesn't state one
LEXICAL_TYPES = {"lexeme_gloss", "homograph", "pos", "segmentation"}

# derivational affix functions change the part of speech or argument structure (a new dictionary word),
# vs inflectional ones that just vary a form. A coarse glossary-based classifier (D13 / task 13.3).
_DERIVATIONAL = {"caus", "causative", "appl", "applicative", "nmlz", "nominalizer", "nominaliz", "agt",
                 "agent", "advz", "adjz", "verbalizer", "vblz", "dim", "diminutive", "abstract", "ize"}


def affix_function_kind(gloss: str, feature: dict | None = None) -> str:
    """'derivational' if the affix's function looks category/valency-changing, else 'inflectional'."""
    g = (gloss or "").lower()
    if any(d in g for d in _DERIVATIONAL):
        return "derivational"
    return "inflectional"


def _nearest_lemma(word: str, lemmas: list[str], k: int = 4) -> str | None:
    """The existing lemma sharing the longest ≥k-char prefix with `word` (a likely stem to attach to)."""
    best, best_len = None, 0
    for lm in lemmas:
        n = 0
        for a, b in zip(word, lm):
            if a != b:
                break
            n += 1
        if n >= k and n > best_len and lm != word:
            best, best_len = lm, n
    return best


def _known_affix_split(word: str, affixes: list[dict]) -> tuple[str, dict] | None:
    """If `word` ends with a known suffix (or starts with a known prefix), return (stem, affix-record)."""
    for a in sorted(affixes, key=lambda a: -len(a.get("affix", ""))):
        f, mt = a.get("affix", ""), a.get("morph_type", "")
        if not f or len(f) < 2:
            continue
        if mt == "suffix" and word.endswith(f) and len(word) > len(f) + 1:
            return word[: -len(f)], a
        if mt == "prefix" and word.startswith(f) and len(word) > len(f) + 1:
            return word[len(f):], a
    return None


def _common_prefix(forms: list[str]) -> str:
    if not forms:
        return ""
    p = forms[0]
    for f in forms[1:]:
        while not f.startswith(p):
            p = p[:-1]
    return p


def _archiphoneme_family(form: str, gloss: str, gold: dict) -> list[str]:
    """Gold affixes sharing this affix's function (gloss/features) and differing only by a trailing
    segment — an allomorph family that an archiphoneme + rule could collapse (e.g. mem/men/meng)."""
    fam: list[str] = []
    g = (gloss or "").lower()
    for a in gold.get("affixes", []):
        af, afg = a.get("affix", ""), str(a.get("features") or a.get("gram") or "").lower()
        if not af or af == form:
            continue
        # same function, and one form is the other ± a short trailing difference on a shared stem
        shared = _common_prefix([af, form])
        if afg and afg == g and len(shared) >= 2 and abs(len(af) - len(form)) <= 2:
            fam.append(af)
    return fam


def _gloss_candidates(rec: dict) -> list[str]:
    """The glosses worth proposing, best-first, de-duped."""
    out: list[str] = []
    for g in (rec.get("gloss"), rec.get("aligner_top1"), *(rec.get("candidates") or [])):
        if g and g not in out:
            out.append(g)
    return out or ["?"]


def enumerate_hypotheses(rec: dict, gold: dict, *, allowed: set[str] | None = None,
                         allowed_affix_kinds: set[str] | None = None) -> tuple[str, str, list[Hypothesis]]:
    """Return (ticket_type, domain, hypotheses) for a defer record.

    `rec` is a defer record (lexical: {word, gloss, pos, aligner_top1, …}; affix: {affix, kind, function,
    feature, …}). `gold` is `goldio.load_gold(pair)`. `allowed` (if given) prunes disallowed edit kinds;
    `allowed_affix_kinds` (the language-profile filter) prunes affix hypotheses whose process — e.g. infix
    for a non-infixing language — is locked off.
    """
    allow = set(allowed) if allowed is not None else set(EDIT_KINDS)

    def ok(h: Hypothesis) -> bool:
        return all(e.kind in allow for e in h.edits)

    if "affix" in rec:                       # an affix-function deferral
        return _affix_hypotheses(rec, gold, ok, allowed_affix_kinds)
    return _lexical_hypotheses(rec, gold, ok, allowed_affix_kinds)


# common Tagalog-style infixes inserted after the stem's first consonant (HC supports infix rules)
_INFIXES = ("um", "in")


def _infix_split(word: str) -> tuple[str, str] | None:
    """If `word` looks like C + <infix> + rest, return (stem=C+rest, infix). E.g. sumulat → (sulat, um)."""
    if len(word) < 4 or word[0] in "aeiou":
        return None
    for inf in _INFIXES:
        if word[1:1 + len(inf)] == inf and len(word) > len(inf) + 2:
            return word[0] + word[1 + len(inf):], inf
    return None


def _lexical_hypotheses(rec: dict, gold: dict, ok, allowed_affix_kinds: set[str] | None = None) -> tuple[str, str, list[Hypothesis]]:
    word = (rec.get("word") or "").lower()
    pos = rec.get("pos") or "Noun"
    glosses = _gloss_candidates(rec)
    lemmas = gold.get("lemmas", [])
    senses = gold.get("senses", {})
    hyps: list[Hypothesis] = []

    # is this a homograph predicament? (gold already records >1 sense/POS for the form)
    s = senses.get(word) or {}
    homograph = bool(s.get("homograph")) or len(s.get("pos", []) or []) > 1

    n = 0
    def add(mech, desc, edits, discriminates=()):
        nonlocal n
        n += 1
        h = Hypothesis(id=f"h{n}", mechanism=mech, description=desc,
                       edits=[GrammarEdit(**e) for e in edits], discriminates=list(discriminates))
        if ok(h):
            hyps.append(h)

    # H: add as a new root
    add("add_lexentry", f"“{word}” is its own word meaning ‘{glosses[0]}’.",
        [{"kind": "add_lexentry", "params": {"form": word, "gloss": glosses[0], "pos": pos}}],
        discriminates=["meaning_choice"])

    # H: stem allomorph of the nearest existing lemma (irregular form of a known word)
    near = _nearest_lemma(word, lemmas)
    if near:
        near_gloss = (gold.get("glosses", {}).get(near) or near)
        add("add_allomorph", f"“{word}” is another form of the existing word “{near}” (‘{near_gloss}’).",
            [{"kind": "add_allomorph", "params": {"entry_form": near, "allomorph": word,
                                                  "gloss": near_gloss, "pos": gold.get("pos", {}).get(near, pos)}}],
            discriminates=["allomorph_check", "minimal_pair"])

    # H: re-segment as a new stem + a known affix
    split = _known_affix_split(word, gold.get("affixes", []))
    if split:
        stem, aff = split
        add("resegment", f"“{word}” = new stem “{stem}” + the known affix “{aff['affix']}” "
                         f"({aff.get('features', aff['affix'])}).",
            [{"kind": "resegment", "params": {"edits": [
                {"kind": "add_lexentry", "params": {"form": stem, "gloss": glosses[0], "pos": pos}}]}}],
            discriminates=["segmentation", "contrast_function"])

    # H: infix re-segmentation (task 13.1) — only where the profile permits infixation (e.g. Tagalog).
    # HC supports infix rules; we propose the inner stem as a root + an infix affix rule.
    if allowed_affix_kinds is None or "infix" in allowed_affix_kinds:
        inf = _infix_split(word)
        if inf:
            stem, infx = inf
            add("resegment", f"“{word}” = stem “{stem}” with the INFIX “-{infx}-” inserted inside it.",
                [{"kind": "resegment", "params": {"edits": [
                    {"kind": "add_lexentry", "params": {"form": stem, "gloss": glosses[0], "pos": pos}},
                    {"kind": "add_affix", "params": {"form": infx, "gloss": f"INFIX:{infx}", "kind": "infix"}}]}}],
                discriminates=["segmentation", "contrast_function"])

    # H: homograph split (only if the form already carries another sense)
    if homograph and len(glosses) > 0:
        add("split_homograph", f"“{word}” is a SECOND, distinct word here meaning ‘{glosses[0]}’.",
            [{"kind": "split_homograph", "params": {"form": word, "gloss": glosses[0], "pos": pos}}],
            discriminates=["meaning_choice"])

    ttype = "homograph" if homograph else "lexeme_gloss"
    return ttype, "lexical", hyps


def followon_stubs(word: str, profile=None) -> list[Hypothesis]:
    """Documented stubs for processes whose HC representation is a follow-on (D13/D16): reduplication,
    noun-class concord, compounding. Emitted (unverified, source='follow-on') only when the profile
    permits the process and the surface form hints at it — so a real case is flagged, never silently
    dropped, even though we can't yet generate the executable edit."""
    word = (word or "").lower()
    stubs: list[Hypothesis] = []
    allow = profile.allowed_affix_kinds() if profile else {"reduplication", "compounding"}

    def doubled(w: str) -> bool:                       # a crude reduplication hint: a repeated chunk
        n = len(w)
        return any(w[:k] == w[k:2 * k] for k in range(2, n // 2 + 1)) or "-" in w

    if "reduplication" in allow and doubled(word):
        stubs.append(Hypothesis(id="fo_redup", mechanism="reduplication",
                                description=f"“{word}” may involve REDUPLICATION (a repeated piece). "
                                            f"HC representation is a follow-on — flagged for a linguist.",
                                edits=[], source="follow-on", unverified=True))
    if "compounding" in allow and len(word) >= 8:
        stubs.append(Hypothesis(id="fo_compound", mechanism="compounding",
                                description=f"“{word}” may be a COMPOUND of two roots. HC multi-root "
                                            f"representation is a follow-on — flagged for a linguist.",
                                edits=[], source="follow-on", unverified=True))
    if profile and profile.feature_present("noun_class") and profile.feature_present("agreement"):
        stubs.append(Hypothesis(id="fo_concord", mechanism="concord",
                                description="A noun-class CONCORD marker may be involved (cross-word "
                                            "agreement). Modeling concord is a follow-on — flagged.",
                                edits=[], source="follow-on", unverified=True))
    return stubs


def _affix_hypotheses(rec: dict, gold: dict, ok, allowed_affix_kinds: set[str] | None = None) -> tuple[str, str, list[Hypothesis]]:
    form = (rec.get("affix") or "").lstrip("-").rstrip("-").lower()
    kind = rec.get("kind") or rec.get("side") or "suffix"
    if allowed_affix_kinds is not None and kind not in allowed_affix_kinds:
        return "affix_function", "morphology", []     # profile locks this affix process off → no hypotheses
    function = rec.get("function") or rec.get("gloss") or form
    feat = rec.get("feature") or {}
    gloss = "|".join(f"{k}={v}" for k, v in feat.items()) if isinstance(feat, dict) and feat else str(function)
    existing = {a.get("affix") for a in gold.get("affixes", [])}
    hyps: list[Hypothesis] = []
    n = 0

    def add(mech, desc, edits, discriminates=()):
        nonlocal n
        n += 1
        h = Hypothesis(id=f"h{n}", mechanism=mech, description=desc,
                       edits=[GrammarEdit(**e) for e in edits], discriminates=list(discriminates))
        if ok(h):
            hyps.append(h)

    # H: add the affix→function rule, tagged inflectional vs derivational (D13 / task 13.3)
    fkind = affix_function_kind(gloss, feat if isinstance(feat, dict) else None)
    add("add_affix", f"“{form}” ({kind}) is a{'n' if fkind[0]=='i' else ''} {fkind} affix meaning {gloss}.",
        [{"kind": "add_affix", "params": {"form": form, "gloss": gloss, "kind": kind,
                                          "function_kind": fkind}}],
        discriminates=["contrast_function", "agreement_probe"])

    # archiphoneme-collapse (D11/D13, task 13.2): if the gold has an allomorph FAMILY — several affixes
    # with the SAME function differing by one phonologically-conditioned segment (Indonesian meN-:
    # mem/men/meng) — propose one underlying form + a rule instead of listing them. The phonological rule
    # is verified by round-trip in the phonology pipeline (cycle/hc_phonology); here we detect + propose.
    family = _archiphoneme_family(form, gloss, gold)
    if len(family) >= 2:
        members = sorted(set(family) | {form})
        underlying = _common_prefix(members) + "N"          # archiphoneme placeholder for the varying seg
        add("add_phon_rule",
            f"“{form}” is one of an allomorph family {members} (same function {gloss}); collapse them to "
            f"one underlying form “{underlying}” + a sound rule, instead of listing each.",
            [{"kind": "add_phon_rule", "params": {"id": f"collapse_{form}", "archiphoneme": underlying,
                                                  "members": members, "conditioning": "phonological"}}],
            discriminates=["minimal_pair", "allomorph_check"])

    # repair: if the affix already exists, it may be over-broad → narrow it, or retract it
    if form in existing:
        add("narrow_affix", f"The existing affix “{form}” is too broad — restrict where it attaches.",
            [{"kind": "narrow_affix", "params": {"form": form, "gloss": gloss}}],
            discriminates=["grammaticality", "acceptability_rank"])
        add("retract_affix", f"The affix “{form}” is wrong here — remove it.",
            [{"kind": "retract_affix", "params": {"form": form, "gloss": gloss}}],
            discriminates=["grammaticality"])

    return "affix_function", "morphology", hyps
