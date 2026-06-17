"""Parse LingGym's released ``*_questions.txt`` files into structured items.

Block format (verified against the repo, commit ce6059b):

    Question N:
    You are a linguist specializing in <Language>. ...        # framing
    Sentence (with missing item): ...                          # S
    Gloss (with missing item): ...                             # G
    The English translation of this sentence is: ...           # T
    Here is a relevant knowledge point ...: ...                # KP
    A: word: ...    gloss: ...
    B: word: ...    gloss: ...
    C: word: ...    gloss: ...
    D: word: ...    gloss: ...
    Please only return the letter (A-D). Do not say anything else.
    Correct Answer: B

The official eval script concatenates the 10 lines after the ``Question`` line as the
prompt (the full S+G+KP+T condition) and reads the next line as the answer. We reproduce
that verbatim in ``prompt_full`` and also parse the components so lower info levels can
be reconstructed (see ``prompt.py``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# The 18 reference-grammar languages, per the released eval script.
KNOWN_LANGUAGES = {
    "Fwe", "Gyeli", "Ik", "Japhug", "Kagayanen", "Kalamang", "Komnzo",
    "Mauwake", "Mehweb", "Moloko", "Palula", "Papuan_Malay", "Pichi",
    "Rapa_Nui", "Tuatschin", "Ulwa", "Vamale", "Yauyos_Quecha",
}

_QLINE = re.compile(r"^Question\s+(\d+)\s*:")
_ANS = re.compile(r"Correct Answer:\s*([A-Da-d])")
_SPECIALIZING = re.compile(r"specializing in ([A-Za-z_ ]+?)[\.\n]")


@dataclass
class LingGymItem:
    qid: str
    language: str
    source_file: str
    prompt_full: str  # verbatim 10-line prompt = the released S+G+KP+T condition
    gold: str  # 'A'..'D'
    framing: str = ""
    sentence: str = ""
    gloss: str = ""
    translation: str = ""
    knowledge_point: str = ""
    options: dict = field(default_factory=dict)


def _after(line: str, prefix: str) -> str:
    s = line.rstrip("\n")
    return s[len(prefix):].strip() if s.startswith(prefix) else s.strip()


def _language_for(path: Path, framing: str) -> str:
    for part in path.parts:
        if part in KNOWN_LANGUAGES:
            return part
    m = _SPECIALIZING.search(framing)
    return m.group(1).strip().replace(" ", "_") if m else "unknown"


def parse_file(path: str | Path) -> list[LingGymItem]:
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    items: list[LingGymItem] = []
    for i, line in enumerate(lines):
        m = _QLINE.match(line)
        if not m:
            continue
        block = lines[i + 1: i + 11]
        if len(block) < 10:
            continue  # malformed / truncated block
        ans_line = lines[i + 11] if i + 11 < len(lines) else ""
        am = _ANS.search(ans_line)
        if not am:
            continue  # no gold answer — skip
        framing = block[0]
        items.append(
            LingGymItem(
                qid=f"{path.parent.name}/{path.stem}#{m.group(1)}",
                language=_language_for(path, framing),
                source_file=str(path),
                prompt_full="".join(block),
                gold=am.group(1).upper(),
                framing=framing.strip(),
                sentence=_after(block[1], "Sentence (with missing item):"),
                gloss=_after(block[2], "Gloss (with missing item):"),
                translation=_after(block[3], "The English translation of this sentence is:"),
                knowledge_point=_after(
                    block[4],
                    "Here is a relevant knowledge point for this example, with the "
                    "related morphemes and glosses masked:",
                ),
                options={
                    "A": block[5].strip(),
                    "B": block[6].strip(),
                    "C": block[7].strip(),
                    "D": block[8].strip(),
                },
            )
        )
    return items


def load_items(
    root: str | Path,
    *,
    languages: set[str] | None = None,
    limit: int | None = None,
) -> list[LingGymItem]:
    """Load all items under ``root`` (recursively over ``*_questions.txt``)."""
    root = Path(root)
    files = sorted(root.rglob("*_questions.txt"))
    out: list[LingGymItem] = []
    for f in files:
        for it in parse_file(f):
            if languages and it.language not in languages:
                continue
            out.append(it)
            if limit and len(out) >= limit:
                return out
    return out
