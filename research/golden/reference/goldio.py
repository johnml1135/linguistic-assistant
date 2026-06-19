"""Read/write the frozen golden set as reviewable JSONL + LIFT — lexemes and wordforms kept separate.

The golden set is a handful of line-oriented files a person (or `grep`, or a review) can read:

  lexicon.jsonl   {word, pos, pos_all, senses, homograph, in_scripture}  — one ENTRY per LEMMA (real
                  senses only; inflected forms are NOT here)
  lexicon.lift    the same lexicon as FLEx-native LIFT XML (stems + affix entries)
  wordforms.jsonl {surface, lemma, pos, features, source}                — the morphology gold: every
                  scripture wordform → its (lemma + FsFeatStruc) analysis
  grammar_rules.jsonl {affix, morph_type, features, inflection, count}   — the affix→function rules
  phonology.jsonl     segment inventory + natural classes + rules
  key_terms.jsonl     {term}            meta.json   summary       golden_scripture.tsv  wordform view

`load_gold(pair)` reconstructs the in-memory dict consumers expect (pos, glosses, lemmas, lexicon, senses,
affixes, wordforms, …), so a lemma's gloss/POS comes from its entry and inflected forms resolve via lemma.
"""

from __future__ import annotations

import json
from pathlib import Path

from golden.reference import lift

_THIS = Path(__file__).resolve()
FROZEN = _THIS.parents[2] / "golden_sets"

# files retired by earlier layouts — removed on every write so the gold can't drift out of sync
_RETIRED = ("golden_set.json", "golden_lexicon.txt", "golden_senses.json", "senses.jsonl")


def _write_jsonl(path: Path, records) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_gold(pair: str, *, lex_entries: list[dict], wordforms: list[dict], affixes: list[dict],
               key_terms: list, meta: dict, phonology: list | None = None) -> dict:
    frozen = FROZEN / pair
    frozen.mkdir(parents=True, exist_ok=True)
    counts = {
        "lexicon.jsonl": _write_jsonl(frozen / "lexicon.jsonl", lex_entries),
        "wordforms.jsonl": _write_jsonl(frozen / "wordforms.jsonl", wordforms),
        "grammar_rules.jsonl": _write_jsonl(frozen / "grammar_rules.jsonl", affixes),
        "key_terms.jsonl": _write_jsonl(frozen / "key_terms.jsonl", ({"term": t} for t in key_terms)),
        "phonology.jsonl": _write_jsonl(frozen / "phonology.jsonl", phonology or []),
        "lexicon.lift": lift.write_lift(frozen / "lexicon.lift", pair, lex_entries, affixes),
    }
    (frozen / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    for stale in _RETIRED:
        (frozen / stale).unlink(missing_ok=True)
    return counts


def load_gold(pair: str) -> dict:
    """Reconstruct the gold dict (pos/glosses/lemmas/lexicon/senses/affixes/wordforms/…) from the files."""
    frozen = FROZEN / pair
    meta = json.loads((frozen / "meta.json").read_text(encoding="utf-8")) if (frozen / "meta.json").exists() else {}
    lex = _read_jsonl(frozen / "lexicon.jsonl")
    wordforms = _read_jsonl(frozen / "wordforms.jsonl")
    pos: dict[str, str] = {}
    glosses: dict[str, str] = {}
    senses: dict[str, dict] = {}
    lemmas: list[str] = []
    in_scripture: set[str] = set()
    for e in lex:
        w = e["word"]
        lemmas.append(w)
        if e.get("pos") and e["pos"] != "Unknown":
            pos[w] = e["pos"]
        if e.get("senses"):
            glosses[w] = e["senses"][0]
        senses[w] = {"pos": e.get("pos_all", []), "senses": e.get("senses", []),
                     "homograph": bool(e.get("homograph"))}
        if e.get("in_scripture"):
            in_scripture.add(w)
    for wf in wordforms:
        in_scripture.add(wf["surface"])
        if wf.get("pos") and wf["pos"] != "Unknown":
            pos.setdefault(wf["surface"], wf["pos"])
    lexicon = sorted(set(lemmas) | {wf["surface"] for wf in wordforms})
    return {**meta, "pos": pos, "glosses": glosses, "lemmas": sorted(set(lemmas)), "lexicon": lexicon,
            "in_scripture": sorted(in_scripture), "senses": senses, "wordforms": wordforms,
            "affixes": _read_jsonl(frozen / "grammar_rules.jsonl"),
            "key_terms": [r["term"] for r in _read_jsonl(frozen / "key_terms.jsonl")],
            "phonology": _read_jsonl(frozen / "phonology.jsonl")}
