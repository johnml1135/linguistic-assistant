"""Typed grammar-edit ops over a `golden.grammar.LangModel` — the executable form of a hypothesis.

`apply_edits(model, edits)` returns a CLONE of the model with the edits applied (the gold is never
mutated) plus any phonological-rule XML the edits introduce (HC takes those out-of-band via
`run_parse(phon_rules=...)`). Each op maps to a LibLCM/HC construct:

  add_lexentry   -> LexEntry (root)                 add_phon_rule  -> PhonologicalRule
  add_allomorph  -> MoStemAllomorph (extra stem)    split_homograph-> a second LexEntry for one form
  add_affix      -> MoInflAffMsa / MorphologicalRule  resegment    -> a composite of sub-edits
  narrow_affix / retract_affix                      -> repair ops on a noisy grammar (narrow/remove)

The ops are deliberately small and total: an op that can't find its target degrades to the closest
sensible action (e.g. add_allomorph on an absent lemma creates the entry) rather than raising, so a
counterfactual always yields *some* grammar to parse.
"""

from __future__ import annotations

from dataclasses import replace

from engine.grammar import Affix, LangModel, LexEntry

from .schema import GrammarEdit


def clone(model: LangModel) -> LangModel:
    """A shallow-but-safe clone: new lists, same frozen entries (LexEntry/Affix are immutable)."""
    return LangModel(code=model.code, lexicon=list(model.lexicon), affixes=list(model.affixes))


def _find_lex(model: LangModel, form: str) -> int:
    for i, e in enumerate(model.lexicon):
        if e.form == form:
            return i
    return -1


def _apply_one(model: LangModel, edit: GrammarEdit) -> list[tuple[str, str]]:
    """Mutate `model` in place (it is already a clone) for one edit; return any phon-rule (id, xml)."""
    p = edit.params
    phon: list[tuple[str, str]] = []
    if edit.kind == "add_lexentry":
        model.lexicon.append(LexEntry(
            form=p["form"], gloss=p.get("gloss", "?"), pos=p.get("pos", "root"),
            count=int(p.get("count", 0)), allomorphs=tuple(p.get("allomorphs", ()))))
    elif edit.kind == "add_allomorph":
        entry_form = p["entry_form"]
        allo = p["allomorph"]
        i = _find_lex(model, entry_form)
        if i >= 0:
            e = model.lexicon[i]
            if allo not in e.allomorphs and allo != e.form:
                model.lexicon[i] = replace(e, allomorphs=tuple(e.allomorphs) + (allo,))
        else:
            model.lexicon.append(LexEntry(form=entry_form, gloss=p.get("gloss", "?"),
                                          pos=p.get("pos", "root"), allomorphs=(allo,)))
    elif edit.kind == "add_affix":
        model.affixes.append(Affix(
            form=p["form"], gloss=p.get("gloss", p["form"]), kind=p.get("kind", "suffix"),
            count=int(p.get("count", 0)), slot_ord=int(p.get("slot_ord", 1)),
            req_pos=p.get("req_pos", "")))
    elif edit.kind == "split_homograph":
        model.lexicon.append(LexEntry(form=p["form"], gloss=p.get("gloss", "?"),
                                      pos=p.get("pos", "root")))
    elif edit.kind == "add_phon_rule":
        if p.get("xml"):
            phon.append((p.get("id", "pr_hyp"), p["xml"]))
    elif edit.kind == "resegment":
        for sub in p.get("edits", []):
            phon += _apply_one(model, GrammarEdit(**sub) if isinstance(sub, dict) else sub)
    elif edit.kind == "narrow_affix":
        for i, a in enumerate(model.affixes):
            if a.form == p["form"] and (not p.get("gloss") or a.gloss == p["gloss"]):
                model.affixes[i] = replace(a, req_pos=p.get("req_pos", a.req_pos),
                                           slot_ord=int(p.get("slot_ord", a.slot_ord)))
    elif edit.kind == "retract_affix":
        model.affixes[:] = [a for a in model.affixes
                            if not (a.form == p["form"] and (not p.get("gloss") or a.gloss == p["gloss"]))]
    else:  # pragma: no cover — schema.validate() blocks unknown kinds upstream
        raise ValueError(f"unknown edit kind {edit.kind!r}")
    return phon


def apply_edits(model: LangModel, edits: list[GrammarEdit]) -> tuple[LangModel, list[tuple[str, str]]]:
    """Apply `edits` to a clone of `model`. Returns (new_model, phon_rules). Gold is untouched."""
    m = clone(model)
    phon: list[tuple[str, str]] = []
    for e in edits:
        phon += _apply_one(m, e)
    return m, phon
