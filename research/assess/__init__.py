"""Grammar-assessment scorecard (Approach A of the `assess-grammar` spec).

Deterministic, paper-backed measures over HermitCrab (`golden.LangModel` + `hc`) and LibLCM/LIFT data.
"""

from __future__ import annotations

from . import inventory, mdl, metrics
from .builders import assess_hermitcrab, assess_liblcm, assess_lift
from .mdl import (
    better_grammar,
    decide_split_or_combine,
    description_length,
    spearman,
    worstness_mdl_ranking,
)
from .scorecard import Scorecard
from .worst_part import worst_part_ranking

__all__ = [
    "metrics",
    "inventory",
    "mdl",
    "Scorecard",
    "assess_hermitcrab",
    "assess_liblcm",
    "assess_lift",
    "worst_part_ranking",
    "description_length",
    "better_grammar",
    "decide_split_or_combine",
    "worstness_mdl_ranking",
    "spearman",
]
