"""Resolve the LAST words from the parallel corpus alone — no Wiktionary needed.

For a vernacular word Wiktionary doesn't gloss (mostly proper nouns: `babilonia`, `babilón`…), the
scripture itself is the dictionary: pull every verse containing it + the English parallel, and the English
token that co-occurs with it — once you discount the words already explained by known glosses — is its
meaning. Proper nouns align almost 1:1 and are rare, so the signal is strong ("this means babylon!").

Method:
  1. Target = scripture words whose lemma has no gloss yet.
  2. Group inflectional variants by shared stem (babilonia / babilón / babilonios → one entity).
  3. Score each English candidate by Dice(group, e) over verses, down-weighting English tokens already
     "claimed" by other words' glosses (the "subtract what's known" step — it sharpens as more is linked).
  4. Emit the top-k candidates + a confidence; confident ones are proposed glosses (source=alignment).

Run: `python golden/reference/align_gloss.py --pair spa` (writes alignment_glosses.jsonl + prints samples).
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from gold.compile import EBIBLE, FROZEN, PAIR_DIR  # noqa: E402
from gold.goldio import load_gold  # noqa: E402
from gold.orthography import is_word  # noqa: E402

# English function words — never a content gloss. (eng-engwebp = World English Bible.)
STOP = set("the of and to a in that he was for it with as his they be at one have this from or had by not "
           "but what all were we when there an which she do their if will up other about out into has who is "
           "are you i my me on no unto shall them then so some her would him more your our us its also may "
           "every these those him her thy thee thou ye o am being been being".split())


def _verses(pair: str) -> list[tuple[list[str], list[str]]]:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                out.append(([t.lower() for t in d.get("src", [])], [t.lower() for t in d.get("tgt", [])]))
    return out


def _stem_groups(words: list[str], min_prefix: int = 5) -> list[list[str]]:
    """Cluster inflectional variants of one entity by shared prefix (babilon… → one group)."""
    groups: list[list[str]] = []
    cur: list[str] = []
    for w in sorted(words):
        if cur and len(w) >= min_prefix and len(cur[-1]) >= min_prefix and w[:min_prefix] == cur[-1][:min_prefix]:
            cur.append(w)
        else:
            if cur:
                groups.append(cur)
            cur = [w]
    if cur:
        groups.append(cur)
    return groups


def induce(pair: str, *, topk: int = 5, min_df: int = 2) -> list[dict]:
    gold = load_gold(pair)
    glosses = gold.get("glosses", {})
    wf_lemma = {w["surface"]: w["lemma"] for w in gold.get("wordforms", [])}
    return induce_from(_verses(pair), glosses, wf_lemma, topk=topk, min_df=min_df)


def induce_from(verses, glosses: dict, wf_lemma: dict, *, topk: int = 5, min_df: int = 2) -> list[dict]:
    # English tokens already "claimed" by some known gloss → discount them for the unknowns
    claims: Counter = Counter()
    for g in glosses.values():
        for t in str(g).lower().replace(",", " ").split():
            if t.isalpha():
                claims[t] += 1

    scrip = {w for _, tgt in verses for w in tgt if is_word(w)}
    targets = {w for w in scrip if (wf_lemma.get(w, w) not in glosses)}

    eng_df: Counter = Counter()
    w_verses: dict[str, set[int]] = defaultdict(set)
    verse_eng: list[set[str]] = []
    for i, (src, tgt) in enumerate(verses):
        eng = {e for e in src if e.isalpha() and len(e) > 1 and e not in STOP}
        verse_eng.append(eng)
        for e in eng:
            eng_df[e] += 1
        for w in set(tgt) & targets:
            w_verses[w].add(i)

    n_verses = max(1, len(verses))
    results = []
    for group in _stem_groups([w for w in targets if w_verses.get(w)]):
        gv: set[int] = set().union(*(w_verses[w] for w in group))
        gdf = len(gv)
        if gdf < min_df:
            continue
        cand: Counter = Counter()
        for i in gv:
            for e in verse_eng[i]:
                cand[e] += 1
        scored = []
        for e, c in cand.items():
            if eng_df[e] > 0.4 * n_verses:        # too frequent to be a specific gloss
                continue
            dice = 2 * c / (gdf + eng_df[e])
            dice /= (1 + 0.5 * claims.get(e, 0))   # discount English already claimed by known glosses
            scored.append((round(dice, 3), e, c))
        scored.sort(reverse=True)
        if not scored:
            continue
        top = scored[:topk]
        best_d, best_e, _ = top[0]
        margin = best_d - (top[1][0] if len(top) > 1 else 0.0)
        conf = "high" if best_d >= 0.45 and margin >= 0.1 else "medium" if best_d >= 0.25 else "low"
        results.append({"stem": group[0][:6], "forms": group, "group_df": gdf,
                        "best": best_e, "best_dice": best_d, "confidence": conf,
                        "candidates": [{"en": e, "dice": d, "cooc": c} for d, e, c in top]})
    results.sort(key=lambda r: -r["best_dice"])
    return results


def apply(pair: str, lex_entries: list[dict], wordforms: list[dict], attested: list[str],
          uncovered: list[str]) -> dict:
    """Fold corpus-aligned glosses into the in-memory gold: fill a known lemma that still lacks a gloss,
    and create a Proper-noun lexeme + wordforms for confidently-resolved UNCOVERED words. Mutates the
    lists; returns counts. This is what lets the corpus resolve the words Wiktionary can't."""
    glosses = {e["word"]: e["senses"][0] for e in lex_entries if e.get("senses")}
    wf_lemma = {w["surface"]: w["lemma"] for w in wordforms}
    res = induce_from(_verses(pair), glosses, wf_lemma)
    by_word = {e["word"]: e for e in lex_entries}
    covered = set(attested)
    unc = set(uncovered)
    filled = new = 0
    for r in res:
        if r["confidence"] == "low":
            continue
        best, forms = r["best"], r["forms"]
        # 1) a KNOWN lemma whose gloss is missing OR junk (a meta sense: name/initialism) → the corpus
        #    has the real meaning, so fill/correct it (the eBible beats the gold here).
        from gold.morphology import is_meta_sense
        handled = False
        for f in forms:
            e = by_word.get(wf_lemma.get(f, f))
            if not e:
                continue
            senses = e.get("senses") or []
            if not senses or is_meta_sense(senses[0]):
                e["senses"] = [best] + [s for s in senses if s != best]
                e["gloss_source"] = "alignment"
                filled += 1
                handled = True
        if handled or r["confidence"] != "high":
            continue
        # 2) UNCOVERED words (proper-noun names absent from every dictionary) → a new Proper-noun lexeme
        rep = min(forms, key=len)
        if rep not in by_word:
            ne = {"word": rep, "pos": "Proper noun", "pos_all": ["Proper noun"], "senses": [best],
                  "homograph": False, "in_scripture": True, "inflection_class": None, "stem": rep,
                  "irregular": [], "gloss_source": "alignment"}
            lex_entries.append(ne)
            by_word[rep] = ne
            new += 1
        for f in forms:
            if f not in covered:
                wordforms.append({"surface": f, "lemma": rep, "pos": "Proper noun",
                                  "features": {}, "source": "alignment"})
                covered.add(f)
                unc.discard(f)
    attested[:] = sorted(covered)
    uncovered[:] = sorted(unc)
    return {"glosses_filled": filled, "names_added": new}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args(argv)
    res = induce(args.pair)
    out = FROZEN / args.pair / "alignment_glosses.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = Counter(r["confidence"] for r in res)
    print(f"[{args.pair}] {len(res)} unknown word-groups resolved from the corpus → {out.name}")
    print(f"  confidence: {dict(by)}")
    print(f"  top {args.show} (high-confidence):")
    for r in [x for x in res if x["confidence"] == "high"][:args.show]:
        forms = "/".join(r["forms"][:3]) + ("…" if len(r["forms"]) > 3 else "")
        print(f"    {forms:24} → {r['best']:14} (dice {r['best_dice']}, {r['group_df']} verses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
