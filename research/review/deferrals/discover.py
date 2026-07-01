"""Concept-driven lexeme discovery — "we have no word for HAND; go find it."

The rest of the pipeline is target-word-first ("here is an unparsed word, what is it?"). This is the
**source-anchored** complement (a Stage-2 discovery strategy): start from a reference concept the source
expresses but the vernacular lexicon does not yet realize (e.g. English `hand`), then use THOT + HC + a
**maximum-shared-span** core extractor to produce a mini report:

  "Top candidates for `hand`: **mkono** (×110) — shared core `kono` — best-guess parse `m-kono` /
   `mi-kono` (PL) — example verses: …  →  propose: add lexeme `kono` = hand."

The report IS a deferral ticket (`build_ticket` / `render`), so it flows through the existing review +
`deltas/` path. Reuses `align/` (THOT), `golden/hc` (best-guess parse), and the gold.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align import align  # noqa: E402
from gold.compile import EBIBLE, PAIR_DIR  # noqa: E402
from gold.goldio import load_gold  # noqa: E402

# compact English function-word stoplist — concepts worth discovering are content words
STOP = {
    "the", "a", "an", "of", "to", "and", "in", "that", "he", "it", "for", "was", "is", "his", "with",
    "they", "not", "you", "but", "be", "as", "him", "this", "had", "have", "i", "we", "their", "them",
    "she", "her", "on", "at", "by", "from", "which", "who", "all", "will", "are", "were", "or", "so",
    "if", "then", "when", "there", "out", "up", "what", "shall", "unto", "into", "my", "your", "our",
    "me", "us", "thy", "thee", "ye", "o", "也", "did", "do", "has", "been", "would", "may", "no", "yes",
}


def _shared_core(words: list[str], min_len: int = 3) -> tuple[str, int]:
    """Maximum shared span: the substring (≥ min_len) that maximises **coverage × length** — the root is
    both long AND common, so this beats a short high-coverage prefix fragment (the `disciples→'wan'`
    trap) and a long low-coverage accident. For [mkono, mikono, mkononi] → ('kono', 3) (strips the
    `m-/mi-` class prefixes); for [wayahudi, myahudi, kiyahudi] → ('yahudi', 3). Returns ('', 0) when
    nothing is shared by ≥2 candidates."""
    counts: Counter = Counter()
    for w in set(words):
        seen = set()
        for i in range(len(w)):
            for j in range(i + min_len, len(w) + 1):
                s = w[i:j]
                if s not in seen:
                    seen.add(s)
                    counts[s] += 1
    shared = {s: c for s, c in counts.items() if c >= 2}
    if not shared:
        return "", 0
    best = max(shared.items(), key=lambda kv: (kv[1] * len(kv[0]), len(kv[0])))
    return best[0], best[1]


def load_corpus(pair: str, sample: int = 0) -> list[tuple[str, list[str], list[str]]]:
    rows = []
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            rows.append((d.get("ref", ""), [w.lower() for w in d["src"]],
                         [t.lower() for t in d["tgt"] if t.isalpha()]))
        if sample and len(rows) >= sample:
            break
    return rows


def _known_english(gold: dict) -> set[str]:
    """English words the vernacular lexicon already realizes (so we don't 're-discover' them)."""
    known: set[str] = set()
    for g in gold.get("glosses", {}).values():
        known.update(t for t in str(g).lower().replace(";", " ").replace(",", " ").split() if len(t) > 1)
    return known


def candidates_for(en: str, by_src: dict[str, list[str]], freqs: Counter, *, top: int = 8) -> list[tuple[str, int]]:
    """Target words aligned to the concept (its singular/plural source forms), ranked by frequency."""
    forms = {en, en + "s", en.rstrip("s")}
    cands: Counter = Counter()
    for f in forms:
        for w in by_src.get(f, []):
            cands[w] = freqs.get(w, 0)
    return cands.most_common(top)


def discover_concept(pair: str, en: str, *, by_src, freqs, rows, model=None, pf=None,
                     n_examples: int = 3) -> dict:
    """Build the mini report for one missing concept."""
    cands = candidates_for(en, by_src, freqs)
    forms = [w for w, _ in cands]
    core, core_cov = _shared_core(forms)
    # best-guess HC parse of the candidate surfaces (may be empty → 'unknown lexeme')
    parses: dict[str, list] = {}
    if model is not None and forms:
        from engine.hc import gloss_seq, run_parse
        raw = run_parse(model, forms, templated=False, phon_feats=pf, chunk_timeout=20)
        parses = {w: ["-".join(gloss_seq(a)) for a in raw.get(w, [])[:2]] for w in forms}
    top_form = forms[0] if forms else None
    examples = []
    if top_form:
        for ref, src, tgt in rows:
            if top_form in tgt:
                examples.append({"ref": ref, "text": " ".join(tgt),
                                 "best_guess": parses.get(top_form) or ["(no parse — unknown lexeme)"]})
            if len(examples) >= n_examples:
                break
    return {"concept": en, "candidates": [{"form": w, "count": c, "parse": parses.get(w) or []}
                                          for w, c in cands],
            "shared_core": core, "core_coverage": core_cov, "best_form": top_form,
            "proposed_lexeme": core or top_form, "examples": examples}


def missing_concepts(rows, gt, gold: dict, *, top: int = 20) -> tuple[list[str], dict, Counter]:
    """Frequent English content concepts whose aligned target words carry NO known gloss — i.e. concepts
    the vernacular lexicon does not yet realize. Returns (concepts, by_src, target_freqs)."""
    en_freq: Counter = Counter()
    tgt_freq: Counter = Counter()
    for _, src, tgt in rows:
        en_freq.update(w for w in src if w.isalpha() and len(w) > 2 and w not in STOP)
        tgt_freq.update(tgt)
    by_src: dict[str, list[str]] = defaultdict(list)
    for w, _cands in gt:                                  # GlossTable: target_word -> [CandidateGloss]
        best = gt.best(w)
        if best:
            by_src[best.source_word].append(w)
    known_en = _known_english(gold)
    glossed_lemmas = set(gold.get("glosses", {}))
    missing = []
    for en, _ in en_freq.most_common():
        if en in known_en:                                # already realized somewhere → not missing
            continue
        cands = [w for w in by_src.get(en, []) if w not in glossed_lemmas]
        if cands:                                         # the source uses it AND we have an unglossed target
            missing.append(en)
        if len(missing) >= top:
            break
    return missing, by_src, tgt_freq


def run(pair: str, *, backend: str = "eflomal", top: int = 15, ticket: bool = False, sample: int = 0) -> dict:
    gold = load_gold(pair)
    rows = load_corpus(pair, sample)
    gt, used = align([(s, t) for _, s, t in rows], backend=backend,
                     allow_cooccur_fallback=(backend == "cooccur"))
    concepts, by_src, freqs = missing_concepts(rows, gt, gold, top=top)
    model = pf = None
    try:
        from gold.hc_coverage import build_reference_model, hc_available
        from gold.phonology_gold import phon_feats
        if hc_available():
            model = build_reference_model(pair)
            pf = phon_feats(pair, model.charset)
    except Exception:
        model = pf = None
    reports = [discover_concept(pair, en, by_src=by_src, freqs=freqs, rows=rows, model=model, pf=pf)
               for en in concepts]
    reports = [r for r in reports if r["candidates"]]
    tickets = 0
    if ticket:
        tickets = _ticket(pair, reports, gold)
    return {"pair": pair, "backend": used, "missing_concepts": len(reports),
            "reports": reports, "ticketed": tickets}


def to_defer_record(report: dict) -> dict:
    """A concept report → a defer record `build_ticket` consumes (a lexeme_gloss deferral, concept-anchored)."""
    return {"word": report["proposed_lexeme"] or report["best_form"] or "?",
            "gloss": "", "aligner_top1": report["concept"],
            "candidates": [c["form"] for c in report["candidates"]],
            "conf": "low", "decision": "defer", "source": "concept-discovery"}


def _ticket(pair: str, reports: list[dict], gold: dict) -> int:
    from .build import build_ticket
    from .store import TicketStore
    store = TicketStore(pair)
    built = [build_ticket(pair, to_defer_record(r), gold=gold, with_counterfactuals=False) for r in reports]
    n = store.upsert(built)
    store.save()
    return n


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=["spa", "ind", "tgl", "swh"])
    ap.add_argument("--backend", default="eflomal", help="eflomal (THOT) | cooccur (offline)")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--ticket", action="store_true", help="emit deferral tickets for the reports")
    args = ap.parse_args(argv)
    s = run(args.pair, backend=args.backend, top=args.top, ticket=args.ticket, sample=args.sample)
    print(f"[{args.pair}] concept-driven lexeme discovery ({s['backend']}): "
          f"{s['missing_concepts']} missing concepts found")
    for r in s["reports"][:12]:
        cands = ", ".join(f"{c['form']}(×{c['count']})" for c in r["candidates"][:4])
        print(f"  '{r['concept']}' → core '{r['shared_core']}' | candidates: {cands}")
        for ex in r["examples"][:1]:
            print(f"      e.g. {ex['ref']}: {ex['text'][:70]}…  parse={ex['best_guess']}")
    if args.ticket:
        print(f"  → {s['ticketed']} deferral tickets written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
