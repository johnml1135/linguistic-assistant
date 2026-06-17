"""Offline fixture: a reordered+inflected source/target pair + a toy bidix.

Demonstrates the three behaviors with no Apertium binary, no HC, no network:
- a reference found despite reordering + inflection,
- a missing concept,
- a number-agreement mismatch.
"""

from __future__ import annotations

from .bidix import Bidix, BidixEntry
from .stream import parse_stream

# Reference (English-ish) sentence: "(the) shepherds saw a sheep (and) love"
#   shepherd<n><pl>  see<v><past>  sheep<n><sg>  love<n><sg>(not in bidix)
SOURCE_STREAM = "^shepherds/shepherd<n><pl>$ ^saw/see<v><past>$ ^sheep/sheep<n><sg>$ ^love/love<n><sg>$"

# Target (toy vernacular), REORDERED (verb-first) and INFLECTED — and 'sheep' is PLURAL here:
#   ona<v><past>  mchungaji<n><pl>  kondoo<n><pl>
TARGET_STREAM = "^aliona/ona<v><past>$ ^wachungaji/mchungaji<n><pl>$ ^kondoo/kondoo<n><pl>$"


def fixture_bidix() -> Bidix:
    return Bidix(
        entries=[
            BidixEntry(reference=("shepherd", ("n",)), vernacular=("mchungaji", ("n",))),
            BidixEntry(reference=("see", ("v",)), vernacular=("ona", ("v",))),
            BidixEntry(reference=("sheep", ("n",)), vernacular=("kondoo", ("n",))),
            # 'love' deliberately absent -> missing concept
        ]
    )


def fixture_source_tokens():
    return parse_stream(SOURCE_STREAM)


def fixture_target_tokens():
    return parse_stream(TARGET_STREAM)
