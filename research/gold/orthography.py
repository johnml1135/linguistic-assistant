"""Writing-system / tokenization layer — decide what is a WORD vs a NUMBER, PUNCTUATION or SYMBOL.

Hermit Crab parses phonological segments; digits and punctuation are not phonemes and must never enter
the lexicon or the parser. In FieldWorks/LibLCM this is the **writing system's** job: it defines the
word-forming characters, the tokenizer separates punctuation, and numerals are recognised as a token TYPE
(not morphologically parsed). Number formatting is locale-specific (CLDR): the thousands/decimal
separators differ between, e.g., English/Tagalog/Swahili (1,000.00) and Spanish/Indonesian (1.000,00).

So a clean golden lexicon contains only words. This module classifies a token and exposes the per-language
number format; `compile.py` uses it to keep numbers/punctuation/symbols OUT of the lexicon and to record
the writing system in `meta.json`.
"""

from __future__ import annotations

import re

# Per-language number format (CLDR). `group` = thousands separator(s) accepted; `decimal` = decimal mark.
WRITING_SYSTEMS: dict[str, dict] = {
    "spa": {"locale": "es", "group": [".", " ", " "], "decimal": ",", "style": "european"},
    "ind": {"locale": "id-ID", "group": [".", " ", " "], "decimal": ",", "style": "european"},
    "tgl": {"locale": "fil-PH", "group": [",", " ", " "], "decimal": ".", "style": "us"},
    "swh": {"locale": "sw", "group": [",", " ", " "], "decimal": ".", "style": "us"},
    "eng": {"locale": "en", "group": [",", " ", " "], "decimal": ".", "style": "us"},
}
DEFAULT_WS = {"locale": "und", "group": [",", ".", " ", " "], "decimal": ".", "style": "us"}

# A WORD is one or more Unicode letters, with optional single internal hyphen/apostrophe joins
# (anti-war, o'clock). No digits, no leading/trailing punctuation, no spaces, no HTML entities.
_WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*$", re.UNICODE)


def writing_system(pair: str) -> dict:
    return WRITING_SYSTEMS.get(pair, DEFAULT_WS)


def is_word(token: str) -> bool:
    return bool(token) and _WORD.match(token) is not None


def is_number(token: str, ws: dict) -> bool:
    """True if the token is a numeral in this writing system (after stripping surrounding punctuation)."""
    core = token.strip("()[]{}<>%+±°\"'‘’“”.,;:!?–—- ")
    if not core or not any(c.isdigit() for c in core):
        return False
    body = core
    for g in ws["group"]:
        body = body.replace(g, "")
    body = body.replace(ws["decimal"], "", 1)
    return body.isdigit()


def classify(token: str, ws: dict) -> str:
    """word | number | punctuation | other (mixed junk: HTML entities, quoted phrases, part-words)."""
    if is_word(token):
        return "word"
    if is_number(token, ws):
        return "number"
    if token and not any(c.isalnum() for c in token):
        return "punctuation"
    return "other"
