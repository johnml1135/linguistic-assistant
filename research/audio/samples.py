"""Sample-word loading and pair-data resolution for the audio evidence add-on."""

from __future__ import annotations

import json
from pathlib import Path

from .contract import ResolvedSampleWord, SampleWord, require_supported_target


def load_sample_manifest(path: str | Path) -> list[SampleWord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    samples = data.get("samples", [])
    if not isinstance(samples, list):
        raise ValueError("sample manifest 'samples' must be a list")

    out: list[SampleWord] = []
    for raw in samples:
        if not isinstance(raw, dict):
            raise ValueError("sample entry must be an object")
        target_key = require_supported_target(str(raw.get("target_key", "")))
        word = str(raw.get("word", "")).strip()
        if not word:
            raise ValueError("sample entry missing word")
        out.append(
            SampleWord(
                target_key=target_key,
                word=word,
                lemma=_optional_text(raw.get("lemma")),
                gloss=_optional_text(raw.get("gloss")),
                ref=_optional_text(raw.get("ref")),
                note=_optional_text(raw.get("note")),
            )
        )
    return out


def resolve_and_persist_samples(
    pair_dir: str | Path,
    target_key: str,
    samples: list[SampleWord],
) -> list[ResolvedSampleWord]:
    normalized_target = require_supported_target(target_key)
    pair_path = Path(pair_dir)
    rows = _read_parallel_rows(pair_path / "parallel.jsonl")

    resolved: list[ResolvedSampleWord] = []
    for sample in samples:
        if sample.target_key != normalized_target:
            continue
        refs = [str(row["ref"]) for row in rows if sample.word in row["tgt"]]
        status = "matched" if refs else "unresolved"
        resolved.append(
            ResolvedSampleWord(
                target_key=sample.target_key,
                word=sample.word,
                status=status,
                refs=refs,
                lemma=sample.lemma,
                gloss=sample.gloss,
                note=sample.note,
            )
        )

    out_dir = pair_path / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "target_key": normalized_target,
        "samples": [item.to_dict() for item in resolved],
    }
    (out_dir / "samples.resolved.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return resolved


def _read_parallel_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        refs = str(raw.get("ref", "")).strip()
        tgt = raw.get("tgt", [])
        if not isinstance(tgt, list):
            raise ValueError("parallel row 'tgt' must be a list")
        rows.append({"ref": refs, "tgt": [str(token) for token in tgt]})
    return rows


def _optional_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)