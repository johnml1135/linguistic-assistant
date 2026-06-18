"""Download eBible source files (vref + verse-per-line texts) — stdlib urllib, idempotent."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from .config import CORPUS_URL, VREF_URL

DEFAULT_SRC_DIR = Path("research/golden/_sources/ebible")


def _download(url: str, dest: Path, *, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force and dest.stat().st_size > 0:
        return dest  # idempotent
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (trusted raw.githubusercontent.com)
        dest.write_bytes(r.read())
    return dest


def fetch_vref(src_dir: Path = DEFAULT_SRC_DIR, *, force: bool = False) -> Path:
    return _download(VREF_URL, src_dir / "vref.txt", force=force)


def fetch_text(corpus_id: str, src_dir: Path = DEFAULT_SRC_DIR, *, force: bool = False) -> Path:
    return _download(CORPUS_URL.format(id=corpus_id), src_dir / f"{corpus_id}.txt", force=force)
