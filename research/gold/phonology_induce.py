"""Derive phonological RULES from the eBible corpus distribution — validated, not hand-authored.

A prefix family like Indonesian meN- surfaces as mem-/men-/meng- and the variant correlates with the
following consonant's PLACE (mem before labials, men before coronals, meng before dorsals/vowels). That
correlation, measured over the segmented vocabulary, IS nasal place assimilation — a phonological rule the
data proves. We detect such conditioned-allomorphy families and emit rules with their distributional
witnesses to `phonology_induced.jsonl` (kept separate from the static `phonology.jsonl`; survives recompile).

This advances the phonology layer for the agglutinative languages the way segmentation advanced morphology:
from the corpus alone, no grammar book. Run: `python golden/reference/phonology_induce.py --pair ind`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from gold.compile import PAIR_DIR  # noqa: E402
from gold.segment import segment  # noqa: E402

FROZEN = _THIS.parents[1] / "golden_sets"
PLACE = {**{c: "labial" for c in "bpmfw"}, **{c: "coronal" for c in "tdnslrzcj"},
         **{c: "dorsal" for c in "kghq"}, **{c: "vowel" for c in "aeiou"}}
# the nasal that assimilation predicts before each place
EXPECT = {"m": "labial", "n": "coronal", "ng": "dorsal", "ny": "coronal"}


def _place_dist(prefix: str, seg: dict, freq: dict) -> Counter:
    c: Counter = Counter()
    for w in seg:
        if w.startswith(prefix) and len(w) > len(prefix) and w[len(prefix):] in freq:
            c[PLACE.get(w[len(prefix)], "?")] += 1
    return c


def nasal_assimilation(pair: str, *, min_support: int = 8) -> list[dict]:
    """Detect meN-/peN-style nasal place-assimilation families from the segmentation distribution."""
    affixes, seg, freq = segment(pair)
    pre = set(affixes["prefix"])
    rules = []
    for core in sorted({p[:-2] if p.endswith("ng") else p[:-1] for p in pre if len(p) >= 2}):
        variants = {n: core + n for n in ("m", "n", "ng", "ny") if core + n in pre}
        if len(variants) < 2:
            continue
        evidence, hits = {}, 0
        for n, pfx in variants.items():
            dist = _place_dist(pfx, seg, freq)
            top = dist.most_common(1)[0] if dist else ("", 0)
            evidence[pfx + "-"] = {"top_place": top[0], "n": top[1], "dist": dict(dist.most_common(3))}
            if top[1] >= min_support and top[0] == EXPECT.get(n):
                hits += 1
        if hits >= 2:                              # ≥2 variants match the predicted place → real assimilation
            rules.append({
                "type": "rule", "id": f"{pair}_{core}N_nasal_assimilation", "kind": "assimilation",
                "status": "data-derived", "source": "corpus distribution",
                "description": f"Prefix {core}N-: the nasal assimilates to the following consonant's place "
                               f"({core}m before labials, {core}n before coronals, {core}ng before dorsals/vowels).",
                "mechanism": "PhonologicalRule: nasal place = following C place (archiphoneme N)",
                "evidence": evidence, "variants_confirmed": hits})
    return rules


def vowel_harmony(pair: str, *, min_support: int = 8) -> list[dict]:
    """Detect i/e suffix harmony (swh applicative -ia/-ea, causative -isha/-esha): the suffix vowel
    matches the stem's last vowel height — -i… after high/low stems (a,i,u), -e… after mid stems (e,o)."""
    affixes, seg, freq = segment(pair)
    suf = set(affixes["suffix"])
    rules = []
    for s in sorted(suf):
        if "i" not in s:
            continue
        partner = s.replace("i", "e", 1)
        if partner not in suf or partner == s or partner > s:   # each pair once
            continue

        def last_vowel_dist(sfx: str) -> Counter:
            c: Counter = Counter()
            for w in seg:
                if w.endswith(sfx) and len(w) > len(sfx) and w[: -len(sfx)] in freq:
                    lv = next((ch for ch in reversed(w[: -len(sfx)]) if ch in "aeiou"), "")
                    c[lv] += 1
            return c
        di, de = last_vowel_dist(s), last_vowel_dist(partner)
        i_hl, i_mid = sum(di[v] for v in "aiu"), sum(di[v] for v in "eo")
        e_hl, e_mid = sum(de[v] for v in "aiu"), sum(de[v] for v in "eo")
        if i_hl >= min_support and e_mid >= 4 and i_hl > i_mid and e_mid > e_hl:
            rules.append({
                "type": "rule", "id": f"{pair}_{s}_{partner}_vowel_harmony", "kind": "harmony",
                "status": "data-derived", "source": "corpus distribution",
                "description": f"Suffix harmony -{s}/-{partner}: -{s} after stems whose last vowel is a/i/u, "
                               f"-{partner} after mid vowels e/o (height harmony).",
                "mechanism": "PhonologicalRule: alpha-variable on vowel height (archiphoneme suffix vowel)",
                "evidence": {f"-{s}": dict(di.most_common(5)), f"-{partner}": dict(de.most_common(5))}})
    return rules


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    args = ap.parse_args(argv)
    rules = nasal_assimilation(args.pair) + vowel_harmony(args.pair)
    out = FROZEN / args.pair / "phonology_induced.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rules:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[{args.pair}] corpus-derived phonological rules: {len(rules)} → {out.name}")
    for r in rules:
        print(f"  {r['id']}  [{r['kind']}]  {r.get('evidence')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
