"""Apertium-alignment bridge: morphology-aware cross-lingual reference-finding + FLExTrans interop.

Bidix + Hermit Crab lemma analyses → locate a source concept in an unaligned target sentence (input to
parallel-translation QA). Sense links are the primary `bilingual/*` store; the Apertium `.dix` is a
derived artifact. No MT, no transfer rules, no Constraint Grammar. The native Apertium binary is
optional — everything here runs on plain Python.
"""

from __future__ import annotations

from .bidix import Bidix, BidixEntry, parse_bidix, serialize_bidix
from .crosswalk import Crosswalk, load_crosswalk
from .finder import Correspondence, Match, find_all, find_reference
from .flextrans import export_flextrans_bidix, import_flextrans_bidix
from .qa import Flag, assess
from .sense_links import SenseLink, build_bidix, from_change_set
from .stream import Analysis, Token, hc_analysis_to_token, parse_stream, render_stream, render_token

__all__ = [
    "Bidix",
    "BidixEntry",
    "parse_bidix",
    "serialize_bidix",
    "Crosswalk",
    "load_crosswalk",
    "Analysis",
    "Token",
    "parse_stream",
    "render_token",
    "render_stream",
    "hc_analysis_to_token",
    "SenseLink",
    "from_change_set",
    "build_bidix",
    "Correspondence",
    "Match",
    "find_reference",
    "find_all",
    "Flag",
    "assess",
    "import_flextrans_bidix",
    "export_flextrans_bidix",
]
