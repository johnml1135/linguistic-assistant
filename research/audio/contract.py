"""Data contracts for the optional audio evidence add-on.

These structures are intentionally conservative: they record analyst intent and derived evidence
without implying that audio is always available or that phone strings are parser-authoritative.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

SUPPORTED_TARGET_KEYS = frozenset({"tur", "hun"})


def require_supported_target(target_key: str) -> str:
    target = str(target_key).strip().lower()
    if target not in SUPPORTED_TARGET_KEYS:
        raise ValueError(f"unsupported target_key {target_key!r}; supported: {sorted(SUPPORTED_TARGET_KEYS)}")
    return target


@dataclass(frozen=True)
class AudioCatalogEntry:
    target_key: str
    source_id: str
    local_path: str | None = None
    text_anchor: str | None = None
    word: str | None = None
    segmentation: str = "unknown"
    license_note: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class SampleWord:
    target_key: str
    word: str
    lemma: str | None = None
    gloss: str | None = None
    ref: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ResolvedSampleWord:
    target_key: str
    word: str
    status: str
    refs: list[str] = field(default_factory=list)
    lemma: str | None = None
    gloss: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PhoneEvidence:
    target_key: str
    source_id: str
    text_anchor: str
    word: str | None = None
    audio_path: str = ""
    phones: tuple[str, ...] = ()
    timestamps: tuple[dict[str, float | str], ...] = ()
    provenance: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["phones"] = list(self.phones)
        data["timestamps"] = [dict(item) for item in self.timestamps]
        return data


@dataclass(frozen=True)
class RecognitionResult:
    status: str
    target_key: str
    source_id: str
    text_anchor: str
    word: str | None = None
    audio_path: str = ""
    evidence: PhoneEvidence | None = None
    reason: str = ""


@dataclass(frozen=True)
class PronunciationCandidate:
    word: str
    refs: list[str] = field(default_factory=list)
    phones: tuple[str, ...] = ()
    source_id: str = ""
    audio_path: str = ""
    gloss: str | None = None


@dataclass(frozen=True)
class OrthographyAlert:
    kind: str
    words: list[str] = field(default_factory=list)
    phones: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class TriangulationReport:
    word: str
    status: str
    refs: list[str] = field(default_factory=list)
    has_audio: bool = False
    phone_count: int = 0
    gloss: str | None = None
    note: str = ""