"""The PolyGloss corpus row schema (`lecslab/polygloss-corpus` on Hugging Face).

Stdlib-only, deliberately independent of the `datasets` library so `convert.py`/`to_gold.py`/
`score.py` can be unit-tested offline without it installed. One row = one sentence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolyglossRow:
    """One example from the corpus. Field names match the HF dataset columns exactly."""

    id: str
    source: str
    transcription: str
    translation: str
    glottocode: str
    language: str
    metalanguage: str
    metalang_glottocode: str
    #: whitespace-separated per word, `-`/`=`-separated per morph within a word; may be missing
    #: (~93,648 rows in the full corpus lack it, per the paper's data-quality audit).
    segmentation: str | None = None
    #: same tokenization as `segmentation`; the two must have matching word/morph counts to convert.
    glosses: str | None = None

    @property
    def is_segmented(self) -> bool:
        return bool(self.segmentation and self.glosses)

    @classmethod
    def from_dict(cls, d: dict) -> "PolyglossRow":
        """Build from a raw HF row dict — tolerant of the exact key set varying by dataset version."""
        return cls(
            id=str(d.get("id", "")),
            source=str(d.get("source", "")),
            transcription=d.get("transcription") or "",
            translation=d.get("translation") or "",
            glottocode=d.get("glottocode") or "",
            language=d.get("language") or "",
            metalanguage=d.get("metalanguage") or "",
            metalang_glottocode=d.get("metalang_glottocode") or "",
            segmentation=d.get("segmentation"),
            glosses=d.get("glosses"),
        )
