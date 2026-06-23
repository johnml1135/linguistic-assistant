"""Optional English word-vector similarity — a complementary MEANING signal for the allomorph detector.

Two morpheme forms are allomorph candidates only if they MEAN the same thing. String-identical English
alignments miss synonyms (`big`/`large`, `he`/`she`), so we compare each form's THOT-aligned English in a
moderate CPU word-vector space (GloVe via gensim — NO torch, matching the repo's light-deps philosophy).

ALWAYS OPTIONAL (like THOT / audio / the LLM): if gensim or the model is absent, `available` is False,
`meaning_vector` returns None, and the detector falls back to string/distribution overlap — same decisions,
just without the synonym bonus.

CAVEAT (why it is ONE check among several, never the sole arbiter): function words cluster tightly in
GloVe (of~the 0.90, to~for 0.90), so for grammatical morphemes vector similarity over-merges. The hard
gates stay complementary-distribution + phonological similarity + env-predicts-form.
"""

from __future__ import annotations

import numpy as np

DEFAULT_MODEL = "glove-wiki-gigaword-50"


class WordVectors:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model_name = model
        self.kv = None
        self.available = False
        self.reason = ""
        try:
            import gensim.downloader as api
            self.kv = api.load(model)            # cached after first download
            self.available = True
        except Exception as exc:                 # no gensim / no model / offline
            self.reason = str(exc)[:160]

    def vec(self, word: str):
        if not self.available:
            return None
        w = word.lower()
        return self.kv[w] if w in self.kv else None

    def similarity(self, a: str, b: str):
        if not self.available:
            return None
        va, vb = self.vec(a), self.vec(b)
        if va is None or vb is None:
            return None
        return float(self.kv.similarity(a.lower(), b.lower()))

    def meaning_vector(self, dist: dict):
        """A morpheme's MEANING embedding = its THOT English distribution as a probability-weighted mean of
        word vectors. `dist` is {english_word: prob}. Returns a unit vector, or None if no word is in vocab
        (or vectors unavailable)."""
        if not self.available or not dist:
            return None
        acc, total = None, 0.0
        for word, p in dist.items():
            v = self.vec(word)
            if v is not None and p > 0:
                acc = v * p if acc is None else acc + v * p
                total += p
        if acc is None or total == 0:
            return None
        acc = acc / total
        n = float(np.linalg.norm(acc))
        return acc / n if n > 0 else None


def cosine(a, b) -> float:
    if a is None or b is None:
        return 0.0
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


_VECTORS: WordVectors | None = None


def get_vectors(model: str = DEFAULT_MODEL) -> WordVectors:
    """Lazy singleton — load the model once per process."""
    global _VECTORS
    if _VECTORS is None or _VECTORS.model_name != model:
        _VECTORS = WordVectors(model)
    return _VECTORS
