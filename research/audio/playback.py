"""Temporary preview rendering and on-demand playback for stored audio occurrences."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Callable

from .contract import PlaybackPreviewResult


def play_candidate_occurrence(
    artifact_path: str | Path,
    occurrence_id: str,
    *,
    padding_ms: int = 60,
    fade_ms: int = 25,
    player: Callable[[str], bool] | None = None,
) -> PlaybackPreviewResult:
    occurrence = _load_occurrence(artifact_path, occurrence_id)
    if occurrence is None:
        return PlaybackPreviewResult(status="occurrence_not_found", occurrence_id=occurrence_id, reason="occurrence id not found")

    preview = render_occurrence_preview(occurrence, padding_ms=padding_ms, fade_ms=fade_ms)
    if preview.status != "preview_ready":
        return preview

    runtime = player or _default_player()
    if runtime is None:
        return PlaybackPreviewResult(
            status="playback_unavailable",
            occurrence_id=occurrence_id,
            preview_path=preview.preview_path,
            source_audio_path=preview.source_audio_path,
            start=preview.start,
            end=preview.end,
            padding_ms=preview.padding_ms,
            fade_ms=preview.fade_ms,
            reason="no supported local player available",
        )

    try:
        played = bool(runtime(preview.preview_path))
    except Exception as exc:
        return PlaybackPreviewResult(
            status="playback_unavailable",
            occurrence_id=occurrence_id,
            preview_path=preview.preview_path,
            source_audio_path=preview.source_audio_path,
            start=preview.start,
            end=preview.end,
            padding_ms=preview.padding_ms,
            fade_ms=preview.fade_ms,
            reason=str(exc),
        )

    if not played:
        return PlaybackPreviewResult(
            status="playback_unavailable",
            occurrence_id=occurrence_id,
            preview_path=preview.preview_path,
            source_audio_path=preview.source_audio_path,
            start=preview.start,
            end=preview.end,
            padding_ms=preview.padding_ms,
            fade_ms=preview.fade_ms,
            reason="player reported unavailable playback",
        )

    return PlaybackPreviewResult(
        status="played",
        occurrence_id=occurrence_id,
        preview_path=preview.preview_path,
        source_audio_path=preview.source_audio_path,
        start=preview.start,
        end=preview.end,
        padding_ms=preview.padding_ms,
        fade_ms=preview.fade_ms,
    )


def render_occurrence_preview(
    occurrence: dict[str, object],
    *,
    padding_ms: int = 60,
    fade_ms: int = 25,
) -> PlaybackPreviewResult:
    occurrence_id = str(occurrence.get("id", ""))
    audio_path = Path(str(occurrence.get("audio_path", "")))
    if not audio_path.exists():
        return PlaybackPreviewResult(
            status="source_unavailable",
            occurrence_id=occurrence_id,
            source_audio_path=str(audio_path),
            reason="source audio asset not found",
        )

    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            params = wav_file.getparams()
            if params.sampwidth != 2:
                return PlaybackPreviewResult(
                    status="unsupported_format",
                    occurrence_id=occurrence_id,
                    source_audio_path=str(audio_path),
                    reason="preview rendering currently supports 16-bit PCM WAV only",
                )

            frame_rate = params.framerate
            start = max(float(occurrence.get("start", 0.0)) - (padding_ms / 1000.0), 0.0)
            end = float(occurrence.get("end", 0.0)) + (padding_ms / 1000.0)
            start_frame = int(start * frame_rate)
            end_frame = min(int(end * frame_rate), params.nframes)

            wav_file.setpos(start_frame)
            frames = wav_file.readframes(max(end_frame - start_frame, 0))
    except wave.Error as exc:
        return PlaybackPreviewResult(
            status="unsupported_format",
            occurrence_id=occurrence_id,
            source_audio_path=str(audio_path),
            reason=str(exc),
        )

    faded = _apply_fades(frames, channels=params.nchannels, fade_ms=fade_ms, frame_rate=frame_rate)
    preview_path = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name)
    with wave.open(str(preview_path), "wb") as out_file:
        out_file.setnchannels(params.nchannels)
        out_file.setsampwidth(params.sampwidth)
        out_file.setframerate(frame_rate)
        out_file.writeframes(faded)

    return PlaybackPreviewResult(
        status="preview_ready",
        occurrence_id=occurrence_id,
        preview_path=str(preview_path),
        source_audio_path=str(audio_path),
        start=round(start, 4),
        end=round(min(end, params.nframes / frame_rate), 4),
        padding_ms=padding_ms,
        fade_ms=fade_ms,
    )


def _load_occurrence(artifact_path: str | Path, occurrence_id: str) -> dict[str, object] | None:
    data = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    for occurrence in data.get("occurrences", []):
        if isinstance(occurrence, dict) and str(occurrence.get("id", "")) == occurrence_id:
            return occurrence
    return None


def _apply_fades(frames: bytes, *, channels: int, fade_ms: int, frame_rate: int) -> bytes:
    if not frames or fade_ms <= 0:
        return frames
    samples = array("h")
    samples.frombytes(frames)
    fade_frames = min(int(frame_rate * (fade_ms / 1000.0)), len(samples) // max(channels, 1) // 2 or len(samples))
    if fade_frames <= 0:
        return frames

    total_samples = len(samples)
    fade_samples = fade_frames * max(channels, 1)
    for index in range(fade_samples):
        samples[index] = int(samples[index] * (index / fade_samples))

    for offset in range(fade_samples):
        idx = total_samples - fade_samples + offset
        if idx < 0 or idx >= total_samples:
            continue
        samples[idx] = int(samples[idx] * ((fade_samples - offset) / fade_samples))
    return samples.tobytes()


def _default_player() -> Callable[[str], bool] | None:
    try:
        import winsound  # type: ignore
    except Exception:
        winsound = None  # type: ignore[assignment]

    if winsound is not None:
        def _play_windows(path: str) -> bool:
            winsound.PlaySound(path, winsound.SND_FILENAME)
            return True

        return _play_windows

    for command in ("afplay", "aplay"):
        binary = shutil.which(command)
        if binary is None:
            continue

        def _play_subprocess(path: str, exe: str = binary) -> bool:
            completed = subprocess.run([exe, path], check=False, capture_output=True)
            return completed.returncode == 0

        return _play_subprocess

    return None