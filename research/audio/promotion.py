"""Phase 3/4 of the phonology-induction loop: human-gated pronunciation promotion + consistency checks.

This is the deliberately-last, deliberately-conservative tail of the loop:

- **Promotion (Phase 3, human-gated).** Stabilized pronunciation evidence is promoted to
  `lexical.pronunciation.create` change-set ops ONLY for candidates an analyst explicitly confirmed.
  Each op carries form (per writing system), rationale, confidence, and provenance, and is validated
  against the change-set contract. Unconfirmed candidates stay review-only evidence — no op is emitted.
- **Consistency checks (Phase 3 + Phase 4).** A Hermit-Crab-generated surface can be compared against a
  recorded pronunciation (Phase 3) or against observed phones (Phase 4). Disagreement is a *reviewable
  signal* pointing at the phoneme inventory / rules — never an automatic edit. The HC `generate`
  direction (producing the surface) needs `hc.exe`; the comparison/metric here is pure and offline.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field

from .features import map_phones_to_features


@dataclass(frozen=True)
class PronunciationConfirmation:
    """An analyst decision about one pronunciation candidate derived from phone evidence."""

    entry: str
    word: str
    form: str  # the phonetic/IPA pronunciation string
    writing_system: str  # BCP-47 tag for the form, e.g. "tur-fonipa"
    confirmed: bool
    confidence: float = 0.6
    refs: list[str] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ConsistencyFlag:
    """A reviewable disagreement signal. Never triggers an automatic grammar/lexicon change."""

    entry: str
    kind: str
    generated: str
    observed: str
    detail: str = ""
    review_only: bool = True


def promote_pronunciations(
    confirmations: list[PronunciationConfirmation],
    *,
    source: str = "allosaurus",
) -> list[dict[str, object]]:
    """Emit `lexical.pronunciation.create` ops for confirmed candidates only (human-gated).

    The returned ops validate against `research/proposal/change_set.py`. Unconfirmed candidates yield
    nothing — promotion never happens automatically from phone evidence.
    """
    ops: list[dict[str, object]] = []
    for c in confirmations:
        if not c.confirmed:
            continue
        provenance = {"source": source, "promotion": "human-confirmed", **c.provenance}
        if c.refs:
            provenance.setdefault("refs", ", ".join(c.refs))
        ops.append(
            {
                "op": "lexical.pronunciation.create",
                "entry": c.entry,
                "form": {c.writing_system: c.form},
                "rationale": f"Pronunciation for '{c.word}' confirmed by an analyst from phone evidence.",
                "confidence": c.confidence,
                "provenance": provenance,
            }
        )
    return ops


def validate_ops(ops: list[dict[str, object]]):
    """Validate emitted ops against the shared change-set contract (returns ChangeSet|ValidationFailure)."""
    from proposal.change_set import validate_change_set

    return validate_change_set(json.dumps({"ops": ops}, ensure_ascii=False))


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip().casefold()


def check_recorded_consistency(
    entry: str,
    generated_surface: str,
    recorded_pronunciation: str,
) -> ConsistencyFlag | None:
    """Flag a disagreement between the HC-generated surface and a recorded pronunciation (Phase 3)."""
    if _norm(generated_surface) == _norm(recorded_pronunciation):
        return None
    return ConsistencyFlag(
        entry=entry,
        kind="generated_vs_recorded_mismatch",
        generated=generated_surface,
        observed=recorded_pronunciation,
        detail="generated surface differs from the recorded pronunciation; check phonemes/rules",
    )


def _vowel_feature_seq(items: list[str]) -> list[tuple[str, str, str]]:
    return [(f["back"], f["round"], f["high"]) for f in map_phones_to_features(items)]


def feature_mismatch_count(generated_surface: str, observed_phones: list[str]) -> int:
    """Vowel-feature distance between a generated surface and observed phones (Phase 4 metric).

    Aligns the two vowel sequences positionally and counts feature-tuple disagreements, adding a
    length penalty for unaligned vowels. Consonants carry no harmony features and are ignored.
    """
    g = _vowel_feature_seq(list(generated_surface))
    p = _vowel_feature_seq(list(observed_phones))
    n = min(len(g), len(p))
    mismatches = sum(1 for i in range(n) if g[i] != p[i])
    return mismatches + abs(len(g) - len(p))


def compare_generated_to_phones(
    entry: str,
    generated_surface: str,
    observed_phones: list[str],
    *,
    threshold: int = 1,
) -> ConsistencyFlag | None:
    """Flag a generated-surface vs observed-phones disagreement above ``threshold`` (Phase 4 gate).

    Review-only: a mismatch points at the phoneme inventory / rules; it never mutates the grammar.
    """
    distance = feature_mismatch_count(generated_surface, observed_phones)
    if distance <= threshold:
        return None
    return ConsistencyFlag(
        entry=entry,
        kind="generated_vs_phones_mismatch",
        generated=generated_surface,
        observed=" ".join(observed_phones),
        detail=f"vowel-feature distance {distance} > threshold {threshold}; check phonemes/rules",
    )
