"""Fetch + parse external references into one per-language gold (`gold.json`).

Idempotent fetch-on-box (skips a source that 404s / is absent); parses UniMorph (lemma/form/features),
UD CoNLL-U (form→UPOS, lemmas), and the unfoldingWord key-term vocabulary into a common gold the
evaluator scores against. Run: `python golden/reference/build.py --pair spa`.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from gold.sources import UD, UNIMORPH, UW_TW_DIRS  # noqa: E402

CACHE = _THIS.parents[1] / "_sources" / "reference"
_UA = {"User-Agent": "linguistic-assistant-refgold"}


def _get(url: str, dest: Path, *, force: bool = False) -> str | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force and dest.stat().st_size > 0:
        return dest.read_text(encoding="utf-8", errors="replace")
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (trusted github)
            text = r.read().decode("utf-8", errors="replace")
        dest.write_text(text, encoding="utf-8")
        return text
    except Exception as exc:  # 404 / offline → skip this source
        print(f"  skip {url} ({exc})")
        return None


def _parse_unimorph(text: str) -> dict:
    lemmas, forms, feats = set(), set(), Counter()
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0] and parts[1]:
            lemmas.add(parts[0].lower()); forms.add(parts[1].lower()); feats[parts[2]] += 1
    return {"lemmas": sorted(lemmas), "forms": sorted(forms),
            "features": [f for f, _ in feats.most_common(60)]}


def _parse_ud(text: str) -> dict:
    pos: dict[str, Counter] = {}
    lemmas: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) >= 4 and "-" not in c[0] and "." not in c[0]:  # skip multiword/empty-node ids
            form, lemma, upos = c[1].lower(), c[2].lower(), c[3]
            pos.setdefault(form, Counter())[upos] += 1
            if lemma and lemma != "_":
                lemmas.add(lemma)
    return {"pos_by_form": {f: cnt.most_common(1)[0][0] for f, cnt in pos.items()},
            "lemmas": sorted(lemmas)}


def fetch_kaikki(pair: str, *, max_mb: int = 2000) -> dict | None:
    """Stream the kaikki Wiktionary extract for `pair` → {words:{word:{pos,gloss}}, forms:[...], truncated}.

    Streams line-by-line with a byte cap (the Spanish file is huge) and caches only the small extract,
    not the raw dump. Each JSONL entry → word, its POS, and the first English sense gloss (the bilingual
    gloss UD/UniMorph lack); inflected `forms` feed the lexicon.
    """
    from gold.sources import KAIKKI
    url = KAIKKI.get(pair)
    if not url:
        return None
    out = CACHE / pair / "kaikki_extract.json"
    if out.exists() and out.stat().st_size > 0:
        cached = json.loads(out.read_text(encoding="utf-8"))
        # re-fetch if old format OR previously truncated (a raised cap can now capture more)
        if cached.get("version") == 2 and not cached.get("truncated"):
            return cached
    words: dict[str, dict] = {}
    forms: set[str] = set()
    read = 0
    cap = max_mb * 1024 * 1024
    truncated = False
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310 (trusted kaikki.org)
            for raw in r:
                read += len(raw)
                if read > cap:
                    truncated = True
                    break
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                w = (e.get("word") or "").strip().lower()
                if not w:
                    continue
                # AGGREGATE across the word's entries: a word can have several POS (homograph) and many
                # senses (polysemy). Keep all distinct POS + a capped list of senses, not just the first.
                rec = words.setdefault(w, {"pos": [], "senses": []})
                p = e.get("pos", "")
                if p and p not in rec["pos"]:
                    rec["pos"].append(p)
                for s in e.get("senses", []):
                    for g in (s.get("glosses") or s.get("raw_glosses") or []):
                        g = str(g).strip()
                        if g and g not in rec["senses"] and len(rec["senses"]) < 8:
                            rec["senses"].append(g)
                for fm in e.get("forms", []):
                    f = (fm.get("form") or "").strip().lower()
                    if f and " " not in f:
                        forms.add(f)
    except Exception as exc:
        print(f"  kaikki skip {url} ({exc})")
        return None
    extract = {"version": 2, "words": words, "forms": sorted(forms), "truncated": truncated}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(extract, ensure_ascii=False), encoding="utf-8")
    if truncated:
        print(f"  kaikki {pair}: capped at {max_mb}MB ({len(words)} words parsed)")
    return extract


def _parse_uw_terms(dest_dir: Path) -> list[str]:
    terms: set[str] = set()
    for i, url in enumerate(UW_TW_DIRS):
        text = _get(url, dest_dir / f"uw_tw_{i}.json")
        if not text:
            continue
        try:
            for item in json.loads(text):
                name = item.get("name", "")
                if name.endswith(".md"):
                    terms.add(name[:-3].lower())
        except Exception as exc:
            print(f"  uw parse error: {exc}")
    return sorted(terms)


def build(pair: str) -> dict:
    out = CACHE / pair
    gold: dict = {"pair": pair, "sources": []}
    if pair in UNIMORPH:
        t = _get(UNIMORPH[pair], out / "unimorph.txt")
        if t:
            gold["unimorph"] = _parse_unimorph(t)
            gold["sources"].append("unimorph")
    if pair in UD:
        t = _get(UD[pair], out / "ud.conllu")
        if t:
            gold["ud"] = _parse_ud(t)
            gold["sources"].append("ud")
    terms = _parse_uw_terms(out)
    if terms:
        gold["key_terms"] = terms
        gold["sources"].append("unfoldingword")
    (out / "gold.json").write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
    return {"pair": pair, "sources": gold["sources"],
            "unimorph_forms": len(gold.get("unimorph", {}).get("forms", [])),
            "ud_forms": len(gold.get("ud", {}).get("pos_by_form", {})),
            "key_terms": len(gold.get("key_terms", []))}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True)
    args = ap.parse_args(argv)
    s = build(args.pair)
    print(f"[{args.pair}] reference gold: sources={s['sources']} unimorph_forms={s['unimorph_forms']} "
          f"ud_forms={s['ud_forms']} key_terms={s['key_terms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
