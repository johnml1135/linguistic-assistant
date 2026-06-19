"""Sample-driven candidate localization over longer local audio assets."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

from .allosaurus import run_phone_recognition
from .catalog import load_audio_catalog
from .contract import AudioCatalogEntry, CandidateOccurrence, ResolvedSampleWord, TimestampedWord, require_supported_target
from .features import map_phones_to_features
from .playback import play_candidate_occurrence, render_occurrence_preview
from .samples import load_sample_manifest, resolve_and_persist_samples

_LANGUAGE_CODES = {"swh": "sw", "ind": "id", "tgl": "tl", "spa": "es"}


class WordTimestampBackend(Protocol):
    backend_name: str

    def transcribe_words(self, audio_path: str, *, target_key: str) -> list[TimestampedWord | dict[str, object]]:
        """Return recognized words with start/end offsets and probability."""


class FasterWhisperBackend:
    """Optional word-timestamp backend powered by faster-whisper."""

    backend_name = "faster-whisper"

    def __init__(
        self,
        *,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 5,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._beam_size = beam_size
        self._model: Any | None = None

    def transcribe_words(self, audio_path: str, *, target_key: str) -> list[TimestampedWord]:
        model = self._get_model()
        language = _LANGUAGE_CODES[require_supported_target(target_key)]
        segments, _info = model.transcribe(
            audio_path,
            language=language,
            beam_size=self._beam_size,
            word_timestamps=True,
            condition_on_previous_text=False,
            vad_filter=True,
        )
        out: list[TimestampedWord] = []
        for segment in list(segments):
            for word in getattr(segment, "words", []) or []:
                out.append(
                    TimestampedWord(
                        word=str(getattr(word, "word", "")),
                        start=float(getattr(word, "start", 0.0) or 0.0),
                        end=float(getattr(word, "end", 0.0) or 0.0),
                        probability=float(getattr(word, "probability", 0.0) or 0.0),
                    )
                )
        return out

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel  # type: ignore

        self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)
        return self._model


def run_candidate_localization(
    pair_dir: str | Path,
    *,
    target_key: str,
    sample_manifest_path: str | Path,
    catalog_path: str | Path | None = None,
    backend: WordTimestampBackend | None = None,
    stems: list[str] | None = None,
    recognizer: Any | None = None,
) -> dict[str, object]:
    normalized_target = require_supported_target(target_key)
    pair_path = Path(pair_dir)
    out_dir = pair_path / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_sample_manifest(sample_manifest_path)
    resolved_samples = resolve_and_persist_samples(pair_path, normalized_target, samples, stems=stems)
    matched_samples = [sample for sample in resolved_samples if sample.status == "matched"]
    catalog_entries = _catalog_entries_for_target(catalog_path, normalized_target)

    runtime = backend or _load_default_backend()
    if runtime is None:
        _write_occurrence_artifact(out_dir / "word_occurrences.json", normalized_target, "backend_unavailable", resolved_samples, [])
        return {
            "target_key": normalized_target,
            "candidate_count": 0,
            "backend_status": "backend_unavailable",
        }

    occurrences: list[CandidateOccurrence] = []
    stems_set = {_normalize_word(item) for item in (stems or [])}
    for sample in matched_samples:
        for entry in _eligible_catalog_entries(sample, catalog_entries):
            if not entry.local_path:
                continue
            words = [_coerce_timestamped_word(item) for item in runtime.transcribe_words(entry.local_path, target_key=normalized_target)]
            occurrences.extend(_occurrences_for_sample(sample, entry, words, runtime, stems_set))

    ranked = sorted(occurrences, key=lambda item: (-item.score, item.start, item.id))
    if recognizer is not None:
        ranked = [_attach_phone_cues(item, recognizer=recognizer) for item in ranked]
    _write_occurrence_artifact(out_dir / "word_occurrences.json", normalized_target, "ok", resolved_samples, ranked)
    return {
        "target_key": normalized_target,
        "candidate_count": len(ranked),
        "backend_status": "ok",
    }


def _load_default_backend() -> WordTimestampBackend | None:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return None
    return FasterWhisperBackend()


def _load_default_phone_recognizer() -> Any | None:
    try:
        from allosaurus.app import read_recognizer  # type: ignore
    except Exception:
        return None
    return read_recognizer()


def _catalog_entries_for_target(catalog_path: str | Path | None, target_key: str) -> list[AudioCatalogEntry]:
    if catalog_path is None:
        return []
    return load_audio_catalog(catalog_path).get(target_key, [])


def _eligible_catalog_entries(sample: ResolvedSampleWord, entries: list[AudioCatalogEntry]) -> list[AudioCatalogEntry]:
    refs = sample.refs or ([] if sample.note is None else [])
    eligible: list[AudioCatalogEntry] = []
    for entry in entries:
        if not (entry.local_path and entry.text_anchor):
            continue
        if any(_anchor_covers_ref(entry.text_anchor, ref) for ref in refs):
            eligible.append(entry)
    return eligible


def _anchor_covers_ref(anchor: str, ref: str) -> bool:
    normalized_anchor = anchor.strip().upper()
    normalized_ref = ref.strip().upper()
    if normalized_anchor == normalized_ref:
        return True
    return normalized_ref.startswith(normalized_anchor + ":") or normalized_ref.startswith(normalized_anchor + " ")


def _coerce_timestamped_word(item: TimestampedWord | dict[str, object]) -> TimestampedWord:
    if isinstance(item, TimestampedWord):
        return item
    return TimestampedWord(
        word=str(item.get("word", "")),
        start=float(item.get("start", 0.0) or 0.0),
        end=float(item.get("end", 0.0) or 0.0),
        probability=float(item.get("probability", 0.0) or 0.0),
    )


def _occurrences_for_sample(
    sample: ResolvedSampleWord,
    entry: AudioCatalogEntry,
    words: list[TimestampedWord],
    runtime: WordTimestampBackend,
    stems: set[str],
) -> list[CandidateOccurrence]:
    normalized_sample = _normalize_word(sample.word)
    occurrences: list[CandidateOccurrence] = []
    for index, recognized in enumerate(words):
        normalized_word = _normalize_word(recognized.word)
        lexical_match = _classify_match(normalized_sample, normalized_word, stems)
        if lexical_match is None:
            continue
        boundary_score = _boundary_score(words, index)
        score_breakdown = {
            "lexical": 2.0 if lexical_match == "exact" else 1.0,
            "probability": round(recognized.probability, 4),
            "boundary": round(boundary_score, 4),
        }
        total_score = float(score_breakdown["lexical"]) + float(score_breakdown["probability"]) + float(score_breakdown["boundary"])
        context_before = tuple(word.word for word in words[max(0, index - 2):index])
        context_after = tuple(word.word for word in words[index + 1:index + 3])
        occurrence_id = f"{sample.word}:{entry.source_id}:{index}:{int(recognized.start * 1000)}"
        occurrences.append(
            CandidateOccurrence(
                id=occurrence_id,
                target_key=sample.target_key,
                sample_word=sample.word,
                word=recognized.word,
                source_id=entry.source_id,
                audio_path=entry.local_path or "",
                text_anchor=entry.text_anchor or "",
                start=round(recognized.start, 4),
                end=round(recognized.end, 4),
                score=round(total_score, 4),
                lexical_match=lexical_match,
                score_breakdown=score_breakdown,
                context_before=context_before,
                context_after=context_after,
                provenance={
                    "backend": getattr(runtime, "backend_name", type(runtime).__name__),
                    "review_only": "true",
                },
            )
        )
    return occurrences


def _classify_match(normalized_sample: str, normalized_word: str, stems: set[str]) -> str | None:
    if normalized_word == normalized_sample:
        return "exact"
    if normalized_sample in stems and normalized_word.startswith(normalized_sample) and len(normalized_word) > len(normalized_sample):
        return "stem"
    return None


def _boundary_score(words: list[TimestampedWord], index: int) -> float:
    before_gap = 0.0 if index == 0 else max(words[index].start - words[index - 1].end, 0.0)
    after_gap = 0.0 if index == len(words) - 1 else max(words[index + 1].start - words[index].end, 0.0)
    return min(before_gap + after_gap, 0.5)


def _normalize_word(text: str) -> str:
    return "".join(ch for ch in text.casefold().strip() if ch.isalnum())


def _write_occurrence_artifact(
    path: Path,
    target_key: str,
    backend_status: str,
    samples: list[ResolvedSampleWord],
    occurrences: list[CandidateOccurrence],
) -> None:
    payload = {
        "target_key": target_key,
        "backend_status": backend_status,
        "samples": [sample.to_dict() for sample in samples],
        "occurrences": [item.to_dict() for item in occurrences],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _attach_phone_cues(occurrence: CandidateOccurrence, *, recognizer: Any) -> CandidateOccurrence:
    preview = render_occurrence_preview(
        occurrence.to_dict(),
        padding_ms=20,
        fade_ms=0,
    )
    if preview.status != "preview_ready" or not preview.preview_path:
        return occurrence

    try:
        result = run_phone_recognition(
            preview.preview_path,
            target_key=occurrence.target_key,
            source_id=occurrence.source_id,
            text_anchor=occurrence.text_anchor,
            word=occurrence.word,
            recognizer=recognizer,
        )
        if result.evidence is None:
            return occurrence
        return replace(
            occurrence,
            phones=result.evidence.phones,
            vowel_features=tuple(map_phones_to_features(list(result.evidence.phones))),
        )
    finally:
        try:
            Path(preview.preview_path).unlink(missing_ok=True)
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    locate = sub.add_parser("locate", help="find and persist ranked word candidates from local audio")
    locate.add_argument("--pair-dir", required=True, help="pair output directory containing parallel.jsonl")
    locate.add_argument("--target", required=True, choices=["swh", "ind", "tgl", "spa"], help="target key")
    locate.add_argument("--samples", required=True, help="path to the sample-word manifest JSON")
    locate.add_argument("--catalog", required=True, help="path to the audio catalog JSON")
    locate.add_argument("--stem", action="append", default=[], help="sample word to treat as stem-aware")
    locate.add_argument("--phone-cues", action="store_true", help="attach review-only phone cues when Allosaurus is available")

    play = sub.add_parser("play", help="render and play a stored occurrence preview")
    play.add_argument("--artifact", required=True, help="path to word_occurrences.json")
    play.add_argument("--occurrence", required=True, help="stored occurrence identifier")
    play.add_argument("--padding-ms", type=int, default=60, help="preview padding in milliseconds")
    play.add_argument("--fade-ms", type=int, default=25, help="fade in/out duration in milliseconds")

    args = ap.parse_args(argv)

    if args.command == "locate":
        summary = run_candidate_localization(
            args.pair_dir,
            target_key=args.target,
            sample_manifest_path=args.samples,
            catalog_path=args.catalog,
            stems=list(args.stem or []),
            recognizer=_load_default_phone_recognizer() if args.phone_cues else None,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    result = play_candidate_occurrence(
        args.artifact,
        args.occurrence,
        padding_ms=args.padding_ms,
        fade_ms=args.fade_ms,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())