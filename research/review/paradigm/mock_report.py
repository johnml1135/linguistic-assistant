"""A JSON-emitting mock LLM client to exercise the *structured* report path offline.

The shared ``propose.harness.mock.MockClient`` returns a single A-D letter (built for multiple-choice
benchmarks), so it can't test report generation. This one returns a deliberately MESSY ParadigmReport
JSON — an unknown top-level key, a cell with an extra field, a citation missing its optional stat — so the
test proves ``json.loads -> ParadigmReport.from_dict -> score`` survives real-model-shaped output, not just
the clean dicts we author by hand.

It reads a few real markers out of the packet embedded in the prompt so the produced report is non-trivial
(it actually reports SOME of the packet's cells), giving a meaningful — and deliberately partial, hence
weaker-than-golden — score rather than a degenerate one.
"""

from __future__ import annotations

import json
import re
from typing import Any, Sequence

from propose.harness.base import CompletionResult, Message


class JsonReportMockClient:
    name = "mockjson"

    def __init__(self, *, name: str = "mockjson") -> None:
        self.name = name

    def complete(self, messages: Sequence[Message], *, max_tokens: int = 2048,
                 json_schema: dict | None = None, **kwargs: Any) -> CompletionResult:
        prompt = "\n".join(m.content for m in messages)
        lang = (re.search(r'"language":\s*"([^"]+)"', prompt) or [None, "xx"])[1]
        ptype = (re.search(r"PARADIGM IN QUESTION:\s*(\S+)", prompt) or [None, "noun-class"])[1]
        # pull up to 3 class-group labels + their prefixes from the packet text (partial coverage on purpose)
        labels = re.findall(r'"label":\s*"([^"]+)"', prompt)
        prefixes = re.findall(r'"prefixes":\s*\[([^\]]*)\]', prompt)
        cells = []
        for i, lab in enumerate(labels[:3]):
            ms = re.findall(r'"([^"]+)"', prefixes[i]) if i < len(prefixes) else []
            cells.append({"label": lab, "markers": ms, "function": "reported by mock",
                          "support": 0, "examples": [], "_extra_field": "ignored"})  # extra key on purpose
        out = {
            "language": lang, "paradigm_type": ptype, "detected": True, "confidence": 0.5,
            "cells": cells, "conditioning": "phonology",
            "fit_none": {"n": 0, "examples": []},
            "evidence_citations": [{"claim": "classes exist", "source": "hc"}],  # no 'stat' (optional)
            "prose": f"Mock report for {lang} {ptype}: {len(cells)} cells reported.",
            "_unknown_top_key": "should be ignored by from_dict",  # unknown key on purpose
        }
        text = json.dumps(out, ensure_ascii=False)
        return CompletionResult(text=text, model=self.name, input_tokens=len(prompt) // 4,
                                output_tokens=len(text) // 4, latency_s=0.0, stop_reason="stop")
