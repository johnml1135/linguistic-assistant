"""Derived, review-only reports built from optional phone evidence."""

from __future__ import annotations

from collections import defaultdict

from .contract import (
    OrthographyAlert,
    PhoneEvidence,
    PronunciationCandidate,
    ResolvedSampleWord,
    TriangulationReport,
)


def build_pronunciation_candidates(
    samples: list[ResolvedSampleWord],
    evidence_records: list[PhoneEvidence],
) -> list[PronunciationCandidate]:
    evidence_by_word: dict[str, list[PhoneEvidence]] = defaultdict(list)
    for evidence in evidence_records:
        if evidence.word:
            evidence_by_word[evidence.word].append(evidence)

    candidates: list[PronunciationCandidate] = []
    for sample in samples:
        if sample.status != "matched":
            continue
        for evidence in evidence_by_word.get(sample.word, []):
            candidates.append(
                PronunciationCandidate(
                    word=sample.word,
                    refs=list(sample.refs),
                    phones=evidence.phones,
                    source_id=evidence.source_id,
                    audio_path=evidence.audio_path,
                    gloss=sample.gloss,
                )
            )
    return candidates


def build_orthography_alerts(candidates: list[PronunciationCandidate]) -> list[OrthographyAlert]:
    words_by_phone: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for candidate in candidates:
        words_by_phone[candidate.phones].append(candidate.word)

    alerts: list[OrthographyAlert] = []
    for phones, words in words_by_phone.items():
        unique_words = sorted(set(words))
        if len(unique_words) < 2:
            continue
        alerts.append(
            OrthographyAlert(
                kind="possible_misspelling",
                words=unique_words,
                phones=phones,
                note="multiple spellings share the same observed phone evidence",
            )
        )
    return alerts


def build_triangulation_reports(
    samples: list[ResolvedSampleWord],
    evidence_records: list[PhoneEvidence],
) -> list[TriangulationReport]:
    evidence_by_word: dict[str, list[PhoneEvidence]] = defaultdict(list)
    for evidence in evidence_records:
        if evidence.word:
            evidence_by_word[evidence.word].append(evidence)

    reports: list[TriangulationReport] = []
    for sample in samples:
        sample_evidence = evidence_by_word.get(sample.word, [])
        phone_count = len(sample_evidence[0].phones) if sample_evidence else 0
        reports.append(
            TriangulationReport(
                word=sample.word,
                status=sample.status,
                refs=list(sample.refs),
                has_audio=bool(sample_evidence),
                phone_count=phone_count,
                gloss=sample.gloss,
                note="audio evidence available" if sample_evidence else "no audio evidence",
            )
        )
    return reports