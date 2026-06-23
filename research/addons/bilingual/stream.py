"""Apertium stream format: parse/render `^surface/lemma<tag>…$` tokens, plus the HC->stream adapter.

The stream format is the seam that lets Hermit Crab analyses of the vernacular participate in the
bidix world without a second vernacular morphology. Stdlib-only, deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .crosswalk import Crosswalk

_TOKEN_RE = re.compile(r"\^(.*?)\$")
_TAG_RE = re.compile(r"<([^>]+)>")


@dataclass(frozen=True)
class Analysis:
    lemma: str
    tags: tuple[str, ...]


@dataclass
class Token:
    surface: str
    analyses: list[Analysis]  # >=1; multiple = morphological ambiguity


def _parse_analysis(blob: str) -> Analysis:
    tags = tuple(_TAG_RE.findall(blob))
    lemma = blob.split("<", 1)[0]
    return Analysis(lemma=lemma, tags=tags)


def parse_stream(text: str) -> list[Token]:
    """Parse an Apertium stream into Tokens. Text outside ^...$ is ignored (whitespace/superblanks)."""
    tokens: list[Token] = []
    for body in _TOKEN_RE.findall(text):
        parts = body.split("/")
        surface = parts[0]
        analyses = [_parse_analysis(p) for p in parts[1:]] or [Analysis(lemma=surface, tags=())]
        tokens.append(Token(surface=surface, analyses=analyses))
    return tokens


def render_analysis(a: Analysis) -> str:
    return a.lemma + "".join(f"<{t}>" for t in a.tags)


def render_token(tok: Token) -> str:
    return "^" + tok.surface + "".join("/" + render_analysis(a) for a in tok.analyses) + "$"


def render_stream(tokens: list[Token]) -> str:
    return " ".join(render_token(t) for t in tokens)


def hc_analysis_to_token(
    surface: str, lemma: str, project_tags: list[str], crosswalk: Crosswalk
) -> tuple[Token, list[str]]:
    """Render one Hermit Crab analysis as an Apertium stream Token.

    ``project_tags`` are the HC-side POS/feature labels (e.g. ["Noun", "pl"]). Returns the Token plus
    any tags the crosswalk couldn't map (reported, not dropped).
    """
    apertium_tags, unmapped = crosswalk.to_apertium(project_tags)
    return Token(surface=surface, analyses=[Analysis(lemma=lemma, tags=tuple(apertium_tags))]), unmapped
