"""Sense-picking: a model chooses a word's gloss from the aligner's ranked candidates + its verses.

The statistical aligner gives a *ranked list* of English candidates per target word; taking rank-1 is a
prior, not the answer (rank-1 is often a co-occurring function word, or one of two near-synonyms). This
step shows the model the word's verses + the top-k candidates and asks it to pick the real meaning — or
say "function word" / "I don't know". It runs against any harness client (Gemma via Ollama, Qwen via
vLLM, Opus, or mock), so the same skill calibrates a local model and the frontier one.

Run: `python golden/reference/sense_pick.py --pair spa --endpoint mock --sample 8`
     `uv run python golden/reference/sense_pick.py --pair spa --endpoint ollama --sample 30`  (Gemma)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from propose.harness import build_client  # noqa: E402
from propose.harness.base import Message  # noqa: E402

from gold.align_gloss import _verses  # noqa: E402
from gold.compile import PAIR_DIR  # noqa: E402

_SKILL = (_THIS.parents[1] / "skills" / "sense_pick.md").read_text(encoding="utf-8")
LANG = {"spa": "Spanish", "ind": "Indonesian", "tgl": "Tagalog", "swh": "Swahili"}


def _prompt(word: str, lang: str, contexts: list[tuple[str, str]], candidates: list[tuple[str, float]]) -> str:
    ctx = "\n".join(f"  - {t}\n    (EN: {e})" for t, e in contexts[:4])
    cands = "\n".join(f"  {i+1}. {g}  (aligner prob {p})" for i, (g, p) in enumerate(candidates))
    return (f"Language: {lang}\nTarget word: {word}\n\nVerses it occurs in:\n{ctx}\n\n"
            f"Aligner's ranked candidate glosses:\n{cands}\n\nReturn the JSON described above.")


def pick(client, word: str, lang: str, contexts, candidates) -> dict:
    res = client.complete([Message("system", _SKILL), Message("user", _prompt(word, lang, contexts, candidates))])
    txt = res.text.strip()
    try:
        i, j = txt.find("{"), txt.rfind("}")
        return json.loads(txt[i:j + 1]) if i >= 0 else {"gloss": None, "raw": txt}
    except Exception:
        return {"gloss": None, "raw": txt}


# sense_pick's coarse POS → LibLCM PartOfSpeech (language-agnostic; no English tagger involved)
_POS_LIBLCM = {"noun": "Noun", "verb": "Verb", "adj": "Adjective", "adv": "Adverb",
               "name": "Proper noun", "function": "Unknown", "unknown": "Unknown"}


def assess(pair: str, *, endpoint: str = "mock", words: list[str] | None = None, sample: int = 200,
           k: int = 6, backend: str = "hmm") -> dict[str, dict]:
    """word → Gemma's assessment {gloss, gloss_en, pos (LibLCM), conf, alt} over the aligner's ranked
    candidates + the word's verses. Pivot-language-agnostic — the model reads whatever the verses are in."""
    from align.aligner import align as align_corpus
    verses = _verses(pair)
    gt, _used = align_corpus([(s, t) for s, t in verses], backend=backend, allow_cooccur_fallback=False)
    occ: dict[str, list[tuple[str, str]]] = {}
    for s, t in verses:
        for w in set(t):
            if w in gt.table and len(occ.get(w, [])) < 4:
                occ.setdefault(w, []).append((" ".join(t), " ".join(s)))
    client = build_client(endpoint)
    cand_words = words if words is not None else [w for w, c in gt.table.items() if c and len(w) > 2][:sample]
    out: dict[str, dict] = {}
    for w in cand_words:
        if w not in gt.table or not gt.table[w]:
            continue
        cands = [(cg.source_word, round(cg.prob, 2)) for cg in gt.table[w][:k]]
        p = pick(client, w, LANG.get(pair, pair), occ.get(w, []), cands)
        out[w] = {"gloss": p.get("gloss_en") or p.get("gloss"), "pos": _POS_LIBLCM.get(p.get("pos", ""), "Unknown"),
                  "conf": p.get("confidence", "low"), "alt": p.get("alt", []), "aligner_top1": cands[0][0]}
    return out


def run(pair: str, *, endpoint: str = "mock", sample: int = 12, k: int = 6, backend: str = "hmm") -> list[dict]:
    a = assess(pair, endpoint=endpoint, sample=sample, k=k, backend=backend)
    return [{"word": w, "aligner_top1": v["aligner_top1"], "pick": v} for w, v in a.items()]


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--endpoint", default="mock", help="mock | ollama (Gemma) | vllm (Qwen) | opus")
    ap.add_argument("--sample", type=int, default=10)
    args = ap.parse_args(argv)
    rows = run(args.pair, endpoint=args.endpoint, sample=args.sample)
    print(f"[{args.pair}] sense-picking via '{args.endpoint}' ({len(rows)} words):")
    for r in rows:
        p = r["pick"]
        print(f"  {r['word']:14} aligner→{r['aligner_top1']:12} | picked: {p.get('gloss')!r:14} "
              f"[{p.get('pos','?')}/{p.get('conf','?')}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
