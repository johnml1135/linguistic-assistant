"""Isolating-language detector — the "correctly find NOTHING" capability. An isolating language (vie) has
no inflectional morphology; the right report is "no paradigms here", and inventing case/gender/voice for it
is the failure mode.

The robust, tokenization-resistant signal is SYLLABLES PER WORD: Vietnamese words are ~1 syllable (97%
monosyllabic) where agglutinative/fusional words pack 2+ morphemes into 2+ syllables. This sidesteps the
inducer's over-segmentation (which wrongly makes vie look synthetic by inventing affixes).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

# vowel groups = syllable nuclei (Latin incl. Vietnamese diacritics + Cyrillic)
_VOWEL_RE = re.compile(r"[aeiouyăâêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
                       r"аеёиоуыэюяäöü]+", re.IGNORECASE)


def _syllables(word: str) -> int:
    return len(_VOWEL_RE.findall(word.lower()))


def syllable_stats(pair: str, *, sample: int = 400) -> dict:
    from induce.tdd import load_freqs
    top = [w for w, _ in load_freqs(pair).most_common(sample) if len(w) > 1]
    sy = [s for s in (_syllables(w) for w in top) if s > 0]
    if not sy:
        return {"mean_syllables": 0.0, "frac_monosyllabic": 0.0, "n": 0}
    return {"mean_syllables": round(sum(sy) / len(sy), 3),
            "frac_monosyllabic": round(sum(1 for s in sy if s == 1) / len(sy), 3), "n": len(sy)}


def is_isolating(pair: str, *, sample: int = 400) -> bool:
    """True when words are overwhelmingly monosyllabic — robust to the inducer's spurious affixes."""
    st = syllable_stats(pair, sample=sample)
    return st["n"] >= 50 and st["mean_syllables"] < 1.4 and st["frac_monosyllabic"] > 0.7


def detect_isolating(pair: str, *, sample: int = 400) -> tuple[bool, float, str, dict]:
    st = syllable_stats(pair, sample=sample)
    iso = is_isolating(pair, sample=sample)
    ev = (f"mean {st['mean_syllables']} syllables/word, {st['frac_monosyllabic']} monosyllabic"
          + (" → isolating (no inflectional morphology)" if iso else " → synthetic (words carry multiple morphemes)"))
    return iso, (0.85 if iso else 0.6), ev, st
