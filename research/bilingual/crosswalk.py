"""Tag crosswalk: project POS / inflection-feature labels <-> Apertium `sdef` tags.

An explicit, reviewable contract used by the HC->stream adapter and `.dix` export/import. Unmapped
tags are *reported*, never silently dropped. Stdlib-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Minimal default mapping (project label -> Apertium sdef). Extend per project; load_crosswalk()
# overrides/augments from a JSON file.
DEFAULT_MAP: dict[str, str] = {
    # parts of speech
    "Noun": "n",
    "Verb": "v",
    "Adjective": "adj",
    "Adverb": "adv",
    "Pronoun": "prn",
    "Adposition": "adp",
    # number / person (a few; extend as needed)
    "sg": "sg",
    "pl": "pl",
    "du": "du",
    "1": "p1",
    "2": "p2",
    "3": "p3",
    # tense/aspect
    "past": "past",
    "pres": "pres",
    "fut": "fut",
}


@dataclass
class Crosswalk:
    project_to_apertium: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MAP))

    @property
    def apertium_to_project(self) -> dict[str, str]:
        # last-writer-wins is fine; the map is intended to be ~bijective per project
        return {v: k for k, v in self.project_to_apertium.items()}

    def to_apertium(self, tags: list[str] | tuple[str, ...]) -> tuple[list[str], list[str]]:
        """Map project tags -> Apertium tags. Returns (mapped, unmapped) — never drops silently."""
        mapped, unmapped = [], []
        for t in tags:
            a = self.project_to_apertium.get(t)
            (mapped.append(a) if a is not None else unmapped.append(t))
        return mapped, unmapped

    def from_apertium(self, tags: list[str] | tuple[str, ...]) -> tuple[list[str], list[str]]:
        rev = self.apertium_to_project
        mapped, unmapped = [], []
        for t in tags:
            p = rev.get(t)
            (mapped.append(p) if p is not None else unmapped.append(t))
        return mapped, unmapped


def load_crosswalk(path: str | Path | None = None) -> Crosswalk:
    cw = Crosswalk()
    if path is not None and Path(path).exists():
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cw.project_to_apertium.update(data)
    return cw
