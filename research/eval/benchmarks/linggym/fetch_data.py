"""Fetch and pin the LingGym benchmark data into a local (gitignored) cache.

Clones https://github.com/changbingY/LingGym at a pinned commit so runs are reproducible.
Prints the path to pass as ``--root`` to ``run.py``.

    python benchmarks/linggym/fetch_data.py
    python benchmarks/linggym/run.py --endpoint ik_llama --root <printed_path>

License: the LingGym data is CC-BY-4.0 (Yang et al., EMNLP 2025) — attribute on use.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/changbingY/LingGym.git"
# main @ 2026-06-16; update deliberately and record changes in the run summary.
PINNED_COMMIT = "ce6059b47c8839ac3de1b976a858cfbfc6daa6c9"
CACHE = Path(__file__).resolve().parent / ".cache" / "LingGym"


def _run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> int:
    if (CACHE / ".git").exists():
        _run("git", "-C", str(CACHE), "fetch", "--depth", "1", "origin", PINNED_COMMIT)
        _run("git", "-C", str(CACHE), "checkout", PINNED_COMMIT)
    else:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        # Shallow clone of default branch; main currently == PINNED_COMMIT.
        _run("git", "clone", "--depth", "1", REPO, str(CACHE))

    head = subprocess.run(
        ["git", "-C", str(CACHE), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    bench = CACHE / "Benchmark_multiple_choice"
    n_files = len(list(bench.rglob("*_questions.txt"))) if bench.exists() else 0
    print(f"HEAD:   {head}")
    if head != PINNED_COMMIT:
        print(f"WARNING: HEAD != pinned commit {PINNED_COMMIT}", file=sys.stderr)
    print(f"data:   {bench}  ({n_files} question files)")
    print(f"\nrun:    python benchmarks/linggym/run.py --endpoint ik_llama --root {bench}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
