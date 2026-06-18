"""TDD-for-grammar cycle over the eBible-derived wordforms (Turkish, Hungarian).

Red   = held-out frequent target wordforms that do NOT parse against the current grammar.
Green = induce the affix (or stem) that makes failing forms parse — accepted ONLY if HC coverage rises.
Refactor = (assess) keep the grammar minimal; HC search explosion on bloated affix sets shows up as
           chunk timeouts → coverage drops → the gate reverts the change (an emergent Occam pressure).

Reuses the sibling golden harness: `golden.grammar.LangModel` + `golden.hc.run_parse` (the `hc` CLI).
Deterministic induction (no model needed to demonstrate the loop); the propose step is swappable for
the LLM `propose-from-evidence` skill later.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RESEARCH))

from golden.grammar import Affix, LangModel, LexEntry  # noqa: E402
from golden.hc import run_parse  # noqa: E402

EBIBLE = _RESEARCH / "golden" / "_sources" / "ebible"
PAIR_DIR = {"tur": "eng-engwebp__tur-turytc", "hun": "eng-engwebp__hun-hun"}


def load_freqs(pair: str) -> Counter:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    c: Counter = Counter()
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c.update(json.loads(line)["tgt"])
    return c


def load_glosses(pair: str) -> dict[str, str]:
    p = EBIBLE / PAIR_DIR[pair] / "glosses.tsv"
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def seed(pair: str, n_roots: int) -> tuple[LangModel, list[str], Counter]:
    freqs = load_freqs(pair)
    glosses = load_glosses(pair)
    ranked = [w for w, _ in freqs.most_common() if len(w) >= 2]
    roots = ranked[:n_roots]
    rootset = set(roots)
    model = LangModel(
        code=pair,
        lexicon=[LexEntry(form=w, gloss=glosses.get(w, "?"), count=freqs[w]) for w in roots],
        affixes=[],
    )
    # held-out test set = next frequent forms not used as roots (the Red tests)
    test = [w for w in ranked[n_roots:] if w not in rootset][:120]
    return model, test, freqs


def residue_candidates(model: LangModel, freqs: Counter, *, max_len: int = 4, min_root: int = 3) -> Counter:
    """Frequent residues after the longest known-root prefix = candidate suffixes."""
    roots = sorted({e.form for e in model.lexicon}, key=len, reverse=True)
    known = {a.form for a in model.affixes}
    cand: Counter = Counter()
    for w, f in freqs.items():
        for r in roots:
            if len(r) >= min_root and w.startswith(r) and len(w) > len(r):
                res = w[len(r):]
                if 1 <= len(res) <= max_len and res not in known:
                    cand[res] += f
                break  # longest root only
    return cand


def grow_roots(model: LangModel, freqs: Counter, *, max_new: int = 20, min_stem: int = 3) -> list[LexEntry]:
    """Refactor/Green: strip a known suffix off frequent forms → propose the stem as a new root.

    This breaks the coverage plateau: held-out forms can't parse if their stem isn't a root, no matter
    how many suffixes exist. Discovering stems from the morphology is the lever that pushes coverage up.
    """
    rootset = {e.form for e in model.lexicon}
    suffixes = sorted({a.form for a in model.affixes}, key=len, reverse=True)
    stems: Counter = Counter()
    for w, f in freqs.items():
        if len(w) < min_stem + 1:
            continue
        for s in suffixes:
            if w.endswith(s) and len(w) - len(s) >= min_stem:
                stem = w[: -len(s)]
                if stem not in rootset:
                    stems[stem] += f
                break
    return [LexEntry(form=st, gloss="?", count=c) for st, c in stems.most_common(max_new)]


def coverage(model: LangModel, words: list[str]) -> tuple[float, float]:
    res = run_parse(model, words, chunk_size=25, chunk_timeout=20, templated=False)
    parsed = [w for w in words if res.get(w)]
    amb = sum(len(res[w]) for w in parsed) / len(parsed) if parsed else 0.0
    return (len(parsed) / len(words) if words else 0.0), amb


def run(pair: str, seconds: float, n_roots: int = 300, batch: int = 4,
        test_size: int = 120, expand: int = 120) -> dict:
    """Moving-window curriculum: promote frequent forms to roots, test the next tranche, induce affixes
    to parse it (HC-gated), and when that window converges, slide to the next — real work, no spin."""
    freqs = load_freqs(pair)
    glosses = load_glosses(pair)
    ranked = [w for w, _ in freqs.most_common() if len(w) >= 2]

    roots_end = n_roots
    model = LangModel(code=pair, affixes=[],
                      lexicon=[LexEntry(form=w, gloss=glosses.get(w, "?"), count=freqs[w]) for w in ranked[:roots_end]])
    test = ranked[roots_end:roots_end + test_size]
    trend: list[dict] = []
    rejected: set[str] = set()

    cov, base_amb = coverage(model, test)
    base_cov0 = cov
    trend.append({"iter": 0, "window": 0, "affixes": 0, "roots": len(model.lexicon),
                  "coverage": round(cov, 4), "ambiguity": round(base_amb, 2), "action": "seed", "kept": True})
    print(f"[{pair}] seed: roots={len(model.lexicon)} test={len(test)} cov={cov:.3f}")

    pool = [s for s, _ in residue_candidates(model, freqs).most_common(80)]
    t0 = time.monotonic()
    it = window = stall = 0
    while time.monotonic() - t0 < seconds:
        it += 1
        if it % 3 == 0:  # root growth (morphology-derived stems)
            new_roots = grow_roots(model, freqs, max_new=25)
            model.lexicon.extend(new_roots)
            new_cov, new_amb = coverage(model, test)
            kept = new_cov > cov + 1e-9
            if not kept and new_roots:
                del model.lexicon[-len(new_roots):]
            else:
                cov = max(cov, new_cov)
            action, label = f"roots+{len(new_roots)}", f"+{len(new_roots)} roots"
        else:  # affix induction
            pool = [s for s in pool if s not in rejected]
            if not pool:
                pool = [s for s, _ in residue_candidates(model, freqs).most_common(120)
                        if s not in rejected and s not in {a.form for a in model.affixes}]
            if not pool:
                stall += 1
                if stall >= 2:  # window converged → slide to the next tranche (productive, no spin)
                    if roots_end + test_size >= len(ranked):
                        break  # walked the whole frequent vocabulary
                    window += 1
                    model.lexicon.extend(
                        LexEntry(form=w, gloss=glosses.get(w, "?"), count=freqs[w]) for w in test)  # promote tested forms to roots
                    roots_end += test_size
                    test = ranked[roots_end:roots_end + test_size]
                    cov, _ = coverage(model, test)
                    pool = [s for s, _ in residue_candidates(model, freqs).most_common(120)
                            if s not in {a.form for a in model.affixes}]
                    rejected.clear()
                    stall = 0
                    trend.append({"iter": it, "window": window, "affixes": len(model.affixes),
                                  "roots": len(model.lexicon), "coverage": round(cov, 4),
                                  "ambiguity": 0.0, "action": f"slide->window{window}", "kept": True})
                    print(f"[{pair}] it{it}: slide to window {window} "
                          f"(roots={len(model.lexicon)} test={len(test)} cov={cov:.3f})")
                continue
            take, pool = pool[:batch], pool[batch:]
            model.affixes.extend(Affix(form=s, gloss=f"-{s}", kind="suffix", count=freqs.get(s, 0)) for s in take)
            new_cov, new_amb = coverage(model, test)
            kept = new_cov > cov + 1e-9
            if not kept:
                del model.affixes[-len(take):]
                rejected.update(take)
            else:
                cov = new_cov
                stall = 0
            action, label = "add:" + ",".join(take), "+[" + " ".join(take) + "]"
        trend.append({"iter": it, "window": window, "affixes": len(model.affixes), "roots": len(model.lexicon),
                      "coverage": round(new_cov, 4), "ambiguity": round(new_amb, 2), "action": action, "kept": kept})
        print(f"[{pair}] it{it} w{window}: {label} -> cov={new_cov:.3f} amb={new_amb:.1f} "
              f"{'KEEP' if kept else 'revert'}  ({len(model.affixes)} aff / {len(model.lexicon)} roots)")
    base_cov = base_cov0

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{pair}_trend.jsonl").write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in trend), encoding="utf-8"
    )
    kept_affixes = [a.form for a in model.affixes]
    result = {"pair": pair, "iterations": it, "base_coverage": round(base_cov, 4),
              "final_coverage": round(cov, 4), "delta": round(cov - base_cov, 4),
              "affixes_kept": kept_affixes}
    (out_dir / f"{pair}_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{pair}] DONE: coverage {base_cov:.3f} -> {cov:.3f} (+{cov-base_cov:.3f}); "
          f"kept suffixes: {' '.join(kept_affixes) or '(none)'}")
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--seconds", type=float, default=480.0)
    ap.add_argument("--roots", type=int, default=300)
    ap.add_argument("--batch", type=int, default=4)
    args = ap.parse_args(argv)
    run(args.pair, args.seconds, n_roots=args.roots, batch=args.batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
