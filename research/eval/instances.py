"""Load golden instances from ``research/golden/`` via the contract.

This is the **adapter seam** to the sibling golden-set work. The golden-set design freezes per-language
files under ``research/golden/<glottocode>/`` (`raw/igt.jsonl`, `gold/lexicon.lift`,
`gold/grammar.hcgr.xml`, …); the ablator turns those into scored *instances*. Until that instance/
ablation manifest shape is finalized, this loader reads the documented gold files into a single Case
per language and is intentionally tolerant — reconcile the exact instance shape with the sibling agent
(tasks 5.1 / 6.4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from proposal.contract import Case, IGTRecord


@dataclass
class GoldenFileInstance:
    id: str
    glottocode: str
    tier: str
    _case: Case

    @property
    def case(self) -> Case:
        return self._case


def _read_igt_jsonl(path: Path) -> list[IGTRecord]:
    records: list[IGTRecord] = []
    if not path.exists():
        return records
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        records.append(
            IGTRecord(
                id=str(d.get("id", i)),
                text=d.get("text") or d.get("t") or "",
                translation=d.get("translation") or d.get("l") or "",
                segmentation=d.get("segmentation") or d.get("m"),
                gloss=d.get("gloss") or d.get("g"),
                pos=d.get("pos") or d.get("p"),
            )
        )
    return records


def load_golden_instances(
    glottocodes: list[str],
    *,
    tier: str = "hard",
    golden_root: str | Path = "research/golden",
) -> list[GoldenFileInstance]:
    """Best-effort loader for the documented golden layout. Skips languages with missing files."""
    root = Path(golden_root)
    out: list[GoldenFileInstance] = []
    for gc in glottocodes:
        d = root / gc
        igt = _read_igt_jsonl(d / "raw" / "igt.jsonl")
        lift = (d / "gold" / "lexicon.lift")
        hcgr = (d / "gold" / "grammar.hcgr.xml")
        if not igt or not lift.exists():
            print(f"[instances] skip {gc!r}: missing raw/igt.jsonl or gold/lexicon.lift under {d}")
            continue
        case = Case(
            glottocode=gc,
            igt=igt,
            lexicon_lift=lift.read_text(encoding="utf-8") if lift.exists() else "",
            grammar_hcgr=hcgr.read_text(encoding="utf-8") if hcgr.exists() else "",
            meta={"source": str(d)},
        )
        out.append(GoldenFileInstance(id=f"{gc}/{tier}/0", glottocode=gc, tier=tier, _case=case))
    return out
