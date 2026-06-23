"""The real Hermit Crab scorer behind the eval/proposal loop's seam.

``build_scorer()`` is the entry point ``research/eval`` auto-imports the moment this module is
present (replacing its labeled stub). It maps a ``proposal.contract.ChangeSet`` (the agent's
change-set) onto additions to the instance's *incomplete* grammar, runs Hermit Crab, and rewards
held-out gloss re-parse gated on non-regression — the HC-functional reward of the golden design.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from propose.contract import ChangeSet, Instance, ScoreResult

from . import score
from .grammar import Affix, LexEntry


def changeset_to_proposal(ops: list[dict[str, Any]]) -> tuple[score.Proposal, dict]:
    """Map change-set ops onto lexicon/affix additions. Unsupported (v1) ops are noted, not applied."""
    # Collect glosses proposed per entry via lexical.sense.create.
    sense_gloss: dict[str, str] = {}
    for op in ops:
        if op.get("op") == "lexical.sense.create" and op.get("entry") and op.get("gloss"):
            sense_gloss.setdefault(str(op["entry"]), str(op["gloss"]))

    lex: list[LexEntry] = []
    affix: list[Affix] = []
    ignored: list[str] = []
    for op in ops:
        t = op.get("op")
        if t == "lexical.entry.create":
            form = str(op.get("lexeme_form", ""))
            gloss = sense_gloss.get(str(op.get("id", form))) or sense_gloss.get(form, "")
            if form:
                lex.append(LexEntry(form=form, gloss=gloss))
        elif t == "morphophonology.affix.add":
            form, gram = str(op.get("form", "")), str(op.get("gram", ""))
            if form and gram:
                # direction unspecified in the op; model both so the gloss is reachable either way.
                affix.append(Affix(form=form, gloss=gram, kind="suffix"))
                affix.append(Affix(form=form, gloss=gram, kind="prefix"))
        elif t == "lexical.sense.create":
            continue  # consumed above
        else:
            ignored.append(str(t))
    return score.Proposal(lex=lex, affix=affix), {"ignored_ops": ignored}


class HcScorer:
    name = "hermitcrab-gloss-roundtrip"

    def score(self, instance: Instance, change_set: ChangeSet) -> ScoreResult:
        abl = getattr(instance, "abl", None)
        if abl is None:
            return ScoreResult(reward=0.0, parsed_ok=False,
                               diagnostics={"error": "instance has no ablation payload (.abl)"})
        proposal, notes = changeset_to_proposal(change_set.ops)
        rew = score.score(abl, proposal)
        return ScoreResult(
            reward=rew.reward,
            parsed_ok=rew.held_recall > 0.0 and not rew.regressed,
            diagnostics={"scorer": self.name, **rew.as_dict(), **notes,
                         "n_lex_added": len(proposal.lex), "n_affix_added": len(proposal.affix)},
        )


def build_scorer() -> HcScorer:
    return HcScorer()
