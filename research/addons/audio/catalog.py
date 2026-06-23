"""Load explicit audio source metadata for the optional add-on."""

from __future__ import annotations

import json
from pathlib import Path

from .contract import AudioCatalogEntry, require_supported_target


def load_audio_catalog(path: str | Path) -> dict[str, list[AudioCatalogEntry]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("catalog 'entries' must be a list")

    catalog: dict[str, list[AudioCatalogEntry]] = {}
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("catalog entry must be an object")
        target_key = require_supported_target(str(raw.get("target_key", "")))
        source_id = str(raw.get("source_id", "")).strip()
        if not source_id:
            raise ValueError("catalog entry missing source_id")
        entry = AudioCatalogEntry(
            target_key=target_key,
            source_id=source_id,
            local_path=_optional_text(raw.get("local_path")),
            text_anchor=_optional_text(raw.get("text_anchor")),
            word=_optional_text(raw.get("word")),
            segmentation=str(raw.get("segmentation", "unknown") or "unknown"),
            license_note=str(raw.get("license_note", "") or ""),
            note=str(raw.get("note", "") or ""),
        )
        catalog.setdefault(target_key, []).append(entry)
    return catalog


def _optional_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)