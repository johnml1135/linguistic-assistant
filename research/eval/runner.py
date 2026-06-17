"""The loop: instances -> propose -> score -> records. Correctness is never computed here."""

from __future__ import annotations

from typing import Iterable

from harness.base import LLMClient

from proposal.contract import ChangeSet, Instance, Scorer, ValidationFailure
from proposal.propose import ProposeConfig, propose


def run_instances(
    instances: Iterable[Instance],
    client: LLMClient,
    scorer: Scorer,
    cfg: ProposeConfig | None = None,
) -> list[dict]:
    cfg = cfg or ProposeConfig()
    records: list[dict] = []
    for inst in instances:
        result = propose(inst.case, client, cfg)
        rec: dict = {
            "id": inst.id,
            "glottocode": inst.glottocode,
            "tier": inst.tier,
            "model": getattr(client, "name", "?"),
            "seed": cfg.seed,
            "backend_kind": cfg.backend_kind,
            "scorer": getattr(scorer, "name", "?"),
        }
        if isinstance(result, ValidationFailure):
            rec.update(parsed_ok=False, reward=0.0, n_ops=0,
                       diagnostics={"validation_failure": result.reason})
        else:
            assert isinstance(result, ChangeSet)
            score = scorer.score(inst, result)
            rec.update(parsed_ok=score.parsed_ok, reward=round(score.reward, 4),
                       n_ops=len(result.ops), diagnostics=score.diagnostics)
        records.append(rec)
    return records
