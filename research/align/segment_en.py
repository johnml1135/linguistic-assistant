"""Pluggable English-side segmentation for the thot-on-morphs paradigm study (`thot-on-morphs.md` §4).

Three strategies, matching the paradigm ladder:
  identity  (P1, today's default) — no change, whole English words.
  bpe       (P2) — unsupervised, language-independent subword segmentation (Sennrich et al. 2016 BPE;
            the dependency-free stand-in for Morfessor, since this repo takes no torch/heavy-ML deps).
  guided    (P4) — Fraser (2009)'s guided-segmentation idea, simplified: only split an English word where
            the OTHER language's morphemes already give repeated cross-lingual evidence that the word is
            doing two jobs, reusing this repo's own root+residue statistics (`induce.tdd.affix_candidates`
            shape) instead of an independent English morphology model.
"""

from __future__ import annotations

from collections import Counter

_END = "▁"  # end-of-word marker; never occurs in eBible English text


# --------------------------------------------------------------------------- P1: identity
def identity_segment(tokens: list[str]) -> list[str]:
    return list(tokens)


# --------------------------------------------------------------------------- P2: unsupervised BPE
def learn_bpe(word_freqs: Counter, num_merges: int) -> list[tuple[str, str]]:
    """Classic BPE merge learning: repeatedly merge the most frequent adjacent symbol pair, starting from
    characters + an end-of-word marker. Stops early if no pair recurs (>=2 tokens) before `num_merges`."""
    vocab: dict[tuple[str, ...], int] = {tuple(w) + (_END,): f for w, f in word_freqs.items()}
    merges: list[tuple[str, str]] = []
    for _ in range(num_merges):
        pairs: Counter = Counter()
        for word, f in vocab.items():
            for a, b in zip(word, word[1:]):
                pairs[(a, b)] += f
        if not pairs:
            break
        best, count = pairs.most_common(1)[0]
        if count < 2:
            break
        merges.append(best)
        a, b = best
        merged = a + b
        new_vocab: dict[tuple[str, ...], int] = {}
        for word, f in vocab.items():
            out, i = [], 0
            while i < len(word):
                if i < len(word) - 1 and word[i] == a and word[i + 1] == b:
                    out.append(merged)
                    i += 2
                else:
                    out.append(word[i])
                    i += 1
            key = tuple(out)
            new_vocab[key] = new_vocab.get(key, 0) + f
        vocab = new_vocab
    return merges


def apply_bpe(word: str, merges: list[tuple[str, str]]) -> list[str]:
    """Apply learned merges IN LEARNED ORDER to segment one word into subword pieces (marker stripped)."""
    pieces = list(word) + [_END]
    for a, b in merges:
        merged = a + b
        out, i = [], 0
        while i < len(pieces):
            if i < len(pieces) - 1 and pieces[i] == a and pieces[i + 1] == b:
                out.append(merged)
                i += 2
            else:
                out.append(pieces[i])
                i += 1
        pieces = out
    if pieces and pieces[-1].endswith(_END):
        pieces[-1] = pieces[-1][: -len(_END)]
        if not pieces[-1]:
            pieces.pop()
    return pieces or [word]


def bpe_segment(tokens: list[str], merges: list[tuple[str, str]]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        out.extend(apply_bpe(t, merges))
    return out


# --------------------------------------------------------------------------- P4: guided split
def guided_split_map(en_freqs: Counter, rev_table, *, min_root: int = 3, max_res: int = 4,
                     min_evidence: int = 2) -> dict[str, tuple[str, str]]:
    """English word -> (base, residue) ONLY where cross-lingual evidence supports the split: `base` and
    the full word must each have a confident best-aligned target morph (via `rev_table`, an
    `align.contract.GlossTable` built with English as the "target" side and target-language morphemes as
    the "source" side — i.e. `align(morph_rows)` called with each row reversed, so `.best(english_word)`
    returns its best target-morph pivot), and those pivots must DIFFER — i.e. the English residue is doing
    a different translation job than the base, not just an English-internal coincidence (an English-side
    mirror of `induce.tdd.affix_candidates`'s residue logic, gated by real bilingual evidence instead of
    surface frequency alone)."""
    words = sorted({w for w, f in en_freqs.items() if f >= min_evidence}, key=len, reverse=True)
    wordset = set(words)
    out: dict[str, tuple[str, str]] = {}
    for w in words:
        for base_len in range(min_root, len(w)):
            base = w[:base_len]
            res = w[base_len:]
            if base not in wordset or not (1 <= len(res) <= max_res):
                continue
            b_best = rev_table.best(base)
            w_best = rev_table.best(w)
            if not (b_best and w_best):
                continue
            if b_best.source_word != w_best.source_word:  # different pivot = real evidence of 2 jobs
                out[w] = (base, res)
                break
    return out


def guided_segment(tokens: list[str], split_map: dict[str, tuple[str, str]]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        if t in split_map:
            out.extend(split_map[t])
        else:
            out.append(t)
    return out
