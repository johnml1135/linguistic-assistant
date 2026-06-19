"""Curate a ParseGym from the frozen gold + scripture — real predicaments, known good responses.

Mines the four stages from data we already trust, so the *answers* are grounded (not invented):
  cold_start  — frequent scripture words with no stem in the lexicon → add a root, or (no gloss) ask /
                "I don't know".
  hidden_rule — a near-lemma exists but the surface stem differs irregularly → add a stem ALLOMORPH
                (LibLCM MoStemAllomorph — HC's easy path), or ask if the lemma is ambiguous.
  homophone   — forms the gold flags as homographs (>1 POS) → ask the speaker which sense (meaning_choice).
  overparse   — forms with several root+affix decompositions the grammar would all accept → prune to the
                one whose root POS matches the gold, or rank with the speaker, or "I don't know".

The mix is deliberately balanced across stages and seeded across difficulties/phases, and includes a
fraction of genuine `unknown` answers. Output: `parsegym/gym/<pair>.jsonl` (a curated, tracked seed —
grow it toward 100–600 by raising --target and adding sources). Run: `python parsegym/curate.py --pair spa`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from parsegym.questions import get as q  # noqa: E402
from parsegym.schema import Scenario, Solution, write_jsonl  # noqa: E402

from golden.reference.compile import EBIBLE, FROZEN, PAIR_DIR  # noqa: E402

GYM = _THIS.parent / "gym"
LANG = {"spa": "Spanish", "ind": "Indonesian", "tgl": "Tagalog", "swh": "Swahili"}

# What each stage assesses + which skills resolve it (parsegym_resolve is the triage skill that picks
# fix/unknown/ask_speaker; the second skill is the domain skill that would generate the fix).
STAGE_META: dict[str, tuple[str, list[str]]] = {
    "cold_start":  ("lexical_bootstrapping",   ["parsegym_resolve", "gloss_reference"]),
    "hidden_rule": ("irregular_morphology",    ["parsegym_resolve", "propose_rule"]),
    "homophone":   ("sense_disambiguation",    ["parsegym_resolve", "gloss_reference"]),
    "overparse":   ("segmentation_precision",  ["parsegym_resolve", "propose_rule"]),
}


def _load(pair: str):
    gold = json.loads((FROZEN / pair / "golden_set.json").read_text(encoding="utf-8"))
    sp = FROZEN / pair / "golden_senses.json"
    senses = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    return gold, senses


def _scripture_index(pair: str, *, max_ex: int = 3) -> tuple[Counter, dict]:
    """Word frequency + up to ``max_ex`` example (sentence, english) occurrences per word — enough
    context for an LLM to judge the word in use, not just in isolation."""
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    freqs: Counter = Counter()
    exmap: dict[str, list[dict]] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            tgt = d.get("tgt", [])
            freqs.update(t.lower() for t in tgt)
            sent = " ".join(tgt)
            en = " ".join(d.get("src", []))
            for t in {t.lower() for t in tgt}:
                lst = exmap.setdefault(t, [])
                if len(lst) < max_ex:
                    lst.append({"sentence": sent, "en": en})
    return freqs, exmap


def _affix_forms(gold: dict) -> tuple[list[str], list[str]]:
    suf = [a["affix"] for a in gold.get("affixes", []) if a.get("morph_type") == "suffix"]
    pre = [a["affix"] for a in gold.get("affixes", []) if a.get("morph_type") == "prefix"]
    return suf, pre


def _decompositions(word: str, lemset: set[str], suf: list[str], pre: list[str]) -> list[tuple[str, str, str]]:
    """(root, affix, side) splits where the root is a known lemma — the grammar's candidate analyses."""
    out = []
    for a in suf:
        if a and word.endswith(a) and (word[: -len(a)] in lemset):
            out.append((word[: -len(a)], a, "suffix"))
    for a in pre:
        if a and word.startswith(a) and (word[len(a):] in lemset):
            out.append((word[len(a):], a, "prefix"))
    return out


def _ex(exmap: dict, word: str) -> tuple[str, str]:
    """Primary (sentence, english) for the target word."""
    lst = exmap.get(word) or [{"sentence": "", "en": ""}]
    return lst[0]["sentence"], lst[0]["en"]


def curate(pair: str, *, target: int = 150) -> list[Scenario]:
    gold, senses = _load(pair)
    pos, gloss = gold.get("pos", {}), gold.get("glosses", {})
    lemset = set(gold.get("lemmas", []))
    suf, pre = _affix_forms(gold)
    freqs, example = _scripture_index(pair)
    per = max(1, target // 4)
    out: list[Scenario] = []
    lname = LANG.get(pair, pair)
    seen: set[str] = set()

    def add(s: Scenario):
        # fill the assessment metadata + multi-occurrence context from the stage + corpus
        s.assesses, s.skills = STAGE_META[s.stage]
        s.examples = example.get(s.word, [])
        s.validate()
        out.append(s)
        seen.add(s.word)

    ranked = [w for w, _ in freqs.most_common() if len(w) >= 2 and w.isalpha()]

    # --- cold_start: words with no stem in the lexicon and no clean decomposition --------------------
    # Frequent words first (fix / ask), then a reserved tail of rare no-gloss hapaxes (genuine
    # "I don't know") so all three answer kinds are represented rather than crowded out.
    def cold_scenario(w: str) -> Scenario | None:
        if w in seen or w in lemset or _decompositions(w, lemset, suf, pre):
            return None
        sent, en = _ex(example, w)
        g = gloss.get(w)
        if g:
            sol = Solution("fix", action=f"Add LexEntry root “{w}” with gloss ‘{g}’ (POS {pos.get(w, '?')}).",
                           mechanism="LexEntry (MoStemMsa)", rationale="Reference gives a confident gloss.")
            diff = "easy" if len(w) <= 7 else "medium"
        elif en and freqs[w] >= 2:
            qq = q("elicit_meaning")
            sol = Solution("ask_speaker", question_id=qq.id, ask=qq.render(form=w),
                           rationale="No reference gloss; the verse English is a hint, not proof — confirm with the speaker.")
            diff = "medium"
        else:
            sol = Solution("unknown",
                           rationale="Hapax, no reference gloss, no stem — the single verse can't isolate its meaning. "
                                     "Defer until it recurs or a speaker is available.")
            diff = "hard"
        return Scenario(id=f"{pair}:cold:{w}", language=lname, stage="cold_start", difficulty=diff,
                        phase="early", word=w, sentence=sent, sentence_en=en, partial_parse=[],
                        observations=[f"freq={freqs[w]}", "in_lexicon=False", f"gloss={g or '∅'}"],
                        solution=sol, provenance={"source": "scripture∖lexicon"})

    reserve = max(2, per // 4)
    n = 0
    for w in ranked:                                   # frequent → mostly fix / ask
        if n >= per - reserve:
            break
        s = cold_scenario(w)
        if s:
            add(s); n += 1
    for w in (w for w in reversed(ranked) if freqs[w] == 1 and not gloss.get(w)):  # rare tail → unknown
        if n >= per:
            break
        s = cold_scenario(w)
        if s:
            add(s); n += 1

    # --- hidden_rule: a near-lemma exists but the surface stem differs irregularly -> stem allomorph --
    n = 0
    for w in ranked:
        if n >= per or w in seen or w in lemset or _decompositions(w, lemset, suf, pre):
            continue
        cands = [lm for lm in lemset if len(lm) >= 4 and len(w) >= 4 and lm[:3] == w[:3] and lm != w
                 and abs(len(lm) - len(w)) <= 4]
        if not cands:
            continue
        cands.sort(key=lambda lm: -len(_common_prefix(lm, w)))
        sent, en = _ex(example, w)
        stem = _common_prefix(cands[0], w) or w[:3]
        if len(cands) == 1:
            lm = cands[0]
            sol = Solution("fix",
                           action=f"Add stem allomorph “{stem}…” to LexEntry “{lm}” (‘{gloss.get(lm, '?')}’) so HC parses “{w}”.",
                           mechanism="MoStemAllomorph", rationale="One plausible lemma; irregular stem, not a new word.")
            diff = "hard"
        else:
            qq = q("allomorph_check")
            sol = Solution("ask_speaker", question_id=qq.id, ask=qq.render(a=w, b=cands[0]),
                           options=tuple(cands[:5]),
                           rationale="Several lemmas could own this irregular stem — one allomorph or a new entry?")
            diff = "hard"
        add(Scenario(id=f"{pair}:hidden:{w}", language=lname, stage="hidden_rule", difficulty=diff,
                     phase="late", word=w, sentence=sent, sentence_en=en, partial_parse=[],
                     observations=[f"candidate lemmas={cands[:5]}", f"shared stem=“{stem}”"],
                     solution=sol, provenance={"source": "near-lemma stem alternation"}))
        n += 1

    # --- homophone: gold flags >1 POS / several senses -> ask which sense ------------------------------
    n = 0
    for w, inv in sorted(senses.items(), key=lambda kv: -freqs.get(kv[0], 0)):
        if n >= per or w in seen:
            continue
        sns = inv.get("senses", [])
        if not (inv.get("homograph") or len(sns) >= 3):
            continue
        sent, en = _ex(example, w)
        opts = tuple(sns[:8]) if len(sns) >= 2 else tuple(inv.get("pos", []))
        if len(opts) < 2:
            continue
        qq = q("meaning_choice")
        sol = Solution("ask_speaker", question_id=qq.id, ask=qq.render(form=w, options="; ".join(opts)),
                       options=opts, rationale="Multiple senses/POS; context narrows but the speaker confirms which.")
        add(Scenario(id=f"{pair}:homophone:{w}", language=lname, stage="homophone", difficulty="medium",
                     phase="late", word=w, sentence=sent, sentence_en=en, partial_parse=[],
                     observations=[f"POS={inv.get('pos')}", f"senses={sns[:8]}", f"homograph={inv.get('homograph')}"],
                     solution=sol, provenance={"source": "golden_senses homograph"}))
        n += 1

    # --- overparse: several root+affix analyses the grammar would all accept --------------------------
    n = 0
    for w in ranked:
        if n >= per or w in seen:
            continue
        d = _decompositions(w, lemset, suf, pre)
        if len(d) < 2:
            continue
        sent, en = _ex(example, w)
        analyses = [f"{r}+{a}({side})" for r, a, side in d]
        gp = pos.get(w)
        good = [x for (r, a, side), x in zip(d, analyses) if gp and pos.get(r) == gp]
        if good:
            sol = Solution("fix",
                           action=f"Keep “{good[0]}”; prune the others — only the analysis whose root POS matches {gp} is licit.",
                           mechanism="AffixTemplate slot / MSA requiredPartsOfSpeech",
                           rationale="Gold POS disambiguates the competing splits.")
            diff = "medium"
        else:
            qq = q("acceptability_rank")
            sol = Solution("ask_speaker", question_id=qq.id, ask=qq.render(options="; ".join(analyses[:6])),
                           options=tuple(analyses[:6]),
                           rationale="Gold POS doesn't single one out — let the speaker rank acceptability.")
            diff = "hard"
        add(Scenario(id=f"{pair}:overparse:{w}", language=lname, stage="overparse", difficulty=diff,
                     phase="late", word=w, sentence=sent, sentence_en=en, partial_parse=analyses,
                     observations=[f"{len(d)} competing analyses", f"gold POS={gp or '∅'}"],
                     solution=sol, provenance={"source": "multi-decomposition"}))
        n += 1

    return out[:target]


def _common_prefix(a: str, b: str) -> str:
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--target", type=int, default=150, help="scenarios to curate (100–600)")
    args = ap.parse_args(argv)
    scen = curate(args.pair, target=args.target)
    write_jsonl(scen, GYM / f"{args.pair}.jsonl")
    by_stage = Counter(s.stage for s in scen)
    by_kind = Counter(s.solution.kind for s in scen)
    print(f"[{args.pair}] ParseGym: {len(scen)} scenarios → parsegym/gym/{args.pair}.jsonl")
    print(f"  stages: {dict(by_stage)}")
    print(f"  answers: {dict(by_kind)}  (fix / ask_speaker / unknown)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
