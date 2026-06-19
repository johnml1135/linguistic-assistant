"""Offline smoke tests for the audio evidence add-on.

Run: `python research/audio/tests_smoke.py` (also pytest-discoverable).
No network, no Allosaurus runtime, no local audio assets required.

Targets are the four audio-backed languages (swh/ind/tgl/spa). Fixtures use Swahili words
("mungu" = god) and Spanish where convenient; the feature-confirmation tests use Swahili
verb-extension HEIGHT harmony (the conditioning feature is `high`).
"""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio.allosaurus import run_phone_recognition  # noqa: E402
from audio.catalog import load_audio_catalog  # noqa: E402
from audio.candidates import run_candidate_localization  # noqa: E402
from audio.contract import PhoneEvidence, ResolvedSampleWord  # noqa: E402
from audio.sources import audit_audio_sources, load_alternatives, load_audio_sources  # noqa: E402
from audio.features import (  # noqa: E402
    confirm_conditioning,
    map_phones_to_features,
    triangulate_family,
)
from audio.promotion import (  # noqa: E402
    PronunciationConfirmation,
    check_recorded_consistency,
    compare_generated_to_phones,
    feature_mismatch_count,
    promote_pronunciations,
)
from audio.reports import (  # noqa: E402
    build_orthography_alerts,
    build_pronunciation_candidates,
    build_triangulation_reports,
)
from audio.playback import play_candidate_occurrence  # noqa: E402
from audio.run import main, run_enrichment  # noqa: E402
from audio.samples import load_sample_manifest, resolve_and_persist_samples  # noqa: E402


def test_load_audio_catalog_preserves_metadata_for_supported_targets():
    with TemporaryDirectory() as td:
        path = Path(td) / "catalog.json"
        path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "swh",
                            "source_id": "fcbh-local",
                            "local_path": "C:/audio/swh/mat1.wav",
                            "segmentation": "chapter",
                            "license_note": "operator supplied",
                        },
                        {
                            "target_key": "ind",
                            "source_id": "fcbh-local",
                            "segmentation": "book",
                            "license_note": "review before reuse",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        catalog = load_audio_catalog(path)
        assert [entry.source_id for entry in catalog["swh"]] == ["fcbh-local"]
        assert catalog["swh"][0].local_path == "C:/audio/swh/mat1.wav"
        assert catalog["ind"][0].segmentation == "book"


def test_load_sample_manifest_rejects_unsupported_targets():
    with TemporaryDirectory() as td:
        path = Path(td) / "samples.json"
        path.write_text(
            json.dumps(
                {
                    "samples": [
                        {"target_key": "swh", "word": "mungu"},
                        {"target_key": "zzz", "word": "foo"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        try:
            load_sample_manifest(path)
        except ValueError as exc:
            assert "unsupported target_key" in str(exc)
        else:
            raise AssertionError("expected ValueError for unsupported target")


def test_resolve_and_persist_samples_keeps_matched_and_unresolved_entries():
    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            "".join(
                [
                    json.dumps({"ref": "MAT 1:1", "src": ["god", "love"], "tgt": ["mungu", "upendo"]}) + "\n",
                    json.dumps({"ref": "MAT 1:2", "src": ["good", "shepherd"], "tgt": ["njema", "mchungaji"]}) + "\n",
                ]
            ),
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps(
                {
                    "samples": [
                        {"target_key": "swh", "word": "mungu", "gloss": "god"},
                        {"target_key": "swh", "word": "haipo", "note": "keep even if unresolved"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        samples = load_sample_manifest(samples_path)
        resolved = resolve_and_persist_samples(pair_dir, "swh", samples)

        assert [(item.word, item.status) for item in resolved] == [("mungu", "matched"), ("haipo", "unresolved")]
        assert resolved[0].refs == ["MAT 1:1"]
        out_path = pair_dir / "audio" / "samples.resolved.json"
        assert out_path.exists()
        persisted = json.loads(out_path.read_text(encoding="utf-8"))
        assert persisted["target_key"] == "swh"
        assert [item["status"] for item in persisted["samples"]] == ["matched", "unresolved"]


def test_run_phone_recognition_reports_missing_audio_without_runtime_failure():
    result = run_phone_recognition(
        Path("missing.wav"),
        target_key="swh",
        source_id="fcbh-local",
        text_anchor="MAT 1:1",
        word="mungu",
    )
    assert result.status == "audio_unavailable"
    assert result.evidence is None


def test_run_phone_recognition_records_raw_evidence_with_injected_recognizer():
    class FakeRecognizer:
        def recognize(self, audio_file: str, lang_id: str | None = None, timestamp: bool = False):
            assert lang_id == "swh"
            assert timestamp is True
            return [(0.0, 0.1, "m"), (0.1, 0.1, "u"), (0.2, 0.1, "n")]

    with TemporaryDirectory() as td:
        wav_path = Path(td) / "sample.wav"
        wav_path.write_bytes(b"RIFF")
        result = run_phone_recognition(
            wav_path,
            target_key="swh",
            source_id="fcbh-local",
            text_anchor="MAT 1:1",
            word="mungu",
            include_timestamps=True,
            recognizer=FakeRecognizer(),
        )

    assert result.status == "ok"
    assert result.evidence is not None
    assert result.evidence.phones == ("m", "u", "n")
    assert result.evidence.word == "mungu"
    assert result.evidence.provenance["backend"] == "allosaurus"
    assert result.evidence.provenance["lang_id"] == "swh"
    assert result.evidence.timestamps[0]["phone"] == "m"


def test_reports_build_candidates_alerts_and_triangulation_conservatively():
    samples = [
        ResolvedSampleWord(target_key="swh", word="mngu", status="matched", refs=["MAT 1:1"], gloss="god"),
        ResolvedSampleWord(target_key="swh", word="mungu", status="matched", refs=["MAT 1:1"], gloss="god"),
        ResolvedSampleWord(target_key="swh", word="haipo", status="unresolved", refs=[]),
    ]
    evidence = [
        PhoneEvidence(
            target_key="swh",
            source_id="fcbh-local",
            text_anchor="MAT 1:1",
            word="mngu",
            audio_path="C:/audio/swh/mat1.wav",
            phones=("m", "u", "n", "g", "u"),
            provenance={"backend": "fake"},
        ),
        PhoneEvidence(
            target_key="swh",
            source_id="fcbh-local",
            text_anchor="MAT 1:1",
            word="mungu",
            audio_path="C:/audio/swh/mat1.wav",
            phones=("m", "u", "n", "g", "u"),
            provenance={"backend": "fake"},
        ),
    ]

    candidates = build_pronunciation_candidates(samples, evidence)
    assert [item.word for item in candidates] == ["mngu", "mungu"]
    alerts = build_orthography_alerts(candidates)
    assert len(alerts) == 1
    assert alerts[0].kind == "possible_misspelling"
    assert sorted(alerts[0].words) == ["mngu", "mungu"]
    reports = build_triangulation_reports(samples, evidence)
    by_word = {item.word: item for item in reports}
    assert by_word["mungu"].has_audio is True
    assert by_word["mngu"].phone_count == 5
    assert by_word["haipo"].status == "unresolved"


def test_run_enrichment_persists_status_artifacts_without_audio():
    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["mungu"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "swh", "word": "mungu", "gloss": "god"}]}),
            encoding="utf-8",
        )
        catalog_path = Path(td) / "catalog.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "swh",
                            "source_id": "fcbh-local",
                            "segmentation": "chapter",
                            "license_note": "operator supplied",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        summary = run_enrichment(pair_dir, target_key="swh", sample_manifest_path=samples_path, catalog_path=catalog_path)

        assert summary["target_key"] == "swh"
        assert summary["sample_count"] == 1
        assert summary["evidence_count"] == 0
        assert (pair_dir / "audio" / "catalog.status.json").exists()
        assert (pair_dir / "audio" / "phone_evidence.json").exists()
        reports = json.loads((pair_dir / "audio" / "reports.json").read_text(encoding="utf-8"))
        assert reports["triangulation"][0]["word"] == "mungu"
        assert reports["triangulation"][0]["has_audio"] is False


def test_map_phones_to_features_is_review_only_and_skips_unknown():
    feats = map_phones_to_features(["a", "e", "r", "ɔœ"])
    by_phone = {f["phone"]: f for f in feats}
    assert by_phone["a"]["back"] == "+" and by_phone["a"]["round"] == "-"
    assert by_phone["e"]["back"] == "-"
    assert "r" not in by_phone  # consonants carry no harmony vowel features here


# The feature-confirmation tests use Swahili verb-extension HEIGHT harmony (front pair {i,e});
# the alternating vowel is last here so it sets the expected feature value. Conditioning is `high`.
def test_confirm_conditioning_confirms_height_for_ki_ke():
    report = confirm_conditioning(
        members=["ki", "ke"],
        phones_by_member={"ki": ["k", "i"], "ke": ["k", "e"]},
        feature="high",
    )
    assert report.status == "confirmed"
    assert report.supporting_phones


def test_confirm_conditioning_flags_conflict():
    report = confirm_conditioning(
        members=["ki", "ke"],
        phones_by_member={"ki": ["k", "e"]},  # high-spelled form sounds mid
        feature="high",
    )
    assert report.status == "conflict"


def test_confirm_conditioning_reports_insufficient_without_audio():
    report = confirm_conditioning(members=["ki", "ke"], phones_by_member={}, feature="high")
    assert report.status == "insufficient"


def test_triangulate_family_degrades_gracefully_without_audio():
    summary = triangulate_family(
        members=["ki", "ke"],
        conditioning_class="E",
        distribution_collapsible=True,
        confirmation=None,
    )
    assert summary.audio_status == "absent"
    assert summary.agreement == "distribution_only"


def test_triangulate_family_reports_agreement_with_all_witnesses():
    confirmation = confirm_conditioning(
        members=["ki", "ke"],
        phones_by_member={"ki": ["k", "i"], "ke": ["k", "e"]},
        feature="high",
    )
    summary = triangulate_family(
        members=["ki", "ke"],
        conditioning_class="E",
        distribution_collapsible=True,
        confirmation=confirmation,
    )
    assert summary.audio_status == "confirmed"
    assert summary.agreement == "agree"


def test_stem_aware_resolution_matches_inflected_occurrences():
    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            "".join(
                [
                    json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["mungu"]}) + "\n",
                    json.dumps({"ref": "MAT 1:2", "src": ["in god"], "tgt": ["munguni"]}) + "\n",
                ]
            ),
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "swh", "word": "mungu"}]}),
            encoding="utf-8",
        )
        samples = load_sample_manifest(samples_path)
        resolved = resolve_and_persist_samples(pair_dir, "swh", samples, stems=["mungu"])
        assert resolved[0].status == "matched"
        assert resolved[0].refs == ["MAT 1:1", "MAT 1:2"]  # exact + inflected occurrence via stem


def test_promote_pronunciations_emits_only_confirmed_validated_ops():
    from proposal.change_set import validate_change_set
    from proposal.contract import ChangeSet

    confirmations = [
        PronunciationConfirmation(
            entry="entry:mungu", word="mungu", form="muŋɡu", writing_system="swh-fonipa",
            confirmed=True, confidence=0.7, refs=["MAT 1:1"], provenance={"source_id": "fcbh-local"},
        ),
        PronunciationConfirmation(
            entry="entry:haipo", word="haipo", form="haipo", writing_system="swh-fonipa",
            confirmed=False,
        ),
    ]
    ops = promote_pronunciations(confirmations)
    assert len(ops) == 1
    op = ops[0]
    assert op["op"] == "lexical.pronunciation.create"
    assert op["entry"] == "entry:mungu"
    assert op["form"] == {"swh-fonipa": "muŋɡu"}
    assert op["confidence"] == 0.7
    assert op["rationale"] and op["provenance"]["source_id"] == "fcbh-local"
    cs = validate_change_set(json.dumps({"ops": ops}))
    assert isinstance(cs, ChangeSet) and len(cs.ops) == 1


def test_promote_pronunciations_emits_nothing_without_confirmation():
    confirmations = [
        PronunciationConfirmation(
            entry="e", word="w", form="f", writing_system="swh-fonipa", confirmed=False,
        )
    ]
    assert promote_pronunciations(confirmations) == []


def test_check_recorded_consistency_flags_mismatch_only():
    assert check_recorded_consistency("entry:x", "mungu", "mungu") is None
    flag = check_recorded_consistency("entry:x", "mungu", "mngu")
    assert flag is not None
    assert flag.kind == "generated_vs_recorded_mismatch"
    assert flag.review_only is True


def test_feature_mismatch_count_counts_vowel_feature_disagreements():
    assert feature_mismatch_count("kula", ["k", "u", "l", "a"]) == 0
    assert feature_mismatch_count("kula", ["k", "e", "l", "a"]) >= 1


def test_compare_generated_to_phones_flags_above_threshold_only():
    assert compare_generated_to_phones("entry:x", "kula", ["k", "u", "l", "a"], threshold=0) is None
    flag = compare_generated_to_phones("entry:x", "kula", ["k", "e", "l", "a"], threshold=0)
    assert flag is not None
    assert flag.kind == "generated_vs_phones_mismatch"
    assert flag.review_only is True


def test_run_candidate_localization_persists_ranked_occurrences_with_fake_backend():
    class FakeBackend:
        backend_name = "fake-whisper"

        def transcribe_words(self, audio_path: str, *, target_key: str):
            assert target_key == "swh"
            return [
                {"word": "neno", "start": 0.00, "end": 0.20, "probability": 0.30},
                {"word": "mungu", "start": 0.35, "end": 0.64, "probability": 0.78},
                {"word": "mungu", "start": 1.10, "end": 1.38, "probability": 0.93},
            ]

    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["mungu"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "swh", "word": "mungu", "gloss": "god"}]}),
            encoding="utf-8",
        )
        audio_path = Path(td) / "mat1.wav"
        audio_path.write_bytes(b"RIFF")
        catalog_path = Path(td) / "catalog.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "swh",
                            "source_id": "fcbh-local",
                            "local_path": str(audio_path),
                            "text_anchor": "MAT 1:1",
                            "segmentation": "verse",
                            "license_note": "operator supplied",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        summary = run_candidate_localization(
            pair_dir,
            target_key="swh",
            sample_manifest_path=samples_path,
            catalog_path=catalog_path,
            backend=FakeBackend(),
        )

        assert summary["target_key"] == "swh"
        assert summary["candidate_count"] == 2
        persisted = json.loads((pair_dir / "audio" / "word_occurrences.json").read_text(encoding="utf-8"))
        assert persisted["target_key"] == "swh"
        assert persisted["backend_status"] == "ok"
        assert persisted["occurrences"][0]["word"] == "mungu"
        assert persisted["occurrences"][0]["source_id"] == "fcbh-local"
        assert persisted["occurrences"][0]["start"] == 1.1
        assert persisted["occurrences"][0]["score"] > persisted["occurrences"][1]["score"]


def test_play_candidate_occurrence_renders_preview_and_reports_player_fallback():
    with TemporaryDirectory() as td:
        audio_path = Path(td) / "source.wav"
        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 8000)

        artifact_path = Path(td) / "word_occurrences.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "target_key": "swh",
                    "backend_status": "ok",
                    "samples": [],
                    "occurrences": [
                        {
                            "id": "occ-1",
                            "target_key": "swh",
                            "sample_word": "mungu",
                            "word": "mungu",
                            "source_id": "fcbh-local",
                            "audio_path": str(audio_path),
                            "text_anchor": "MAT 1:1",
                            "start": 0.2,
                            "end": 0.4,
                            "score": 2.5,
                            "lexical_match": "exact",
                            "score_breakdown": {"lexical": 2.0, "probability": 0.5},
                            "context_before": ["neno"],
                            "context_after": ["wake"],
                            "provenance": {"backend": "fake", "review_only": "true"},
                            "phones": [],
                            "vowel_features": [],
                            "note": ""
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = play_candidate_occurrence(
            artifact_path,
            "occ-1",
            padding_ms=50,
            fade_ms=20,
            player=lambda path: False,
        )

        assert result.status == "playback_unavailable"
        assert result.occurrence_id == "occ-1"
        assert result.preview_path
        assert Path(result.preview_path).exists()
        assert result.padding_ms == 50
        assert result.fade_ms == 20


def test_run_candidate_localization_attaches_review_only_phone_cues():
    class FakeBackend:
        backend_name = "fake-whisper"

        def transcribe_words(self, audio_path: str, *, target_key: str):
            assert target_key == "swh"
            return [{"word": "mungu", "start": 0.25, "end": 0.50, "probability": 0.91}]

    class FakeRecognizer:
        def recognize(self, audio_file: str, lang_id: str | None = None, timestamp: bool = False):
            assert lang_id == "swh"
            assert timestamp is False
            return ["m", "u", "n", "g", "u"]

    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["mungu"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "swh", "word": "mungu", "gloss": "god"}]}),
            encoding="utf-8",
        )
        audio_path = Path(td) / "mat1.wav"
        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 8000)
        catalog_path = Path(td) / "catalog.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "swh",
                            "source_id": "fcbh-local",
                            "local_path": str(audio_path),
                            "text_anchor": "MAT 1:1",
                            "segmentation": "verse",
                            "license_note": "operator supplied",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        run_candidate_localization(
            pair_dir,
            target_key="swh",
            sample_manifest_path=samples_path,
            catalog_path=catalog_path,
            backend=FakeBackend(),
            recognizer=FakeRecognizer(),
        )

        persisted = json.loads((pair_dir / "audio" / "word_occurrences.json").read_text(encoding="utf-8"))
        assert persisted["occurrences"][0]["phones"] == ["m", "u", "n", "g", "u"]
        assert persisted["occurrences"][0]["vowel_features"][0]["phone"] == "u"
        assert persisted["occurrences"][0]["vowel_features"][1]["phone"] == "u"


def test_run_candidate_localization_reports_backend_unavailable():
    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["mungu"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "swh", "word": "mungu"}]}),
            encoding="utf-8",
        )
        catalog_path = Path(td) / "catalog.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "swh",
                            "source_id": "fcbh-local",
                            "local_path": str(Path(td) / "missing.wav"),
                            "text_anchor": "MAT 1:1",
                            "segmentation": "verse",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        with patch("audio.candidates._load_default_backend", return_value=None):
            summary = run_candidate_localization(
                pair_dir,
                target_key="swh",
                sample_manifest_path=samples_path,
                catalog_path=catalog_path,
            )

        assert summary["backend_status"] == "backend_unavailable"
        persisted = json.loads((pair_dir / "audio" / "word_occurrences.json").read_text(encoding="utf-8"))
        assert persisted["backend_status"] == "backend_unavailable"
        assert persisted["occurrences"] == []


def test_exact_candidate_outranks_stem_match_when_other_evidence_is_similar():
    class FakeBackend:
        backend_name = "fake-whisper"

        def transcribe_words(self, audio_path: str, *, target_key: str):
            assert target_key == "swh"
            return [
                {"word": "munguni", "start": 0.20, "end": 0.45, "probability": 0.99},
                {"word": "mungu", "start": 0.60, "end": 0.82, "probability": 0.55},
            ]

    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__swh-swhulb"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["mungu", "munguni"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "swh", "word": "mungu"}]}),
            encoding="utf-8",
        )
        audio_path = Path(td) / "mat1.wav"
        audio_path.write_bytes(b"RIFF")
        catalog_path = Path(td) / "catalog.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "swh",
                            "source_id": "fcbh-local",
                            "local_path": str(audio_path),
                            "text_anchor": "MAT 1:1",
                            "segmentation": "verse",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        run_candidate_localization(
            pair_dir,
            target_key="swh",
            sample_manifest_path=samples_path,
            catalog_path=catalog_path,
            backend=FakeBackend(),
            stems=["mungu"],
        )

        persisted = json.loads((pair_dir / "audio" / "word_occurrences.json").read_text(encoding="utf-8"))
        assert persisted["occurrences"][0]["word"] == "mungu"
        assert persisted["occurrences"][0]["lexical_match"] == "exact"
        assert persisted["occurrences"][1]["lexical_match"] == "stem"


def test_bundled_audio_sources_need_verification_and_are_not_eligible():
    sources = load_audio_sources()
    by_key = {s.target_key: s for s in sources}
    assert set(by_key) == {"swh", "ind", "tgl", "spa"}
    for s in sources:
        assert s.download_eligible is False
        assert s.status == "needs_verification"


def test_audit_reports_nothing_approved_and_empty_alternatives():
    report = audit_audio_sources()
    assert report["approved_count"] == 0
    assert report["alternatives"] == []  # the four targets ARE the verify-first set now


def test_bundled_sources_are_self_consistent():
    for s in load_audio_sources():
        assert s.music_free is True       # FCBH Non-Drama / PD narration are music-free
        assert s.download_eligible is False  # but not eligible until license + exact-match confirmed
    assert load_alternatives() == []      # fallback shortlist intentionally empty


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
