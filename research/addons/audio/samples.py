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
    stems: list[str] | None = None,
) -> list[ResolvedSampleWord]:
    normalized_target = require_supported_target(target_key)
    pair_path = Path(pair_dir)
    rows = _read_parallel_rows(pair_path / "parallel.jsonl")
    stem_set = set(stems or [])

    resolved: list[ResolvedSampleWord] = []
    for sample in samples:
        if sample.target_key != normalized_target:
            continue
        refs = _match_refs(rows, sample.word, stem_aware=sample.word in stem_set)
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


def _match_refs(rows: list[dict[str, object]], word: str, *, stem_aware: bool) -> list[str]:
    """Refs where ``word`` appears. Stem-aware mode also matches inflected occurrences (a token that
    starts with the word as a stem), so an agglutinative sample resolves to its inflected forms too,
    preserving the matched/unresolved contract."""
    refs: list[str] = []
    for row in rows:
        tokens = [str(t) for t in row["tgt"]]  # type: ignore[index]
        exact = word in tokens
        inflected = stem_aware and any(t.startswith(word) and len(t) > len(word) for t in tokens)
        if exact or inflected:
            refs.append(str(row["ref"]))
    return refs


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