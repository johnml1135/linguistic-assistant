"""The report schema — the shared contract between GOLDEN reports (hand-authored ceiling) and GENERATED
reports (Gemma, from the packet alone). Both are ``ParadigmReport``; the scorer compares them slot by slot.

A ParadigmReport answers one question about one language: "is paradigm X present, and if so what are its
cells, what conditions it, and what doesn't fit?" — backed by citations to packet evidence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


def _mk(klass, c):
    """Build a dataclass from a possibly-dirty dict: keep known fields, coerce, drop extras."""
    if isinstance(c, klass):
        return c
    if not isinstance(c, dict):
        return klass(label=str(c)) if klass is Cell else klass(claim=str(c), source="explorer")
    known = {f.name for f in fields(klass)}
    return klass(**{k: v for k, v in c.items() if k in known})

PARADIGM_TYPES = (
    "noun-class", "case", "np-case", "voice-focus", "gender-number", "isolating", "tam",
    "agreement", "reduplication", "possessive", "classifier",
)


@dataclass
class Cell:
    """One cell of the paradigm — a noun class, a case, a voice, a gender/number value."""
    label: str                      # e.g. "cl1/2 (m-/wa-)", "accusative", "actor voice"
    markers: list[str] = field(default_factory=list)   # surface forms realising it
    function: str = ""              # grammatical function (e.g. "human sg/pl", "direct object")
    support: int = 0                # corpus occurrences backing it
    examples: list[str] = field(default_factory=list)
    # Optional (golden-side): the projected dep-role(s) this cell's marker should co-vary with — e.g.
    # accusative→["obj"], locative→["obl"]. When set, role-aware scoring credits the cell only if a packet
    # family has BOTH an overlapping marker AND a matching role (kills coincidental vowel-overlap in
    # fusional langs). Empty → marker-only matching (noun-class/agreement, where roles don't apply).
    match_roles: list[str] = field(default_factory=list)


@dataclass
class Citation:
    claim: str
    source: str                     # "thot" | "hc" | "explorer"
    stat: str = ""                  # the number/fact backing the claim


@dataclass
class ParadigmReport:
    language: str
    paradigm_type: str
    detected: bool
    confidence: float = 0.0
    cells: list[Cell] = field(default_factory=list)
    conditioning: str | None = None     # "vowel-harmony" | "gender" | "phonology" | "none" | None
    fit_none: dict = field(default_factory=lambda: {"n": 0, "examples": [], "note": ""})
    evidence_citations: list[Citation] = field(default_factory=list)
    prose: str = ""

    # ---- (de)serialisation -------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ParadigmReport":
        # Tolerant of real model JSON: ignore unknown keys, supply defaults for missing ones.
        cells = [_mk(Cell, c) for c in d.get("cells", []) or []]
        cites = [_mk(Citation, c) for c in d.get("evidence_citations", []) or []]
        fn = d.get("fit_none") or {}
        return cls(
            language=str(d.get("language", "")), paradigm_type=str(d.get("paradigm_type", "")),
            detected=bool(d.get("detected", False)), confidence=float(d.get("confidence", 0.0) or 0.0),
            cells=cells, conditioning=d.get("conditioning"),
            fit_none={"n": int(fn.get("n", 0) or 0), "examples": fn.get("examples", []) or [],
                      "note": fn.get("note", "") or ""},
            evidence_citations=cites, prose=str(d.get("prose", "") or ""),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ParadigmReport":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# JSON schema handed to the LLM so it returns a ParadigmReport-shaped object (forced structured output).
REPORT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "paradigm_type": {"type": "string", "enum": list(PARADIGM_TYPES)},
        "detected": {"type": "boolean"},
        "confidence": {"type": "number"},
        "cells": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "markers": {"type": "array", "items": {"type": "string"}},
                    "function": {"type": "string"},
                    "support": {"type": "integer"},
                    "examples": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["label", "markers", "function"],
            },
        },
        "conditioning": {"type": ["string", "null"]},
        "fit_none": {
            "type": "object",
            "properties": {
                "n": {"type": "integer"},
                "examples": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"},
            },
        },
        "evidence_citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "source": {"type": "string", "enum": ["thot", "hc", "explorer"]},
                    "stat": {"type": "string"},
                },
                "required": ["claim", "source"],
            },
        },
        "prose": {"type": "string"},
    },
    "required": ["language", "paradigm_type", "detected", "cells", "prose"],
}

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def golden_path(language: str, paradigm_type: str) -> Path:
    return GOLDEN_DIR / f"{language}_{paradigm_type}.json"
