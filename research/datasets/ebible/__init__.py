"""eBible golden-set ingestion: fetch verse-aligned English↔target NT, read into tokenized parallel
rows, and feed the word-gloss aligner. See README.md and the `golden-pair-selection` memory.
"""

from __future__ import annotations

from .config import ENGLISH_ID, NT_BOOKS, TARGETS
from .read import VerseRow, parallel_rows, parallel_rows_from_lines, tokenize

__all__ = [
    "ENGLISH_ID",
    "TARGETS",
    "NT_BOOKS",
    "VerseRow",
    "parallel_rows",
    "parallel_rows_from_lines",
    "tokenize",
]
