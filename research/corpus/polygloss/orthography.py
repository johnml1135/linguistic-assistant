"""Per-language tokenizer exceptions for the PolyGloss pilot.

`corpus.ebible.read.tokenize()` is a general-purpose, script-agnostic tokenizer shared by the 8
production eBible languages — it deliberately hardcodes no language's quirks. But some orthographies
use a character as part of a word (a length mark, a tone mark, ...) that `tokenize()`'s default
word-character class (`\\w` + Unicode combining marks) doesn't cover, because that character is
categorized as punctuation rather than a letter/mark. Left alone, `tokenize()` silently splits such
words in two — both in the training corpus AND in gold scoring — with no error, just quietly wrong
segmentation.

`EXTRA_WORD_CHARS` is the opt-in list of exceptions, looked up by glottocode wherever a pilot
language's rows get tokenized (`build.py`, `to_gold.py`), so `tokenize()` itself stays untouched by
default and every other caller (the 8 production languages included) is unaffected.

Discovered via Cayuga (cayu1261, Iroquoian): its orthography uses a colon `:` as a vowel-length mark
inside a word (e.g. `"ahóhto:'"` is ONE word, not two) — colon is Unicode category `Po` (punctuation),
not `\\w`. See `Polygloss_integration.md` and `corpus/polygloss/out/PILOT_REPORT.md` for how this was
diagnosed (67% of Cayuga's gold misses were literally shattered by `tokenize()` at that character).
"""

from __future__ import annotations

EXTRA_WORD_CHARS: dict[str, str] = {
    "cayu1261": ":",  # vowel-length mark, e.g. ahóhto:', ekhni:no', ne:kyé
}


def extra_word_chars_for(glottocode: str) -> str:
    return EXTRA_WORD_CHARS.get(glottocode, "")
