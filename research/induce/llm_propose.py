"""LLM propose step — turn curated morpheme EVIDENCE into a grammatical ANALYSIS, and bank it as a
reusable golden-set "scenario".

This is the seam where judgment replaces heuristics: given everything the deterministic loop knows about
an affix (its surface, side, slot, the POS it attaches to, the English its morpheme aligned to, and a
few real examples), an LLM proposes *what the morpheme actually is* — "this `-s` is PL", "this `na-` is
the present-tense subject prefix". The judgment is the [[propose-from-evidence]] skill.

Two design commitments the project depends on:
  1. **Swappable backend (config, not code).** The model is resolved through `harness.build_client`:
     `opus` (claude-opus-4-8) today; `vllm`/`ollama` (Qwen3.6 / Gemma4) or `ik_llama` later — same prompt,
     same schema. A deterministic **heuristic** proposer is the offline baseline (and the fallback when
     no API key / server is present), so the pipeline always runs.
  2. **Every call is a curated, self-contained scenario.** The (evidence → question → answer) triple is
     written to `out/<pair>_scenarios.jsonl`. These are the *foundation*: validate the answers against
     external data later, and the curated scenarios become the 50–400-item suite for testing small local
     models — the curation (the hard linguistic context-building) is model-independent and reusable.

Run: `python cycle/llm_propose.py --pair spa --endpoint mock` (offline heuristic) or `--endpoint opus`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RESEARCH))

from induce.morph_align import EBIBLE, OUT, PAIR_DIR, load_model  # noqa: E402

# Grammatical labels the proposer is asked to choose from (extend as needed; "?" = unknown/leave).
LABELS = ["PL", "SG", "PST", "PRS", "FUT", "PROG", "PFV", "SUBJ", "OBJ", "POSS", "DEF", "INDF",
          "NEG", "CAUS", "APPL", "PASS", "NMLZ", "ADVZ", "CMPR", "SUPL", "GEN", "DAT", "LOC", "?"]

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": LABELS,
                  "description": "the grammatical category gloss for this morpheme"},
        "category": {"type": "string", "enum": ["inflectional", "derivational", "clitic", "unknown"]},
        "gloss": {"type": "string", "description": "a short human gloss (often the label or an English word)"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string", "description": "one sentence citing the evidence"},
    },
    "required": ["label", "category", "gloss", "confidence", "rationale"],
}


@dataclass
class MorphemeAnalysis:
    label: str
    category: str
    gloss: str
    confidence: float
    rationale: str
    source: str = "heuristic"  # which proposer produced it (model name / "heuristic")


@dataclass
class Scenario:
    """A self-contained, model-independent unit of work: curated evidence + question + proposed answer.

    `validated` stays None until an answer is confirmed (e.g. against external descriptive data); the
    validated set is the gold the local-model suite is scored against.
    """

    id: str
    task: str
    language: str
    evidence: dict
    question: str
    proposed: dict | None = None
    validated: dict | None = None
    notes: list[str] = field(default_factory=list)


# ── Evidence curation (the reusable, model-independent part) ─────────────────────────────────────
def _word_glosses(pair: str) -> dict[str, str]:
    p = EBIBLE / PAIR_DIR[pair] / "glosses.tsv"
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def build_affix_scenarios(pair: str, *, max_examples: int = 6) -> list[Scenario]:
    """Assemble one scenario per induced affix from the dumped model + morpheme glosses + examples."""
    model = load_model(pair)
    wg = _word_glosses(pair)
    summ_path = OUT / f"{pair}_morpheme_glosses.summary.json"
    morph_gloss = json.loads(summ_path.read_text(encoding="utf-8"))["affix_glosses"] if summ_path.exists() else {}
    words = list(wg)

    scenarios: list[Scenario] = []
    for a in model.affixes:
        # a few real example words bearing this affix, with their English gloss
        examples = []
        for w in words:
            hit = (a.kind == "suffix" and w.endswith(a.form) and len(w) > len(a.form)) or \
                  (a.kind == "prefix" and w.startswith(a.form) and len(w) > len(a.form)) or \
                  (a.kind == "infix" and a.form in w[1:-1])
            if hit and wg.get(w) and wg[w] != "?":
                examples.append({"word": w, "english": wg[w]})
            if len(examples) >= max_examples:
                break
        evidence = {
            "affix": a.form, "side": a.kind, "slot": a.slot_ord,
            "attaches_to_pos": a.req_pos or "any", "frequency": a.count,
            "current_gloss": a.gloss, "morpheme_alignment_gloss": morph_gloss.get(a.form),
            "examples": examples,
        }
        scenarios.append(Scenario(
            id=f"{pair}:{a.kind}:{a.form}",
            task="analyze_affix",
            language={"swh": "Swahili", "ind": "Indonesian", "tgl": "Tagalog", "spa": "Spanish"}.get(pair, pair),
            evidence=evidence,
            question=(f"In {pair}, the {a.kind} '{a.form}' attaches to {a.req_pos or 'words'}. From the "
                      "evidence (examples with English glosses, the morpheme's aligned English, its slot), "
                      "what grammatical morpheme is it? Give a label, category, gloss, confidence, rationale."),
        ))
    return scenarios


# ── Proposers (swappable) ────────────────────────────────────────────────────────────────────────
_FUNC_WORD_LABEL = {  # morpheme-aligned English function word → a grammatical label (heuristic baseline)
    "the": "DEF", "a": "INDF", "an": "INDF", "of": "GEN", "in": "LOC", "to": "DAT", "not": "NEG",
    "us": "OBJ", "them": "OBJ", "him": "OBJ", "her": "OBJ", "me": "OBJ", "my": "POSS", "his": "POSS",
}


def heuristic_analysis(ev: dict) -> MorphemeAnalysis:
    """Deterministic baseline (and offline fallback): read the analysis off the existing evidence."""
    cur = (ev.get("current_gloss") or "").strip()
    if cur.isupper() and cur not in ("", "?"):  # already relabelled (English-diff inference) → trust it
        return MorphemeAnalysis(cur, "inflectional", cur, 0.6, "carried over from English-inflection inference.")
    al = (ev.get("morpheme_alignment_gloss") or "").lower()
    if al in _FUNC_WORD_LABEL:
        lab = _FUNC_WORD_LABEL[al]
        return MorphemeAnalysis(lab, "clitic" if lab in ("OBJ", "POSS") else "inflectional", al, 0.4,
                                f"morpheme aligned to the English function word '{al}'.")
    return MorphemeAnalysis("?", "unknown", al or ev.get("affix", ""), 0.1,
                            "no clear evidence; needs review / a stronger model.")


def llm_analysis(ev: dict, question: str, client, *, skill: str | None = None) -> MorphemeAnalysis:
    """Ask a real model (via the harness) for a structured analysis. Raises on transport/parse error."""
    from propose.harness.base import Message

    system = (
        "You are a field linguist analyzing morphology. Given evidence about one affix — example words "
        "with English glosses, the English its morpheme statistically aligns to, the POS it attaches to, "
        "and its position slot — identify the grammatical morpheme. Prefer a standard Leipzig label. "
        "Be conservative: if the evidence is weak, answer label '?' with low confidence. "
        "Return ONLY JSON matching the schema (label, category, gloss, confidence, rationale)."
    )
    user = json.dumps({"question": question, "evidence": ev}, ensure_ascii=False, indent=2)
    res = client.complete([Message("system", system), Message("user", user)],
                          max_tokens=512, json_schema=ANALYSIS_SCHEMA)
    data = json.loads(res.text)
    return MorphemeAnalysis(
        label=str(data.get("label", "?")), category=str(data.get("category", "unknown")),
        gloss=str(data.get("gloss", "")), confidence=float(data.get("confidence", 0.0)),
        rationale=str(data.get("rationale", "")), source=res.model,
    )


def analyze(pair: str, endpoint: str = "mock") -> dict:
    """Build scenarios, propose an analysis for each (LLM if reachable, else heuristic), persist."""
    scenarios = build_affix_scenarios(pair)
    client = None
    if endpoint not in ("mock", "heuristic"):
        try:
            from propose.harness.registry import build_client
            client = build_client(endpoint)
        except Exception as exc:  # no key / no server / not installed → heuristic baseline
            print(f"[{pair}] LLM endpoint '{endpoint}' unavailable ({exc!r}); using heuristic baseline.")

    used_llm = 0
    for s in scenarios:
        analysis = None
        if client is not None:
            try:
                analysis = llm_analysis(s.evidence, s.question, client)
                used_llm += 1
            except Exception as exc:  # transport/parse failure on this item → heuristic for it
                s.notes.append(f"llm error: {exc!r}")
        if analysis is None:
            analysis = heuristic_analysis(s.evidence)
        s.proposed = asdict(analysis)

    OUT.mkdir(exist_ok=True)
    path = OUT / f"{pair}_scenarios.jsonl"
    path.write_text("".join(json.dumps(asdict(s), ensure_ascii=False) + "\n" for s in scenarios), encoding="utf-8")
    return {"pair": pair, "scenarios": len(scenarios), "via_llm": used_llm,
            "endpoint": endpoint, "path": str(path)}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--endpoint", default="mock",
                    help="harness endpoint: mock/heuristic (offline), opus, vllm, ollama, ik_llama")
    args = ap.parse_args(argv)
    s = analyze(args.pair, endpoint=args.endpoint)
    print(f"[{args.pair}] {s['scenarios']} scenarios written to {s['path']} "
          f"({s['via_llm']} via LLM '{s['endpoint']}', rest heuristic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
