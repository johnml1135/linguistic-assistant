"""Offline smoke tests for the audio evidence add-on.

Run: `python research/audio/tests_smoke.py` (also pytest-discoverable).
No network, no Allosaurus runtime, no local audio assets required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio.allosaurus import run_phone_recognition  # noqa: E402
from audio.catalog import load_audio_catalog  # noqa: E402
from audio.contract import PhoneEvidence, ResolvedSampleWord  # noqa: E402
from audio.reports import (  # noqa: E402
    build_orthography_alerts,
    build_pronunciation_candidates,
    build_triangulation_reports,
)
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
                            "target_key": "tur",
                            "source_id": "ytc-local",
                            "local_path": "C:/audio/tur/mat1.wav",
                            "segmentation": "chapter",
                            "license_note": "operator supplied",
                        },
                        {
                            "target_key": "hun",
                            "source_id": "wordproject-local",
                            "segmentation": "book",
                            "license_note": "review before reuse",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        catalog = load_audio_catalog(path)
        assert [entry.source_id for entry in catalog["tur"]] == ["ytc-local"]
        assert catalog["tur"][0].local_path == "C:/audio/tur/mat1.wav"
        assert catalog["hun"][0].segmentation == "book"


def test_load_sample_manifest_rejects_unsupported_targets():
    with TemporaryDirectory() as td:
        path = Path(td) / "samples.json"
        path.write_text(
            json.dumps(
                {
                    "samples": [
                        {"target_key": "tur", "word": "tanrı"},
                        {"target_key": "fin", "word": "jumala"},
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
        pair_dir = Path(td) / "eng-engwebp__tur-turytc"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            "".join(
                [
                    json.dumps({"ref": "MAT 1:1", "src": ["god", "love"], "tgt": ["tanrı", "sevgi"]}) + "\n",
                    json.dumps({"ref": "MAT 1:2", "src": ["good", "shepherd"], "tgt": ["iyi", "çoban"]}) + "\n",
                ]
            ),
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps(
                {
                    "samples": [
                        {"target_key": "tur", "word": "tanrı", "gloss": "god"},
                        {"target_key": "tur", "word": "yanlis", "note": "keep even if unresolved"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        samples = load_sample_manifest(samples_path)
        resolved = resolve_and_persist_samples(pair_dir, "tur", samples)

        assert [(item.word, item.status) for item in resolved] == [("tanrı", "matched"), ("yanlis", "unresolved")]
        assert resolved[0].refs == ["MAT 1:1"]
        out_path = pair_dir / "audio" / "samples.resolved.json"
        assert out_path.exists()
        persisted = json.loads(out_path.read_text(encoding="utf-8"))
        assert persisted["target_key"] == "tur"
        assert [item["status"] for item in persisted["samples"]] == ["matched", "unresolved"]


def test_run_phone_recognition_reports_missing_audio_without_runtime_failure():
    result = run_phone_recognition(
        Path("missing.wav"),
        target_key="tur",
        source_id="ytc-local",
        text_anchor="MAT 1:1",
        word="tanrı",
    )
    assert result.status == "audio_unavailable"
    assert result.evidence is None


def test_run_phone_recognition_records_raw_evidence_with_injected_recognizer():
    class FakeRecognizer:
        def recognize(self, audio_file: str, lang_id: str | None = None, timestamp: bool = False):
            assert lang_id == "tur"
            assert timestamp is True
            return [(0.0, 0.1, "t"), (0.1, 0.1, "a"), (0.2, 0.1, "n")]

    with TemporaryDirectory() as td:
        wav_path = Path(td) / "sample.wav"
        wav_path.write_bytes(b"RIFF")
        result = run_phone_recognition(
            wav_path,
            target_key="tur",
            source_id="ytc-local",
            text_anchor="MAT 1:1",
            word="tanrı",
            include_timestamps=True,
            recognizer=FakeRecognizer(),
        )

    assert result.status == "ok"
    assert result.evidence is not None
    assert result.evidence.phones == ("t", "a", "n")
    assert result.evidence.word == "tanrı"
    assert result.evidence.provenance["backend"] == "allosaurus"
    assert result.evidence.provenance["lang_id"] == "tur"
    assert result.evidence.timestamps[0]["phone"] == "t"


def test_reports_build_candidates_alerts_and_triangulation_conservatively():
    samples = [
        ResolvedSampleWord(target_key="tur", word="tanri", status="matched", refs=["MAT 1:1"], gloss="god"),
        ResolvedSampleWord(target_key="tur", word="tanrı", status="matched", refs=["MAT 1:1"], gloss="god"),
        ResolvedSampleWord(target_key="tur", word="yanlis", status="unresolved", refs=[]),
    ]
    evidence = [
        PhoneEvidence(
            target_key="tur",
            source_id="ytc-local",
            text_anchor="MAT 1:1",
            word="tanri",
            audio_path="C:/audio/tur/mat1.wav",
            phones=("t", "a", "n", "r", "ɯ"),
            provenance={"backend": "fake"},
        ),
        PhoneEvidence(
            target_key="tur",
            source_id="ytc-local",
            text_anchor="MAT 1:1",
            word="tanrı",
            audio_path="C:/audio/tur/mat1.wav",
            phones=("t", "a", "n", "r", "ɯ"),
            provenance={"backend": "fake"},
        ),
    ]

    candidates = build_pronunciation_candidates(samples, evidence)
    assert [item.word for item in candidates] == ["tanri", "tanrı"]
    alerts = build_orthography_alerts(candidates)
    assert len(alerts) == 1
    assert alerts[0].kind == "possible_misspelling"
    assert sorted(alerts[0].words) == ["tanri", "tanrı"]
    reports = build_triangulation_reports(samples, evidence)
    by_word = {item.word: item for item in reports}
    assert by_word["tanrı"].has_audio is True
    assert by_word["tanri"].phone_count == 5
    assert by_word["yanlis"].status == "unresolved"


def test_run_enrichment_persists_status_artifacts_without_audio():
    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__tur-turytc"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["tanrı"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "tur", "word": "tanrı", "gloss": "god"}]}),
            encoding="utf-8",
        )
        catalog_path = Path(td) / "catalog.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target_key": "tur",
                            "source_id": "ytc-local",
                            "segmentation": "chapter",
                            "license_note": "operator supplied",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        summary = run_enrichment(pair_dir, target_key="tur", sample_manifest_path=samples_path, catalog_path=catalog_path)

        assert summary["target_key"] == "tur"
        assert summary["sample_count"] == 1
        assert summary["evidence_count"] == 0
        assert (pair_dir / "audio" / "catalog.status.json").exists()
        assert (pair_dir / "audio" / "phone_evidence.json").exists()
        reports = json.loads((pair_dir / "audio" / "reports.json").read_text(encoding="utf-8"))
        assert reports["triangulation"][0]["word"] == "tanrı"
        assert reports["triangulation"][0]["has_audio"] is False


def test_run_main_accepts_cli_arguments():
    with TemporaryDirectory() as td:
        pair_dir = Path(td) / "eng-engwebp__hun-hun"
        pair_dir.mkdir(parents=True)
        (pair_dir / "parallel.jsonl").write_text(
            json.dumps({"ref": "MAT 1:1", "src": ["god"], "tgt": ["isten"]}) + "\n",
            encoding="utf-8",
        )
        samples_path = Path(td) / "samples.json"
        samples_path.write_text(
            json.dumps({"samples": [{"target_key": "hun", "word": "isten", "gloss": "god"}]}),
            encoding="utf-8",
        )

        code = main([
            "--pair-dir",
            str(pair_dir),
            "--target",
            "hun",
            "--samples",
            str(samples_path),
        ])

        assert code == 0
        assert (pair_dir / "audio" / "reports.json").exists()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")