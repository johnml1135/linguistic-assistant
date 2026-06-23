"""Appliers: turn the store's ACCEPTED deltas into something a backend can ingest.

Two paths, matching the recorded split:
  * **MiniLcm export** (offline, here): the accepted `lexical.*` ops → a MiniLcm-shaped lexicon JSON the
    Harmony/LexBox/FwLite lexicon can import (syncable, no FieldWorks). This is the lexicon tier.
  * **flexlibs / FLExTools** (Windows host): apply the same accepted ops into a real FLEx (LibLCM)
    project. Stubbed here — it needs FieldWorks + the `data-prep` extra — with the op→LibLCM mapping
    documented; package it as a FLExTools module for the Preview/Apply UI.

`morphophonology.*` ops stay in the git grammar deltas (the CRDT lexicon is lexicon-only).
Run: `python deltas/apply.py --pair spa` → writes `deltas/apply/<pair>.minilcm.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RESEARCH))

from propose.contract import ChangeSet  # noqa: E402

from review.deltas.store import DeltaStore  # noqa: E402

STORE_DIR = Path(__file__).resolve().parent / "store"
APPLY_DIR = Path(__file__).resolve().parent / "apply"


def to_minilcm(cs: ChangeSet) -> list[dict]:
    """Group accepted `lexical.*` ops into MiniLcm-shaped entries (lexemeForm + senses + partOfSpeech)."""
    entries: dict[str, dict] = {}

    def _entry(eid: str) -> dict:
        e = entries.get(eid)
        if e is None:
            # backfill lexemeForm from the id ("entry:<pair>:<form>") so a sense accepted without its
            # (lower-confidence) entry.create still carries its form.
            parts = eid.split(":", 2)
            lf = {parts[1]: parts[2]} if len(parts) == 3 and parts[0] == "entry" else {}
            e = entries[eid] = {"id": eid, "lexemeForm": lf, "partOfSpeech": None, "senses": []}
        return e

    for op in cs.ops:
        t = op.get("op")
        if t == "lexical.entry.create":
            e = _entry(op.get("entry") or json.dumps(op["lexeme_form"], sort_keys=True))
            e["lexemeForm"] = op["lexeme_form"]
        elif t == "lexical.sense.create":
            _entry(op["entry"])["senses"].append({"gloss": op["gloss"]})
        elif t == "lexical.entry.set_pos":
            _entry(op["entry"])["partOfSpeech"] = op["pos"]
        elif t == "lexical.pronunciation.create":
            _entry(op["entry"]).setdefault("pronunciations", []).append({"form": op["form"]})
        # morphophonology.* / bilingual.* are not lexicon-CRDT material → left for the grammar deltas
    return list(entries.values())


def export_minilcm(pair: str) -> dict:
    store = DeltaStore.load(STORE_DIR / f"{pair}.deltas.jsonl")
    store.route()  # ensure statuses are current
    cs = store.accepted_change_set()
    entries = to_minilcm(cs)
    APPLY_DIR.mkdir(parents=True, exist_ok=True)
    path = APPLY_DIR / f"{pair}.minilcm.json"
    path.write_text(json.dumps({"pair": pair, "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    grammar_ops = [op for op in cs.ops if str(op.get("op", "")).startswith("morphophonology.")]
    return {"pair": pair, "accepted_ops": len(cs.ops), "minilcm_entries": len(entries),
            "grammar_ops_for_git": len(grammar_ops), "path": str(path)}


def apply_via_flexlibs(cs: ChangeSet, project: str) -> None:  # pragma: no cover (Windows host only)
    """Apply accepted lexical ops into a real FLEx project. Windows + FieldWorks + `data-prep` extra.

    Mapping: lexical.entry.create → FLExProject.LexiconAddEntry; lexical.sense.create → AddSense + gloss;
    lexical.entry.set_pos → set the sense's MorphoSyntaxAnalysis POS. Package as a FLExTools module so
    edits run under its Preview/Report/Apply UI (undo-safe). Offline, use `export_minilcm` instead.
    """
    try:
        import flexlibs  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "flexlibs unavailable — run on Windows with FieldWorks + `uv sync --extra data-prep`. "
            "This is the apply-into-FLEx bridge; offline use export_minilcm()."
        ) from e
    raise NotImplementedError("flexlibs apply is the Windows host step (see module docstring + README).")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True)
    args = ap.parse_args(argv)
    s = export_minilcm(args.pair)
    print(f"[{args.pair}] MiniLcm export: {s['minilcm_entries']} entries from {s['accepted_ops']} accepted ops "
          f"({s['grammar_ops_for_git']} grammar ops kept as git deltas) -> {s['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
