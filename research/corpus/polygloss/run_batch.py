"""Run the curated PolyGloss pilot batch (Polygloss_integration.md §5/§6) across a hand-picked,
typologically diverse set of languages and write a markdown report.

Language selection (manual judgment call, per §5 — not automated): English metalanguage, >=500
train examples, not already one of the current 8 golden-set languages (swh/ind/tgl/spa/tur/rus/hin/
vie), chosen to fill real typological gaps against that set (which skews Bantu/Austronesian/Romance/
Turkic/Slavic/Indo-Aryan/isolating). Where the corpus provides genuine `test`/`dev` splits (its own
9-language SIGMORPHON-2023 held-out set, minus Gitksan [89 rows, below the volume floor] and
Uspanteko [0 English-metalanguage rows]), those give contamination-free scores; the rest fall back to
a held-out slice of `train` (flagged in the report as an optimistic upper bound on parse_rate — see
`pilot.py`).
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from corpus.ebible.read import tokenize  # noqa: E402

from .pilot import run_pilot  # noqa: E402


def _tokenizer_split_fraction(miss_parse: list[str]) -> float:
    """Fraction of `miss_parse` surfaces that `tokenize()` actually SHATTERS into >1 piece — the
    concrete signature of the in-word-punctuation tokenizer gap (see Cayuga's colon-as-length-mark
    finding). A coverage-vs-parse_rate gap with a LOW split fraction has some other cause (e.g. plain
    root-coverage sparsity on rare gold words) and must not be attributed to tokenization."""
    if not miss_parse:
        return 0.0
    split = sum(1 for w in miss_parse if len(tokenize(w)) != 1)
    return split / len(miss_parse)

# (glottocode, language, typological note)
LANGUAGES = [
    ("arap1274", "Arapaho", "Algonquian, polysynthetic — test split"),
    ("vera1241", "Vera'a", "Oceanic (Vanuatu) — train holdout"),
    ("dido1241", "Tsez", "Nakh-Daghestanian, ergative — test split"),
    ("lezg1247", "Lezgian", "Nakh-Daghestanian, ergative — test split"),
    ("nyan1302", "Nyangbo", "Niger-Congo (Kwa) — test split"),
    ("ainu1240", "Hokkaido Ainu", "isolate, polysynthetic — test split"),
    ("ruul1235", "Ruuli", "Bantu, non-Swahili subgroup — test split"),
    ("natu1246", "Natügu", "Oceanic (Reef-Santa Cruz) — test split"),
    ("cayu1261", "Cayuga", "Iroquoian, polysynthetic — train holdout"),
    ("japh1234", "Japhug", "Sino-Tibetan (Gyalrongic), polysynthetic agreement — train holdout"),
    ("beja1238", "Beja", "Cushitic (Afro-Asiatic) — train holdout"),
    ("dolg1241", "Dolgan", "Turkic (Siberia), agglutinative — train holdout"),
    ("kama1378", "Kamas", "Uralic (Samoyedic) — train holdout"),
    ("selk1253", "Selkup", "Uralic (Samoyedic) — train holdout"),
    ("nngg1234", "N‖ng", "Tuu/Khoisan, click language — train holdout"),
    ("mauw1238", "Mauwake", "Trans-New Guinea — train holdout"),
    ("kara1499", "Kalamang", "Papuan isolate — train holdout"),
    ("basq1248", "Basque", "isolate, ergative — train holdout"),
]

OUT_DIR = Path(__file__).resolve().parent / "out"


def run_batch(seconds: float = 150.0, languages: list[tuple[str, str, str]] | None = None) -> list[dict]:
    languages = languages if languages is not None else LANGUAGES
    results = []
    for glottocode, language, note in languages:
        t0 = time.monotonic()
        print(f"\n===== [{glottocode}] {language} ({note}) =====", flush=True)
        try:
            r = run_pilot(glottocode, language=language, seconds=seconds)
            r["typology_note"] = note
            r["status"] = "ok"
        except Exception as e:  # one language's failure must not abort the batch
            r = {
                "glottocode": glottocode, "language": language, "typology_note": note,
                "status": "error", "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
                "secs": round(time.monotonic() - t0, 1),
            }
            print(f"[{glottocode}] FAILED: {r['error']}", flush=True)
        results.append(r)
    return results


def write_report(results: list[dict], path: Path) -> None:
    lines = [
        "# PolyGloss pilot report",
        "",
        "Blind-benchmark pilot: HC induction (`induce/tdd.py`) run over PolyGloss-sourced parallel "
        "text, gold-blind (see `build.py`), scored against the corpus's own hand-annotated "
        "segmentation/glosses (see `score.py`). Per Polygloss_integration.md — curated pilot, "
        "exploratory, no fixed pass threshold; results recorded honestly including weak ones.",
        "",
        "| Language | Glottocode | Typology | Gold split | Train rows | Internal coverage | "
        "Roots glossed | Gold parse_rate | Gold lemma_recall | Gold feature_recall | Harmony debt | Secs |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    n_ok = n_err = 0
    low_gloss: list[str] = []
    tokenizer_gap: list[str] = []
    unexplained_gap: list[str] = []
    for r in results:
        if r.get("status") != "ok":
            n_err += 1
            lines.append(
                f"| {r['language']} | {r['glottocode']} | {r['typology_note']} | — | — | — | — | — | — | — | — | "
                f"ERROR: {r.get('error', '?')} |"
            )
            continue
        n_ok += 1
        gb = r.get("gold_benchmark") or {}
        split = r["manifest"]["gold_source_split"]
        split_label = f"{split} ({'contamination-free' if split == 'test' else 'upper bound'})"
        ind = r["induction"]
        glossed_frac = ind["lexicon"]["glossed_frac"]
        if glossed_frac < 0.1:
            low_gloss.append(f"{r['manifest']['language']} ({r['glottocode']}, glossed_frac={glossed_frac:.3f})")
        parse_rate = gb.get("parse_rate")
        if parse_rate is not None and ind["final_coverage"] - parse_rate > 0.3:
            # Distinguish the two possible causes by evidence, not by the gap size alone: a real
            # tokenizer split (in-word punctuation shattering a word into pieces absent from training)
            # vs. plain root-coverage sparsity on rare gold words, which looks identical in the gap
            # metric but has nothing to do with tokenization (see Selkup vs. Cayuga — same-size gap,
            # different cause, verified against `miss_parse`).
            split_frac = _tokenizer_split_fraction(gb.get("miss_parse", []))
            entry = (f"{r['manifest']['language']} ({r['glottocode']}, internal coverage="
                     f"{ind['final_coverage']:.3f} vs. gold parse_rate={parse_rate:.3f}, "
                     f"{split_frac:.0%} of misses tokenizer-split)")
            (tokenizer_gap if split_frac >= 0.5 else unexplained_gap).append(entry)
        lines.append(
            f"| {r['manifest']['language']} | {r['glottocode']} | {r['typology_note']} | {split_label} | "
            f"{r['manifest']['rows_train_english_meta']} | "
            f"{ind['base_coverage']:.3f}→{ind['final_coverage']:.3f} | {glossed_frac:.3f} | "
            f"{gb.get('parse_rate', float('nan')):.3f} | {gb.get('lemma_recall', float('nan')):.3f} | "
            f"{gb.get('feature_recall', float('nan')):.3f} | {ind['enumeration_debt']} | {r['secs']} |"
        )
    lines += [
        "",
        f"**{n_ok} succeeded, {n_err} failed** out of {len(results)} languages attempted.",
        "",
        "Notes:",
        "- `test`-split rows come from PolyGloss's own held-out split for that language — never seen "
        "by the aligner or the induction loop, so those scores are contamination-free.",
        "- `train`-split holdout rows ARE part of the same corpus the aligner/induction ran over "
        "(only their raw tokens, never their segmentation/gloss labels) — `parse_rate` there is an "
        "optimistic upper bound since a frequent gold surface can become a root by coincidence of "
        "frequency; `lemma_recall`/`feature_recall` are not inflated this way (root glosses come from "
        "THOT alignment, not from the gold).",
        "- Scores reflect a fixed, deliberately short per-language time/root budget (auto-scaled by "
        "vocabulary size, see `pilot.py::_scale`) — a pilot floor, not each language's ceiling.",
        "- `lemma_recall`/`feature_recall` are a JOINT test of segmentation AND THOT-gloss-match: a "
        "root only counts as recalled if its THOT-aligned English gloss exactly matches the hand "
        "gloss (after slugging). Low scores (0.0-0.3 across most languages here) mostly reflect THOT "
        "alignment noise on a short, thin parallel corpus, not pure segmentation failure — `Roots "
        "glossed` (the fraction of induced roots that got ANY non-'?' THOT gloss) is a useful cross-"
        "check: a language with low `Roots glossed` will have a near-zero recall almost by "
        "construction, independent of how good its morphology induction is.",
        "- Gold surfaces are matched against HC's parses via `to_gold._parse_surface` (tokenizer-"
        "normalized: lowercased, non-word characters stripped, same as training tokens) rather than "
        "the raw segmentation-tier surface — without this, case alone made some gold words unparsable "
        "for reasons unrelated to morphology. This recovered most of the gap on most languages "
        "(e.g. Arapaho's apostrophe-final words) but not all of it everywhere — see below.",
        "- **Cayuga (cayu1261) tokenizer fix applied**: `tokenize()` now accepts an `extra_word_chars` "
        "switch (see `corpus/ebible/read.py`), and `corpus/polygloss/orthography.py` maps `cayu1261 "
        "-> \":\"` (its vowel-length mark). Before the fix: internal coverage 0.858 vs. gold "
        "parse_rate 0.086 — a 0.77 gap, because training tokens and gold surfaces disagreed on where "
        "words ended. After: internal coverage 0.175 vs. gold parse_rate 0.135 — both numbers dropped, "
        "but the GAP closed to 0.04. That is the correct outcome, not a regression: the old 0.858 was "
        "measuring induction over artificially fragmented pseudo-words (each real Cayuga word cut "
        "into 2+ meaningless pieces), which is an easier — but wrong — task. With real, whole "
        "polysynthetic word forms, this pilot's fixed budget genuinely isn't enough to reach good "
        "coverage; that's now an honest signal about corpus size/budget vs. Cayuga's difficulty, not "
        "an artifact of broken tokenization.",
    ]
    if low_gloss:
        lines.append(
            "- **Alignment near-failure, not a segmentation finding**: " + "; ".join(low_gloss) +
            " — THOT produced a real English gloss for almost no induced root (see `Roots glossed` "
            "above), so `lemma_recall`/`feature_recall` for these languages are not a meaningful "
            "morphology signal at this corpus size/budget."
        )
    if tokenizer_gap:
        lines.append(
            "- **Known remaining limitation — in-word length/tone marks split as token boundaries** "
            "(confirmed: most of that language's `miss_parse` surfaces are literally shattered by "
            "`tokenize()` into >1 piece): " + "; ".join(tokenizer_gap) +
            ". `corpus/ebible/read.py::tokenize()`'s word-character class (`\\w` + Unicode marks) "
            "does not include some punctuation-category characters used AS PART OF a word in these "
            "orthographies — e.g. the colon `:` (category `Po`) as a vowel-length mark in Cayuga. "
            "During training-corpus construction that word becomes TWO separate tokens; "
            "`to_gold._parse_surface`'s normalization instead JOINS the same characters into one "
            "string (since it doesn't re-split on the boundary) — so the gold form matches neither "
            "training token, and no root ever gets a chance at it. A genuine, unresolved gap, not "
            "fixed by the parse_surface normalization above. Fixing it means widening `tokenize()`'s "
            "character class, which is shared production code for the current 8 eBible languages — a "
            "separate, carefully-reviewed change, deliberately out of scope for this pilot."
        )
    if unexplained_gap:
        lines.append(
            "- **Coverage-vs-parse_rate gap with a DIFFERENT cause than tokenization** (checked: most "
            "of that language's `miss_parse` surfaces are NOT tokenizer-split — ruled out as the "
            "explanation): " + "; ".join(unexplained_gap) +
            ". Most likely plain root-coverage sparsity: this pilot's auto-scaled root budget "
            "(`pilot.py::_scale`) covers only the most frequent word types, so held-out gold words "
            "that happen to be rare in the training corpus may simply never have become roots or "
            "affixed forms, independent of any tokenizer issue."
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--only", nargs="*", default=None, help="restrict to these glottocodes")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    langs = LANGUAGES if not args.only else [t for t in LANGUAGES if t[0] in set(args.only)]
    results = run_batch(seconds=args.seconds, languages=langs)

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "batch_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    write_report(results, OUT_DIR / "PILOT_REPORT.md")
    print(f"\nWrote {OUT_DIR / 'PILOT_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
