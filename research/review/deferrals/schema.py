"""The strict DeferralTicket schema (JSON + JSONL I/O) — the stable contract every tier populates.

Mirrors `parsegym.schema.Scenario` in spirit (frozen-ish dataclasses, `validate()`, JSONL round-trip),
but adds the resolution-ticket pieces: typed grammar-edit hypotheses, HC counterfactual diffs,
presentation options, triage tags, and a single structured resolution that flows to `deltas/`.

Phase A populates everything deterministically; Phase B/C only *append* hypotheses/prose to the same
record, so the store and renderer never branch on which tier produced a ticket.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ticket.type — the deferral predicament (what kind of decision is owed)
TYPES = ("lexeme_gloss", "affix_function", "segmentation", "phonology_rule", "homograph", "pos")
# ticket.domain — the linguistic layer
DOMAINS = ("lexical", "morphology", "phonology", "syntax")
# bug-tracker lifecycle
STATUSES = ("open", "in_review", "resolved", "wont_fix")
# the typed HC grammar-edit mechanisms a hypothesis may use (LibLCM/HC constructs)
EDIT_KINDS = (
    "add_lexentry",       # LexEntry (root) + gloss + POS
    "add_allomorph",      # MoStemAllomorph — extra stem shape on an existing entry
    "add_affix",          # MoInflAffMsa / MorphologicalRule — an affix→function rule
    "add_phon_rule",      # PhonologicalRule (incl. archiphoneme-collapse of an allomorph family)
    "split_homograph",    # a second LexEntry (sense/POS) for one surface form
    "resegment",          # a composite re-analysis (stem + known affix), expressed as sub-edits
    "narrow_affix",       # repair: restrict an existing affix (req_pos / slot)
    "retract_affix",      # repair: remove an over-broad affix
)
# the one resolution a reviewer records
RESOLUTION_ACTIONS = ("", "accept_option", "accept_with_words", "reject_with_reason")


@dataclass
class GrammarEdit:
    """A single typed op over the gold `golden.grammar.LangModel`. `params` is kind-specific and is
    consumed by `deferrals.edits.apply`. Kept as a flat dict so the whole ticket serialises trivially."""

    kind: str
    params: dict = field(default_factory=dict)

    def validate(self) -> None:
        assert self.kind in EDIT_KINDS, f"unknown edit kind {self.kind!r}"


@dataclass
class Counterfactual:
    """One verse's before/after under a hypothesis — the literal 'if A, this parses thus'.

    `now` / `if_hyp` are per-word analyses as gloss sequences (the reliable HC output, see hc.gloss_seq):
    `{word: [["gloss","gloss",...], ...]}`. `focus_*` summarise whether the ticket's focus form parsed.
    """

    ref: str                              # verse reference (e.g. "MAT 1:1") or a synthetic id
    text: str                             # the verse text (vernacular)
    focus: str = ""                       # the focus surface form in this verse
    now: dict = field(default_factory=dict)
    if_hyp: dict = field(default_factory=dict)
    focus_parsed_now: bool = False
    focus_parsed_if: bool = False
    unverified: bool = False              # HC timed out → not presented as confirmed


@dataclass
class Hypothesis:
    """A candidate resolution = one or more typed grammar edits, with its HC consequences + metrics."""

    id: str
    mechanism: str                        # the HC mechanism label (an EDIT_KIND, or "composite")
    description: str                      # plain-language statement of the hypothesis
    edits: list = field(default_factory=list)            # list[GrammarEdit]
    counterfactuals: list = field(default_factory=list)  # list[Counterfactual]
    discriminates: list = field(default_factory=list)    # option ids this hypothesis is distinguished by
    metrics: dict = field(default_factory=dict)          # ΔMDL, coverage, net_delta, over_gen, … (stage 4)
    source: str = "taxonomy"              # taxonomy | llm | workflow
    unverified: bool = False              # any counterfactual timed out / HC unavailable
    verdict: dict = field(default_factory=dict)          # {acceptable: bool, gains, regressions, net, …}

    def validate(self) -> None:
        assert self.id, "hypothesis needs an id"
        for e in self.edits:
            e.validate()


@dataclass
class PresentationOption:
    """A scripted speaker question (from parsegym.questions) slot-filled for this ticket."""

    id: str
    question_id: str                      # a parsegym.questions id
    kind: str                             # the question's elicitation move (open/choice/yes_no/…)
    text: str                             # the rendered question
    discriminates: list = field(default_factory=list)    # hypothesis ids this question tells apart


@dataclass
class Resolution:
    """The single action a reviewer records. Empty `action` = unresolved."""

    action: str = ""
    hypothesis_id: str = ""               # accept_option / accept_with_words
    extra_words: list = field(default_factory=list)      # accept_with_words
    reason: str = ""                      # reject_with_reason
    by: str = ""
    delta_ops: list = field(default_factory=list)        # the deltas/ ops emitted on accept (audit trail)

    def validate(self) -> None:
        assert self.action in RESOLUTION_ACTIONS, f"unknown resolution action {self.action!r}"
        if self.action in ("accept_option", "accept_with_words"):
            assert self.hypothesis_id, f"{self.action} needs a hypothesis_id"
        if self.action == "reject_with_reason":
            assert self.reason, "reject_with_reason needs a reason"


@dataclass
class DeferralTicket:
    id: str
    pair: str
    type: str
    domain: str
    status: str = "open"
    target: dict = field(default_factory=dict)           # {form, lemma?, gloss?, candidates?, …}
    confidence: float = 0.0
    impact: dict = field(default_factory=dict)           # {freq, wordforms, score, priority}
    dependencies: list = field(default_factory=list)     # ids of related tickets (shared lemma/affix/stem)
    context_md: str = ""
    hypotheses: list = field(default_factory=list)       # list[Hypothesis]
    presentation_options: list = field(default_factory=list)  # list[PresentationOption]
    resolution: Resolution = field(default_factory=Resolution)
    tags: dict = field(default_factory=dict)             # domain (dup), impact bucket, source, …
    provenance: dict = field(default_factory=dict)
    history: list = field(default_factory=list)          # [{from, to, by}] status transitions

    def validate(self) -> None:
        assert self.type in TYPES, f"unknown type {self.type!r}"
        assert self.domain in DOMAINS, f"unknown domain {self.domain!r}"
        assert self.status in STATUSES, f"unknown status {self.status!r}"
        assert self.id and self.pair, "ticket needs id + pair"
        for h in self.hypotheses:
            h.validate()
        self.resolution.validate()

    # ---- serialisation -------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DeferralTicket":
        d = dict(d)
        d["hypotheses"] = [_hyp_from_dict(h) for h in d.get("hypotheses", [])]
        d["presentation_options"] = [PresentationOption(**o) for o in d.get("presentation_options", [])]
        res = d.get("resolution") or {}
        d["resolution"] = Resolution(**res) if isinstance(res, dict) else res
        # drop unknown keys defensively so a forward-compatible field never breaks load
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})


def _hyp_from_dict(h: dict) -> Hypothesis:
    h = dict(h)
    h["edits"] = [GrammarEdit(**e) for e in h.get("edits", [])]
    h["counterfactuals"] = [Counterfactual(**c) for c in h.get("counterfactuals", [])]
    known = Hypothesis.__dataclass_fields__.keys()
    return Hypothesis(**{k: v for k, v in h.items() if k in known})


def write_jsonl(tickets: list[DeferralTicket], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for t in tickets:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
    return len(tickets)


def read_jsonl(path: Path) -> list[DeferralTicket]:
    if not Path(path).exists():
        return []
    out: list[DeferralTicket] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(DeferralTicket.from_dict(json.loads(line)))
    return out
