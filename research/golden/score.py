"""Score an agent proposal against an ablation instance — the reward function (spec comp. 4).

A *proposal* is the agent's set of lexicon/grammar additions (the LIFT/HC change-set,
represented here as :class:`~golden.grammar.LexEntry` / :class:`~golden.grammar.Affix` to
add). Reward is HC-functional: apply the proposal to the crippled model and ask whether
HermitCrab re-glosses the held-out wordforms correctly — *gated on non-regression* of the
control set. Pure ``(instance, proposal) -> reward`` so the same function serves harness
eval and RL.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import hc
from .ablate import Instance
from .grammar import Affix, LangModel, LexEntry


@dataclass
class Proposal:
    lex: list[LexEntry]
    affix: list[Affix]


@dataclass
class Reward:
    reward: float          # held-out gloss recall AFTER repair, 0 if regression
    held_recall: float     # fraction of held-out forms re-glossed correctly
    regressed: bool        # did any control form stop round-tripping?
    n_held: int
    mean_ambiguity: float

    def as_dict(self) -> dict:
        return {
            "reward": round(self.reward, 4), "held_recall": round(self.held_recall, 4),
            "regressed": self.regressed, "n_held": self.n_held,
            "mean_ambiguity": round(self.mean_ambiguity, 2),
        }


def apply_proposal(incomplete: LangModel, proposal: Proposal) -> LangModel:
    return LangModel(
        code=incomplete.code,
        lexicon=list(incomplete.lexicon) + list(proposal.lex),
        affixes=list(incomplete.affixes) + list(proposal.affix),
    )


def score(instance: Instance, proposal: Proposal, timeout: int = 300) -> Reward:
    repaired = apply_proposal(instance.incomplete, proposal)
    held = instance.held_out
    rt = hc.round_trip(repaired, held, timeout=timeout) if held else None
    held_recall = rt.recall if rt else 1.0
    amb = rt.mean_ambiguity if rt else 0.0

    # Non-regression guard: control words must still round-trip on the repaired grammar.
    regressed = False
    if instance.control:
        ctl = hc.round_trip(repaired, instance.control, timeout=timeout)
        base = hc.round_trip(instance.incomplete, instance.control, timeout=timeout)
        regressed = ctl.recall < base.recall - 1e-9

    return Reward(
        reward=0.0 if regressed else held_recall,
        held_recall=held_recall,
        regressed=regressed,
        n_held=len(held),
        mean_ambiguity=amb,
    )
