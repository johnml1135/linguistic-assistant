"""Held-out PolyGloss rows -> `golden_sets/<pair>/` gold, via the existing `gold/goldio.py` schema.

Only wordforms with an identified lexical stem (see `convert.stem_and_features`) become gold
records — a word whose every morph is a Leipzig-capitalized grammatical tag (e.g. a bare particle)
carries no lemma to score against and is intentionally skipped, not guessed at.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from gold import goldio  # noqa: E402

from corpus.ebible.read import tokenize  # noqa: E402

from .convert import stem_and_features, to_morphwords  # noqa: E402
from .orthography import extra_word_chars_for  # noqa: E402
from .schema import PolyglossRow  # noqa: E402


def _parse_surface(surface: str, *, extra_word_chars: str = "") -> str:
    """Normalize a gold word's surface the same way `corpus.ebible.read.tokenize` normalizes every
    training token (lowercase; keep only word chars + Unicode marks, plus any per-language
    `extra_word_chars` exception — see `corpus/polygloss/orthography.py`) — WITHOUT touching
    `tokenize` itself, which is shared production code for the current 8 eBible languages. Gold
    surfaces come straight from the segmentation tier at its original casing/punctuation; training
    tokens went through `tokenize()`. Skipping this step means a gold word can literally never appear
    in the induced grammar's vocabulary for reasons that have nothing to do with morphology (e.g.
    `"Wowōt"` vs. training's `"wowōt"`) — verified on Cayuga: only 36% of raw gold surfaces occurred
    in that language's own training tokens before `extra_word_chars` was added for its length-mark
    colon. See Polygloss_integration.md."""
    toks = tokenize(surface, extra_word_chars=extra_word_chars)
    return "".join(toks) if toks else surface.lower()


def rows_to_wordforms_and_lexicon(rows: list[PolyglossRow], *, glottocode: str) -> tuple[list[dict], list[dict]]:
    """-> (wordforms.jsonl records, lexicon.jsonl records), deduplicating lexicon entries by lemma.

    ``lemma`` is the stem's surface form (not a synthetic id) — matching the existing gold
    convention where `gold/goldio.py::load_gold` keys a word's gloss off `lex_entry["word"]`
    directly (`glosses[w] = e["senses"][0]`). Two different PolyGloss stems that happen to share a
    surface form collide the way any real homograph would; `homograph` is left `False` here since
    disambiguating that from a single sentence's worth of context isn't this loader's job.

    Each record also carries `parse_surface` — the tokenizer-normalized form `score.py` should
    actually query HC with (see `_parse_surface`); `surface` stays the original orthography for
    display/promotion.
    """
    extra = extra_word_chars_for(glottocode)
    wordforms: list[dict] = []
    lexicon: dict[str, dict] = {}
    for row in rows:
        for word in to_morphwords(row):
            stem, features = stem_and_features(word)
            if stem is None:
                continue  # no lexical content to anchor a lemma on (e.g. a bare grammatical particle)
            lemma = stem.form
            wordforms.append({
                "surface": word.surface,
                "parse_surface": _parse_surface(word.surface, extra_word_chars=extra),
                "lemma": lemma,
                "pos": "Unknown",
                "features": sorted(features),
                "source": f"polygloss:{row.id}",
            })
            if lemma not in lexicon:
                lexicon[lemma] = {
                    "word": stem.form,
                    "pos": "Unknown",
                    "pos_all": [],
                    "senses": [stem.gloss],
                    "homograph": False,
                    "in_scripture": True,  # "in_scripture" here means "attested in the held-out sample"
                }
    return wordforms, list(lexicon.values())


def write_pilot_gold(pair_key: str, rows: list[PolyglossRow], *, glottocode: str, language: str, source: str) -> dict:
    """Write a new `golden_sets/<pair_key>/` directory (e.g. `pair_key="pg_vera1241"`). Only the
    wordform/lexicon tiers are populated — `inflection_classes`/`phonology`/`key_terms` are left
    empty; PolyGloss doesn't give us those, and inducing them is `induce/`'s job, not this loader's."""
    wordforms, lex_entries = rows_to_wordforms_and_lexicon(rows, glottocode=glottocode)
    meta = {
        "language": language,
        "glottocode": glottocode,
        "source": source,
        "note": "Pilot gold from the PolyGloss corpus (hand-annotated; see Polygloss_integration.md). "
                 "Features are simplified Leipzig-tag lists, not yet gold/inflection.py::canon()-compatible.",
    }
    return goldio.write_gold(
        pair_key,
        lex_entries=lex_entries,
        wordforms=wordforms,
        affixes=[],
        inflection_classes=[],
        key_terms=[],
        meta=meta,
    )
