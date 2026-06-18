"""Workflow entrypoint for the optional audio evidence add-on."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .allosaurus import run_phone_recognition
from .catalog import load_audio_catalog
from .contract import AudioCatalogEntry, PhoneEvidence, RecognitionResult, require_supported_target
from .reports import build_orthography_alerts, build_pronunciation_candidates, build_triangulation_reports
from .samples import load_sample_manifest, resolve_and_persist_samples


def run_enrichment(
    pair_dir: str | Path,
    *,
    target_key: str,
    sample_manifest_path: str | Path,
    catalog_path: str | Path | None = None,
    include_timestamps: bool = False,
    recognizer: Any | None = None,
) -> dict[str, object]:
    normalized_target = require_supported_target(target_key)
    pair_path = Path(pair_dir)
    out_dir = pair_path / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_sample_manifest(sample_manifest_path)
    resolved_samples = resolve_and_persist_samples(pair_path, normalized_target, samples)

    catalog_entries = _catalog_entries_for_target(catalog_path, normalized_target)
    _write_json(
        out_dir / "catalog.status.json",
        {
            "target_key": normalized_target,
            "entries": [
                {
                    **entry.to_dict(),
                    "has_local_audio": bool(entry.local_path),
                    "ready_for_recognition": bool(entry.local_path and entry.text_anchor and entry.word),
                }
                for entry in catalog_entries
            ],
        },
    )

    evidence_records: list[PhoneEvidence] = []
    recognition_runs: list[dict[str, object]] = []
    for entry in catalog_entries:
        if not (entry.local_path and entry.text_anchor and entry.word):
            recognition_runs.append(
                {
                    "source_id": entry.source_id,
                    "status": "catalog_incomplete",
                    "word": entry.word,
                    "text_anchor": entry.text_anchor,
                    "audio_path": entry.local_path or "",
                }
            )
            continue

        result = run_phone_recognition(
            entry.local_path,
            target_key=normalized_target,
            source_id=entry.source_id,
            text_anchor=entry.text_anchor,
            word=entry.word,
            include_timestamps=include_timestamps,
            recognizer=recognizer,
        )
        recognition_runs.append(_recognition_result_to_dict(result))
        if result.evidence is not None:
            evidence_records.append(result.evidence)

    _write_json(
        out_dir / "phone_evidence.json",
        {
            "target_key": normalized_target,
            "runs": recognition_runs,
            "evidence": [item.to_dict() for item in evidence_records],
        },
    )

    pronunciation = build_pronunciation_candidates(resolved_samples, evidence_records)
    alerts = build_orthography_alerts(pronunciation)
    triangulation = build_triangulation_reports(resolved_samples, evidence_records)
    _write_json(
        out_dir / "reports.json",
        {
            "target_key": normalized_target,
            "pronunciation_candidates": [asdict(item) for item in pronunciation],
            "orthography_alerts": [asdict(item) for item in alerts],
            "triangulation": [asdict(item) for item in triangulation],
        },
    )

    return {
        "target_key": normalized_target,
        "sample_count": len(resolved_samples),
        "catalog_entry_count": len(catalog_entries),
        "evidence_count": len(evidence_records),
    }


def _catalog_entries_for_target(catalog_path: str | Path | None, target_key: str) -> list[AudioCatalogEntry]:
    if catalog_path is None:
        return []
    return load_audio_catalog(catalog_path).get(target_key, [])


def _recognition_result_to_dict(result: RecognitionResult) -> dict[str, object]:
    payload = {
        "status": result.status,
        "target_key": result.target_key,
        "source_id": result.source_id,
        "text_anchor": result.text_anchor,
        "word": result.word,
        "audio_path": result.audio_path,
        "reason": result.reason,
    }
    if result.evidence is not None:
        payload["evidence"] = result.evidence.to_dict()
    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair-dir", required=True, help="pair output directory containing parallel.jsonl")
    ap.add_argument("--target", required=True, choices=["tur", "hun"], help="target key")
    ap.add_argument("--samples", required=True, help="path to the opt-in sample-word manifest JSON")
    ap.add_argument("--catalog", help="optional audio catalog JSON path")
    ap.add_argument("--timestamps", action="store_true", help="request timestamp output when recognition runs")
    args = ap.parse_args(argv)

    summary = run_enrichment(
        args.pair_dir,
        target_key=args.target,
        sample_manifest_path=args.samples,
        catalog_path=args.catalog,
        include_timestamps=args.timestamps,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())