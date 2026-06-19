"""Coarse part-of-speech for a root, inferred from its English gloss (offline, no NLTK).

The cycle's roots are glossed with an English word from the statistical alignment; English POS is a
usable *proxy* for the target root's category (a target word glossed "walk" is almost always a verb).
Closed-class words are tagged from curated sets (high confidence); open-class content words fall back to
noun unless they're in the common-verb / common-adjective sets. This is deliberately coarse — it adds
the POS dimension to the lexicon and lets affix MSAs attach to a category; the golden gate keeps the
POS-aware grammar only if it doesn't cost coverage. See linguistics/skills/assign-pos-and-msa.md.
"""

from __future__ import annotations

# Closed classes (high confidence).
_DET = {"the", "a", "an", "this", "that", "these", "those", "every", "each", "all", "some", "any", "no"}
_PRON = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "who", "whom",
         "whose", "which", "what", "myself", "himself", "herself", "themselves", "yourself", "ourselves",
         "my", "your", "his", "its", "our", "their", "mine", "yours", "hers", "ours", "theirs", "one"}
_PREP = {"in", "on", "at", "to", "from", "of", "for", "with", "without", "by", "about", "against",
         "between", "among", "through", "into", "onto", "upon", "over", "under", "above", "below",
         "before", "after", "behind", "beside", "within", "toward", "towards", "until", "unto", "out"}
_CONJ = {"and", "or", "but", "if", "because", "although", "though", "while", "whereas", "nor", "yet",
         "so", "than", "as", "whether", "since", "unless"}
_AUX = {"be", "is", "am", "are", "was", "were", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "shall", "should", "may", "might", "must", "can", "could", "let"}
_NEG = {"not", "no", "never", "nor"}
_NUM = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "hundred",
        "thousand", "first", "second", "third", "many", "few", "much"}

# Common open-class verbs (NT-frequent) — content words that default to noun otherwise.
_VERB = {
    "say", "said", "speak", "tell", "go", "come", "came", "went", "see", "saw", "know", "knew", "give",
    "gave", "make", "made", "take", "took", "find", "found", "think", "thought", "believe", "love",
    "hate", "hear", "heard", "send", "sent", "bring", "brought", "ask", "answer", "call", "called",
    "follow", "live", "die", "died", "rise", "raise", "eat", "drink", "walk", "run", "stand", "sit",
    "fall", "fell", "write", "read", "keep", "kept", "leave", "left", "receive", "save", "judge",
    "forgive", "pray", "preach", "teach", "taught", "heal", "baptize", "worship", "serve", "obey",
    "sin", "repent", "fear", "rejoice", "weep", "cry", "seek", "fulfill", "destroy", "build", "open",
    "shut", "lead", "led", "carry", "throw", "cast", "touch", "wash", "feed", "bear", "born", "do",
    "be", "become", "began", "begin", "abide", "remain", "dwell", "glorify", "bless", "curse", "deny",
    "betray", "crucify", "suffer", "command", "promise", "gather", "scatter", "return", "depart",
    "enter", "bow", "kneel", "lift", "fill", "pour", "break", "bind", "loose", "deliver", "tempt",
}
# Common adjectives.
_ADJ = {"good", "great", "evil", "holy", "righteous", "wicked", "true", "false", "new", "old", "first",
        "last", "high", "low", "great", "small", "little", "big", "strong", "weak", "rich", "poor",
        "wise", "foolish", "clean", "unclean", "pure", "blessed", "faithful", "eternal", "living",
        "dead", "blind", "deaf", "lame", "sick", "whole", "right", "left", "full", "empty", "many",
        "few", "own", "such", "same", "other", "own", "able", "worthy", "glad", "afraid", "ready"}


def _head(gloss: str) -> str:
    """The classifying token: last alphabetic word of a possibly multi-word gloss (English is right-headed)."""
    toks = [t for t in gloss.lower().replace("-", " ").split() if t.isalpha()]
    return toks[-1] if toks else ""


def pos_of(gloss: str) -> str:
    """Coarse POS id for a root gloss: noun|verb|adj|adv|pron|prep|conj|det|num|ptcl, default noun."""
    g = _head(gloss)
    if not g:
        return "noun"  # "?" / empty / punctuation-only → default content category
    if g in _DET:
        return "det"
    if g in _PRON:
        return "pron"
    if g in _PREP:
        return "prep"
    if g in _CONJ:
        return "conj"
    if g in _NUM:
        return "num"
    if g in _AUX or g in _VERB:
        return "verb"
    if g in _ADJ:
        return "adj"
    if g in _NEG:
        return "ptcl"
    if g.endswith("ly") and len(g) > 3:
        return "adv"
    return "noun"
