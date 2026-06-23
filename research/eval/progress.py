"""One-page progress report across every dimension — runs on the data, emits markdown.

Assembles, per language: the NT inventory (the denominator), parse coverage (words parsed well vs the
number that would need parsing, names split out), the lexicon/morphology/phonology scorecard
(`gold.completeness`), the 12 master switches (which value chosen, its confidence, and whether it aligns
with the reference data), and the headline indicator metrics. Consumer-layer (nothing imports this).

Run:  uv run python -m eval.progress              (full, needs hc for parse coverage)
      uv run python -m eval.progress --no-hc      (skip the HC parse-coverage section, fast)
Writes `docs/progress-report.md` and prints a one-line summary.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from gold.compile import EBIBLE, PAIR_DIR  # noqa: E402

PAIRS = ("spa", "ind", "tgl", "swh")
SWITCH_ORDER = ("synthesis", "affix_polarity", "infixation", "reduplication", "vowel_harmony",
                "nasal_assimilation", "tone", "gender_or_noun_class", "case", "tam_locus",
                "agreement_head_marking", "articles")


def _inventory(pair: str) -> dict:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    toks: Counter = Counter(); verses = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            verses += 1
            toks.update(t.lower() for t in json.loads(line)["tgt"] if t.isalpha())
    tot = sum(toks.values()); uniq = len(toks); hapax = sum(1 for c in toks.values() if c == 1)
    return {"verses": verses, "tokens": tot, "unique": uniq,
            "hapax_pct": round(100 * hapax / uniq) if uniq else 0}


def gather(pair: str, *, hc: bool, sample: int) -> dict:
    from gold.completeness import score
    from review.deferrals import profile_detect as PD
    row = {"pair": pair, "inv": _inventory(pair), "complete": score(pair),
           "switches": {s.name: s for s in PD.detect(pair)}}
    if hc:
        try:
            from gold.hc_coverage import coverage, hc_available
            row["cov"] = coverage(pair, sample=sample) if hc_available() else None
        except Exception as e:
            row["cov"] = {"error": str(e)[:60]}
    else:
        row["cov"] = None
    return row


def _switch_cell(sw) -> str:
    mark = {True: "✓", False: "⚠", None: "·"}.get(getattr(sw, "agrees", None), "·")
    val = str(sw.value)[:13] if sw.value is not None else "—"
    return f"{val} {mark}"


def render(rows: list[dict], *, date: str) -> str:
    P = [r["pair"] for r in rows]
    out = [f"# Linguistic Assistant — progress report ({date})", "",
           "_Per the four eBible NTs. Switch marks: ✓ agrees with reference typology · ⚠ conflicts "
           "(low-confidence, flagged for review) · · no reference._", ""]

    out += ["## Corpus (the denominator)", "",
            "| pair | verses | tokens | unique forms | hapax% |", "|---|--:|--:|--:|--:|"]
    for r in rows:
        i = r["inv"]
        out.append(f"| {r['pair']} | {i['verses']} | {i['tokens']:,} | {i['unique']:,} | {i['hapax_pct']}% |")

    out += ["", "## Parsing — words parsed well vs the number needing parsing", ""]
    if any(r.get("cov") and "coverage" in r["cov"] for r in rows):
        out += ["| pair | sample tested | parsed | coverage | ex-names | real morphology gap | likely names |",
                "|---|--:|--:|--:|--:|--:|--:|"]
        for r in rows:
            c = r.get("cov") or {}
            if "coverage" in c:
                out.append(f"| {r['pair']} | {c['tested']} | {c['parsed']} | {c['coverage']:.0%} | "
                           f"{c['coverage_ex_names']:.0%} | {c['real_gap']} | {c['likely_names']} |")
            else:
                out.append(f"| {r['pair']} | — | — | — | — | — | — |")
        out += ["", "_Coverage = parsed / tested on a held-out frequent-form sample; the real morphology "
                "gap (not names) is what's left to close._"]
    else:
        out.append("_(parse coverage skipped — run without `--no-hc` and with the `hc` CLI installed)_")

    out += ["", "## Lexicon · morphology · phonology", "",
            "| pair | lemmas | glossed | affixes | infl-classes | wordforms | phon rules |",
            "|---|--:|--:|--:|--:|--:|--:|"]
    for r in rows:
        c = r["complete"]; lx = c["lexicography"]; m = c["morphology"]; ph = c["phonology"]
        out.append(f"| {r['pair']} | {lx['lemmas']:,} | {lx['gloss_pct']}% | {m['affixes_gold']} | "
                   f"{m['inflection_classes']} | {m['wordforms']:,} | {ph['rules_total']} |")

    out += ["", "## The 12 master switches (chosen value · alignment with the data)", "",
            "| switch | " + " | ".join(P) + " |", "|---|" + "---|" * len(P)]
    for sid in SWITCH_ORDER:
        cells = [_switch_cell(r["switches"][sid]) if sid in r["switches"] else "—" for r in rows]
        out.append(f"| {sid} | " + " | ".join(cells) + " |")
    # per-pair switch alignment numbers
    out += ["", "**Switch alignment with the data** (of switches with a reference):"]
    for r in rows:
        sws = list(r["switches"].values())
        ref = [s for s in sws if getattr(s, "internet", None) is not None]
        agree = sum(1 for s in ref if s.agrees)
        hi = sum(1 for s in sws if s.confidence >= 0.7)
        out.append(f"- **{r['pair']}**: {agree}/{len(ref)} agree with reference · {hi}/12 high-confidence "
                   f"· {len(ref) - agree} flagged conflict")

    out += ["", "## Headline indicators", "",
            "| pair | scripture parse-cov | gloss% | real gap | switches agree | switches hi-conf |",
            "|---|--:|--:|--:|--:|--:|"]
    for r in rows:
        c = r.get("cov") or {}
        sws = list(r["switches"].values())
        ref = [s for s in sws if getattr(s, "internet", None) is not None]
        agree = sum(1 for s in ref if s.agrees)
        hi = sum(1 for s in sws if s.confidence >= 0.7)
        cov = f"{c['coverage']:.0%}" if "coverage" in c else "—"
        out.append(f"| {r['pair']} | {cov} | {r['complete']['lexicography']['gloss_pct']}% | "
                   f"{c.get('real_gap', '—')} | {agree}/{len(ref)} | {hi}/12 |")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-hc", action="store_true", help="skip the HC parse-coverage section (fast)")
    ap.add_argument("--sample", type=int, default=300, help="held-out forms per language for parse coverage")
    ap.add_argument("--out", default=str(_RESEARCH.parent / "docs" / "progress-report.md"))
    ap.add_argument("--date", default="")
    args = ap.parse_args(argv)
    rows = [gather(p, hc=not args.no_hc, sample=args.sample) for p in PAIRS]
    md = render(rows, date=args.date or "data snapshot")
    Path(args.out).write_text(md, encoding="utf-8")
    print(f"wrote {args.out} ({md.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
