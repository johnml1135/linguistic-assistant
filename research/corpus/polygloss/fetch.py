"""Fetch PolyGloss corpus rows for a language and cache them locally.

`lecslab/polygloss-corpus` is gated on Hugging Face (login + accepting the dataset's access
agreement) — this needs a human to run `huggingface-cli login` and visit the dataset page once
before this will work. Not exercised by `tests_smoke.py` (network + auth); the conversion/scoring
layers are tested independently against a hand-built fixture row.
"""

from __future__ import annotations

import json
from pathlib import Path

DATASET_ID = "lecslab/polygloss-corpus"
# research/_sources/polygloss/ (git-ignored; regenerable), parallel to _sources/ebible/.
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "_sources" / "polygloss"


def fetch_language(glottocode: str, *, cache_dir: Path = DEFAULT_CACHE_DIR, split: str = "train",
                    force: bool = False) -> Path:
    """Pull every row for `glottocode` from `split` and cache as JSONL. Returns the cache path."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"{glottocode}.{split}.jsonl"
    if dest.exists() and not force:
        return dest
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise RuntimeError(
            "the `datasets` package is required (uv sync --extra polygloss). "
            "Also requires `huggingface-cli login` and accepting the corpus's access "
            f"agreement at https://huggingface.co/datasets/{DATASET_ID}."
        ) from e
    ds = load_dataset(DATASET_ID, split=split)
    rows = [r for r in ds if r.get("glottocode") == glottocode]
    with dest.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return dest


def load_cached(glottocode: str, *, cache_dir: Path = DEFAULT_CACHE_DIR, split: str = "train") -> list[dict]:
    path = cache_dir / f"{glottocode}.{split}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"{path} — run fetch_language({glottocode!r}) first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
