"""ParseGym scenario schema.

A ParseGym scenario is a *parsing predicament* with a known good response. Unlike the affix-analysis
scenarios in `cycle/llm_propose.py` (one affix → one label), these capture the messy states a grammar
is actually in mid-induction, and — crucially — allow the correct response to be "I don't know" or
"ask the speaker question X", not only "make this edit". Those non-edit answers are the point: they are
where an LLM must stop guessing, and they are what we test small local models (Gemma/Qwen) on.

Stages (what kind of predicament):
  cold_start   — almost nothing parses; goal is just an initial gloss / root.
  overparse    — the grammar accepts too much; rules must be pared back.
  homophone    — one surface form, several senses/POS; which is meant.
  hidden_rule  — an irregular stem / morphophonological alternation the rules don't yet capture.

Difficulty: easy | medium | hard.   Phase: early | late (in the documentation lifecycle).

Solution kinds:
  fix          — a concrete grammar/lexicon edit, stated in LibLCM/HC terms (the known answer).
  unknown      — genuinely undecidable from the evidence at hand ("I don't know" is correct).
  ask_speaker  — invoke a scripted `SpeakerQuestion`; the answer IS choosing the right question + fillers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STAGES = ("cold_start", "overparse", "homophone", "hidden_rule")
DIFFICULTIES = ("easy", "medium", "hard")
PHASES = ("early", "late")
SOLUTION_KINDS = ("fix", "unknown", "ask_speaker")


@dataclass
class Solution:
    kind: str                         # one of SOLUTION_KINDS
    # kind == "fix": a concrete edit, phrased in LibLCM/HC mechanism terms.
    action: str = ""
    mechanism: str = ""               # e.g. "MoStemAllomorph", "AffixTemplate slot prune", "LexEntry"
    # kind == "ask_speaker": the scripted question + its rendered text and offered options.
    question_id: str = ""
    ask: str = ""
    options: tuple[str, ...] = ()
    rationale: str = ""

    def validate(self) -> None:
        assert self.kind in SOLUTION_KINDS, self.kind
        if self.kind == "fix":
            assert self.action, "fix needs an action"
        if self.kind == "ask_speaker":
            assert self.question_id and self.ask, "ask_speaker needs a question_id + rendered ask"


@dataclass
class Scenario:
    id: str
    language: str
    stage: str                        # one of STAGES
    difficulty: str
    phase: str
    word: str                         # the target surface form
    assesses: str = ""                # the capability this scenario tests (see CAPABILITIES)
    skills: list = field(default_factory=list)  # skill file(s) that would resolve it
    sentence: str = ""                # the primary example sentence containing it (scripture)
    sentence_en: str = ""             # its English parallel (ground truth for meaning)
    examples: list = field(default_factory=list)  # more occurrences: [{"sentence":.., "en":..}, ...]
    partial_parse: list = field(default_factory=list)   # current analyses: [] / one / too-many / wrong
    observations: list[str] = field(default_factory=list)  # what the references say
    solution: Solution = field(default_factory=lambda: Solution("unknown"))
    provenance: dict = field(default_factory=dict)

    def validate(self) -> None:
        assert self.stage in STAGES, self.stage
        assert self.difficulty in DIFFICULTIES, self.difficulty
        assert self.phase in PHASES, self.phase
        self.solution.validate()

    def context_complete(self) -> bool:
        """Enough to populate an LLM test prompt on its own: an example, references, and an answer space."""
        has_example = bool(self.sentence or self.examples)
        has_refs = bool(self.observations)
        has_answer_space = bool(
            (self.solution.kind == "ask_speaker" and self.solution.ask)  # open questions need no options
            or (self.solution.kind == "fix" and self.solution.action)
            or self.partial_parse
            or self.solution.kind == "unknown"
        )
        return has_example and has_refs and has_answer_space

    def to_dict(self) -> dict:
        return asdict(self)


def write_jsonl(scenarios: list[Scenario], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(s.to_dict(), ensure_ascii=False) + "\n" for s in scenarios),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[Scenario]:
    out: list[Scenario] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        sol = d.get("solution", {"kind": "unknown"})
        sol["options"] = tuple(sol.get("options", ()))
        d["solution"] = Solution(**sol)
        out.append(Scenario(**d))
    return out
