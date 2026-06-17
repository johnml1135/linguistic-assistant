"""Grammar-assessment scorecard (Approach A of the `assess-grammar` spec).

Deterministic, paper-backed measures over HermitCrab (`golden.LangModel` + `hc`) and LibLCM/LIFT data.
"""

from __future__ import annotations

from . import inventory, metrics
from .builders import assess_hermitcrab, assess_liblcm, assess_lift
from .scorecard import Scorecard
from .worst_part import worst_part_ranking

__all__ = [
    "metrics",
    "inventory",
    "Scorecard",
    "assess_hermitcrab",
    "assess_liblcm",
    "assess_lift",
    "worst_part_ranking",
]
