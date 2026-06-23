"""Assess the ParseGym: what it covers, how hard, which skills — and render LLM test prompts.

Two jobs:
  1. COVERAGE — cross-tabulate the curated scenarios (stage × difficulty × phase × answer-kind ×
     capability × skill × language) so you can see what the suite actually exercises and where it is thin.
  2. LLM-READINESS — render the exact prompt a model would see for a scenario (the resolving skill +
     a self-contained context block) and check every scenario carries enough context to be answerable
     standalone (`Scenario.context_complete`). Reports prompt sizes so the suite fits a small model's window.

Run: `python parsegym/assess.py` (all pairs) or `--pair spa`; `--render <scenario_id>` to print one prompt;
`--md report.md` to write a Markdown report.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from eval.parsegym.questions import get as getq  # noqa: E402
from eval.parsegym.schema import Scenario, read_jsonl  # noqa: E402

GYM = _THIS.parent / "gym"
SKILLS = _THIS.parents[2] / "skills"

DIFFICULTY_RUBRIC = {
    "easy":   "the reference gives a confident answer; one obvious move.",
    "medium": "evidence points one way but needs a judgement call (which sense, which split).",
    "hard":   "evidence is thin or conflicting; the answer is often 'ask the speaker' or 'I don't know'.",
}
CAPABILITY_DESC = {
    "lexical_bootstrapping": "recognise an unknown word and decide add-root / elicit / defer.",
    "irregular_morphology":  "see that a form belongs to a known lemma despite an irregular stem (allomorph).",
    "sense_disambiguation":  "one form, several senses/POS — choose the right meaning or the right question.",
    "segmentation_precision":"reject spurious over-segmentation; keep only the licit analysis.",
}


def load_all(pair: str | None = None) -> dict[str, list[Scenario]]:
    files = [GYM / f"{pair}.jsonl"] if pair else sorted(GYM.glob("*.jsonl"))
    return {f.stem: read_jsonl(f) for f in files if f.exists()}


def render_prompt(s: Scenario) -> str:
    """The exact prompt a model sees: the triage skill + a self-contained scenario context block."""
    skill = (SKILLS / "parsegym_resolve.md").read_text(encoding="utf-8")
    ex = s.examples or ([{"sentence": s.sentence, "en": s.sentence_en}] if s.sentence else [])
    ex_block = "\n".join(f'  - {e["sentence"]}\n    (EN: {e["en"]})' for e in ex[:3]) or "  (no example sentence)"
    obs = "\n".join(f"  - {o}" for o in s.observations) or "  (none)"
    answer_space = ""
    if s.solution.options:
        answer_space = "Candidate options to choose among:\n" + "\n".join(f"  {i+1}. {o}" for i, o in enumerate(s.solution.options))
    elif s.partial_parse:
        answer_space = "Current (competing) analyses:\n" + "\n".join(f"  - {a}" for a in s.partial_parse)
    return (
        f"{skill}\n\n"
        f"=== SCENARIO {s.id} ===\n"
        f"Language: {s.language}   Stage: {s.stage}   Assesses: {s.assesses}   Difficulty: {s.difficulty}\n"
        f"Target word: {s.word}\n"
        f"Examples in use:\n{ex_block}\n"
        f"What the references say:\n{obs}\n"
        f"{answer_space}\n"
        f"Give your response as JSON (kind = fix | unknown | ask_speaker)."
    )


def _dist(scen: list[Scenario], key) -> dict:
    return dict(Counter(key(s) for s in scen).most_common())


def assess(by_pair: dict[str, list[Scenario]]) -> dict:
    alls = [s for v in by_pair.values() for s in v]
    complete = sum(s.context_complete() for s in alls)
    sizes = sorted(len(render_prompt(s)) for s in alls)
    return {
        "total": len(alls),
        "by_pair": {p: len(v) for p, v in by_pair.items()},
        "stage": _dist(alls, lambda s: s.stage),
        "difficulty": _dist(alls, lambda s: s.difficulty),
        "phase": _dist(alls, lambda s: s.phase),
        "answer_kind": _dist(alls, lambda s: s.solution.kind),
        "assesses": _dist(alls, lambda s: s.assesses),
        "skills": dict(Counter(sk for s in alls for sk in s.skills).most_common()),
        "context_complete": f"{complete}/{len(alls)}",
        "prompt_chars_median": sizes[len(sizes) // 2] if sizes else 0,
        "prompt_chars_max": sizes[-1] if sizes else 0,
        "prompt_tokens_est_median": (sizes[len(sizes) // 2] // 4) if sizes else 0,
    }


def _bar(d: dict) -> str:
    return "  ".join(f"{k}={v}" for k, v in d.items())


def print_report(by_pair: dict[str, list[Scenario]]) -> dict:
    a = assess(by_pair)
    print(f"ParseGym coverage — {a['total']} scenarios across {len(by_pair)} languages {a['by_pair']}\n")
    print(f"  stage:       {_bar(a['stage'])}")
    print(f"  assesses:    {_bar(a['assesses'])}")
    print(f"  difficulty:  {_bar(a['difficulty'])}   phase: {_bar(a['phase'])}")
    print(f"  answer kind: {_bar(a['answer_kind'])}  (the point: fix vs 'I don't know' vs ask a speaker)")
    print(f"  skills used: {_bar(a['skills'])}")
    print(f"\n  LLM-ready:   {a['context_complete']} scenarios are self-contained (example + refs + answer space)")
    print(f"  prompt size: ~{a['prompt_tokens_est_median']} tokens median, "
          f"{a['prompt_chars_max']} chars max (fits a small-model window)")
    return a


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", choices=["spa", "ind", "tgl", "swh"])
    ap.add_argument("--render", help="print the LLM prompt for one scenario id")
    ap.add_argument("--md", help="write a Markdown report to this path")
    args = ap.parse_args(argv)
    by_pair = load_all(args.pair)
    if args.render:
        for scen in by_pair.values():
            for s in scen:
                if s.id == args.render:
                    print(render_prompt(s))
                    return 0
        print(f"scenario {args.render} not found")
        return 1
    a = print_report(by_pair)
    if args.md:
        Path(args.md).write_text(_markdown(a, by_pair), encoding="utf-8")
        print(f"\nwrote {args.md}")
    return 0


def _markdown(a: dict, by_pair: dict) -> str:
    L = [f"# ParseGym coverage report\n", f"**{a['total']} scenarios** across {a['by_pair']}.\n"]
    L.append("## What it assesses\n")
    for cap, n in a["assesses"].items():
        L.append(f"- **{cap}** ({n}) — {CAPABILITY_DESC.get(cap, '')}")
    L.append("\n## Difficulty rubric\n")
    for d, n in a["difficulty"].items():
        L.append(f"- **{d}** ({n}) — {DIFFICULTY_RUBRIC.get(d, '')}")
    L.append(f"\n## Distributions\n- stage: {a['stage']}\n- phase: {a['phase']}\n"
             f"- answer kind: {a['answer_kind']}\n- skills: {a['skills']}\n")
    L.append(f"## LLM-readiness\n- self-contained: {a['context_complete']}\n"
             f"- prompt size: ~{a['prompt_tokens_est_median']} tokens median, {a['prompt_chars_max']} chars max\n")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
