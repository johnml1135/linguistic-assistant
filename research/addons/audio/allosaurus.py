"""Optional Allosaurus wrapper for generating review-only phone evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import PhoneEvidence, RecognitionResult, require_supported_target


def run_phone_recognition(
    audio_path: str | Path,
    *,
    target_key: str,
    source_id: str,
    text_anchor: str,
    word: str | None = None,
    include_timestamps: bool = False,
    recognizer: Any | None = None,
) -> RecognitionResult:
    normalized_target = require_supported_target(target_key)
    path = Path(audio_path)
    if not path.exists():
        return RecognitionResult(
            status="audio_unavailable",
            target_key=normalized_target,
            source_id=source_id,
            text_anchor=text_anchor,
            word=word,
            audio_path=str(path),
            reason="local audio asset not found",
        )

    runtime = recognizer or _load_recognizer()
    if runtime is None:
        return RecognitionResult(
            status="recognizer_unavailable",
            target_key=normalized_target,
            source_id=source_id,
            text_anchor=text_anchor,
            word=word,
            audio_path=str(path),
            reason="Allosaurus runtime unavailable",
        )

    output = runtime.recognize(str(path), lang_id=normalized_target, timestamp=include_timestamps)
    phones, timestamps = _normalize_output(output, include_timestamps=include_timestamps)
    evidence = PhoneEvidence(
        target_key=normalized_target,
        source_id=source_id,
        text_anchor=text_anchor,
        word=word,
        audio_path=str(path),
        phones=phones,
        timestamps=timestamps,
        provenance={
            "backend": "allosaurus",
            "lang_id": normalized_target,
            "timestamps": str(bool(include_timestamps)).lower(),
            "recognizer": type(runtime).__name__,
        },
    )
    return RecognitionResult(
        status="ok",
        target_key=normalized_target,
        source_id=source_id,
        text_anchor=text_anchor,
        word=word,
        audio_path=str(path),
        evidence=evidence,
    )


def _load_recognizer() -> Any | None:
    try:
        from allosaurus.app import read_recognizer  # type: ignore
    except Exception:
        return None
    return read_recognizer()


def _normalize_output(output: Any, *, include_timestamps: bool) -> tuple[tuple[str, ...], tuple[dict[str, float | str], ...]]:
    if include_timestamps:
        items: list[dict[str, float | str]] = []
        phones: list[str] = []
        for raw in output:
            start, duration, phone = raw
            phone_text = str(phone)
            phones.append(phone_text)
            items.append({"start": float(start), "duration": float(duration), "phone": phone_text})
        return tuple(phones), tuple(items)

    if isinstance(output, str):
        return tuple(token for token in output.split() if token.strip()), ()

    phones = [str(token) for token in output]
    return tuple(phones), ()