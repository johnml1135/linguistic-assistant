"""Unsupervised morpheme segmentation from the eBible vocabulary alone — no UniMorph, no dictionary.

For an unknown language there are no paradigms to seed affixes; we must DISCOVER them from the wordlist.
An affix is productive if stripping it leaves a STEM that recurs — either a free word, or a stem shared
by several affixes (paradigm structure). That gives an affix inventory + a segmentation per word + stem
groups (paradigms), which feed the affix-function assessment (Gemma names what each affix does, from the
aligned meanings of stem vs stem+affix).

This is scaffold #2 of the bootstrap: it unlocks the MORPHOLOGY half for tgl/swh the way `align_gloss`
unlocked the lexical half. Run: `python golden/reference/segment.py --pair swh`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from golden.reference.align_gloss import _verses  # noqa: E402
from golden.reference.compile import PAIR_DIR  # noqa: E402
from golden.reference.orthography import is_word  # noqa: E402


def vocab(pair: str) -> Counter:
    c: Counter = Counter()
    for _src, tgt in _verses(pair):
        c.update(w for w in tgt if is_word(w) and len(w) >= 3)
    return c


def induce_affixes(freq: Counter, *, min_stems: int = 12, max_len: int = 5, min_stem: int = 3):
    """Discover productive prefixes & suffixes. Two passes: collect residual-stems per candidate affix,
    then keep affixes whose stem is a free word OR a stem shared across ≥2 affixes (paradigm evidence)."""
    words = {w for w in freq if len(w) >= min_stem}
    suf_stems: dict[str, set] = defaultdict(set)
    pre_stems: dict[str, set] = defaultdict(set)
    for w in words:
        for i in range(1, min(max_len, len(w) - min_stem) + 1):
            suf_stems[w[-i:]].add(w[:-i])
            pre_stems[w[:i]].add(w[i:])
    stem_aff: Counter = Counter()
    for st_set in (*suf_stems.values(), *pre_stems.values()):
        stem_aff.update(st_set)

    def keep(stems: set) -> set:
        return {s for s in stems if s in words or stem_aff[s] >= 2}

    suffixes = {a: len(real) for a, st in suf_stems.items() if len(real := keep(st)) >= min_stems}
    prefixes = {a: len(real) for a, st in pre_stems.items() if len(real := keep(st)) >= min_stems}
    return ({"suffix": dict(sorted(suffixes.items(), key=lambda x: -x[1])),
             "prefix": dict(sorted(prefixes.items(), key=lambda x: -x[1]))},
            suf_stems, pre_stems, words, stem_aff)


def segment(pair: str, *, min_stems: int = 12, max_strips: int = 4):
    """MULTI-AFFIX segmentation: iteratively peel known prefixes then suffixes (longest-match), but only
    when the residual stays a 'real' stem (a free word, or a residual that recurs across affixes). This
    isolates the root of an agglutinative form (swh ni-na-ku-pend-a → root `pend`), where single-strip
    only peeled one layer. Returns (affixes, seg, freq) with seg[w] = (prefixes:list, root, suffixes:list)."""
    freq = vocab(pair)
    affixes, suf_stems, pre_stems, words, stem_aff = induce_affixes(freq, min_stems=min_stems)
    suf = sorted(affixes["suffix"], key=len, reverse=True)
    pre = sorted(affixes["prefix"], key=len, reverse=True)

    def real(r: str) -> bool:                       # a valid residual: free word or recurs under ≥3 affixes
        return len(r) >= 3 and (r in words or stem_aff[r] >= 3)

    seg: dict[str, tuple[list, str, list]] = {}
    for w in words:
        prefixes, suffixes, stem = [], [], w
        for _ in range(max_strips):                 # peel prefixes (stop at a free root, or when stuck)
            if stem in words and len(prefixes) > 0:
                break
            nxt = next((a for a in pre if stem.startswith(a) and real(stem[len(a):])), None)
            if not nxt:
                break
            prefixes.append(nxt)
            stem = stem[len(nxt):]
        for _ in range(max_strips):                 # then peel suffixes
            if stem in words and len(suffixes) > 0:
                break
            nxt = next((a for a in suf if stem.endswith(a) and real(stem[: -len(a)])), None)
            if not nxt:
                break
            suffixes.insert(0, nxt)
            stem = stem[: -len(nxt)]
        seg[w] = (prefixes, stem, suffixes)
    return affixes, seg, freq


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--min-stems", type=int, default=12)
    args = ap.parse_args(argv)
    affixes, seg, freq = segment(args.pair, min_stems=args.min_stems)
    out = _THIS.parents[2] / "golden_sets" / args.pair / "segmentation.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for w in sorted(seg):
            pre, st, suf = seg[w]
            if pre or suf:
                f.write(json.dumps({"word": w, "prefixes": pre, "root": st, "suffixes": suf}, ensure_ascii=False) + "\n")
    segmented = sum(1 for v in seg.values() if v[0] or v[2])
    classes, assigned = morph_classes(seg)
    print(f"[{args.pair}] unsupervised segmentation from {len(freq)} eBible word types:")
    print(f"  prefixes (#stems): {dict(list(affixes['prefix'].items())[:10])}")
    print(f"  suffixes (#stems): {dict(list(affixes['suffix'].items())[:10])}")
    print(f"  segmented {segmented} words → {out.name}")
    print(f"  roots {len({st for _, st, _ in seg.values()})}; INFLECTION CLASSES induced {len(classes)} "
          f"(roots assigned {len(assigned)}) — was 0 for this language")
    return 0


def morph_classes(seg: dict, *, min_class: int = 8):
    """Induce inflection CLASSES from the segmentation: group roots by the SET of affix-signatures they
    take (their paradigm shape). A signature = '<prefixes>|<suffixes>'. Roots sharing the same set of
    signatures are one class. This is the thin-language analogue of the UniMorph-seeded classes."""
    by_root: dict[str, set] = defaultdict(set)
    for w, (pre, st, suf) in seg.items():
        if pre or suf:
            by_root[st].add("+".join(pre) + "|" + "+".join(suf))
    groups: dict[frozenset, list] = defaultdict(list)
    for root, sigs in by_root.items():
        if len(sigs) >= 2:                          # a paradigm = a root with ≥2 distinct affix patterns
            groups[frozenset(sigs)].append(root)
    classes, assigned = [], {}
    for i, (sig, roots) in enumerate(sorted((g for g in groups.items() if len(g[1]) >= min_class),
                                            key=lambda g: -len(g[1]))):
        cid = f"class-{i + 1}"
        classes.append({"class_id": cid, "size": len(roots), "signatures": sorted(sig)})
        for r in roots:
            assigned[r] = cid
    return classes, assigned


if __name__ == "__main__":
    raise SystemExit(main())
