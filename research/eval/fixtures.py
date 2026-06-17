"""A tiny, offline fixture: one toy-language instance + a deterministic MockProposer.

Lets the whole loop run with no model and no network (CI), and gives the sibling golden-set agent a
concrete shape to validate their instances against.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from harness.base import CompletionResult, Message

from proposal.contract import Case, IGTRecord

# An incomplete LIFT lexicon: only the verb root "amba" is known.
_FIXTURE_LIFT = """\
<lift version="0.13">
  <entry id="amba">
    <lexical-unit><form lang="tst"><text>amba</text></form></lexical-unit>
    <sense><grammatical-info value="Verb"/><gloss lang="en"><text>speak</text></gloss></sense>
  </entry>
</lift>
"""

_FIXTURE_HCGR = "<m3sketch><morphemes/><phonology/></m3sketch>"


@dataclass
class FixtureInstance:
    """Concrete Instance for the fixture; carries the answer key the StubScorer consumes."""

    id: str
    glottocode: str
    tier: str
    _case: Case
    answer_key: set[tuple[str, str]]

    @property
    def case(self) -> Case:
        return self._case


def fixture_instances() -> list[FixtureInstance]:
    case = Case(
        glottocode="tstx1234",
        igt=[
            IGTRecord(id="s1", text="niamba", translation="I speak", pos="Verb"),
            IGTRecord(id="s2", text="toto", translation="child", pos="Noun"),
        ],
        lexicon_lift=_FIXTURE_LIFT,
        grammar_hcgr=_FIXTURE_HCGR,
        meta={"fixture": True},
    )
    # Missing pieces a correct proposal should add: the 1SG prefix and the noun 'child'.
    answer_key = {
        ("morphophonology.affix.add", "ni-"),
        ("lexical.entry.create", "toto"),
    }
    return [FixtureInstance(id="tstx1234/easy/0", glottocode="tstx1234", tier="easy",
                            _case=case, answer_key=answer_key)]


# The change-set a "good" run should produce on the fixture (matches the answer key).
_CANNED_OPS = {
    "ops": [
        {"op": "morphophonology.affix.add", "form": "ni-", "gram": "1SG",
         "rationale": "niamba = ni-amba 'I speak'", "confidence": 0.8},
        {"op": "lexical.entry.create", "lexeme_form": "toto", "morph_type": "stem",
         "gloss": "child", "pos": "Noun", "confidence": 0.9},
    ]
}


class MockProposer:
    """Deterministic offline LLMClient that returns the canned fixture change-set."""

    name = "mock-proposer"

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 1024,
        json_schema: dict | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        return CompletionResult(
            text=json.dumps(_CANNED_OPS),
            model="mock-proposer",
            input_tokens=sum(len(m.content) for m in messages) // 4,
            output_tokens=64,
            latency_s=0.0,
            stop_reason="stop",
        )
