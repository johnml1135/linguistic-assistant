"""Read/write the frozen golden set as reviewable JSONL — one record per line, split by kind.

A single 26 MB `golden_set.json` is impossible to eyeball or diff. Instead each golden set is a handful
of line-oriented files a person (or `grep`, or a code review) can actually read:

  lexicon.jsonl       {word, pos, gloss, is_lemma, in_scripture}   — one line per word
  grammar_rules.jsonl {affix, morph_type, features, inflection, count} — the affix→function rules
  senses.jsonl        {word, pos[], senses[], homograph}            — sense inventory (attested words)
  key_terms.jsonl     {term}                                        — unfoldingWord key terms
  meta.json           {pair, sources, stats, destination, …samples} — a single small summary object
  golden_scripture.tsv                                              — the attested validation slice (tabular)

`load_gold(pair)` reconstructs the in-memory dict the rest of the code already expects (pos, glosses,
lemmas, affixes, senses, …), so consumers swap `json.loads(golden_set.json)` → `load_gold(pair)`.
"""

from __future__ import annotations

import json
from pathlib import Path

_THIS = Path(__file__).resolve()
FROZEN = _THIS.parents[2] / "golden_sets"


def _write_jsonl(path: Path, records) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def write_gold(pair: str, *, lexicon: set, pos: dict, glosses: dict, lemmas: set,
               in_scripture: set, affixes: list, senses: dict, key_terms: list, meta: dict,
               phonology: list | None = None) -> dict:
    """Write the split JSONL golden set. Returns the file→count map."""
    frozen = FROZEN / pair
    frozen.mkdir(parents=True, exist_ok=True)
    def lex_record(w: str) -> dict:
        # sparse: only carry the fields that say something (most words have neither pos nor gloss)
        r = {"word": w}
        if pos.get(w):
            r["pos"] = pos[w]
        if glosses.get(w):
            r["gloss"] = glosses[w]
        if w in lemmas:
            r["is_lemma"] = True
        if w in in_scripture:
            r["in_scripture"] = True
        return r

    counts = {}
    counts["lexicon.jsonl"] = _write_jsonl(frozen / "lexicon.jsonl", (lex_record(w) for w in sorted(lexicon)))
    # remove superseded files from the old monolithic/JSON layout
    for stale in ("golden_lexicon.txt", "golden_senses.json", "golden_set.json"):
        (frozen / stale).unlink(missing_ok=True)
    counts["grammar_rules.jsonl"] = _write_jsonl(frozen / "grammar_rules.jsonl", affixes)
    counts["senses.jsonl"] = _write_jsonl(
        frozen / "senses.jsonl",
        ({"word": w, **inv} for w, inv in sorted(senses.items())))
    counts["key_terms.jsonl"] = _write_jsonl(frozen / "key_terms.jsonl", ({"term": t} for t in key_terms))
    counts["phonology.jsonl"] = _write_jsonl(frozen / "phonology.jsonl", phonology or [])
    (frozen / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return counts


def load_gold(pair: str) -> dict:
    """Reconstruct the gold dict (pos/glosses/lemmas/affixes/senses/key_terms/lexicon/stats) from JSONL."""
    frozen = FROZEN / pair
    meta = json.loads((frozen / "meta.json").read_text(encoding="utf-8")) if (frozen / "meta.json").exists() else {}
    pos: dict[str, str] = {}
    glosses: dict[str, str] = {}
    lemmas: list[str] = []
    lexicon: list[str] = []
    in_scripture: list[str] = []
    lex_path = frozen / "lexicon.jsonl"
    if lex_path.exists():
        for line in lex_path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            r = json.loads(line)
            w = r["word"]
            lexicon.append(w)
            if r.get("pos"):
                pos[w] = r["pos"]
            if r.get("gloss"):
                glosses[w] = r["gloss"]
            if r.get("is_lemma"):
                lemmas.append(w)
            if r.get("in_scripture"):
                in_scripture.append(w)
    affixes = _read_jsonl(frozen / "grammar_rules.jsonl")
    senses = {r["word"]: {k: v for k, v in r.items() if k != "word"}
              for r in _read_jsonl(frozen / "senses.jsonl")}
    key_terms = [r["term"] for r in _read_jsonl(frozen / "key_terms.jsonl")]
    phonology = _read_jsonl(frozen / "phonology.jsonl")
    return {**meta, "pos": pos, "glosses": glosses, "lemmas": lemmas, "lexicon": lexicon,
            "in_scripture": in_scripture, "affixes": affixes, "senses": senses, "key_terms": key_terms,
            "phonology": phonology}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
