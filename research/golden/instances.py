"""Generate contract-shaped, ablated golden instances from a frozen gold directory.

This is the golden side of the seam with ``research/proposal`` + ``research/eval`` (their tasks
5.1 / 6.4). Each instance satisfies ``proposal.contract.Instance`` (``id``/``glottocode``/``tier`` +
a ``.case``) and ALSO carries the hidden answer data (the ablated :class:`~golden.ablate.Instance`
and an op-signature ``answer_key``) on the concrete type — so both the real HC scorer
(:mod:`golden.scorer`) and the fixture stub scorer work against it.

Instances are rebuilt from ``gold/analyses.jsonl`` alone, so evaluation needs no access to the
(git-ignored, CC-BY-NC) ``_sources`` corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from proposal.contract import Case, IGTRecord

from . import ablate, hc
from .grammar import build_model
from .igt import Morph, MorphWord
from .lift_emit import build_lift


def _load_words(analyses_path: Path) -> list[MorphWord]:
    words: list[MorphWord] = []
    for line in analyses_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        morphs = [Morph(form=f, gloss=g) for f, g in d["analysis"]]
        words.append(MorphWord(surface=d["form"], morphs=morphs))
    return words


def _read_igt(path: Path) -> list[IGTRecord]:
    out: list[IGTRecord] = []
    if not path.exists():
        return out
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        d = json.loads(line)
        out.append(IGTRecord(id=str(d.get("id", i)), text=d.get("text", ""),
                             translation=d.get("translation", "")))
    return out


@dataclass
class GoldInstance:
    """A golden instance: contract-shaped, with the hidden answer key kept here, not in the Case."""

    id: str
    glottocode: str
    tier: str
    abl: ablate.Instance                      # incomplete model + held_out + control (the oracle)
    answer_key: set = field(default_factory=set)  # op-signatures the agent should produce
    _case: Case | None = None

    @property
    def case(self) -> Case:
        return self._case


def _answer_sigs(inst: ablate.Instance) -> set[tuple[str, str]]:
    sigs: set[tuple[str, str]] = set()
    for e in inst.removed_lex:
        sigs.add(("lexical.entry.create", e.form))
        sigs.add(("lexical.sense.create", e.gloss))
    for a in inst.removed_affix:
        sigs.add(("morphophonology.affix.add", a.form))
    return sigs


def make_instances(
    glottocode: str,
    golden_root: str | Path = "research/golden",
    *,
    n_lex: int = 5,
    n_affix: int = 5,
    tier: str = "hard",
) -> list[GoldInstance]:
    """Build ablated instances for one frozen language: ``n_lex`` lexical + ``n_affix`` affix removals."""
    d = Path(golden_root) / glottocode
    words = _load_words(d / "gold" / "analyses.jsonl")
    igt = _read_igt(d / "raw" / "igt.jsonl")
    model = build_model(glottocode, words)

    out: list[GoldInstance] = []
    plan = [("lex", r) for r in range(n_lex)] + [("affix", r) for r in range(n_affix)]
    for kind, rank in plan:
        abl = (ablate.ablate_lex if kind == "lex" else ablate.ablate_affix)(model, words, rank=rank)
        if not abl.held_out:
            continue
        case = Case(
            glottocode=glottocode,
            igt=igt,
            lexicon_lift=build_lift(abl.incomplete),
            grammar_hcgr=hc.build_grammar_xml(abl.incomplete),
            meta={"tier": tier, "kind": kind, "held_out": len(abl.held_out)},
        )
        out.append(GoldInstance(
            id=f"{glottocode}/{kind}/{rank}", glottocode=glottocode, tier=tier,
            abl=abl, answer_key=_answer_sigs(abl), _case=case,
        ))
    return out
