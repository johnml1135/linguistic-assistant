"""The deterministic grammar-assessment scorecard (schema shared by the Python and future C# paths).

Per the `assess-grammar-metrics` spec: stable key order, no timestamps, content hash — so two runs on
identical inputs are byte-identical and the C# `liblcm-grammar-analyzer` can emit the same shape.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scorecard:
    grammar_id: str
    corpus_id: str
    source: str  # "hermitcrab" | "liblcm" | "lift"
    measures: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        body = {
            "grammar_id": self.grammar_id,
            "corpus_id": self.corpus_id,
            "source": self.source,
            "measures": self.measures,
        }
        body["content_hash"] = _hash(body)
        return body

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(body: dict) -> str:
    return "sha256:" + hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()[:16]
