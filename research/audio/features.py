"""Phase 2 of the phonology-induction loop: ground harmony conditioning in phone evidence.

Optional and review-only. Allosaurus emits *universal* phones, not language phonemes, so everything
here is a provenance-bearing hypothesis: a phone→feature mapping that can confirm or refute a harmony
family's hypothesized conditioning feature, and a triangulation summary that combines orthography,
distribution (computed by the cycle), and — when present — phones. It never edits the grammar, the
lexicon, or Hermit Crab features (the `pronunciation` primitive boundary, and the audio add-on's own
"evidence, not parser input" rule).

This module takes the distribution facts (collapsibility, conditioning class) as plain data so the
audio add-on stays decoupled from `research/cycle/`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Harmony-relevant vowels → distinctive features (review-only). The current targets are Latin-script
# five-vowel systems (Swahili / Indonesian / Tagalog) plus Spanish (accented vowels); the IPA rows
# cover what Allosaurus is likely to emit. Swahili height harmony keys on `high`; backness/rounding
# remain available for the other targets. Consonants are intentionally absent (no harmony role).
_VOWEL_FEATURES: dict[str, dict[str, str]] = {
    # five-vowel orthography
    "a": {"back": "+", "round": "-", "high": "-"},
    "e": {"back": "-", "round": "-", "high": "-"},
    "i": {"back": "-", "round": "-", "high": "+"},
    "o": {"back": "+", "round": "+", "high": "-"},
    "u": {"back": "+", "round": "+", "high": "+"},
    # Spanish accented vowels (same features as their base vowel)
    "á": {"back": "+", "round": "-", "high": "-"},
    "é": {"back": "-", "round": "-", "high": "-"},
    "í": {"back": "-", "round": "-", "high": "+"},
    "ó": {"back": "+", "round": "+", "high": "-"},
    "ú": {"back": "+", "round": "+", "high": "+"},
    # common IPA realizations Allosaurus may output
    "ɑ": {"back": "+", "round": "-", "high": "-"},
    "ɛ": {"back": "-", "round": "-", "high": "-"},
    "ɔ": {"back": "+", "round": "+", "high": "-"},
    "ɪ": {"back": "-", "round": "-", "high": "+"},
    "ʊ": {"back": "+", "round": "+", "high": "+"},
}


@dataclass(frozen=True)
class FeatureConfirmation:
    """Whether phone evidence confirms a harmony family's hypothesized conditioning feature."""

    members: list[str]
    feature: str
    status: str  # "confirmed" | "conflict" | "insufficient"
    supporting_phones: list[str] = field(default_factory=list)
    conflicting_members: list[str] = field(default_factory=list)
    note: str = ""
    provenance: dict[str, str] = field(default_factory=lambda: {"backend": "allosaurus", "review_only": "true"})


@dataclass(frozen=True)
class TriangulationSummary:
    """Agreement among orthography, distribution, and (optional) phone witnesses for one family."""

    members: list[str]
    conditioning_class: str | None
    distribution_collapsible: bool
    audio_status: str  # "absent" | "confirmed" | "conflict" | "insufficient"
    agreement: str  # "distribution_only" | "agree" | "conflict"


def map_phones_to_features(phones: list[str]) -> list[dict[str, str]]:
    """Map recognized vowel phones to distinctive features (review-only). Unknown phones are skipped."""
    out: list[dict[str, str]] = []
    for phone in phones:
        feats = _VOWEL_FEATURES.get(phone)
        if feats is not None:
            out.append({"phone": phone, **feats})
    return out


def confirm_conditioning(
    members: list[str],
    phones_by_member: dict[str, list[str]],
    feature: str,
) -> FeatureConfirmation:
    """Confirm/refute that ``feature`` conditions a harmony family, from per-member phone evidence.

    For each member, the last orthographic harmony vowel sets the expected feature value; the member's
    phone evidence must contain a vowel phone with that value. Any contradiction is a conflict; no usable
    phone evidence is insufficient. Never authoritative — always a review-only hypothesis.
    """
    supporting: list[str] = []
    conflicting: list[str] = []
    saw_phone_vowel = False

    for member in members:
        ortho_vowels = [c for c in member if c in _VOWEL_FEATURES]
        if not ortho_vowels:
            continue
        expected = _VOWEL_FEATURES[ortho_vowels[-1]][feature]
        phone_values = {
            (_VOWEL_FEATURES[p][feature], p)
            for p in phones_by_member.get(member, [])
            if p in _VOWEL_FEATURES
        }
        if not phone_values:
            continue
        saw_phone_vowel = True
        values = {value for value, _ in phone_values}
        if expected in values and len(values) == 1:
            supporting.extend(p for value, p in phone_values if value == expected)
        else:
            conflicting.append(member)

    if conflicting:
        return FeatureConfirmation(
            sorted(set(members)), feature, "conflict", supporting, sorted(set(conflicting)),
            note="phone evidence contradicts the hypothesized conditioning feature",
        )
    if not saw_phone_vowel:
        return FeatureConfirmation(
            sorted(set(members)), feature, "insufficient", [], [],
            note="no usable phone vowels for this family",
        )
    return FeatureConfirmation(
        sorted(set(members)), feature, "confirmed", sorted(set(supporting)), [],
        note="phone evidence aligns with the hypothesized conditioning feature",
    )


def triangulate_family(
    members: list[str],
    conditioning_class: str | None,
    distribution_collapsible: bool,
    confirmation: FeatureConfirmation | None = None,
) -> TriangulationSummary:
    """Combine orthography + distribution + optional phones into one agreement summary.

    Degrades gracefully: with no ``confirmation`` (no audio) it still reports a distribution-only
    summary; with phones present it reports agreement or flags a conflict.
    """
    audio_status = confirmation.status if confirmation is not None else "absent"
    if confirmation is None or audio_status in ("absent", "insufficient"):
        agreement = "distribution_only"
    elif audio_status == "confirmed" and distribution_collapsible:
        agreement = "agree"
    else:
        agreement = "conflict"
    return TriangulationSummary(
        members=sorted(set(members)),
        conditioning_class=conditioning_class,
        distribution_collapsible=distribution_collapsible,
        audio_status=audio_status,
        agreement=agreement,
    )
